"""Approval engine v1 (WH-30): inbox, approve (locks the week), send back with a reason, history.

Only weeks are handled for now; leave, comp-off and edit requests plug in with their features.
Delegation and escalation routing come with WH-32. Every action is an approval_step plus audit.
"""

from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import Approval, ApprovalStep, TimeEntry, TimesheetWeek, User

router = APIRouter(prefix="/approvals", tags=["approvals"])


class SendBack(BaseModel):
    reason: str = Field(min_length=1)
    entry_ids: list[int] = []  # entries to pin the reason on; empty pins it on the approval only


class InboxItem(BaseModel):
    approval_id: int
    subject_type: str
    subject_id: int
    requester_id: int
    requester_name: str
    requested_at: datetime
    week_start: date | None
    total_minutes: int


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_type: str
    subject_id: int
    status: str
    reason: str | None


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor_id: int
    action: str
    comment: str | None
    at: datetime


@router.get("/inbox", response_model=list[InboxItem])
def inbox(session: SessionDep, user: CurrentUser) -> list[InboxItem]:
    pending = session.scalars(
        select(Approval)
        .where(Approval.approver_id == user.id, Approval.status == "pending")
        .order_by(Approval.created_at)
    )
    items: list[InboxItem] = []
    for a in pending:
        requester = session.get(User, a.requester_id)
        week = session.get(TimesheetWeek, a.subject_id) if a.subject_type == "week" else None
        total = (
            session.scalar(
                select(func.coalesce(func.sum(TimeEntry.minutes), 0)).where(
                    TimeEntry.week_id == week.id
                )
            )
            if week
            else 0
        )
        items.append(
            InboxItem(
                approval_id=a.id,
                subject_type=a.subject_type,
                subject_id=a.subject_id,
                requester_id=a.requester_id,
                requester_name=requester.name if requester else "",
                requested_at=a.created_at,
                week_start=week.week_start if week else None,
                total_minutes=int(total or 0),
            )
        )
    return items


def _my_pending_week(
    session: Session, user: User, approval_id: int
) -> tuple[Approval, TimesheetWeek]:
    """Load (and lock) a pending week approval that is assigned to `user`."""
    approval = session.scalars(
        select(Approval).where(Approval.id == approval_id).with_for_update()
    ).first()
    if approval is None or approval.approver_id != user.id:
        raise HTTPException(404, "Approval not found")
    if approval.status != "pending":
        raise HTTPException(409, f"Already {approval.status}")
    week = (
        session.get(TimesheetWeek, approval.subject_id) if approval.subject_type == "week" else None
    )
    if week is None:
        raise HTTPException(422, f"'{approval.subject_type}' approvals are not supported yet")
    return approval, week


def _log(
    session: Session,
    user: User,
    approval: Approval,
    week: TimesheetWeek,
    action: str,
    before: tuple[dict[str, object], dict[str, object]],
    comment: str | None = None,
) -> None:
    session.add(
        ApprovalStep(approval_id=approval.id, actor_id=user.id, action=action, comment=comment)
    )
    session.flush()
    for entity, row, old in (
        ("approval", approval, before[0]),
        ("timesheet_week", week, before[1]),
    ):
        record(
            session,
            actor_id=user.id,
            entity=entity,
            entity_id=row.id,
            action=action,
            before=old,
            after=snapshot(row),
        )


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(approval_id: int, session: SessionDep, user: CurrentUser) -> Approval:
    approval, week = _my_pending_week(session, user, approval_id)
    before = (snapshot(approval), snapshot(week))
    approval.status = "approved"
    week.status = "approved"
    week.locked_at = datetime.now(UTC)  # an approved week is locked; changes need an edit request
    _log(session, user, approval, week, "approved", before)
    session.commit()
    return approval


@router.post("/{approval_id}/send-back", response_model=ApprovalOut)
def send_back(approval_id: int, body: SendBack, session: SessionDep, user: CurrentUser) -> Approval:
    approval, week = _my_pending_week(session, user, approval_id)
    ids = set(body.entry_ids)
    entries = list(
        session.scalars(
            select(TimeEntry).where(TimeEntry.id.in_(ids), TimeEntry.week_id == week.id)
        )
    )
    if len(entries) != len(ids):
        raise HTTPException(422, "Some entries don't belong to this week")
    before = (snapshot(approval), snapshot(week))
    for entry in entries:
        entry.sent_back_reason = body.reason
    approval.status = "sent_back"
    approval.reason = body.reason
    week.status = "draft"  # back to the employee to fix and resubmit
    _log(session, user, approval, week, "sent_back", before, comment=body.reason)
    session.commit()
    return approval


@router.get("/{approval_id}/history", response_model=list[StepOut])
def history(approval_id: int, session: SessionDep, user: CurrentUser) -> list[ApprovalStep]:
    approval = session.get(Approval, approval_id)
    if approval is None or user.id not in (approval.requester_id, approval.approver_id):
        raise HTTPException(404, "Approval not found")
    return list(
        session.scalars(
            select(ApprovalStep)
            .where(ApprovalStep.approval_id == approval_id)
            .order_by(ApprovalStep.id)
        )
    )
