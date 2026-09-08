import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.db.session import get_db
from app.models.curation import Curation, CurationStatus
from app.models.document import Document
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.patient import PatientCreate, PatientListItem, PatientOut, PatientUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientListItem])
def list_patients(
    q: str | None = Query(default=None, description="search by name or MRN"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Patient)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Patient.name.ilike(like), Patient.mrn.ilike(like)))
    patients = query.order_by(Patient.updated_at.desc()).offset(offset).limit(limit).all()

    if not patients:
        return []
    ids = [p.id for p in patients]
    doc_counts = dict(
        db.query(Document.patient_id, func.count(Document.id))
        .filter(Document.patient_id.in_(ids))
        .group_by(Document.patient_id)
        .all()
    )
    review_counts = dict(
        db.query(Curation.patient_id, func.count(Curation.id))
        .filter(Curation.patient_id.in_(ids), Curation.status.in_([CurationStatus.pending, CurationStatus.in_progress]))
        .group_by(Curation.patient_id)
        .all()
    )
    return [
        PatientListItem(
            id=p.id,
            mrn=p.mrn,
            name=p.name,
            status=p.status,
            updated_at=p.updated_at,
            pending_review_count=review_counts.get(p.id, 0),
            document_count=doc_counts.get(p.id, 0),
        )
        for p in patients
    ]


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    body: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.curator)),
):
    if db.query(Patient).filter(Patient.mrn == body.mrn).first():
        raise HTTPException(status_code=409, detail="A patient with this MRN already exists")
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    log_action(
        db,
        user_id=user.id,
        patient_id=patient.id,
        action="view_patient",
        resource_type="patient",
        resource_id=str(patient.id),
        ip_address=get_client_ip(request),
    )
    db.commit()
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.curator, UserRole.physician)),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(patient, k, v)
    log_action(
        db,
        user_id=user.id,
        patient_id=patient.id,
        action="edit_patient",
        resource_type="patient",
        resource_id=str(patient.id),
        extra={"fields": list(updates.keys())},
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(patient)
    return patient
