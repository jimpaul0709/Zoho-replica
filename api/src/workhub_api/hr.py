"""HR corrections of an approved week. Two ways, both for the HR role, never on your own week.

1. Correct directly: HR makes the add, update and delete changes themselves, with a reason. They are
   checked against every time rule, applied at once, and audited under the HR person's name.
2. Send back: HR returns days (or the whole week) to the employee with a reason. The employee
   fixes them and resubmits, and the manager approves those days again. Days not sent back stay
   approved. (Telling the employee by notification waits for WH-60.)
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.day_decisions import decisions_of, minutes_by_day
from workhub_api.db import SessionDep
from workhub_api.edit_requests import Change, apply_changes
from workhub_api.models import (
    Approval,
    ApprovalStep,
    DayDecision,
    EditRequest,
    TimesheetWeek,
    User,
)
from workhub_api.permissions import require_roles
from workhub_api.timesheets import WeekOut, get_week, week_start_for

router = APIRouter(prefix="/hr", tags=["hr"])

HR = Annotated[User, Depends(require_roles("hr"))]


class CorrectionIn(BaseModel):
    reason: str = Field(min_length=1)
    changes: list[Change] = Field(min_length=1, max_length=50)


class SendBackIn(BaseModel):
    reason: str = Field(min_length=1)
    dates: list[date] = []  # the days to send back; empty means every day with time


def _approved_week(
    session: Session, hr: User, user_id: int, week_start: date
) -> tuple[User, TimesheetWeek]:
    """The employee and their approved week (locked for update), or the reason HR can't act."""
    if user_id == hr.id:
        raise HTTPException(403, "You can't change your own week; file an edit request")
    employee = session.get(User, user_id)
    if employee is None:
        raise HTTPException(404, "User not found")
    if week_start != week_start_for(session, week_start):
        raise HTTPException(422, "week_start must be the first day of a week")
    week = session.scalars(
        select(TimesheetWeek)
        .where(TimesheetWeek.user_id == employee.id, TimesheetWeek.week_start == week_start)
        .with_for_update()
    ).first()
    if week is None or week.status != "approved":
        raise HTTPException(409, "Only an approved (locked) week needs this")
    if session.scalar(
        select(EditRequest.id).where(
            EditRequest.week_id == week.id, EditRequest.status == "pending"
        )
    ):
        raise HTTPException(409, "This week has a pending edit request; resolve that first")
    return employee, week


@router.post("/users/{user_id}/weeks/{week_start}/corrections", response_model=WeekOut)
def correct_week(
    user_id: int, week_start: date, body: CorrectionIn, session: SessionDep, hr: HR
) -> WeekOut:
    """Change an approved week at once. Returns the corrected week."""
    employee, week = _approved_week(session, hr, user_id, week_start)
    stored = [c.model_dump(mode="json", exclude_unset=True) for c in body.changes]
    apply_changes(session, employee, week, stored, actor=hr, dry_run=False)  # 422, nothing applied
    record(
        session,
        actor_id=hr.id,
        entity="timesheet_week",
        entity_id=week.id,
        action="hr_corrected",
        after={"reason": body.reason, "changes": stored},
    )
    session.commit()
    return get_week(session, employee, week_start)


@router.post("/users/{user_id}/weeks/{week_start}/send-back", response_model=WeekOut)
def send_back(
    user_id: int, week_start: date, body: SendBackIn, session: SessionDep, hr: HR
) -> WeekOut:
    """Send days of an approved week back to the employee. The week returns to draft; the days
    not sent back stay approved and locked. After the employee resubmits, the manager approves
    the sent-back days again."""
    employee, week = _approved_week(session, hr, user_id, week_start)
    logged = minutes_by_day(session, week.id)
    days = sorted(set(body.dates)) or sorted(logged)
    for day in days:
        if day not in logged:
            raise HTTPException(404, f"Nothing is logged on {day} in this week")
    decided = decisions_of(session, week.id)
    week_before = snapshot(week)
    changed: list[tuple[DayDecision, dict[str, object] | None]] = []
    for day in days:
        row = decided.get(day)
        old = snapshot(row) if row else None
        if row is None:
            row = DayDecision(
                week_id=week.id,
                work_date=day,
                status="sent_back",
                reason=body.reason,
                decided_by=hr.id,
            )
            session.add(row)
        else:
            row.status, row.reason, row.decided_by = "sent_back", body.reason, hr.id
        changed.append((row, old))
    week.status = "draft"  # the employee fixes the sent-back days and resubmits
    week.locked_at = None
    last = session.scalars(
        select(Approval)
        .where(Approval.subject_type == "week", Approval.subject_id == week.id)
        .order_by(Approval.id.desc())
    ).first()
    if last is not None:  # shows in the approval's history, for the manager and the employee
        session.add(
            ApprovalStep(
                approval_id=last.id, actor_id=hr.id, action="hr_sent_back", comment=body.reason
            )
        )
    session.flush()
    for row, old in changed:
        record(
            session,
            actor_id=hr.id,
            entity="day_decision",
            entity_id=row.id,
            action="hr_sent_back",
            before=old,
            after=snapshot(row),
        )
    record(
        session,
        actor_id=hr.id,
        entity="timesheet_week",
        entity_id=week.id,
        action="hr_sent_back",
        before=week_before,
        after=snapshot(week),
    )
    session.commit()
    return get_week(session, employee, week_start)
