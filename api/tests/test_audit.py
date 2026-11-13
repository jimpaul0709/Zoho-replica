from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.main import engine
from workhub_api.models import AuditEvent, TimesheetWeek, User


@pytest.fixture
def session() -> Iterator[Session]:
    """Rolled back at the end, so the shared database stays clean."""
    with Session(engine) as s:
        yield s
        s.rollback()


def test_record_stores_change_with_snapshots(session: Session) -> None:
    user = User(employee_code="T2", name="T", email="t2@x.io")
    session.add(user)
    session.flush()
    week = TimesheetWeek(user_id=user.id, week_start=date(2026, 11, 9), status="draft")
    session.add(week)
    session.flush()

    before = snapshot(week)
    week.status = "submitted"
    record(
        session,
        actor_id=user.id,
        entity="timesheet_week",
        entity_id=week.id,
        action="submitted",
        before=before,
        after=snapshot(week),
    )
    session.flush()

    event = session.scalars(select(AuditEvent).where(AuditEvent.entity_id == week.id)).one()
    assert event.action == "submitted"
    assert event.before is not None and event.before["status"] == "draft"
    assert event.after is not None and event.after["week_start"] == "2026-11-09"
    assert event.after["status"] == "submitted"
