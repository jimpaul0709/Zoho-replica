"""Delegation API (WH-32): hand your approvals to someone for a date range.

Approvals already moved to the delegate stay with them if the delegation is later removed.
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import or_, select

from workhub_api.audit import record, snapshot
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import Delegation, User
from workhub_api.routing import apply_delegations

router = APIRouter(prefix="/delegations", tags=["delegations"])


class DelegationIn(BaseModel):
    to_user_id: int
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def ends_after_start(self) -> "DelegationIn":
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on must not be before starts_on")
        return self


class DelegationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user_id: int
    to_user_id: int
    starts_on: date
    ends_on: date


@router.post("", response_model=DelegationOut, status_code=201)
def create_delegation(body: DelegationIn, session: SessionDep, user: CurrentUser) -> Delegation:
    if body.to_user_id == user.id:
        raise HTTPException(422, "You can't delegate to yourself")
    to = session.get(User, body.to_user_id)
    if to is None or not to.active:
        raise HTTPException(422, "Unknown or inactive user")
    if body.ends_on < date.today():
        raise HTTPException(422, "That delegation is already over")
    delegation = Delegation(from_user_id=user.id, **body.model_dump())
    session.add(delegation)
    session.flush()
    record(
        session,
        actor_id=user.id,
        entity="delegation",
        entity_id=delegation.id,
        action="created",
        after=snapshot(delegation),
    )
    apply_delegations(session)  # a delegation that is already running takes effect now
    session.commit()
    return delegation


@router.get("", response_model=list[DelegationOut])
def my_delegations(session: SessionDep, user: CurrentUser) -> list[Delegation]:
    """Delegations you gave and delegations you received."""
    return list(
        session.scalars(
            select(Delegation)
            .where(or_(Delegation.from_user_id == user.id, Delegation.to_user_id == user.id))
            .order_by(Delegation.starts_on, Delegation.id)
        )
    )


@router.delete("/{delegation_id}", status_code=204)
def remove_delegation(delegation_id: int, session: SessionDep, user: CurrentUser) -> None:
    delegation = session.get(Delegation, delegation_id)
    if delegation is None or delegation.from_user_id != user.id:
        raise HTTPException(404, "Delegation not found")
    before = snapshot(delegation)
    session.delete(delegation)
    session.flush()
    record(
        session,
        actor_id=user.id,
        entity="delegation",
        entity_id=delegation_id,
        action="deleted",
        before=before,
    )
    session.commit()
