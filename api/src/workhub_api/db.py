from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from workhub_api.config import settings
from workhub_api.models import User

engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def current_user(session: SessionDep, x_user_id: Annotated[int | None, Header()] = None) -> User:
    """Who is calling. Temporary: a dev-only X-User-Id header, until real sign-in lands.

    Sign-in plan: version 1 signs in with email and password; version 2 moves to Microsoft Entra
    ID (WH-04; entra_auth.py is built but not wired in). Either way, replace the body of this
    function; every endpoint already depends on it.
    """
    if not settings.dev_auth:
        raise HTTPException(401, "Sign-in is not available yet (set DEV_AUTH=true for local dev)")
    user = session.get(User, x_user_id) if x_user_id is not None else None
    if user is None or not user.active:
        raise HTTPException(401, "Send a valid X-User-Id header (dev only)")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
