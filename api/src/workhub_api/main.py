from fastapi import FastAPI
from sqlalchemy import text

from workhub_api.db import engine
from workhub_api.timesheets import router as timesheets_router

app = FastAPI(title="WorkHub API")
app.include_router(timesheets_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness plus database check (NFSD OBS-04)."""
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
