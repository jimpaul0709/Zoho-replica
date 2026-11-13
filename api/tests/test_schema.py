"""Checks the rules the database itself enforces (needs `alembic upgrade head` first)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError

from workhub_api.db import engine


@pytest.fixture
def conn() -> Iterator[Connection]:
    """A connection whose work is always rolled back, so the shared database stays clean."""
    with engine.connect() as c:
        trans = c.begin()
        yield c
        trans.rollback()


def _week(c: Connection) -> int:
    uid = c.execute(
        text(
            "insert into app_user (employee_code, name, email) "
            "values ('T1','T','t@x.io') returning id"
        )
    ).scalar_one()
    week: int = c.execute(
        text(
            "insert into timesheet_week (user_id, week_start) "
            "values (:u, '2026-11-09') returning id"
        ),
        {"u": uid},
    ).scalar_one()
    return week


def _entry(c: Connection, week: int, target: str, minutes: int = 60) -> None:
    """Insert a time entry for the week's user. `target` is 'extra cols|extra vals', or empty."""
    cols, vals = target.split("|") if target else ("", "")
    c.execute(
        text(
            f"insert into time_entry (user_id, week_id, work_date, minutes{cols}) "
            f"select user_id, id, '2026-11-09', {minutes}{vals} from timesheet_week where id = :w"
        ),
        {"w": week},
    )


def test_time_entry_needs_exactly_one_target(conn: Connection) -> None:
    week = _week(conn)
    with pytest.raises(IntegrityError):  # neither task nor charge code
        _entry(conn, week, "")


def test_time_entry_minutes_range(conn: Connection) -> None:
    week = _week(conn)
    conn.execute(text("insert into charge_code (code, name) values ('Bench','Bench')"))
    target = ", charge_code_id|, (select id from charge_code where code = 'Bench')"
    _entry(conn, week, target)  # a valid entry goes in
    with pytest.raises(IntegrityError):
        _entry(conn, week, target, minutes=1441)


def test_audit_event_is_append_only(conn: Connection) -> None:
    conn.execute(text("insert into audit_event (entity, action) values ('x','created')"))
    with pytest.raises(DBAPIError, match="append-only"):
        conn.execute(text("update audit_event set action = 'y'"))
