"""Time API (WH-20): entries, week view, rules, submit.

Rules (design spec 6.3): no future dates, a day can't pass 24 h, each entry has exactly one
task or charge code, charge codes only for teams they are shared with, leave/holiday entries are
read-only, and a week can be changed until it is approved (draft or submitted). Approving locks it;
after that only an edit request (WH-22) can change it.
"""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.day_decisions import check_day_open, decisions_of, reopen_returned
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import (
    Approval,
    ApprovalStep,
    ChargeCode,
    ChargeCodeTeam,
    OrgSettings,
    TeamMember,
    TimeEntry,
    TimesheetWeek,
    User,
)
from workhub_api.routing import approver_for, week_due_at
from workhub_api.visibility import can_see_task

router = APIRouter(prefix="/time", tags=["time"])

READ_ONLY_SOURCES = ("leave", "holiday")


class EntryIn(BaseModel):
    work_date: date
    minutes: int = Field(ge=1, le=1440)
    task_id: int | None = None
    charge_code_id: int | None = None
    billable: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> "EntryIn":
        if (self.task_id is None) == (self.charge_code_id is None):
            raise ValueError("give exactly one of task_id or charge_code_id")
        return self


class EntryPatch(BaseModel):
    minutes: int | None = Field(default=None, ge=1, le=1440)
    billable: bool | None = None
    notes: str | None = None


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_date: date
    minutes: int
    task_id: int | None
    charge_code_id: int | None
    billable: bool
    notes: str | None
    source: str
    sent_back_reason: str | None


class WeekOut(BaseModel):
    week_start: date
    status: str
    locked: bool
    entries: list[EntryOut]
    day_minutes: dict[date, int]
    day_status: dict[date, str]  # draft, submitted, approved or sent_back, for each day with time
    day_reasons: dict[date, str]  # why a day was sent back
    approved_minutes: int  # minutes on days the manager has approved


def week_start_for(session: Session, day: date) -> date:
    """First day of the week containing `day`, following org_settings (Monday by default)."""
    org = session.scalars(select(OrgSettings).limit(1)).first()
    offset = (day.weekday() + 1) % 7 if org and org.week_start == "Sunday" else day.weekday()
    return day - timedelta(days=offset)


def _find_week(session: Session, user: User, start: date) -> TimesheetWeek | None:
    return session.scalars(
        select(TimesheetWeek).where(
            TimesheetWeek.user_id == user.id, TimesheetWeek.week_start == start
        )
    ).first()


def _editable_week(session: Session, user: User, day: date) -> TimesheetWeek:
    """The user's week for `day` (created as draft if new); 409 once it is approved (locked)."""
    # One writer per user at a time until commit: stops two requests both passing the 24 h check.
    session.execute(select(func.pg_advisory_xact_lock(user.id)))
    start = week_start_for(session, day)
    week = session.scalars(
        select(TimesheetWeek)
        .where(TimesheetWeek.user_id == user.id, TimesheetWeek.week_start == start)
        .with_for_update()  # an approval at the same moment waits for this edit, or we see it
    ).first()
    if week is None:
        week = TimesheetWeek(user_id=user.id, week_start=start, status="draft")
        session.add(week)
        session.flush()
    if week.status not in ("draft", "submitted"):
        raise HTTPException(409, f"Week is {week.status}; it is locked (file an edit request)")
    return week


def _day_total(session: Session, user: User, day: date, skip_id: int | None = None) -> int:
    q = select(func.coalesce(func.sum(TimeEntry.minutes), 0)).where(
        TimeEntry.user_id == user.id, TimeEntry.work_date == day
    )
    if skip_id is not None:
        q = q.where(TimeEntry.id != skip_id)
    return int(session.scalar(q) or 0)


def check_target(
    session: Session, user: User, task_id: int | None, charge_code_id: int | None
) -> None:
    """The task must exist; a charge code must exist, be active and be shared with their team."""
    if task_id is not None:
        if not can_see_task(
            session, user, task_id
        ):  # a private task looks the same as a missing one
            raise HTTPException(422, "Unknown task, or it is not assigned to you")
        return
    code = session.get(ChargeCode, charge_code_id) if charge_code_id else None
    if code is None or not code.active:
        raise HTTPException(422, "Unknown or inactive charge code")
    shared = session.scalars(
        select(ChargeCodeTeam.team_id)
        .join(TeamMember, TeamMember.team_id == ChargeCodeTeam.team_id)
        .where(ChargeCodeTeam.charge_code_id == code.id, TeamMember.user_id == user.id)
    ).first()
    if shared is None:
        raise HTTPException(422, "This charge code is not shared with your team")


def _own_entry(session: Session, user: User, entry_id: int) -> TimeEntry:
    entry = session.get(TimeEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    if entry.source in READ_ONLY_SOURCES:
        raise HTTPException(409, f"Entries from {entry.source} are read-only")
    return entry


def _audit(session: Session, user: User, entity: str, row: Any, action: str, before: Any) -> None:
    record(
        session,
        actor_id=user.id,
        entity=entity,
        entity_id=row.id,
        action=action,
        before=before,
        after=None if action == "deleted" else snapshot(row),
    )


@router.get("/week", response_model=WeekOut)
def get_week(session: SessionDep, user: CurrentUser, on: date | None = None) -> WeekOut:
    start = week_start_for(session, on or date.today())
    week = _find_week(session, user, start)
    entries = (
        list(
            session.scalars(
                select(TimeEntry)
                .where(TimeEntry.week_id == week.id)
                .order_by(TimeEntry.work_date, TimeEntry.id)
            )
        )
        if week
        else []
    )
    totals: dict[date, int] = {}
    for e in entries:
        totals[e.work_date] = totals.get(e.work_date, 0) + e.minutes
    decided = decisions_of(session, week.id) if week else {}
    waiting = week.status if week and week.status in ("submitted", "approved") else "draft"
    day_status = {day: decided[day].status if day in decided else waiting for day in totals}
    day_reasons = {
        day: d.reason
        for day, d in decided.items()
        if d.status == "sent_back" and d.reason and day in totals
    }
    return WeekOut(
        week_start=start,
        status=week.status if week else "draft",
        locked=bool(week and week.locked_at),
        entries=[EntryOut.model_validate(e) for e in entries],
        day_minutes=totals,
        day_status=day_status,
        day_reasons=day_reasons,
        approved_minutes=sum(m for day, m in totals.items() if day_status[day] == "approved"),
    )


@router.post("/entries", response_model=EntryOut, status_code=201)
def add_entry(body: EntryIn, session: SessionDep, user: CurrentUser) -> TimeEntry:
    if body.work_date > date.today():  # shortcut: server date, not the user's timezone
        raise HTTPException(422, "Entries can't be for future dates")
    check_target(session, user, body.task_id, body.charge_code_id)
    week = _editable_week(session, user, body.work_date)
    check_day_open(session, week.id, body.work_date)
    if _day_total(session, user, body.work_date) + body.minutes > 1440:
        raise HTTPException(422, "A day can't go over 24 hours")
    entry = TimeEntry(user_id=user.id, week_id=week.id, source="manual", **body.model_dump())
    session.add(entry)
    session.flush()
    _audit(session, user, "time_entry", entry, "created", None)
    session.commit()
    return entry


@router.patch("/entries/{entry_id}", response_model=EntryOut)
def edit_entry(
    entry_id: int, body: EntryPatch, session: SessionDep, user: CurrentUser
) -> TimeEntry:
    entry = _own_entry(session, user, entry_id)
    week = _editable_week(session, user, entry.work_date)
    check_day_open(session, week.id, entry.work_date)
    before = snapshot(entry)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("minutes") is not None and (
        _day_total(session, user, entry.work_date, skip_id=entry.id) + changes["minutes"] > 1440
    ):
        raise HTTPException(422, "A day can't go over 24 hours")
    for key, value in changes.items():
        if value is not None or key == "notes":  # notes may be cleared; the rest can't be null
            setattr(entry, key, value)
    session.flush()
    _audit(session, user, "time_entry", entry, "updated", before)
    session.commit()
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int, session: SessionDep, user: CurrentUser) -> None:
    entry = _own_entry(session, user, entry_id)
    week = _editable_week(session, user, entry.work_date)
    check_day_open(session, week.id, entry.work_date)
    before = snapshot(entry)
    session.delete(entry)
    session.flush()
    _audit(session, user, "time_entry", entry, "deleted", before)
    session.commit()


@router.post("/weeks/{week_start}/submit", response_model=WeekOut)
def submit_week(week_start: date, session: SessionDep, user: CurrentUser) -> WeekOut:
    if week_start != week_start_for(session, week_start):
        raise HTTPException(422, "week_start must be the first day of a week")
    week = _find_week(session, user, week_start)
    if week is None or not session.scalar(
        select(func.count()).select_from(TimeEntry).where(TimeEntry.week_id == week.id)
    ):
        raise HTTPException(422, "Nothing to submit: this week has no entries")
    if week.status != "draft":
        raise HTTPException(409, f"Week is already {week.status}")
    if user.manager_id is None:
        raise HTTPException(422, "You have no manager to approve this week")
    before = snapshot(week)
    reopen_returned(session, user, week)  # days sent back earlier wait for the manager again
    week.status = "submitted"
    approval = Approval(
        subject_type="week",
        subject_id=week.id,
        requester_id=user.id,
        approver_id=approver_for(session, user.manager_id, user.id),  # the delegate, if any
        due_at=week_due_at(session, user, week_start),  # overdue ones are escalated (routing.py)
        status="pending",
    )
    session.add(approval)
    session.flush()
    session.add(ApprovalStep(approval_id=approval.id, actor_id=user.id, action="submitted"))
    _audit(session, user, "timesheet_week", week, "submitted", before)
    _audit(session, user, "approval", approval, "created", None)
    session.commit()
    return get_week(session, user, week_start)
