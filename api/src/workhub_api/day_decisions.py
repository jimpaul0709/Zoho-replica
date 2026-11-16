"""Per-day approval: the manager decides a whole week, or any single day of it.

A week is the set of days that have entries. Each day is waiting, approved (and locked) or sent
back (the employee fixes it). When every day is decided the approval closes:
  - all days approved: the week is approved and locked;
  - otherwise: the week goes back to draft. The employee fixes the sent-back days and resubmits;
    days that were approved stay approved, and only the sent-back days go back to the manager.
A whole-week approve or send-back is the same thing applied to every day still waiting.
"""

from datetime import date
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.models import DayDecision, TimeEntry, TimesheetWeek, User

Outcome = Literal["pending", "approved", "sent_back"]


def minutes_by_day(session: Session, week_id: int) -> dict[date, int]:
    rows = session.execute(
        select(TimeEntry.work_date, func.sum(TimeEntry.minutes))
        .where(TimeEntry.week_id == week_id)
        .group_by(TimeEntry.work_date)
    )
    return {day: int(total) for day, total in rows}


def decisions_of(session: Session, week_id: int) -> dict[date, DayDecision]:
    return {
        d.work_date: d
        for d in session.scalars(select(DayDecision).where(DayDecision.week_id == week_id))
    }


def check_day_open(session: Session, week_id: int, day: date) -> None:
    """409 if the manager already approved this day: an approved day is locked."""
    approved = session.scalar(
        select(DayDecision.id).where(
            DayDecision.week_id == week_id,
            DayDecision.work_date == day,
            DayDecision.status == "approved",
        )
    )
    if approved is not None:
        raise HTTPException(409, f"{day} is already approved (locked)")


def waiting_days(session: Session, week_id: int) -> list[date]:
    done = decisions_of(session, week_id)
    return sorted(day for day in minutes_by_day(session, week_id) if day not in done)


def decide(
    session: Session,
    user: User,
    week: TimesheetWeek,
    days: list[date],
    status: Literal["approved", "sent_back"],
    reason: str | None = None,
) -> None:
    """Record `status` for each of `days`: 404 if nothing is logged that day, 409 if decided."""
    logged = minutes_by_day(session, week.id)
    done = decisions_of(session, week.id)
    for day in days:
        if day not in logged:
            raise HTTPException(404, f"Nothing is logged on {day} in this week")
        if day in done:
            raise HTTPException(409, f"{day} is already {done[day].status.replace('_', ' ')}")
    rows = [
        DayDecision(
            week_id=week.id, work_date=day, status=status, reason=reason, decided_by=user.id
        )
        for day in days
    ]
    session.add_all(rows)
    session.flush()
    for row in rows:
        record(
            session,
            actor_id=user.id,
            entity="day_decision",
            entity_id=row.id,
            action=status,
            after=snapshot(row),
        )


def settle(session: Session, week_id: int) -> Outcome:
    """pending while any day waits; approved when every day is approved; else sent_back."""
    logged = minutes_by_day(session, week_id)
    done = decisions_of(session, week_id)
    if any(day not in done for day in logged):
        return "pending"
    return "approved" if all(done[day].status == "approved" for day in logged) else "sent_back"


def returned_reasons(session: Session, week_id: int) -> str:
    rows = session.scalars(
        select(DayDecision)
        .where(DayDecision.week_id == week_id, DayDecision.status == "sent_back")
        .order_by(DayDecision.work_date)
    )
    return "; ".join(f"{r.work_date}: {r.reason}" for r in rows)


def reopen_returned(session: Session, user: User, week: TimesheetWeek) -> None:
    """On resubmit: sent-back days wait for the manager again. Approved days stay approved."""
    rows = list(
        session.scalars(
            select(DayDecision).where(
                DayDecision.week_id == week.id, DayDecision.status == "sent_back"
            )
        )
    )
    before = [(row.id, snapshot(row)) for row in rows]
    for row in rows:
        session.delete(row)
    session.flush()
    for row_id, old in before:
        record(
            session,
            actor_id=user.id,
            entity="day_decision",
            entity_id=row_id,
            action="reopened",
            before=old,
        )
