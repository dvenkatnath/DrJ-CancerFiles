"""
The document -> structured-wiki-JSON pipeline:

  uploaded -> extracting -> summarized -> pending_review -> curated

Text extraction and chunking are synchronous/local (no LLM). The "summarized"
step is where the LLM gateway is called (schema-constrained JSON extraction),
with a fully deterministic rule-based mock (`_mock_extract`) standing in when
LLM_MODE=mock or the gateway is unreachable, per the "runs end-to-end without
the LLM" requirement.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.curation import Curation, CurationPriority, CurationStatus
from app.models.document import DateConfidence, Document, DocumentChunk, DocumentStatus
from app.models.wiki import WikiSectionType
from app.services.classify import classify_doc_type, guess_date
from app.services.llm_gateway import get_gateway

logger = logging.getLogger("ingestion")
settings = get_settings()

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150

SECTION_TYPES = [t.value for t in WikiSectionType if t != WikiSectionType.at_a_glance]

# Canonical lab marker names the Lab Trends panel (app/services/trends.py)
# groups on. Chosen to match the marker panel the earlier single-patient
# dashboard prototype charted (site/assets/*_charts/*.png) so re-ingesting
# the same real documents through this generic pipeline reproduces the same
# trend lines. Anything not in this list still gets extracted as a normal
# lab_highlights fact -- it just won't get trend-charted.
LAB_MARKER_ALIASES: dict[str, str] = {
    "ca125": "CA125", "ca-125": "CA125", "ca 125": "CA125",
    "ca19-9": "CA19-9", "ca 19-9": "CA19-9", "ca19.9": "CA19-9", "ca 19.9": "CA19-9",
    "cea": "CEA",
    "creatinine": "Creatinine", "creat": "Creatinine", "s. creatinine": "Creatinine",
    "hemoglobin": "Hemoglobin", "haemoglobin": "Hemoglobin", "hb": "Hemoglobin",
    "platelet": "Platelet", "platelets": "Platelet", "plt": "Platelet", "platelet count": "Platelet",
    "sgot": "SGOT/AST", "ast": "SGOT/AST", "sgot/ast": "SGOT/AST", "sgot (ast)": "SGOT/AST",
    "sgpt": "SGPT/ALT", "alt": "SGPT/ALT", "sgpt/alt": "SGPT/ALT", "sgpt (alt)": "SGPT/ALT",
    "total bilirubin": "Total Bilirubin", "bilirubin": "Total Bilirubin", "bilirubin total": "Total Bilirubin",
    "wbc": "WBC", "wbc count": "WBC", "total wbc count": "WBC",
}


def normalize_lab_marker(raw_name: str) -> str | None:
    """Maps a lab test name as it appears on a real report (which varies a lot
    across labs -- "CA 125" vs "CA-125" vs "Ca125") to one canonical marker
    name, so results for the same test from different documents land in the
    same trend series. Returns None for anything not in LAB_MARKER_ALIASES --
    the fact is still kept, just without test/value/unit (so no trend chart)."""
    key = re.sub(r"\s+", " ", raw_name.strip().lower())
    if key in LAB_MARKER_ALIASES:
        return LAB_MARKER_ALIASES[key]
    compact = re.sub(r"[\s\-/.]", "", key)
    return LAB_MARKER_ALIASES.get(compact)


EXTRACTION_SYSTEM_PROMPT = f"""You are a clinical data extraction assistant. You will be given the
text of ONE patient document (already OCR'd/extracted, so it may contain noise) and its detected
document type. Extract discrete clinical facts and file each one under exactly one of these
section types: {", ".join(SECTION_TYPES)}.

Rules:
- Only extract facts explicitly supported by the text. Never infer or invent values.
- Each fact needs a `confidence` from 0.0-1.0 reflecting how clearly the text supports it.
- Keep each fact to one concise clinical statement (e.g. "CA-125 240.3 U/mL on 2021-06-30",
  not a whole paragraph).
- If nothing in the text supports a given section, omit that key entirely.
- For a "lab_highlights" fact that reports ONE specific numeric lab result (not a narrative
  mention), ALSO include "test", "value", and "unit" so it can be trend-charted over time:
    "test": the canonical marker name -- use exactly one of {sorted(set(LAB_MARKER_ALIASES.values()))}
             if the test is one of these (matching by meaning, not spelling); otherwise omit "test".
    "value": the numeric result as a JSON number, not a string.
    "unit": the unit exactly as written on the report (e.g. "U/mL", "g/dL").
  Omit test/value/unit entirely for any fact that isn't a single specific numeric lab result, or
  whose test isn't in that list.

Respond with ONLY a JSON object of exactly this shape, nothing else:
{{"sections": {{"<section_type>": [{{"text": "...", "confidence": 0.0, "test": "...", "value": 0.0, "unit": "..."}}, ...]}}}}
(test/value/unit are optional per-fact, as described above.)
"""


def extract_text_from_file(path: Path, mime_type: str) -> tuple[str, bool, int | None]:
    """Returns (text, ocr_used, page_count). Never raises -- extraction failures
    come back as an empty string so the pipeline can flag the document instead
    of crashing the whole upload."""
    try:
        if mime_type == "text/plain" or path.suffix.lower() in (".txt", ".md"):
            return path.read_text(errors="ignore"), False, None

        if path.suffix.lower() == ".docx":
            from docx import Document as DocxDocument

            doc = DocxDocument(str(path))
            text = "\n".join(p.text for p in doc.paragraphs)
            return text, False, None

        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join(pages)
            ocr_used = len(text.strip()) < 40 * max(1, len(pages))
            if ocr_used:
                ocr_text = _try_ocr_pdf(path)
                if ocr_text:
                    text = ocr_text
            return text, ocr_used, len(reader.pages)

        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            ocr_text = _try_ocr_image(path)
            return ocr_text, True, 1

        return "", False, None
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("text extraction failed for %s", path)
        return "", False, None


def _try_ocr_pdf(path: Path) -> str:
    """Best-effort OCR hook. Requires pdf2image+pytesseract+poppler/tesseract to
    be installed on the machine actually running the backend (the on-prem
    client server or the Mac Mini) -- optional dependencies, so this degrades
    to '' (flagged for manual review) rather than failing the whole upload
    when they're absent."""
    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(str(path), dpi=200)
        return "\n\n".join(pytesseract.image_to_string(img) for img in images)
    except Exception:
        logger.info("OCR hook unavailable/failed for %s -- flagging for manual review", path)
        return ""


def _try_ocr_image(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(path))
    except Exception:
        logger.info("OCR hook unavailable/failed for %s -- flagging for manual review", path)
        return ""


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def run_type_and_date_detection(document: Document) -> None:
    sample = (document.filename + " " + (document.extracted_text or "")[:2000])
    document.doc_type = classify_doc_type(sample)
    d, conf = guess_date(document.filename, document.extracted_text or "")
    document.doc_date = d
    document.doc_date_confidence = DateConfidence(conf)


async def embed_chunks(db: Session, document: Document, texts: list[str]) -> None:
    if not texts:
        return
    gateway = get_gateway()
    vectors = await gateway.embed(texts)
    for i, (t, v) in enumerate(zip(texts, vectors)):
        db.add(
            DocumentChunk(
                document_id=document.id,
                patient_id=document.patient_id,
                chunk_index=i,
                text=t,
                embedding=v,
            )
        )


def _mock_extract(doc_type: str, text: str) -> dict:
    """Deterministic rule-based stand-in for the LLM extraction step, used
    whenever the gateway is mocked/unreachable so the whole pipeline -- upload
    through curation -- works with zero LLM configured."""
    _raw_excerpt = " ".join(text.split())[:220]
    excerpt = (_raw_excerpt.rsplit(" ", 1)[0] + "…" if len(_raw_excerpt) == 220 else _raw_excerpt) or "(no extractable text)"
    sections: dict[str, list[dict]] = {}

    if "Lab" in doc_type:
        # Only match actual tabular lab rows ("CA-125   22.4   U/mL   0-35"):
        # name, then a real gap, a numeric value, and a recognized unit. This
        # deliberately will NOT match incidental "Word: number" text elsewhere
        # in the document (a DOB, a list number, a grade) -- those aren't lab
        # results and previously leaked through a looser pattern.
        LAB_UNITS = r"(?:U/mL|mg/dL|g/dL|ng/mL|/uL(?:\s*x10\^3)?|%|U/L|mEq/L|mg/L)"
        facts = []
        for line in text.splitlines():
            m = re.match(
                rf"\s*([A-Za-z][A-Za-z0-9\-/. ]{{1,24}}?)\s{{2,}}(\d{{1,5}}(?:\.\d+)?)\s+({LAB_UNITS})\b", line
            )
            if m:
                name, value_str, unit = m.group(1).strip(), m.group(2), m.group(3)
                fact: dict = {"text": f"{name}: {value_str} {unit}", "confidence": 0.6}
                canonical = normalize_lab_marker(name)
                if canonical:
                    fact["test"] = canonical
                    fact["value"] = float(value_str)
                    fact["unit"] = unit
                facts.append(fact)
        sections["lab_highlights"] = facts[:8] or [{"text": f"Lab result on file (excerpt): {excerpt}", "confidence": 0.3}]
    elif doc_type == "Prescription" or doc_type == "Treatment Note":
        sections["medications"] = [{"text": f"Medication/treatment note (excerpt): {excerpt}", "confidence": 0.4}]
    elif doc_type in ("Discharge Summary", "Case Summary/Advice Note"):
        sections["visit_timeline"] = [{"text": f"{doc_type} (excerpt): {excerpt}", "confidence": 0.4}]
        sections["care_plan"] = [{"text": f"Plan mentioned in {doc_type.lower()} (excerpt): {excerpt}", "confidence": 0.3}]
    elif doc_type in ("Imaging", "Pathology/Biopsy", "Genomic/Molecular"):
        sections["problem_list"] = [{"text": f"{doc_type} finding (excerpt): {excerpt}", "confidence": 0.35}]
    else:
        sections["notes"] = [{"text": f"Unclassified document (excerpt): {excerpt}", "confidence": 0.2}]

    if re.search(r"\ballerg", text, re.I):
        m = re.search(r"allerg[a-z]*\W{0,5}(.{0,80})", text, re.I)
        sections.setdefault("allergies", []).append(
            {"text": f"Possible allergy mention: {(m.group(1) if m else excerpt).strip()}", "confidence": 0.3}
        )

    return {"sections": sections}


async def extract_wiki_proposals(document: Document) -> dict:
    gateway = get_gateway()
    text_for_model = (document.extracted_text or "")[: settings.llm_context_tokens * 3]  # ~chars per token heuristic
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Document type (auto-detected): {document.doc_type}\n\nDocument text:\n{text_for_model}",
        },
    ]
    result = await gateway.chat_json(
        messages,
        model=settings.extraction_model,
        mock_fn=lambda _msgs: _mock_extract(document.doc_type or "Other/Unclassified", document.extracted_text or ""),
    )
    if not isinstance(result, dict) or "sections" not in result:
        result = _mock_extract(document.doc_type or "Other/Unclassified", document.extracted_text or "")
    return result


def build_proposed_changes(document: Document, extraction: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    # The clinical event date (when this happened), not `last_updated` (when
    # this row was extracted) -- carried on every fact so both the visit
    # timeline and the Lab Trends panel can sort/plot by when it actually
    # occurred rather than when the document was ingested.
    event_date = document.doc_date.isoformat() if document.doc_date else None
    proposed: dict[str, dict] = {}
    for section_type, facts in (extraction.get("sections") or {}).items():
        if section_type not in SECTION_TYPES or not facts:
            continue
        additions = []
        for f in facts:
            if not f.get("text"):
                continue
            fact = {
                "id": str(uuid.uuid4()),
                "text": f["text"],
                "confidence": float(f.get("confidence", 0.5)),
                "status": "unreviewed",
                "last_updated": now,
                "event_date": event_date,
                "sources": [
                    {
                        "document_id": str(document.id),
                        "document_name": document.filename,
                        "page": None,
                        "section_label": document.doc_type,
                    }
                ],
            }
            # Structured lab fields, when the extractor (mock or LLM) provided
            # them -- see normalize_lab_marker / EXTRACTION_SYSTEM_PROMPT.
            # Trusted only when the model actually returned a real number;
            # a malformed/hallucinated value here would otherwise silently
            # corrupt the trend series it feeds.
            test, value, unit = f.get("test"), f.get("value"), f.get("unit")
            if test and isinstance(value, (int, float)) and not isinstance(value, bool):
                fact["test"] = str(test)
                fact["value"] = float(value)
                if unit:
                    fact["unit"] = str(unit)
            additions.append(fact)
        if additions:
            proposed[section_type] = {"additions": additions, "modifications": [], "deletions": []}
    return proposed


async def run_ingestion_pipeline(db: Session, document_id: uuid.UUID) -> None:
    """The full pipeline for one document. Designed to be handed to
    BackgroundTasks so the upload endpoint returns immediately; a production
    deployment with heavier volume would swap this for a real task queue
    (Celery/RQ) without changing anything upstream."""
    document = db.get(Document, document_id)
    if document is None:
        return

    try:
        document.status = DocumentStatus.extracting
        db.commit()

        path = Path(document.storage_path)
        text, ocr_used, page_count = extract_text_from_file(path, document.mime_type)
        document.extracted_text = text
        document.ocr_used = ocr_used
        document.page_count = page_count
        run_type_and_date_detection(document)

        if not text.strip():
            document.status = DocumentStatus.error
            document.error_message = (
                "No text could be extracted (scanned image/PDF with no OCR available, or an "
                "unsupported file). Needs manual review."
            )
            db.commit()
            return

        chunks = chunk_text(text)
        await embed_chunks(db, document, chunks)

        document.status = DocumentStatus.summarized
        db.commit()

        extraction = await extract_wiki_proposals(document)
        proposed_changes = build_proposed_changes(document, extraction)

        if proposed_changes:
            curation = Curation(
                document_id=document.id,
                patient_id=document.patient_id,
                status=CurationStatus.pending,
                priority=CurationPriority.normal,
                proposed_changes=proposed_changes,
            )
            db.add(curation)
            document.status = DocumentStatus.pending_review
        else:
            # Nothing extractable into the wiki (e.g. a DICOM archive stub) --
            # still a successful ingest, just nothing to curate.
            document.status = DocumentStatus.curated
        db.commit()
    except Exception as e:  # pragma: no cover - defensive top-level guard
        logger.exception("ingestion pipeline failed for document %s", document_id)
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.error
            document.error_message = f"Pipeline error: {e}"
            db.commit()
