from fastapi import FastAPI
from sqlalchemy import create_engine, text

from workhub_api.config import settings

app = FastAPI(title="WorkHub API")
engine = create_engine(settings.database_url, pool_pre_ping=True)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness plus database check (NFSD OBS-04)."""
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
