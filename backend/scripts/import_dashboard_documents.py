"""
One-time import of the real documents from the earlier single-patient
dashboard prototype (`_Dashboard/`) into this app's normal data model, run
through the SAME automated pipeline any newly-uploaded document goes through
(classify -> chunk -> embed -> LLM/mock extraction -> curation queue).

WHY THIS EXISTS: the prototype's per-patient wiki pages
(`_Dashboard/scripts/build_wiki_*.py`) were hand-written -- a person read the
OCR'd text and manually transcribed a treatment history, lab trend list, etc.
into a Python file. That doesn't generalize. What DOES already exist and IS
reusable is the actual OCR'd text (`_Dashboard/data/text/<patient>/*.txt`)
and its classification (`_Dashboard/data/manifest.json`, produced by
`_Dashboard/scripts/ingest.py`, the same rule-based classifier this app's
`app/services/classify.py` was adapted from). This script feeds THAT real
text through this app's real pipeline, so every one of those documents gets
proper structured extraction (including the lab test/value/unit fields that
feed the Lab Trends panel -- see app/services/trends.py) and lands in the
Curation Queue for a human to review and publish, exactly like a fresh
upload -- instead of trusting a one-off hand-authored summary.

THIS SCRIPT NEVER SENDS DATA ANYWHERE. It reads local files and writes to
whatever DATABASE_URL your local `.env` points at (and copies files into
UPLOAD_DIR, also local). Run it only in the DEV or CLIENT ON-PREM targets,
against your own local Postgres -- never against the Railway PoC target,
which must only ever hold synthetic data (see README.md's PHI/HIPAA notes).

Usage (from backend/, with your .env pointed at your own local Postgres):
    .venv/bin/python -m scripts.import_dashboard_documents \\
        --dashboard-dir "/Volumes/WD2TB/DrJ-CancerFiles/_Dashboard" \\
        --confirm-local-phi-import

Options:
    --dashboard-dir PATH     Required. The old dashboard's folder (contains data/manifest.json).
    --source-root PATH       Where the ORIGINAL scanned files live, for copying alongside the OCR
                             text so "Open original" works in Documents. Defaults to
                             --dashboard-dir's parent (matches how the prototype's manifest paths
                             are written). If a given original file can't be found/copied, the
                             document is still imported using its OCR'd text alone.
    --patient NAME           Only import this one patient (manifest "patient" field, e.g.
                             "Alka Agarwal"). Default: every patient in the manifest.
    --limit N                Import at most N documents (per run, across all selected patients) --
                             useful for a quick first test before importing everything.
    --mrn-prefix PREFIX      MRN assigned to newly-created patients is "<PREFIX>-<sequence>".
                             Default "IMPORTED".
    --dry-run                Parse the manifest and report what WOULD be imported; touches
                             neither the database nor the filesystem.
    --confirm-local-phi-import
                             Required (unless --dry-run) as an explicit acknowledgement that this
                             loads real patient data into your local database.

Safe to re-run / interrupt: after each document is imported, its manifest key
is recorded in "<dashboard-dir>/.clinician_workstation_import_state.json" (a
small local checkpoint file, never copied anywhere by this app) and skipped
on subsequent runs -- so an interrupted import just picks up where it left off.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.curation import Curation, CurationPriority, CurationStatus  # noqa: E402
from app.models.document import DateConfidence, Document, DocumentStatus  # noqa: E402
from app.models.patient import Patient, PatientSex  # noqa: E402
from app.services.ingestion import build_proposed_changes, chunk_text, embed_chunks, extract_wiki_proposals  # noqa: E402

settings = get_settings()

ORIGINAL_FILE_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".txt": "text/plain",
}

# Manifest entries whose file extension is one of these are original-document
# containers we can't meaningfully treat as a single clinical document (an
# archive of many files, or an install-instructions doc) -- imported using
# their OCR'd text only if manifest has an entry for them at all, never
# copied as "the original".
SKIP_COPY_EXTENSIONS = {".zip", ".rar"}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_checkpoint(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text()).get("imported_keys", []))
    except Exception:
        return set()


def save_checkpoint(path: Path, imported_keys: set[str]) -> None:
    path.write_text(json.dumps({"imported_keys": sorted(imported_keys)}, indent=2))


def get_or_create_patient(db, name: str, mrn_prefix: str, sequence: dict[str, int]) -> Patient:
    existing = db.query(Patient).filter(Patient.name == name).first()
    if existing:
        return existing
    seq = sequence.get("n", 0) + 1
    sequence["n"] = seq
    mrn = f"{mrn_prefix}-{seq:04d}"
    patient = Patient(mrn=mrn, name=name, sex=PatientSex.unknown)
    db.add(patient)
    db.flush()
    print(f"  created patient record: {name} (MRN {mrn}) -- demographics unknown, edit in Admin if needed")
    return patient


async def import_one_document(db, patient: Patient, manifest_key: str, entry: dict, dashboard_dir: Path, source_root: Path) -> str | None:
    text_path = entry.get("text_path")
    if not text_path:
        return None
    text_file = dashboard_dir / text_path
    if not text_file.exists():
        print(f"    ! OCR text file missing, skipping: {text_path}")
        return None
    text = text_file.read_text(errors="ignore")
    if not text.strip():
        print(f"    ! empty OCR text, skipping: {manifest_key}")
        return None

    original_path = source_root / manifest_key
    ext = Path(manifest_key).suffix.lower()
    patient_dir = Path(settings.upload_dir) / str(patient.id)
    patient_dir.mkdir(parents=True, exist_ok=True)

    filename = Path(manifest_key).name
    copied_original = False
    if ext not in SKIP_COPY_EXTENSIONS and original_path.exists() and original_path.is_file():
        storage_path = patient_dir / f"{patient.id}-{slugify(filename)}{ext}"
        try:
            shutil.copyfile(original_path, storage_path)
            mime_type = ORIGINAL_FILE_MIME.get(ext, "application/octet-stream")
            copied_original = True
        except Exception as e:
            print(f"    ! could not copy original ({e}), falling back to OCR-text-only for: {filename}")
    if not copied_original:
        # No usable original on disk (moved/renamed since the prototype ran,
        # an archive, or a copy error) -- store the OCR'd text itself so the
        # document is still fully searchable/extractable; just without a
        # faithful "Open original" preview.
        storage_path = patient_dir / f"{patient.id}-{slugify(filename)}.txt"
        storage_path.write_text(text)
        mime_type = "text/plain"

    doc_date = None
    if entry.get("date"):
        try:
            import datetime

            doc_date = datetime.date.fromisoformat(entry["date"])
        except ValueError:
            doc_date = None

    document = Document(
        patient_id=patient.id,
        filename=filename,
        storage_path=str(storage_path),
        mime_type=mime_type,
        size_bytes=storage_path.stat().st_size,
        doc_type=entry.get("doc_type") or "Other/Unclassified",
        doc_type_confirmed=False,
        doc_date=doc_date,
        doc_date_confidence=DateConfidence.parsed_fuzzy if doc_date else DateConfidence.unresolved,
        doc_date_confirmed=False,
        status=DocumentStatus.extracting,
        extracted_text=text,
        ocr_used=bool(entry.get("ocr_used")),
        page_count=None,
    )
    db.add(document)
    db.flush()

    # From here on this mirrors run_ingestion_pipeline (app/services/ingestion.py)
    # starting from the chunk step -- text extraction is skipped because we
    # already have it from the prototype's own OCR pass.
    try:
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
            document.status = DocumentStatus.curated
        db.commit()
    except Exception as e:
        db.rollback()
        document = db.get(Document, document.id)
        if document is not None:
            document.status = DocumentStatus.error
            document.error_message = f"Import pipeline error: {e}"
            db.commit()
        print(f"    ! pipeline error for {filename}: {e}")

    return str(document.id)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dashboard-dir", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=None)
    parser.add_argument("--patient", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mrn-prefix", default="IMPORTED")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-local-phi-import", action="store_true")
    args = parser.parse_args()

    dashboard_dir: Path = args.dashboard_dir.expanduser().resolve()
    source_root: Path = (args.source_root or dashboard_dir.parent).expanduser().resolve()
    manifest_path = dashboard_dir / "data" / "manifest.json"
    if not manifest_path.exists():
        print(f"No manifest.json found at {manifest_path} -- is --dashboard-dir correct?")
        sys.exit(1)

    if not args.dry_run and not args.confirm_local_phi_import:
        print(
            "Refusing to run: this imports real patient data into your local database.\n"
            "Re-run with --confirm-local-phi-import once you've confirmed this is the DEV or "
            "CLIENT ON-PREM target (never Railway PoC), or use --dry-run to preview first."
        )
        sys.exit(1)

    manifest: dict[str, dict] = json.loads(manifest_path.read_text())

    by_patient: dict[str, list[tuple[str, dict]]] = {}
    for key, entry in manifest.items():
        name = entry.get("patient")
        if not name or entry.get("status") != "done":
            continue
        if args.patient and name != args.patient:
            continue
        by_patient.setdefault(name, []).append((key, entry))

    if not by_patient:
        print("No matching manifest entries found (check --patient spelling against manifest.json).")
        return

    total = sum(len(v) for v in by_patient.values())
    print(f"Found {total} importable document(s) across {len(by_patient)} patient(s):")
    for name, entries in by_patient.items():
        print(f"  {name}: {len(entries)} document(s)")

    if args.dry_run:
        print("\n--dry-run: nothing written. Re-run without it (plus --confirm-local-phi-import) to import.")
        return

    checkpoint_path = dashboard_dir / ".clinician_workstation_import_state.json"
    imported_keys = load_checkpoint(checkpoint_path)
    print(f"\n{len(imported_keys)} document(s) already imported in a previous run (will be skipped).")

    db = SessionLocal()
    sequence = {"n": 0}
    imported_this_run = 0
    try:
        for name, entries in by_patient.items():
            patient = get_or_create_patient(db, name, args.mrn_prefix, sequence)
            db.commit()
            for key, entry in entries:
                if args.limit is not None and imported_this_run >= args.limit:
                    break
                if key in imported_keys:
                    continue
                doc_id = await import_one_document(db, patient, key, entry, dashboard_dir, source_root)
                if doc_id:
                    imported_keys.add(key)
                    imported_this_run += 1
                    save_checkpoint(checkpoint_path, imported_keys)
                    print(f"    imported {name}: {Path(key).name} -> document {doc_id}")
            if args.limit is not None and imported_this_run >= args.limit:
                break
    finally:
        db.close()

    print(f"\nDone. Imported {imported_this_run} document(s) this run ({len(imported_keys)} total across all runs).")
    print("Everything landed in the Curation Queue pending review -- nothing is published to any")
    print("patient's wiki until a curator/physician accepts it there, same as any fresh upload.")


if __name__ == "__main__":
    asyncio.run(main())
