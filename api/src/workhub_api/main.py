from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from workhub_api.approvals import router as approvals_router
from workhub_api.auth import router as auth_router
from workhub_api.config import settings
from workhub_api.db import engine
from workhub_api.delegations import router as delegations_router
from workhub_api.edit_requests import router as edit_requests_router
from workhub_api.hr import router as hr_router
from workhub_api.leave import router as leave_router
from workhub_api.org_admin import router as org_admin_router
from workhub_api.payslips import router as payslips_router
from workhub_api.timesheets import router as timesheets_router
from workhub_api.users_admin import router as users_admin_router

app = FastAPI(title="WorkHub API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(timesheets_router)
app.include_router(edit_requests_router)
app.include_router(approvals_router)
app.include_router(delegations_router)
app.include_router(hr_router)
app.include_router(leave_router)
app.include_router(org_admin_router)
app.include_router(payslips_router)
app.include_router(users_admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness plus database check (NFSD OBS-04)."""
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
