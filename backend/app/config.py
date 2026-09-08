"""
Central configuration. EVERYTHING that differs between DEV / RAILWAY POC / CLIENT
on-prem deployments lives here, sourced from environment variables. No code in
the feature layers should ever branch on "which deployment am I" -- they read
these settings instead.

HARD REQUIREMENT: the app talks to LLMs only through app.services.llm_gateway,
which in turn only ever reads OPENAI_BASE_URL + *_MODEL from here. No provider
SDKs (openai, anthropic, etc.) anywhere else in the codebase.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App / environment ---
    app_name: str = "Clinician Workstation"
    environment: Literal["dev", "railway_poc", "client_onprem", "test"] = "dev"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg2://cwuser:cwpass@localhost:5432/clinician_dev"
    )

    # --- Auth ---
    jwt_secret: str = Field(default="dev-only-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # --- SSO / MFA placeholders (wired later, not implemented) ---
    sso_enabled: bool = False
    mfa_enabled: bool = False

    # --- LLM gateway: the ONLY place provider connectivity is configured. ---
    # OpenAI-compatible base URL. Points at:
    #   dev            -> http://localhost:11434/v1 (Ollama on this Mac)
    #   railway_poc    -> the tunneled Ollama on the Mac Mini, or any OpenAI-compatible
    #                      open-weights host (synthetic data only in this mode)
    #   client_onprem  -> http://<onprem-host>:11434/v1
    openai_base_url: str = Field(default="http://localhost:11434/v1")
    openai_api_key: str = Field(default="ollama")  # Ollama ignores the value; kept for OpenAI-compatible hosts that require one

    chat_model: str = Field(default="qwen3:14b")
    extraction_model: str = Field(default="qwen3:8b")
    embedding_model: str = Field(default="nomic-embed-text")
    embedding_dim: int = Field(default=768)  # nomic-embed-text = 768; bge-m3 = 1024 (change together)

    llm_context_tokens: int = Field(default=12000)  # capped 8-16k per the memory guardrail
    llm_keep_alive: str = Field(default="30m")
    llm_request_timeout_seconds: float = Field(default=120.0)
    llm_max_retries: int = Field(default=3)

    # LLM_MODE:
    #   auto  -> probe the gateway; fall back to mock automatically if unreachable
    #   live  -> always call the real gateway (errors surface as model-unavailable)
    #   mock  -> never call a real model; deterministic rule-based stand-ins everywhere.
    #            This is what makes the whole app runnable end-to-end with zero LLM.
    llm_mode: Literal["auto", "live", "mock"] = "auto"

    # --- Ingestion ---
    max_upload_mb: int = 50
    upload_dir: str = "./data/uploads"

    # --- Vector DB escape hatch (not used at this scale; see README) ---
    vector_backend: Literal["pgvector", "qdrant"] = "pgvector"


@lru_cache
def get_settings() -> Settings:
    return Settings()
