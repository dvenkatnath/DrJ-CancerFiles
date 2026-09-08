import datetime
import uuid

from pydantic import BaseModel

from app.models.curation import CurationPriority, CurationStatus, SectionDecision
from app.models.wiki import WikiSectionType


class CurationSectionDecisionOut(BaseModel):
    id: uuid.UUID
    section_type: WikiSectionType
    decision: SectionDecision
    final_content: list | dict | None
    reviewer_note: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class CurationOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    patient_id: uuid.UUID
    status: CurationStatus
    priority: CurationPriority
    assigned_to: uuid.UUID | None
    proposed_changes: dict
    created_at: datetime.datetime
    updated_at: datetime.datetime
    section_decisions: list[CurationSectionDecisionOut] = []

    model_config = {"from_attributes": True}


class CurationListItem(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    document_filename: str
    status: CurationStatus
    priority: CurationPriority
    assigned_to: uuid.UUID | None
    created_at: datetime.datetime
    section_count: int


class CurationAssignRequest(BaseModel):
    assigned_to: uuid.UUID | None = None
    priority: CurationPriority | None = None


class SectionDecisionRequest(BaseModel):
    section_type: WikiSectionType
    decision: SectionDecision
    final_content: list | dict | None = None
    reviewer_note: str | None = None


class PublishRequest(BaseModel):
    decisions: list[SectionDecisionRequest]
