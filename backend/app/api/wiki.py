import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.db.session import get_db
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.models.wiki import ChangeSource, WikiRevision, WikiSection, WikiSectionType
from app.schemas.wiki import TrendMarker, WikiRevisionOut, WikiSectionEditRequest, WikiSectionOut
from app.services.audit import log_action
from app.services.trends import compute_lab_trends

router = APIRouter(prefix="/patients/{patient_id}/wiki", tags=["wiki"])


def _get_or_create_section(db: Session, patient_id: uuid.UUID, section_type: WikiSectionType) -> WikiSection:
    section = (
        db.query(WikiSection)
        .filter(WikiSection.patient_id == patient_id, WikiSection.section_type == section_type)
        .first()
    )
    if section is None:
        section = WikiSection(patient_id=patient_id, section_type=section_type, content=[], version=1, is_reviewed=True)
        db.add(section)
        db.flush()
    return section


@router.get("", response_model=list[WikiSectionOut])
def get_wiki(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    sections = db.query(WikiSection).filter(WikiSection.patient_id == patient_id).all()
    log_action(
        db,
        user_id=user.id,
        patient_id=patient_id,
        action="view_wiki",
        resource_type="patient",
        resource_id=str(patient_id),
        ip_address=get_client_ip(request),
    )
    db.commit()
    return sections


@router.get("/trends", response_model=list[TrendMarker])
def get_lab_trends(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Per-lab-marker time series (CA-125, Hemoglobin, etc.) aggregated from
    every published lab_highlights fact across this patient's whole record --
    NOT just the most recent document. Declared before `/{section_type}` so it
    isn't swallowed by that route (WikiSectionType validation would 422 on
    the literal string "trends" otherwise)."""
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return compute_lab_trends(db, patient_id)


@router.get("/{section_type}", response_model=WikiSectionOut)
def get_wiki_section(
    patient_id: uuid.UUID,
    section_type: WikiSectionType,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    section = _get_or_create_section(db, patient_id, section_type)
    db.commit()
    db.refresh(section)
    return section


@router.put("/{section_type}", response_model=WikiSectionOut)
def edit_wiki_section(
    patient_id: uuid.UUID,
    section_type: WikiSectionType,
    body: WikiSectionEditRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.physician, UserRole.curator, UserRole.admin)),
):
    """Direct inline edit by an authorized role. Always fully reviewed (a human
    typed it), and always recorded as a new WikiRevision for the per-section
    history the design brief calls for."""
    section = _get_or_create_section(db, patient_id, section_type)
    section.content = body.content
    section.version += 1
    section.is_reviewed = True

    change_source = ChangeSource.physician_edit if user.role == UserRole.physician else ChangeSource.curator_edit
    db.add(
        WikiRevision(
            wiki_section_id=section.id,
            version=section.version,
            content=body.content,
            change_source=change_source,
            changed_by=user.id,
            note=body.note,
        )
    )
    log_action(
        db,
        user_id=user.id,
        patient_id=patient_id,
        action="edit_wiki_section",
        resource_type="wiki_section",
        resource_id=str(section.id),
        extra={"section_type": section_type.value, "version": section.version},
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(section)
    return section


@router.get("/{section_type}/revisions", response_model=list[WikiRevisionOut])
def get_wiki_section_revisions(
    patient_id: uuid.UUID,
    section_type: WikiSectionType,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    section = _get_or_create_section(db, patient_id, section_type)
    db.commit()
    return (
        db.query(WikiRevision)
        .filter(WikiRevision.wiki_section_id == section.id)
        .order_by(WikiRevision.version.desc())
        .all()
    )
