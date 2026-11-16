from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from workhub_api.approvals import router as approvals_router
from workhub_api.config import settings
from workhub_api.db import CurrentUser, SessionDep, engine
from workhub_api.delegations import router as delegations_router
from workhub_api.edit_requests import router as edit_requests_router
from workhub_api.permissions import roles_of
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


@app.get("/me")
def me(session: SessionDep, user: CurrentUser) -> dict[str, object]:
    """Who the API thinks you are. Used by the sign-in test page."""
    return {"name": user.name, "email": user.email, "roles": sorted(roles_of(session, user.id))}


@app.get("/auth-config")
def auth_config() -> dict[str, str]:
    """The two non-secret ids the sign-in page needs (so nothing is hard-coded in the HTML)."""
    return {"tenant_id": settings.entra_tenant_id, "client_id": settings.entra_client_id}


# TEST ONLY: sign-in try-out page at /test/login-test.html. Remove before production.
app.mount("/test", StaticFiles(directory=Path(__file__).parent / "static"), name="test")
