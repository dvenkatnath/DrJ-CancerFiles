import datetime
import uuid

from pydantic import BaseModel

from app.models.wiki import ChangeSource, WikiSectionType


class WikiSource(BaseModel):
    document_id: uuid.UUID
    document_name: str | None = None
    page: int | None = None
    section_label: str | None = None


class WikiFact(BaseModel):
    """One statement inside a WikiSection.content array."""

    id: str
    text: str
    sources: list[WikiSource] = []
    confidence: float | None = None  # 0..1, set on ai_extraction facts
    status: str = "reviewed"  # "reviewed" | "unreviewed"
    last_updated: datetime.datetime | None = None

    # Set for every fact at extraction time (app/services/ingestion.py) from the
    # source document's own detected date -- when the clinical event happened,
    # as opposed to `last_updated` (when this row was extracted/edited).
    event_date: datetime.date | None = None

    # Populated only for lab_highlights facts that represent one specific
    # numeric lab result (see ingestion.py's normalize_lab_marker /
    # EXTRACTION_SYSTEM_PROMPT). Lets the Lab Trends panel plot a real time
    # series instead of trying to parse numbers back out of prose.
    test: str | None = None  # canonical marker name, e.g. "CA125", "Hemoglobin"
    value: float | None = None
    unit: str | None = None


class TrendPoint(BaseModel):
    date: datetime.date | None
    value: float
    unit: str | None = None
    document_id: uuid.UUID | None = None
    fact_id: str | None = None


class TrendMarker(BaseModel):
    test: str
    unit: str | None = None
    points: list[TrendPoint]
    direction: str  # "rising" | "falling" | "stable" | "insufficient_data"
    latest_value: float
    latest_date: datetime.date | None = None


class WikiSectionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    section_type: WikiSectionType
    content: list[dict]
    version: int
    is_reviewed: bool
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class WikiSectionEditRequest(BaseModel):
    content: list[dict]
    note: str | None = None


class WikiRevisionOut(BaseModel):
    id: uuid.UUID
    version: int
    content: list[dict]
    change_source: ChangeSource
    changed_by: uuid.UUID | None
    note: str | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
