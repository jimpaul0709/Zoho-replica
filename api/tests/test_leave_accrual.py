"""Monthly leave accrual and year-end carry-forward (leave_accrual.py).

Amounts are minutes (a full day is 480). The job may run twice, so every credit is recorded once
in `leave_credit` and a repeat must change nothing.
"""

from datetime import UTC, date, datetime

from conftest import World
from sqlalchemy import delete, select

import workhub_api.worker  # noqa: F401  (importing the worker registers the job handlers)
from workhub_api.jobs import HANDLERS, enqueue, run_one
from workhub_api.leave import leave_year_of
from workhub_api.leave_accrual import ACCRUAL, accrue_month, ensure_leave_accrual
from workhub_api.models import AuditEvent, Job, LeaveBalance, LeaveType, User
from workhub_api.routing import org_settings

NOV = date(2026, 11, 1)
DEC = date(2026, 12, 1)
MAR = date(2027, 3, 1)
APR = date(2027, 4, 1)
MAY = date(2027, 5, 1)


def make_type(w: World, accrual: int = 600, cap: int = 0, name: str = "T-Acc") -> LeaveType:
    kind = LeaveType(
        name=name,
        paid=True,
        charge_code_id=w.code.id,
        accrual_per_month=accrual,
        carry_forward_cap=cap,
    )
    w.session.add(kind)
    w.session.flush()
    return kind


def balance(w: World, kind: LeaveType, year: int, user: User | None = None) -> LeaveBalance | None:
    return w.session.scalars(
        select(LeaveBalance).where(
            LeaveBalance.user_id == (user or w.emp).id,
            LeaveBalance.leave_type_id == kind.id,
            LeaveBalance.leave_year == year,
        )
    ).first()


def accrued(w: World, kind: LeaveType, year: int, user: User | None = None) -> int | None:
    row = balance(w, kind, year, user)
    return row.accrued if row else None


def give(w: World, kind: LeaveType, year: int, **fields: int) -> LeaveBalance:
    row = LeaveBalance(user_id=w.emp.id, leave_type_id=kind.id, leave_year=year, **fields)
    w.session.add(row)
    w.session.flush()
    return row


def test_each_active_person_is_credited_the_types_monthly_amount(world: World) -> None:
    kind = make_type(world, accrual=600)
    none = make_type(world, accrual=0, name="T-None")
    accrue_month(world.session, NOV)
    assert accrued(world, kind, 2026) == 600
    assert accrued(world, kind, 2026, world.boss) == 600
    assert balance(world, none, 2026) is None  # a type that does not accrue is left alone


def test_running_the_same_month_twice_credits_once(world: World) -> None:
    kind = make_type(world)
    accrue_month(world.session, NOV)
    accrue_month(world.session, NOV)
    assert accrued(world, kind, 2026) == 600


def test_each_month_is_credited_separately(world: World) -> None:
    kind = make_type(world)
    accrue_month(world.session, NOV)
    accrue_month(world.session, DEC)
    assert accrued(world, kind, 2026) == 1200


def test_credit_is_added_to_what_hr_already_set(world: World) -> None:
    kind = make_type(world)
    give(world, kind, 2026, opening=480, accrued=100, adjusted=-60, used=30)
    accrue_month(world.session, NOV)
    row = balance(world, kind, 2026)
    assert row is not None
    assert (row.opening, row.accrued, row.adjusted, row.used) == (480, 700, -60, 30)


def test_months_fall_in_the_right_leave_year(world: World) -> None:
    kind = make_type(world)
    org = org_settings(world.session)
    assert leave_year_of(org, MAR) == 2026 and leave_year_of(org, APR) == 2027
    accrue_month(world.session, MAR)
    accrue_month(world.session, APR)
    assert accrued(world, kind, 2026) == 600
    assert accrued(world, kind, 2027) == 600


def test_people_who_are_not_employed_that_month_get_nothing(world: World) -> None:
    kind = make_type(world)
    gone = User(employee_code="G1", name="G", email="g1@x.io", exited_on=date(2026, 10, 31))
    late = User(employee_code="L1", name="L", email="l1@x.io", joined_on=date(2026, 12, 1))
    off = User(employee_code="O1", name="O", email="o1@x.io", active=False)
    world.session.add_all([gone, late, off])
    world.session.flush()
    accrue_month(world.session, NOV)
    for person in (gone, late, off):
        assert balance(world, kind, 2026, person) is None
    accrue_month(world.session, DEC)  # joined on the 1st: employed that month
    assert accrued(world, kind, 2026, late) == 600


def test_unused_leave_carries_forward_up_to_the_cap_once(world: World) -> None:
    kind = make_type(world, accrual=0, cap=900)
    other = make_type(world, accrual=600, cap=900, name="T-Acc2")
    give(world, kind, 2026, opening=600, accrued=1200, used=300)  # 1500 left, cap 900
    accrue_month(world.session, MAY)  # a late run still carries the year over
    accrue_month(world.session, APR)
    accrue_month(world.session, APR)
    row = balance(world, kind, 2027)
    assert row is not None and row.opening == 900 and row.accrued == 0
    assert accrued(world, other, 2027) == 1200  # April and May


def test_nothing_carries_without_a_cap_or_a_positive_balance(world: World) -> None:
    no_cap = make_type(world, accrual=0, cap=0, name="T-NoCap")
    overdrawn = make_type(world, accrual=0, cap=900, name="T-Over")
    give(world, no_cap, 2026, opening=900)
    give(world, overdrawn, 2026, opening=100, used=400)
    accrue_month(world.session, APR)
    for kind in (no_cap, overdrawn):
        row = balance(world, kind, 2027)
        assert row is None or row.opening == 0


def test_carry_forward_keeps_an_opening_hr_already_set(world: World) -> None:
    kind = make_type(world, accrual=0, cap=900)
    give(world, kind, 2026, opening=600)
    give(world, kind, 2027, opening=120)
    accrue_month(world.session, APR)
    row = balance(world, kind, 2027)
    assert row is not None and row.opening == 720


def test_every_credit_is_audited_without_an_actor(world: World) -> None:
    kind = make_type(world)
    accrue_month(world.session, NOV)
    row = balance(world, kind, 2026)
    assert row is not None
    events = world.session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity == "leave_balance",
            AuditEvent.entity_id == row.id,
            AuditEvent.action == "accrue",
        )
    ).all()
    assert len(events) == 1 and events[0].actor_id is None


def test_the_job_is_registered_and_queued_only_once(world: World) -> None:
    assert ACCRUAL in HANDLERS
    world.session.execute(delete(Job).where(Job.kind == ACCRUAL))
    assert ensure_leave_accrual(world.session) is True
    assert ensure_leave_accrual(world.session) is False


def test_the_repeating_job_accrues_this_month_and_requeues_for_the_next(world: World) -> None:
    kind = make_type(world)
    world.session.execute(delete(Job).where(Job.kind == ACCRUAL))
    enqueue(world.session, ACCRUAL)
    assert run_one(world.session, {ACCRUAL}) is True
    today = datetime.now(UTC).date()
    year = leave_year_of(org_settings(world.session), today)
    assert accrued(world, kind, year) == 600
    queued = world.session.scalars(
        select(Job).where(Job.kind == ACCRUAL, Job.status == "queued")
    ).all()
    first_next = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    assert [j.run_at.date() for j in queued] == [first_next]


def test_a_manual_backfill_for_one_month_does_not_requeue(world: World) -> None:
    kind = make_type(world)
    world.session.execute(delete(Job).where(Job.kind == ACCRUAL))
    enqueue(world.session, ACCRUAL, {"month": "2026-11"})
    assert run_one(world.session, {ACCRUAL}) is True
    assert accrued(world, kind, 2026) == 600
    queued = world.session.scalars(
        select(Job).where(Job.kind == ACCRUAL, Job.status == "queued")
    ).all()
    assert queued == []
