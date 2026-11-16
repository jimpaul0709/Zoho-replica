"""Microsoft Entra sign-in (WH-04): built and tested, but NOT wired in. Nothing imports this file.

It stands alone: its own settings, its own router and its own tests (tests/test_auth.py).
To switch it on later:
  1. Put ENTRA_TENANT_ID and ENTRA_CLIENT_ID in .env (Azure app registration, Overview page).
  2. main.py: `app.include_router(entra_auth.router)`. For the try-out page, also
     `app.mount("/test", StaticFiles(directory=entra_auth.STATIC_DIR))`, then open
     /test/login-test.html.
  3. db.current_user: if an Authorization header is present, `return user_from_token(session, it)`.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import APIRouter, Header, HTTPException
from jwt import PyJWKClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, select

from workhub_api.db import SessionDep
from workhub_api.models import User
from workhub_api.permissions import roles_of

STATIC_DIR = Path(__file__).parent / "static"


class EntraSettings(BaseSettings):
    """Both ids are not secrets: they name the company and the app."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entra_tenant_id: str = ""
    entra_client_id: str = ""


entra = EntraSettings()


@lru_cache
def _jwks() -> PyJWKClient:
    # PyJWKClient caches Microsoft's public signing keys, so this is not a network call per request.
    return PyJWKClient(
        f"https://login.microsoftonline.com/{entra.entra_tenant_id}/discovery/v2.0/keys"
    )


def _email_from_token(token: str) -> str:
    """Check Microsoft's signature, expiry, audience and issuer; return the signed-in email."""
    tenant, client = entra.entra_tenant_id, entra.entra_client_id
    if not tenant or not client:
        raise HTTPException(401, "Microsoft sign-in is not configured (ENTRA_TENANT_ID/CLIENT_ID)")
    try:
        claims = jwt.decode(
            token,
            _jwks().get_signing_key_from_jwt(token).key,
            algorithms=["RS256"],
            # v1 tokens use the api:// form and the sts.windows.net issuer; v2 use the client id.
            audience=[client, f"api://{client}"],
            issuer=[
                f"https://login.microsoftonline.com/{tenant}/v2.0",
                f"https://sts.windows.net/{tenant}/",
            ],
        )
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Invalid or expired Microsoft token") from e
    email = claims.get("preferred_username") or claims.get("upn") or claims.get("email")
    if not email:
        raise HTTPException(401, "Token has no email")
    return str(email)


def user_from_token(session: SessionDep, authorization: str | None) -> User:
    """Map an `Authorization: Bearer <token>` header to the WorkHub user with that email."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Sign in with Microsoft (send 'Authorization: Bearer <token>')")
    email = _email_from_token(token)
    user = session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None or not user.active:
        raise HTTPException(403, f"No active WorkHub account for {email}")
    return user


router = APIRouter()


@router.get("/me")
def me(
    session: SessionDep, authorization: Annotated[str | None, Header()] = None
) -> dict[str, object]:
    """Who the API thinks you are. Used by the sign-in test page."""
    user = user_from_token(session, authorization)
    return {"name": user.name, "email": user.email, "roles": sorted(roles_of(session, user.id))}


@router.get("/auth-config")
def auth_config() -> dict[str, str]:
    """The two ids the sign-in page needs (so nothing is hard-coded in the HTML)."""
    return {"tenant_id": entra.entra_tenant_id, "client_id": entra.entra_client_id}
