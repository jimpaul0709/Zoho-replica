import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from workhub_api.config import settings
from workhub_api.models import AuthSession, User

engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def hash_token(token: str) -> str:
    """Session tokens are stored only as this hash (see auth.py)."""
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[int | None, Header()] = None,
) -> User:
    """Who is calling: the user behind a Bearer session token (sign-in version 1, auth.py).

    Version 2 moves to Microsoft Entra ID (entra_auth.py, not wired in). With DEV_AUTH on, the
    old X-User-Id header also works so tests and local scripts need no password. Every endpoint
    depends on this one function.
    """
    if authorization and authorization.lower().startswith("bearer "):
        now = datetime.now(UTC)
        row = session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == hash_token(authorization[7:].strip()),
                AuthSession.expires_at > now,
            )
        )
        user = session.get(User, row.user_id) if row else None
        if row is None or user is None or not user.active:
            raise HTTPException(401, "Sign in again")
        row.last_used_at = now
        return user
    if settings.dev_auth and x_user_id is not None:
        user = session.get(User, x_user_id)
        if user is not None and user.active:
            return user
    raise HTTPException(401, "Sign in to continue")


CurrentUser = Annotated[User, Depends(current_user)]
