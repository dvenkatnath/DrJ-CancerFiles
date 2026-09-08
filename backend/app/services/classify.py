"""
Rule-based document type + date detection, run BEFORE any LLM call so a
document always has a reasonable type/date guess even in full mock mode (per
spec: "auto-detect type/date with human confirmation"). Adapted from the
keyword/date heuristics proven out in the original single-patient dashboard
prototype (`_Dashboard/scripts/ingest.py`) rather than reinvented from scratch.
"""
from __future__ import annotations

import re
from datetime import date, datetime

DOC_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("Lab - Tumor Marker", ["ca125", "ca 125", "cea", "psa", "chromogranin", "tumor marker", "tumour marker", "ca19", "ca-19", "afp "]),
    ("Lab - CBC/Blood", ["cbc", "complete blood count", "hemoglobin", "haemoglobin", "platelet", "wbc count", "blood test"]),
    ("Lab - Chemistry", ["creatinine", "lft", "kft", "liver function", "kidney function", "electrolyte"]),
    ("Imaging", ["pet scan", "pet-ct", "pet ct", "ct scan", "ct abdomen", "mri", "x-ray", "xray", "ultrasound", "2d echo", "mammograph", "chest x"]),
    ("Pathology/Biopsy", ["histopathology", "biopsy", "cytology"]),
    ("Genomic/Molecular", ["gene report", "genomic", "foundation one", "foundation 1", "molecular"]),
    ("Discharge Summary", ["discharge summary"]),
    ("Case Summary/Advice Note", ["case summary", "advice note", "visit note"]),
    ("Prescription", ["prescription", "rx "]),
    ("Treatment Note", ["chemo", "chemotherapy", "treatment plan", "infusion"]),
]

MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_ALT = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
DATE_MONTHNAME_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:(\d{1,2})\s*[-_./,]?\s*)?" + _MONTH_ALT + r"\s*[-_./,]?\s*(\d{4}|\d{2})?(?![A-Za-z0-9])",
    re.I,
)


def classify_doc_type(text_sample: str) -> str:
    lower = text_sample.lower()
    for label, keywords in DOC_TYPE_RULES:
        if any(kw in lower for kw in keywords):
            return label
    return "Other/Unclassified"


def _fix_year(y: int) -> int:
    if y < 100:
        return 2000 + y if y <= 27 else 1900 + y
    return y


def guess_date(filename: str, text_sample: str) -> tuple[date | None, str]:
    """Returns (date_or_None, confidence) where confidence is one of
    parsed_exact / parsed_fuzzy / unresolved."""
    for token in (filename, text_sample[:400]):
        m = re.search(r"(?<!\d)(\d{4})[\-_./](\d{1,2})[\-_./](\d{1,2})(?!\d)", token)
        if m:
            y, mo, d = _fix_year(int(m.group(1))), int(m.group(2)), int(m.group(3))
            if 1 <= d <= 31 and 1 <= mo <= 12 and 1990 <= y <= 2035:
                try:
                    return datetime(y, mo, d).date(), "parsed_exact"
                except ValueError:
                    pass
        m = re.search(r"(\d{1,2})[\-_./](\d{1,2})[\-_./](\d{2,4})", token)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), _fix_year(int(m.group(3)))
            if 1 <= d <= 31 and 1 <= mo <= 12 and 1990 <= y <= 2035:
                try:
                    return datetime(y, mo, d).date(), "parsed_exact"
                except ValueError:
                    pass
        for dm in DATE_MONTHNAME_RE.finditer(token):
            day_s, month_s, year_s = dm.group(1), dm.group(2), dm.group(3)
            if not year_s:
                continue
            mo = MONTH_NUM[month_s[:3].lower()]
            d = int(day_s) if day_s else 1
            y = _fix_year(int(year_s))
            if 1 <= d <= 31 and 1990 <= y <= 2035:
                try:
                    return datetime(y, mo, d).date(), "parsed_fuzzy"
                except ValueError:
                    continue
    return None, "unresolved"
