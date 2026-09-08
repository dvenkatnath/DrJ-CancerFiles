import datetime
import uuid

from pydantic import BaseModel

from app.models.patient import PatientSex, PatientStatus


class PatientBase(BaseModel):
    mrn: str
    name: str
    date_of_birth: datetime.date | None = None
    sex: PatientSex = PatientSex.unknown


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: str | None = None
    date_of_birth: datetime.date | None = None
    sex: PatientSex | None = None
    status: PatientStatus | None = None


class PatientListItem(BaseModel):
    id: uuid.UUID
    mrn: str
    name: str
    status: PatientStatus
    updated_at: datetime.datetime
    pending_review_count: int
    document_count: int

    model_config = {"from_attributes": True}


class PatientOut(PatientBase):
    id: uuid.UUID
    status: PatientStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


def age_from_dob(dob: datetime.date | None) -> int | None:
    if not dob:
        return None
    today = datetime.date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
