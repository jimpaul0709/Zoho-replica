from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from workhub_api.config import settings
from workhub_api.models import User

engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@lru_cache
def _jwks() -> PyJWKClient:
    # PyJWKClient caches Microsoft's public signing keys, so this is not a network call per request.
    return PyJWKClient(
        f"https://login.microsoftonline.com/{settings.entra_tenant_id}/discovery/v2.0/keys"
    )


def _email_from_token(token: str) -> str:
    """Check Microsoft's signature, expiry, audience and issuer; return the signed-in email."""
    tenant, client = settings.entra_tenant_id, settings.entra_client_id
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


def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[int | None, Header()] = None,
) -> User:
    """Who is calling: a Microsoft Entra bearer token, or (DEV_AUTH only) an X-User-Id header."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(401, "Authorization must be 'Bearer <token>'")
        email = _email_from_token(token)
        user = session.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if user is None or not user.active:
            raise HTTPException(403, f"No active WorkHub account for {email}")
        return user
    if not settings.dev_auth:
        raise HTTPException(401, "Sign in with Microsoft (send a Bearer token)")
    user = session.get(User, x_user_id) if x_user_id is not None else None
    if user is None or not user.active:
        raise HTTPException(401, "Send a valid X-User-Id header (dev only)")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
