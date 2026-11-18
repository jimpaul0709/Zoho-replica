"""Monthly leave accrual and year-end carry-forward, run by the worker (WH-40).

Every month each person who is employed that month gets each leave type's `accrual_per_month`.
When a new leave year starts, unused leave from the year before carries over, up to the type's
`carry_forward_cap`, into the new year's `opening`. The job can run twice (the queue retries), so
each credit is written once to `leave_credit` and the balance changes only when that row is new.

shortcut: a joiner or leaver gets a full month, not a pro-rated one; calendar months are in UTC.
Each credit is a few round trips, so a very large staff would want this batched.
"""

from calendar import monthrange
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.jobs import enqueue, ensure_queued, handler
from workhub_api.leave import _balance, _left, leave_year_of
from workhub_api.models import LeaveBalance, LeaveCredit, LeaveType, User
from workhub_api.routing import org_settings

ACCRUAL = "leave_accrual"


def _credit(
    session: Session, user_id: int, type_id: int, year: int, key: str, minutes: int, field: str
) -> bool:
    """Add `minutes` to `field` of the balance, once per `key`. False if it was already done."""
    new_id = session.execute(
        insert(LeaveCredit)
        .values(user_id=user_id, leave_type_id=type_id, key=key, minutes=minutes)
        .on_conflict_do_nothing()
        .returning(LeaveCredit.id)
    ).scalar_one_or_none()
    if new_id is None:
        return False
    balance = _balance(session, user_id, type_id, year, lock=True)
    if balance is None:
        balance = LeaveBalance(
            user_id=user_id,
            leave_type_id=type_id,
            leave_year=year,
            opening=0,
            accrued=0,
            used=0,
            adjusted=0,
        )
        session.add(balance)
        session.flush()
    before = snapshot(balance)
    setattr(balance, field, getattr(balance, field) + minutes)
    session.flush()
    record(
        session,
        actor_id=None,
        entity="leave_balance",
        entity_id=balance.id,
        action="accrue",
        before=before,
        after=snapshot(balance),
    )
    return True


def _carry_forward(session: Session, year: int) -> None:
    """Move last leave year's unused leave (up to each type's cap) into `year`'s opening."""
    rows = session.execute(
        select(LeaveBalance, LeaveType.carry_forward_cap)
        .join(LeaveType, LeaveType.id == LeaveBalance.leave_type_id)
        .join(User, User.id == LeaveBalance.user_id)
        .where(
            LeaveBalance.leave_year == year - 1,
            LeaveType.carry_forward_cap > 0,
            User.active.is_(True),
        )
    ).all()
    for balance, cap in rows:
        carry = min(_left(balance), cap)
        if carry > 0:
            key = f"carry:{year}"
            _credit(session, balance.user_id, balance.leave_type_id, year, key, carry, "opening")


def accrue_month(session: Session, month: date) -> None:
    """Credit one month (`month` is its first day) to everyone employed in it. Safe to repeat."""
    year = leave_year_of(org_settings(session), month)
    last = month.replace(day=monthrange(month.year, month.month)[1])
    _carry_forward(session, year)
    people = session.scalars(
        select(User.id).where(
            User.active.is_(True),
            or_(User.joined_on.is_(None), User.joined_on <= last),
            or_(User.exited_on.is_(None), User.exited_on >= month),
        )
    ).all()
    kinds = session.execute(
        select(LeaveType.id, LeaveType.accrual_per_month).where(LeaveType.accrual_per_month > 0)
    ).all()
    for user_id in people:
        for type_id, amount in kinds:
            _credit(session, user_id, type_id, year, f"accrual:{month:%Y-%m}", amount, "accrued")


@handler(ACCRUAL)
def run_accrual(session: Session, payload: dict[str, Any]) -> None:
    """With a `month` ("2026-11") it backfills that month only. Without one it accrues this month
    and queues itself for the 1st of the next month, so it keeps repeating."""
    if "month" in payload:
        year, month = (int(part) for part in payload["month"].split("-"))
        accrue_month(session, date(year, month, 1))
        return
    today = datetime.now(UTC).date()
    accrue_month(session, today.replace(day=1))
    following = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    enqueue(
        session,
        ACCRUAL,
        run_at=datetime(following.year, following.month, 1, 0, 5, tzinfo=UTC),
    )


def ensure_leave_accrual(session: Session) -> bool:
    """Keep the repeating accrual job alive (the worker calls this when it is idle)."""
    return ensure_queued(session, ACCRUAL)
