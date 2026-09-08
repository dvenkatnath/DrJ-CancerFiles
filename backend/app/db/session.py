from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings

settings = get_settings()

# Connection pooling: pool_size/max_overflow tuned conservatively for a
# single small Postgres instance (Railway hobby tier or a Mac Mini).
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
