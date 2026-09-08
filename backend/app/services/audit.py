"""
Every PHI touch (view or edit of a patient/document/wiki section) is expected
to call `log_action` so the Admin audit log has a complete trail of who
accessed what, when. Fire-and-forget within the request's own DB transaction --
callers commit alongside their own writes.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    patient_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    extra: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        patient_id=patient_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        extra=extra,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
