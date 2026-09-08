"""
Shared "apply decided sections into the living wiki" logic, used by both the
POST /curation/{id}/publish route and the seed script (which auto-publishes
one demo patient so there's an example of a fully-curated record).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.curation import Curation, CurationStatus, SectionDecision
from app.models.document import Document, DocumentStatus
from app.models.wiki import ChangeSource, WikiRevision, WikiSection, WikiSectionType


def publish_curation(db: Session, curation: Curation, published_by: uuid.UUID | None) -> Curation:
    proposed_sections = set((curation.proposed_changes or {}).keys())
    decisions = {d.section_type.value: d for d in curation.section_decisions}
    undecided = [s for s in proposed_sections if s not in decisions or decisions[s].decision == SectionDecision.pending]
    if undecided:
        raise ValueError(f"Decide every proposed section before publishing (still pending: {', '.join(undecided)})")

    now = datetime.now(timezone.utc)
    for section_key, decision_row in decisions.items():
        if decision_row.decision == SectionDecision.rejected:
            continue
        section_type = WikiSectionType(section_key)
        section = (
            db.query(WikiSection)
            .filter(WikiSection.patient_id == curation.patient_id, WikiSection.section_type == section_type)
            .first()
        )
        if section is None:
            section = WikiSection(patient_id=curation.patient_id, section_type=section_type, content=[], version=0, is_reviewed=True)
            db.add(section)
            db.flush()

        if decision_row.decision == SectionDecision.edited and decision_row.final_content is not None:
            new_facts = decision_row.final_content
        else:
            proposal = curation.proposed_changes[section_key]
            new_facts = list(proposal.get("additions", []))
            for f in new_facts:
                f["status"] = "reviewed"
                f["last_updated"] = now.isoformat()

        section.content = list(section.content or []) + list(new_facts)
        section.version += 1
        section.is_reviewed = True
        db.add(
            WikiRevision(
                wiki_section_id=section.id,
                version=section.version,
                content=section.content,
                change_source=ChangeSource.curator_edit,
                changed_by=published_by,
                note=decision_row.reviewer_note,
            )
        )

    curation.status = CurationStatus.published
    curation.published_at = now
    curation.published_by = published_by

    document = db.get(Document, curation.document_id)
    if document:
        document.status = DocumentStatus.curated

    return curation
