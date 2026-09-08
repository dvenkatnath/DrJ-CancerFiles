"""
Seeds the DB with 3 synthetic patients, sample users for each role, and runs
their documents through the REAL ingestion pipeline (extract -> classify ->
chunk -> embed -> LLM/mock extraction -> curation). One patient is left fully
curated to show what a "clean" chart looks like; the other two are left with
pending curation items so the queue isn't empty on first login.

Usage (from backend/):
    .venv/bin/python -m seed.seed_data

Safe to re-run: skips creation of anything that already exists by natural key
(email / MRN), and skips re-adding documents a patient already has.
"""
from __future__ import annotations

import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.curation import Curation, CurationSectionDecision, SectionDecision
from app.models.document import Document, DocumentStatus
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.services.curation_service import publish_curation
from app.services.ingestion import run_ingestion_pipeline
from seed.sample_documents import SEED_PATIENTS

settings = get_settings()

SEED_USERS = [
    {"email": "admin@democlinic.io", "full_name": "Ada Admin", "role": UserRole.admin, "password": "DemoPass123!"},
    {"email": "physician@democlinic.io", "full_name": "Dr. Priya Sharma", "role": UserRole.physician, "password": "DemoPass123!"},
    {"email": "curator@democlinic.io", "full_name": "Casey Curator", "role": UserRole.curator, "password": "DemoPass123!"},
]


def seed_users(db) -> dict[str, User]:
    out = {}
    for u in SEED_USERS:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if existing:
            out[u["role"].value] = existing
            continue
        user = User(
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            hashed_password=hash_password(u["password"]),
        )
        db.add(user)
        db.flush()
        out[u["role"].value] = user
        print(f"created user {u['email']} ({u['role'].value})")
    db.commit()
    return out


async def seed_patients(db, curator: User) -> None:
    for spec in SEED_PATIENTS:
        patient = db.query(Patient).filter(Patient.mrn == spec["mrn"]).first()
        if patient is None:
            patient = Patient(
                mrn=spec["mrn"],
                name=spec["name"],
                date_of_birth=datetime.date.fromisoformat(spec["date_of_birth"]),
                sex=spec["sex"],
            )
            db.add(patient)
            db.flush()
            print(f"created patient {spec['name']} ({spec['mrn']})")

        existing_docs = db.query(Document).filter(Document.patient_id == patient.id).count()
        if existing_docs > 0:
            print(f"  {spec['name']} already has {existing_docs} document(s), skipping document seed")
            continue

        patient_dir = Path(settings.upload_dir) / str(patient.id)
        patient_dir.mkdir(parents=True, exist_ok=True)

        doc_ids = []
        for filename, content in spec["documents"]:
            path = patient_dir / filename
            path.write_text(content)
            document = Document(
                patient_id=patient.id,
                filename=filename,
                storage_path=str(path),
                mime_type="text/plain",
                size_bytes=len(content.encode()),
                status=DocumentStatus.uploaded,
            )
            db.add(document)
            db.flush()
            doc_ids.append(document.id)
        db.commit()

        for doc_id in doc_ids:
            await run_ingestion_pipeline(db, doc_id)
            print(f"  ingested document {doc_id} for {spec['name']}")

        if spec.get("auto_publish"):
            curations = db.query(Curation).filter(Curation.patient_id == patient.id).all()
            for curation in curations:
                for section_key in (curation.proposed_changes or {}).keys():
                    from app.models.wiki import WikiSectionType

                    db.add(
                        CurationSectionDecision(
                            curation_id=curation.id,
                            section_type=WikiSectionType(section_key),
                            decision=SectionDecision.accepted,
                            decided_by=curator.id,
                        )
                    )
                db.flush()
                db.refresh(curation)
                publish_curation(db, curation, published_by=curator.id)
                print(f"  auto-published curation {curation.id} for {spec['name']}")
            db.commit()


async def main():
    db = SessionLocal()
    try:
        users = seed_users(db)
        await seed_patients(db, curator=users["curator"])
        print("\nSeed complete. Demo logins (all roles share the same password):")
        for u in SEED_USERS:
            print(f"  {u['email']} / {u['password']}  ({u['role'].value})")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
