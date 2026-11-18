"""User administration (HR and admin): create staff, edit them, set roles and passwords, deactivate.

HR and admin can manage users, but only an admin can grant or remove the admin role, or reset an
admin's password (otherwise HR could make themselves an admin). Every change is audited, and no
password or hash ever goes into the audit log or a response.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.auth import hash_password
from workhub_api.db import SessionDep
from workhub_api.models import AuthSession, Credential, RoleAssignment, User
from workhub_api.permissions import require_roles, roles_of

router = APIRouter(prefix="/admin/users", tags=["admin"])
Staff = Annotated[User, Depends(require_roles("hr", "admin"))]

ROLES = {"employee", "manager", "hr", "finance", "admin"}


def _check_roles(roles: list[str]) -> list[str]:
    unknown = set(roles) - ROLES
    if unknown:
        raise ValueError("unknown role: " + ", ".join(sorted(unknown)))
    return roles


class UserOut(BaseModel):
    id: int
    employee_code: str
    name: str
    email: str
    designation: str | None
    department: str | None
    location_id: int | None
    manager_id: int | None
    joined_on: date | None
    exited_on: date | None
    active: bool
    roles: list[str]


class UserIn(BaseModel):
    employee_code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)  # the first one; the person must change it
    designation: str | None = None
    department: str | None = None
    location_id: int | None = None
    manager_id: int | None = None
    joined_on: date | None = None
    roles: list[str] = Field(default_factory=lambda: ["employee"], min_length=1)

    _roles = field_validator("roles")(_check_roles)


class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    designation: str | None = None
    department: str | None = None
    location_id: int | None = None
    manager_id: int | None = None
    joined_on: date | None = None
    active: bool | None = None


class RolesIn(BaseModel):
    roles: list[str] = Field(min_length=1)

    _roles = field_validator("roles")(_check_roles)


class PasswordIn(BaseModel):
    password: str = Field(min_length=8)


def _to_out(user: User, roles: list[str]) -> UserOut:
    return UserOut(
        id=user.id,
        employee_code=user.employee_code,
        name=user.name,
        email=user.email,
        designation=user.designation,
        department=user.department,
        location_id=user.location_id,
        manager_id=user.manager_id,
        joined_on=user.joined_on,
        exited_on=user.exited_on,
        active=user.active,
        roles=sorted(roles),
    )


def _out(session: Session, user: User) -> UserOut:
    return _to_out(user, list(roles_of(session, user.id)))


def _user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "No such user")
    return user


def _need_admin(session: Session, actor: User, touches_admin: bool) -> None:
    if touches_admin and "admin" not in roles_of(session, actor.id):
        raise HTTPException(403, "Only an admin can do that to an admin account")


def _check_manager(session: Session, manager_id: int, user_id: int | None) -> None:
    """The manager must be an active person and must not (even indirectly) report to this user."""
    manager = session.get(User, manager_id)
    if manager is None or not manager.active:
        raise HTTPException(422, "Manager must be an existing, active user")
    node: User | None = manager
    for _ in range(100):  # a longer chain than this is already broken data
        if node is None:
            return
        if node.id == user_id:
            raise HTTPException(422, "That would make a loop in the management chain")
        node = session.get(User, node.manager_id) if node.manager_id else None


@router.post("", status_code=201)
def create_user(body: UserIn, session: SessionDep, actor: Staff) -> UserOut:
    _need_admin(session, actor, "admin" in body.roles)
    clash = session.scalar(
        select(User.id).where(
            (func.upper(User.employee_code) == body.employee_code.upper())
            | (func.lower(User.email) == body.email.lower())
        )
    )
    if clash is not None:
        raise HTTPException(409, "That employee code or email is already in use")
    if body.manager_id is not None:
        _check_manager(session, body.manager_id, None)
    user = User(**body.model_dump(exclude={"password", "roles"}))
    session.add(user)
    session.flush()
    session.add_all(RoleAssignment(user_id=user.id, role=r) for r in body.roles)
    session.add(
        Credential(user_id=user.id, password_hash=hash_password(body.password), must_change=True)
    )
    record(
        session,
        actor_id=actor.id,
        entity="app_user",
        entity_id=user.id,
        action="create",
        after={**snapshot(user), "roles": sorted(body.roles)},
    )
    session.commit()
    return _out(session, user)


@router.get("")
def list_users(session: SessionDep, _actor: Staff) -> list[UserOut]:
    roles: dict[int, list[str]] = {}
    for user_id, role in session.execute(select(RoleAssignment.user_id, RoleAssignment.role)):
        roles.setdefault(user_id, []).append(role)
    users = session.scalars(select(User).order_by(User.employee_code))
    return [_to_out(u, roles.get(u.id, [])) for u in users]


@router.patch("/{user_id}")
def edit_user(user_id: int, body: UserPatch, session: SessionDep, actor: Staff) -> UserOut:
    user = _user(session, user_id)
    before = snapshot(user)
    sent = body.model_fields_set
    if "manager_id" in sent and body.manager_id is not None:
        _check_manager(session, body.manager_id, user.id)
    if body.active is False and user.id == actor.id:
        raise HTTPException(422, "You cannot deactivate yourself")
    for field in sent - {"active"}:
        setattr(user, field, getattr(body, field))
    if body.active is not None:
        user.active = body.active
        if body.active:
            user.exited_on = None
        else:
            user.exited_on = user.exited_on or date.today()
            session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    record(
        session,
        actor_id=actor.id,
        entity="app_user",
        entity_id=user.id,
        action="update",
        before=before,
        after=snapshot(user),
    )
    session.commit()
    return _out(session, user)


@router.put("/{user_id}/roles")
def set_roles(user_id: int, body: RolesIn, session: SessionDep, actor: Staff) -> UserOut:
    user = _user(session, user_id)
    old, new = roles_of(session, user.id), set(body.roles)
    _need_admin(session, actor, "admin" in (old ^ new))
    session.execute(
        delete(RoleAssignment).where(
            RoleAssignment.user_id == user.id, RoleAssignment.role.not_in(new)
        )
    )
    session.add_all(RoleAssignment(user_id=user.id, role=r) for r in new - old)
    record(
        session,
        actor_id=actor.id,
        entity="app_user",
        entity_id=user.id,
        action="update",
        before={"roles": sorted(old)},
        after={"roles": sorted(new)},
    )
    session.commit()
    return _out(session, user)


@router.post("/{user_id}/password", status_code=204)
def reset_password(user_id: int, body: PasswordIn, session: SessionDep, actor: Staff) -> Response:
    """Set a new password the person must change at once; signs them out everywhere."""
    user = _user(session, user_id)
    _need_admin(session, actor, "admin" in roles_of(session, user.id) and user.id != actor.id)
    cred = session.scalar(select(Credential).where(Credential.user_id == user.id))
    if cred is None:
        cred = Credential(user_id=user.id, password_hash="")
        session.add(cred)
    cred.password_hash = hash_password(body.password)
    cred.must_change = True
    cred.failed_attempts = 0
    cred.locked_until = None
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    record(
        session,
        actor_id=actor.id,
        entity="app_user",
        entity_id=user.id,
        action="password_reset",
    )
    session.commit()
    return Response(status_code=204)
