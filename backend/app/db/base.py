from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import every model module here so Alembic's autogenerate and Base.metadata.create_all
# see the full schema from a single import of app.db.base.
from app.models import (  # noqa: E402,F401
    user,
    patient,
    document,
    wiki,
    curation,
    chat,
    audit,
)
