# Backend image: FastAPI app + Alembic migrations. Talks to Postgres (DATABASE_URL)
# and to an LLM only through app.services.llm_gateway (OPENAI_BASE_URL + *_MODEL env
# vars) -- this Dockerfile is identical across DEV / RAILWAY POC / CLIENT on-prem;
# only the environment variables at `docker run` / compose / Railway time differ.
FROM python:3.11-slim

# libpq for psycopg2-binary's runtime deps; curl for the container healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/uploads

ENV PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/app/data/uploads

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fs http://localhost:8000/api/health || exit 1

# Run migrations, then serve. If the DB isn't reachable yet, retry a few times
# instead of crash-looping immediately (compose/Railway startup ordering).
CMD ["sh", "-c", "for i in $(seq 1 10); do alembic upgrade head && break; echo 'DB not ready, retrying...'; sleep 3; done; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
