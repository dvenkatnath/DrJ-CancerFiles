import enum
import datetime

from sqlalchemy import Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class PatientSex(str, enum.Enum):
    female = "female"
    male = "male"
    other = "other"
    unknown = "unknown"


class PatientStatus(str, enum.Enum):
    active = "active"
    pending_review = "pending_review"  # has documents awaiting curation
    archived = "archived"


class Patient(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "patients"

    mrn: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[PatientSex] = mapped_column(
        Enum(PatientSex, name="patient_sex"), nullable=False, default=PatientSex.unknown
    )
    status: Mapped[PatientStatus] = mapped_column(
        Enum(PatientStatus, name="patient_status"), nullable=False, default=PatientStatus.active
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Patient {self.mrn} {self.name}>"
