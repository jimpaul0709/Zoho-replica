from fastapi import FastAPI
from sqlalchemy import text

from workhub_api.approvals import router as approvals_router
from workhub_api.db import engine
from workhub_api.delegations import router as delegations_router
from workhub_api.edit_requests import router as edit_requests_router
from workhub_api.timesheets import router as timesheets_router

app = FastAPI(title="WorkHub API")
app.include_router(timesheets_router)
app.include_router(edit_requests_router)
app.include_router(approvals_router)
app.include_router(delegations_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness plus database check (NFSD OBS-04)."""
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
