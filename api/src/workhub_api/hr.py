"""HR direct correction of an approved week.

An approved week is locked. Normally the employee files an edit request and the manager approves
it (edit_requests.py). HR can also correct it directly, with a required reason: the same add,
update and delete changes, checked against every time rule and applied at once. The changes go in
the audit log under the HR person's name, together with the reason. Nobody corrects their own
week this way. (The other HR option, a notification that lets the employee edit, waits for the
notification work, WH-60.)
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from workhub_api.audit import record
from workhub_api.db import SessionDep
from workhub_api.edit_requests import Change, apply_changes
from workhub_api.models import EditRequest, TimesheetWeek, User
from workhub_api.permissions import require_roles
from workhub_api.timesheets import WeekOut, get_week, week_start_for

router = APIRouter(prefix="/hr", tags=["hr"])

HR = Annotated[User, Depends(require_roles("hr"))]


class CorrectionIn(BaseModel):
    reason: str = Field(min_length=1)
    changes: list[Change] = Field(min_length=1, max_length=50)


@router.post("/users/{user_id}/weeks/{week_start}/corrections", response_model=WeekOut)
def correct_week(
    user_id: int, week_start: date, body: CorrectionIn, session: SessionDep, hr: HR
) -> WeekOut:
    """Change an approved week at once. Returns the corrected week."""
    if user_id == hr.id:
        raise HTTPException(403, "You can't correct your own week; file an edit request")
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
        raise HTTPException(409, "Only an approved (locked) week needs a correction")
    if session.scalar(
        select(EditRequest.id).where(
            EditRequest.week_id == week.id, EditRequest.status == "pending"
        )
    ):
        raise HTTPException(409, "This week has a pending edit request; resolve that first")

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
