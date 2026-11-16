"""Edit requests (WH-22): changing a locked week goes through approval.

An approved week is locked. To change it, the employee files an edit request: a reason and a list
of concrete changes (add, update or delete entries). It goes through the normal approval engine, so
the inbox, delegation, escalation and bulk approve all work for it. When it is approved the changes
are applied in one step and the week stays locked.

The time rules (no future dates, 24 h a day, one task or charge code, shared charge codes,
leave/holiday entries are read-only) are checked when the request is filed and again when it is
approved, because things can change in between. Nothing is applied unless every change passes.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, TypeAdapter, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import (
    Approval,
    ApprovalStep,
    EditRequest,
    TimeEntry,
    TimesheetWeek,
    User,
)
from workhub_api.routing import approver_for, due_at_for
from workhub_api.timesheets import READ_ONLY_SOURCES, check_target, week_start_for

router = APIRouter(prefix="/time", tags=["edit requests"])
MAX_DAY = 1440


class AddChange(BaseModel):
    op: Literal["add"]
    work_date: date
    minutes: int = Field(ge=1, le=MAX_DAY)
    task_id: int | None = None
    charge_code_id: int | None = None
    billable: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> "AddChange":
        if (self.task_id is None) == (self.charge_code_id is None):
            raise ValueError("give exactly one of task_id or charge_code_id")
        return self


class UpdateChange(BaseModel):
    op: Literal["update"]
    entry_id: int
    minutes: int | None = Field(default=None, ge=1, le=MAX_DAY)
    billable: bool | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def changes_something(self) -> "UpdateChange":
        given = self.model_fields_set & {"minutes", "billable", "notes"}
        if not given:
            raise ValueError("an update must change minutes, billable or notes")
        if ("minutes" in given and self.minutes is None) or (
            "billable" in given and self.billable is None
        ):
            raise ValueError("minutes and billable can't be null")
        return self


class DeleteChange(BaseModel):
    op: Literal["delete"]
    entry_id: int


Change = Annotated[AddChange | UpdateChange | DeleteChange, Field(discriminator="op")]
CHANGES = TypeAdapter(list[Change])


class EditRequestIn(BaseModel):
    reason: str = Field(min_length=1)
    changes: list[Change] = Field(min_length=1, max_length=50)


class EditRequestOut(BaseModel):
    id: int
    week_id: int
    week_start: date
    reason: str
    status: str
    approval_id: int | None
    changes: list[dict[str, Any]]
    created_at: datetime


def apply_changes(
    session: Session,
    requester: User,
    week: TimesheetWeek,
    stored: list[dict[str, Any]],
    actor: User,
    dry_run: bool,
) -> None:
    """Check every change against the time rules, then (unless `dry_run`) make them all.

    Raises 422 and changes nothing if any change breaks a rule. `actor` is who is recorded in the
    audit log for the changes (the approver, when the request is approved).
    """
    session.execute(select(func.pg_advisory_xact_lock(requester.id)))  # as the time API does
    changes = CHANGES.validate_python(stored)
    entries = {
        e.id: e for e in session.scalars(select(TimeEntry).where(TimeEntry.week_id == week.id))
    }
    week_end = week.week_start + timedelta(days=6)
    totals: dict[date, int] = defaultdict(int)
    for e in entries.values():
        totals[e.work_date] += e.minutes
    touched: set[int] = set()

    def existing(entry_id: int) -> TimeEntry:
        entry = entries.get(entry_id)
        if entry is None:
            raise HTTPException(422, f"Entry {entry_id} is not in this week")
        if entry.source in READ_ONLY_SOURCES:
            raise HTTPException(422, f"Entry {entry_id} comes from {entry.source}; it is read-only")
        if entry_id in touched:
            raise HTTPException(422, f"Entry {entry_id} has more than one change")
        touched.add(entry_id)
        return entry

    for change in changes:
        if isinstance(change, AddChange):
            if not week.week_start <= change.work_date <= week_end:
                raise HTTPException(422, f"{change.work_date} is outside this week")
            if change.work_date > date.today():
                raise HTTPException(422, "Entries can't be for future dates")
            check_target(session, requester, change.task_id, change.charge_code_id)
            totals[change.work_date] += change.minutes
        elif isinstance(change, UpdateChange):
            entry = existing(change.entry_id)
            if change.minutes is not None:
                totals[entry.work_date] += change.minutes - entry.minutes
        else:
            entry = existing(change.entry_id)
            totals[entry.work_date] -= entry.minutes
    for day, total in totals.items():
        if total > MAX_DAY:
            raise HTTPException(422, f"{day} would go over 24 hours")
    if dry_run:
        return

    for change in changes:
        if isinstance(change, AddChange):
            new = TimeEntry(
                user_id=requester.id,
                week_id=week.id,
                source="manual",
                work_date=change.work_date,
                minutes=change.minutes,
                task_id=change.task_id,
                charge_code_id=change.charge_code_id,
                billable=change.billable,
                notes=change.notes,
            )
            session.add(new)
            session.flush()
            record(
                session,
                actor_id=actor.id,
                entity="time_entry",
                entity_id=new.id,
                action="created",
                after=snapshot(new),
            )
        elif isinstance(change, UpdateChange):
            entry = entries[change.entry_id]
            before = snapshot(entry)
            for field in change.model_fields_set & {"minutes", "billable", "notes"}:
                setattr(entry, field, getattr(change, field))
            session.flush()
            record(
                session,
                actor_id=actor.id,
                entity="time_entry",
                entity_id=entry.id,
                action="updated",
                before=before,
                after=snapshot(entry),
            )
        else:
            entry = entries[change.entry_id]
            before = snapshot(entry)
            session.delete(entry)
            session.flush()
            record(
                session,
                actor_id=actor.id,
                entity="time_entry",
                entity_id=change.entry_id,
                action="deleted",
                before=before,
            )


def _outs(session: Session, rows: list[EditRequest]) -> list[EditRequestOut]:
    if not rows:
        return []
    weeks = {
        w.id: w.week_start
        for w in session.scalars(
            select(TimesheetWeek).where(TimesheetWeek.id.in_({r.week_id for r in rows}))
        )
    }
    approvals = {
        a.subject_id: a.id
        for a in session.scalars(
            select(Approval)
            .where(
                Approval.subject_type == "edit_request",
                Approval.subject_id.in_([r.id for r in rows]),
            )
            .order_by(Approval.id)
        )
    }
    return [
        EditRequestOut(
            id=r.id,
            week_id=r.week_id,
            week_start=weeks[r.week_id],
            reason=r.reason,
            status=r.status,
            approval_id=approvals.get(r.id),
            changes=r.changes,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/weeks/{week_start}/edit-requests", response_model=EditRequestOut, status_code=201)
def file_edit_request(
    week_start: date, body: EditRequestIn, session: SessionDep, user: CurrentUser
) -> EditRequestOut:
    if week_start != week_start_for(session, week_start):
        raise HTTPException(422, "week_start must be the first day of a week")
    week = session.scalars(
        select(TimesheetWeek).where(
            TimesheetWeek.user_id == user.id, TimesheetWeek.week_start == week_start
        )
    ).first()
    if week is None or week.status != "approved":
        raise HTTPException(409, "Only an approved (locked) week needs an edit request")
    if user.manager_id is None:
        raise HTTPException(422, "You have no manager to approve this")
    # Lock before checking, so two requests at the same moment can't both see "none pending".
    session.execute(select(func.pg_advisory_xact_lock(user.id)))
    if session.scalar(
        select(EditRequest.id).where(
            EditRequest.week_id == week.id, EditRequest.status == "pending"
        )
    ):
        raise HTTPException(409, "This week already has a pending edit request")

    stored = [c.model_dump(mode="json", exclude_unset=True) for c in body.changes]
    apply_changes(
        session, user, week, stored, actor=user, dry_run=True
    )  # fail early, change nothing
    request = EditRequest(
        week_id=week.id, requester_id=user.id, reason=body.reason, changes=stored, status="pending"
    )
    session.add(request)
    session.flush()
    approval = Approval(
        subject_type="edit_request",
        subject_id=request.id,
        requester_id=user.id,
        approver_id=approver_for(session, user.manager_id, user.id),
        due_at=due_at_for(session, user),
        status="pending",
    )
    session.add(approval)
    session.flush()
    session.add(
        ApprovalStep(
            approval_id=approval.id, actor_id=user.id, action="submitted", comment=body.reason
        )
    )
    for entity, row in (("edit_request", request), ("approval", approval)):
        record(
            session,
            actor_id=user.id,
            entity=entity,
            entity_id=row.id,
            action="created",
            after=snapshot(row),
        )
    session.commit()
    return _outs(session, [request])[0]


@router.get("/edit-requests", response_model=list[EditRequestOut])
def my_edit_requests(session: SessionDep, user: CurrentUser) -> list[EditRequestOut]:
    rows = list(
        session.scalars(
            select(EditRequest)
            .where(EditRequest.requester_id == user.id)
            .order_by(EditRequest.id.desc())
        )
    )
    return _outs(session, rows)


@router.get("/edit-requests/{request_id}", response_model=EditRequestOut)
def get_edit_request(request_id: int, session: SessionDep, user: CurrentUser) -> EditRequestOut:
    """Readable by the requester, the current approver, and anyone who acted on the approval."""
    request = session.get(EditRequest, request_id)
    approval = session.scalars(
        select(Approval)
        .where(Approval.subject_type == "edit_request", Approval.subject_id == request_id)
        .order_by(Approval.id.desc())
    ).first()
    if request is None or approval is None:
        raise HTTPException(404, "Edit request not found")
    actors = set(
        session.scalars(
            select(ApprovalStep.actor_id).where(ApprovalStep.approval_id == approval.id)
        )
    )
    if user.id not in {request.requester_id, approval.approver_id} | actors:
        raise HTTPException(404, "Edit request not found")
    return _outs(session, [request])[0]


@router.post("/edit-requests/{request_id}/cancel", response_model=EditRequestOut)
def cancel_edit_request(request_id: int, session: SessionDep, user: CurrentUser) -> EditRequestOut:
    request = session.get(EditRequest, request_id)
    if request is None or request.requester_id != user.id:
        raise HTTPException(404, "Edit request not found")
    approval = session.scalars(
        select(Approval)
        .where(Approval.subject_type == "edit_request", Approval.subject_id == request_id)
        .order_by(Approval.id.desc())
        .with_for_update()
    ).first()
    if request.status != "pending" or approval is None or approval.status != "pending":
        raise HTTPException(409, f"This request is already {request.status}")
    before_approval, before_request = snapshot(approval), snapshot(request)
    approval.status = "cancelled"
    request.status = "cancelled"
    session.add(ApprovalStep(approval_id=approval.id, actor_id=user.id, action="cancelled"))
    session.flush()
    for entity, row, old in (
        ("approval", approval, before_approval),
        ("edit_request", request, before_request),
    ):
        record(
            session,
            actor_id=user.id,
            entity=entity,
            entity_id=row.id,
            action="cancelled",
            before=old,
            after=snapshot(row),
        )
    session.commit()
    return _outs(session, [request])[0]
