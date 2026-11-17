"""Approval engine: inbox, approve (locks the week), send back with a reason, history.

WH-30 built approve / send back / history, WH-33 added the deeper inbox: filters and sorting,
each row's age, due date, level and trail (who acted, the comment, how long each step took), and
bulk approve. Weeks, edit requests and leave are handled (leave.py); comp-off plugs in later.
Every action is an approval_step plus audit.

A week can be decided as a whole or day by day (day_decisions.py): approving or sending back the
week is the same thing as doing it for every day that is still waiting.

The inbox loads everything in a handful of queries however many rows it has (not one query per
row), because every database round trip is slow when the database is far away.
"""

from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.day_decisions import decide, returned_reasons, settle, waiting_days
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.edit_requests import apply_changes
from workhub_api.leave import LeaveBrief, approve_leave, briefs, reject_leave
from workhub_api.models import (
    Approval,
    ApprovalStep,
    DayDecision,
    EditRequest,
    TimeEntry,
    TimesheetWeek,
    User,
)
from workhub_api.permissions import Manager

router = APIRouter(prefix="/approvals", tags=["approvals"])


class SendBack(BaseModel):
    reason: str = Field(min_length=1)
    entry_ids: list[int] = []  # entries to pin the reason on; empty pins it on the approval only


class DaySendBack(BaseModel):
    reason: str = Field(min_length=1)
    entry_ids: list[int] = []  # entries of that day to pin the reason on


class BulkApprove(BaseModel):
    approval_ids: list[int] = Field(min_length=1, max_length=100)


class DayOut(BaseModel):
    work_date: date
    minutes: int
    status: str  # pending, approved or sent_back
    reason: str | None


class StepOut(BaseModel):
    actor_id: int
    actor_name: str
    action: str
    comment: str | None
    at: datetime
    minutes_since_previous: int | None  # time taken since the step before; None for the first


class InboxItem(BaseModel):
    approval_id: int
    subject_type: str
    subject_id: int
    requester_id: int
    requester_name: str
    requested_at: datetime
    age_hours: int
    level: int
    due_at: datetime | None
    overdue: bool
    week_start: date | None
    total_minutes: int
    days: list[DayOut]  # each day with time: its minutes and the manager's decision so far
    leave: LeaveBrief | None = None  # set for leave approvals
    timeline: list[StepOut]


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_type: str
    subject_id: int
    status: str
    reason: str | None


class Skipped(BaseModel):
    approval_id: int
    reason: str


class BulkResult(BaseModel):
    approved: list[int]
    skipped: list[Skipped]


def _timelines(session: Session, approval_ids: list[int]) -> dict[int, list[StepOut]]:
    """The steps of each approval, oldest first, with actor names and time between steps."""
    rows = session.execute(
        select(ApprovalStep, User.name)
        .join(User, User.id == ApprovalStep.actor_id)
        .where(ApprovalStep.approval_id.in_(approval_ids))
        .order_by(ApprovalStep.approval_id, ApprovalStep.id)
    ).all()
    out: dict[int, list[StepOut]] = {}
    previous: dict[int, datetime] = {}
    for step, name in rows:
        before = previous.get(step.approval_id)
        taken = None if before is None else max(0, int((step.at - before).total_seconds() // 60))
        previous[step.approval_id] = step.at
        out.setdefault(step.approval_id, []).append(
            StepOut(
                actor_id=step.actor_id,
                actor_name=name,
                action=step.action,
                comment=step.comment,
                at=step.at,
                minutes_since_previous=taken,
            )
        )
    return out


def _days(minutes: dict[date, int], decided: dict[date, DayDecision]) -> list[DayOut]:
    return [
        DayOut(
            work_date=day,
            minutes=total,
            status=decided[day].status if day in decided else "pending",
            reason=decided[day].reason if day in decided else None,
        )
        for day, total in sorted(minutes.items())
    ]


@router.get("/inbox", response_model=list[InboxItem])
def inbox(
    session: SessionDep,
    user: CurrentUser,
    subject_type: str | None = None,
    requester_id: int | None = None,
    overdue: bool = False,
    sort: Literal["oldest", "newest", "due"] = "oldest",
) -> list[InboxItem]:
    """Pending approvals assigned to you. Filter by type or requester, only overdue, and sort."""
    now = datetime.now(UTC)
    query = select(Approval).where(Approval.approver_id == user.id, Approval.status == "pending")
    if subject_type is not None:
        query = query.where(Approval.subject_type == subject_type)
    if requester_id is not None:
        query = query.where(Approval.requester_id == requester_id)
    if overdue:
        query = query.where(Approval.due_at.is_not(None), Approval.due_at < now)
    order = {
        "oldest": (Approval.created_at, Approval.id),
        "newest": (Approval.created_at.desc(), Approval.id.desc()),
        "due": (Approval.due_at.asc().nulls_last(), Approval.id),
    }[sort]
    approvals = list(session.scalars(query.order_by(*order)))
    if not approvals:
        return []

    names = {
        r[0]: r[1]
        for r in session.execute(
            select(User.id, User.name).where(User.id.in_({a.requester_id for a in approvals}))
        )
    }
    request_week = {  # an edit request shows the week it wants to change
        r.id: r.week_id
        for r in session.scalars(
            select(EditRequest).where(
                EditRequest.id.in_(
                    [a.subject_id for a in approvals if a.subject_type == "edit_request"]
                )
            )
        )
    }
    week_of = {
        a.id: a.subject_id if a.subject_type == "week" else request_week.get(a.subject_id)
        for a in approvals
    }
    week_ids = [w for w in week_of.values() if w is not None]
    weeks = {
        w.id: w
        for w in session.scalars(select(TimesheetWeek).where(TimesheetWeek.id.in_(week_ids)))
    }
    minutes: dict[int, dict[date, int]] = {}
    for entry_week, day, total in session.execute(
        select(TimeEntry.week_id, TimeEntry.work_date, func.sum(TimeEntry.minutes))
        .where(TimeEntry.week_id.in_(week_ids))
        .group_by(TimeEntry.week_id, TimeEntry.work_date)
    ):
        minutes.setdefault(entry_week, {})[day] = int(total)
    decided: dict[int, dict[date, DayDecision]] = {}
    for decision in session.scalars(select(DayDecision).where(DayDecision.week_id.in_(week_ids))):
        decided.setdefault(decision.week_id, {})[decision.work_date] = decision
    timelines = _timelines(session, [a.id for a in approvals])
    leave_ids = [a.subject_id for a in approvals if a.subject_type == "leave"]
    leave_briefs = briefs(session, leave_ids) if leave_ids else {}

    items: list[InboxItem] = []
    for a in approvals:
        week_id = week_of[a.id]
        week = weeks.get(week_id) if week_id is not None else None
        items.append(
            InboxItem(
                approval_id=a.id,
                subject_type=a.subject_type,
                subject_id=a.subject_id,
                requester_id=a.requester_id,
                requester_name=names.get(a.requester_id, ""),
                requested_at=a.created_at,
                age_hours=max(0, int((now - a.created_at).total_seconds() // 3600)),
                level=a.level,
                due_at=a.due_at,
                overdue=a.due_at is not None and a.due_at < now,
                week_start=week.week_start if week else None,
                total_minutes=sum(minutes.get(week_id, {}).values()) if week_id is not None else 0,
                days=_days(minutes.get(week_id, {}), decided.get(week_id, {}))
                if week_id is not None
                else [],
                leave=leave_briefs.get(a.subject_id) if a.subject_type == "leave" else None,
                timeline=timelines.get(a.id, []),
            )
        )
    return items


def _my_pending(session: Session, user: User, approval_id: int) -> Approval:
    """Load (and lock) a pending approval that is assigned to `user`."""
    approval = session.scalars(
        select(Approval).where(Approval.id == approval_id).with_for_update()
    ).first()
    if approval is None or approval.approver_id != user.id:
        raise HTTPException(404, "Approval not found")
    if approval.status != "pending":
        raise HTTPException(409, f"Already {approval.status}")
    return approval


def _week_of(session: Session, approval: Approval) -> TimesheetWeek:
    week = (  # locked, so an edit in progress finishes first and we decide on what is really there
        session.get(TimesheetWeek, approval.subject_id, with_for_update=True)
        if approval.subject_type == "week"
        else None
    )
    if week is None:
        raise HTTPException(422, f"'{approval.subject_type}' approvals are not supported yet")
    return week


def _request_of(session: Session, approval: Approval) -> EditRequest:
    request = session.get(EditRequest, approval.subject_id)
    if request is None:
        raise HTTPException(409, "The edit request no longer exists")
    return request


def _log(
    session: Session,
    user: User,
    approval: Approval,
    subject: TimesheetWeek | EditRequest,
    action: str,
    before: tuple[dict[str, object], dict[str, object]],
    comment: str | None = None,
) -> None:
    session.add(
        ApprovalStep(approval_id=approval.id, actor_id=user.id, action=action, comment=comment)
    )
    session.flush()
    subject_entity = "edit_request" if isinstance(subject, EditRequest) else "timesheet_week"
    for entity, row, old in (
        ("approval", approval, before[0]),
        (subject_entity, subject, before[1]),
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


def _finish(
    session: Session,
    user: User,
    approval: Approval,
    week: TimesheetWeek,
    before: tuple[dict[str, object], dict[str, object]],
    reason: str | None = None,
) -> None:
    """Close the approval once every day is decided. Until then it stays pending.

    All days approved: the week is approved and locked (changes need an edit request). Any day
    sent back: the week goes back to draft for the employee to fix and resubmit."""
    outcome = settle(session, week.id)
    if outcome == "pending":
        return
    if outcome == "approved":
        approval.status = "approved"
        week.status = "approved"
        week.locked_at = datetime.now(UTC)
        _log(session, user, approval, week, "approved", before)
        return
    approval.status = "sent_back"
    approval.reason = reason or returned_reasons(session, week.id)
    week.status = "draft"
    _log(session, user, approval, week, "sent_back", before, comment=approval.reason)


def _entries_to_pin(
    session: Session, week: TimesheetWeek, ids: set[int], day: date | None = None
) -> list[TimeEntry]:
    query = select(TimeEntry).where(TimeEntry.id.in_(ids), TimeEntry.week_id == week.id)
    if day is not None:
        query = query.where(TimeEntry.work_date == day)
    entries = list(session.scalars(query))
    if len(entries) != len(ids):
        raise HTTPException(
            422,
            "Some entries don't belong to that day"
            if day
            else "Some entries don't belong to this week",
        )
    return entries


def _approve(session: Session, user: User, approval_id: int) -> Approval:
    """Approve one approval. A week gets locked; an edit request gets its changes applied (and
    stays pending, with the reason, if they no longer pass the rules). The caller commits."""
    approval = _my_pending(session, user, approval_id)
    if approval.subject_type == "edit_request":
        request = _request_of(session, approval)
        week = session.get(TimesheetWeek, request.week_id)
        requester = session.get(User, request.requester_id)
        if week is None or requester is None:
            raise HTTPException(409, "The week or the requester no longer exists")
        edit_before = (snapshot(approval), snapshot(request))
        apply_changes(session, requester, week, request.changes, actor=user, dry_run=False)
        approval.status = "approved"
        request.status = "approved"
        _log(session, user, approval, request, "approved", edit_before)
        return approval
    if approval.subject_type == "leave":
        approve_leave(session, user, approval)
        return approval
    week = _week_of(session, approval)
    if not session.scalar(
        select(func.count()).select_from(TimeEntry).where(TimeEntry.week_id == week.id)
    ):  # the employee can edit until approval, including deleting everything
        raise HTTPException(
            409, "This week has no entries any more, so there is nothing to approve"
        )
    before = (snapshot(approval), snapshot(week))
    decide(session, user, week, waiting_days(session, week.id), "approved")
    _finish(session, user, approval, week, before)
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(approval_id: int, session: SessionDep, user: Manager) -> Approval:
    approval = _approve(session, user, approval_id)
    session.commit()
    return approval


@router.post("/bulk-approve", response_model=BulkResult)
def bulk_approve(body: BulkApprove, session: SessionDep, user: Manager) -> BulkResult:
    """Approve many at once. One that can't be approved is skipped, with the reason, and the
    others still go through. Each approval is all-or-nothing on its own (a savepoint)."""
    approved: list[int] = []
    skipped: list[Skipped] = []
    for approval_id in dict.fromkeys(body.approval_ids):  # drop repeats, keep the order
        try:
            with session.begin_nested():
                _approve(session, user, approval_id)
        except HTTPException as exc:
            skipped.append(Skipped(approval_id=approval_id, reason=str(exc.detail)))
        else:
            approved.append(approval_id)
    session.commit()
    return BulkResult(approved=approved, skipped=skipped)


@router.post("/{approval_id}/send-back", response_model=ApprovalOut)
def send_back(approval_id: int, body: SendBack, session: SessionDep, user: Manager) -> Approval:
    approval = _my_pending(session, user, approval_id)
    if approval.subject_type == "edit_request":
        if body.entry_ids:
            raise HTTPException(422, "Entries can't be pinned on an edit request")
        request = _request_of(session, approval)
        edit_before = (snapshot(approval), snapshot(request))
        approval.status = "sent_back"
        approval.reason = body.reason
        request.status = "rejected"  # the week stays locked and unchanged
        _log(session, user, approval, request, "sent_back", edit_before, comment=body.reason)
        session.commit()
        return approval
    if approval.subject_type == "leave":
        if body.entry_ids:
            raise HTTPException(422, "Entries can't be pinned on a leave request")
        reject_leave(session, user, approval, body.reason)
        session.commit()
        return approval
    week = _week_of(session, approval)
    entries = _entries_to_pin(session, week, set(body.entry_ids))
    before = (snapshot(approval), snapshot(week))
    decide(session, user, week, waiting_days(session, week.id), "sent_back", body.reason)
    for entry in entries:
        entry.sent_back_reason = body.reason
    _finish(session, user, approval, week, before, reason=body.reason)  # closes: nothing waits
    session.commit()
    return approval


@router.post("/{approval_id}/days/{work_date}/approve", response_model=ApprovalOut)
def approve_day(approval_id: int, work_date: date, session: SessionDep, user: Manager) -> Approval:
    """Approve one day. That day is locked. The approval closes once every day is decided."""
    approval = _my_pending(session, user, approval_id)
    week = _week_of(session, approval)
    before = (snapshot(approval), snapshot(week))
    decide(session, user, week, [work_date], "approved")
    session.add(
        ApprovalStep(
            approval_id=approval.id, actor_id=user.id, action="day_approved", comment=str(work_date)
        )
    )
    _finish(session, user, approval, week, before)
    session.commit()
    return approval


@router.post("/{approval_id}/days/{work_date}/send-back", response_model=ApprovalOut)
def send_back_day(
    approval_id: int, work_date: date, body: DaySendBack, session: SessionDep, user: Manager
) -> Approval:
    """Send one day back with a reason. The employee fixes it; the other days carry on."""
    approval = _my_pending(session, user, approval_id)
    week = _week_of(session, approval)
    entries = _entries_to_pin(session, week, set(body.entry_ids), work_date)
    before = (snapshot(approval), snapshot(week))
    decide(session, user, week, [work_date], "sent_back", body.reason)
    for entry in entries:
        entry.sent_back_reason = body.reason
    session.add(
        ApprovalStep(
            approval_id=approval.id,
            actor_id=user.id,
            action="day_sent_back",
            comment=f"{work_date}: {body.reason}",
        )
    )
    _finish(session, user, approval, week, before)
    session.commit()
    return approval


@router.get("/{approval_id}/history", response_model=list[StepOut])
def history(approval_id: int, session: SessionDep, user: CurrentUser) -> list[StepOut]:
    """The trail of an approval. Readable by the requester, the current approver, and anyone who
    acted on it (so a manager who delegated it can still see what happened)."""
    approval = session.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(404, "Approval not found")
    steps = _timelines(session, [approval_id]).get(approval_id, [])
    allowed = {approval.requester_id, approval.approver_id} | {s.actor_id for s in steps}
    if user.id not in allowed:
        raise HTTPException(404, "Approval not found")
    return steps
