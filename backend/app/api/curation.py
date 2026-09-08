import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.db.session import get_db
from app.models.curation import (
    Curation,
    CurationPriority,
    CurationSectionDecision,
    CurationStatus,
    SectionDecision,
)
from app.models.user import User, UserRole
from app.models.wiki import WikiSectionType
from app.schemas.curation import CurationAssignRequest, CurationListItem, CurationOut, SectionDecisionRequest
from app.services.audit import log_action
from app.services.curation_service import publish_curation as apply_publish

router = APIRouter(tags=["curation"])


@router.get("/curation-queue", response_model=list[CurationListItem])
def curation_queue(
    status_filter: CurationStatus | None = Query(default=None, alias="status"),
    priority: CurationPriority | None = None,
    assigned_to: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Curation).options(joinedload(Curation.patient), joinedload(Curation.document))
    if status_filter:
        query = query.filter(Curation.status == status_filter)
    else:
        query = query.filter(Curation.status.in_([CurationStatus.pending, CurationStatus.in_progress]))
    if priority:
        query = query.filter(Curation.priority == priority)
    if assigned_to:
        query = query.filter(Curation.assigned_to == assigned_to)

    priority_rank = {
        CurationPriority.urgent: 0,
        CurationPriority.high: 1,
        CurationPriority.normal: 2,
        CurationPriority.low: 3,
    }
    curations = query.order_by(Curation.created_at.asc()).all()
    curations.sort(key=lambda c: (priority_rank.get(c.priority, 2), c.created_at))

    return [
        CurationListItem(
            id=c.id,
            document_id=c.document_id,
            patient_id=c.patient_id,
            patient_name=c.patient.name if c.patient else "",
            document_filename=c.document.filename if c.document else "",
            status=c.status,
            priority=c.priority,
            assigned_to=c.assigned_to,
            created_at=c.created_at,
            section_count=len(c.proposed_changes or {}),
        )
        for c in curations
    ]


def _get_curation_or_404(db: Session, curation_id: uuid.UUID) -> Curation:
    curation = db.get(Curation, curation_id)
    if not curation:
        raise HTTPException(status_code=404, detail="Curation item not found")
    return curation


@router.get("/curation/{curation_id}", response_model=CurationOut)
def get_curation(curation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_curation_or_404(db, curation_id)


@router.patch("/curation/{curation_id}/assign", response_model=CurationOut)
def assign_curation(
    curation_id: uuid.UUID,
    body: CurationAssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.curator, UserRole.admin)),
):
    curation = _get_curation_or_404(db, curation_id)
    if body.assigned_to is not None:
        curation.assigned_to = body.assigned_to
    if body.priority is not None:
        curation.priority = body.priority
    if curation.status == CurationStatus.pending:
        curation.status = CurationStatus.in_progress
    db.commit()
    db.refresh(curation)
    return curation


@router.put("/curation/{curation_id}/decisions/{section_type}", response_model=CurationOut)
def decide_section(
    curation_id: uuid.UUID,
    section_type: WikiSectionType,
    body: SectionDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.curator, UserRole.physician, UserRole.admin)),
):
    """Accept / edit-inline / reject one proposed section (keyboard shortcuts
    A/E/R in the frontend all resolve to this one call)."""
    curation = _get_curation_or_404(db, curation_id)
    if section_type.value not in (curation.proposed_changes or {}):
        raise HTTPException(status_code=400, detail=f"{section_type.value} was not proposed for this document")

    decision_row = (
        db.query(CurationSectionDecision)
        .filter(CurationSectionDecision.curation_id == curation_id, CurationSectionDecision.section_type == section_type)
        .first()
    )
    if decision_row is None:
        decision_row = CurationSectionDecision(curation_id=curation_id, section_type=section_type)
        db.add(decision_row)

    decision_row.decision = body.decision
    decision_row.final_content = body.final_content
    decision_row.reviewer_note = body.reviewer_note
    decision_row.decided_by = user.id
    decision_row.decided_at = datetime.now(timezone.utc)

    if curation.status == CurationStatus.pending:
        curation.status = CurationStatus.in_progress

    log_action(
        db,
        user_id=user.id,
        patient_id=curation.patient_id,
        action="decide_curation_section",
        resource_type="curation",
        resource_id=str(curation.id),
        extra={"section_type": section_type.value, "decision": body.decision.value},
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(curation)
    return curation


@router.post("/curation/{curation_id}/publish", response_model=CurationOut)
def publish_curation(
    curation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.curator, UserRole.admin)),
):
    """Commits every accepted/edited section into the living wiki, writes the
    WikiRevision audit trail, and marks the source document Curated."""
    curation = _get_curation_or_404(db, curation_id)
    if curation.status == CurationStatus.published:
        raise HTTPException(status_code=400, detail="Already published")

    try:
        apply_publish(db, curation, published_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    log_action(
        db,
        user_id=user.id,
        patient_id=curation.patient_id,
        action="publish_curation",
        resource_type="curation",
        resource_id=str(curation.id),
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(curation)
    return curation
