import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import auth as auth_api
from app.api import patients as patients_api
from app.api import documents as documents_api
from app.api import wiki as wiki_api
from app.api import curation as curation_api
from app.api import chat as chat_api
from app.api import admin as admin_api
from app.config import get_settings
from app.db.session import engine
from app.services.llm_gateway import get_gateway

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_api.router, prefix=settings.api_prefix)
app.include_router(patients_api.router, prefix=settings.api_prefix)
app.include_router(documents_api.router, prefix=settings.api_prefix)
app.include_router(wiki_api.router, prefix=settings.api_prefix)
app.include_router(curation_api.router, prefix=settings.api_prefix)
app.include_router(chat_api.router, prefix=settings.api_prefix)
app.include_router(admin_api.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health")
async def health():
    """Used by the frontend to show a banner when either dependency is down, and
    by the model-unavailable UI state described in the design brief."""
    db_ok = True
    db_error = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:  # pragma: no cover
        db_ok = False
        db_error = str(e)

    gateway = get_gateway()
    llm = await gateway.health()

    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.environment,
        "database": {"ok": db_ok, "error": db_error},
        "llm": llm,
    }
