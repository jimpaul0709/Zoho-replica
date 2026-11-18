"""Sign-in version 1: email and password (WH-04). Version 2 (Microsoft Entra ID) is entra_auth.py.

Login returns a random token; only its SHA-256 is stored (AuthSession). The client sends it as
`Authorization: Bearer <token>`, and db.current_user turns it back into a user.

shortcut: the failed-attempt lock is per account (5 failures, 15 minutes), not per IP; add an IP
limit at the proxy before exposing this to the internet.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from workhub_api.db import CurrentUser, SessionDep, hash_token
from workhub_api.models import AuthSession, Credential, User
from workhub_api.permissions import roles_of

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_DAYS = 7
MAX_FAILURES = 5
LOCK_MINUTES = 15
BAD_LOGIN = "Wrong email or password"  # same text for unknown email and wrong password


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except ValueError:
        return False


_DUMMY = hash_password("not-a-real-password")  # so an unknown email costs the same time


class LoginBody(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    expires_at: datetime


class MeOut(BaseModel):
    id: int
    name: str
    email: str
    roles: list[str]


class PasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/login")
def login(body: LoginBody, session: SessionDep) -> LoginOut:
    now = datetime.now(UTC)
    user = session.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    cred = session.scalar(select(Credential).where(Credential.user_id == user.id)) if user else None
    if cred and cred.locked_until and cred.locked_until > now:
        raise HTTPException(429, "Too many wrong attempts. Try again in a few minutes.")
    ok = verify_password(body.password, cred.password_hash if cred else _DUMMY)
    if not (ok and user and cred and user.active):
        if cred:
            cred.failed_attempts += 1
            if cred.failed_attempts >= MAX_FAILURES:
                cred.failed_attempts = 0
                cred.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            session.commit()  # keep the count even though this request fails
        raise HTTPException(401, BAD_LOGIN)
    cred.failed_attempts = 0
    cred.locked_until = None
    token = secrets.token_urlsafe(32)
    expires = now + timedelta(days=SESSION_DAYS)
    session.add(AuthSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires))
    session.commit()
    return LoginOut(token=token, expires_at=expires)


def _bearer(authorization: str | None) -> str:
    return (authorization or "")[7:].strip()


@router.post("/logout", status_code=204)
def logout(
    session: SessionDep,
    _user: CurrentUser,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    session.execute(
        delete(AuthSession).where(AuthSession.token_hash == hash_token(_bearer(authorization)))
    )
    session.commit()
    return Response(status_code=204)


@router.get("/me")
def me(session: SessionDep, user: CurrentUser) -> MeOut:
    return MeOut(
        id=user.id, name=user.name, email=user.email, roles=sorted(roles_of(session, user.id))
    )


@router.post("/password", status_code=204)
def change_password(
    body: PasswordBody,
    session: SessionDep,
    user: CurrentUser,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    cred = session.scalar(select(Credential).where(Credential.user_id == user.id))
    if cred is None or not verify_password(body.current_password, cred.password_hash):
        raise HTTPException(400, "Current password is wrong")
    cred.password_hash = hash_password(body.new_password)
    cred.must_change = False
    # Sign every other browser out; this one stays.
    session.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user.id,
            AuthSession.token_hash != hash_token(_bearer(authorization)),
        )
    )
    session.commit()
    return Response(status_code=204)
