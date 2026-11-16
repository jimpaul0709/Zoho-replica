"""Approval routing (WH-32): delegation, due dates in working days, and escalation.

- Delegation: a manager hands approvals to someone for a date range. New approvals go to the
  delegate, and approvals already pending move to the delegate (`apply_delegations`).
- Due date: 2 working days after the request (org setting), skipping non-working days and the
  requester's location holidays.
- Escalation: an approval past its due date moves to the approver's manager, and gets a fresh
  due date (`escalate_overdue`). Notifying both people comes with the notification work (WH-60);
  for now the move is recorded as an approval step and in the audit log.

Both jobs run from one repeating worker job, `approval_housekeeping`, every 15 minutes.
Every move is a single hop: an approval that was just delegated is not delegated back and forth.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.jobs import enqueue, ensure_queued, handler
from workhub_api.models import Approval, ApprovalStep, Delegation, Holiday, OrgSettings, User

HOUSEKEEPING = "approval_housekeeping"
HOUSEKEEPING_EVERY = timedelta(minutes=15)
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DEFAULT_DUE_DAYS = 2


def org_settings(session: Session) -> OrgSettings | None:
    return session.scalars(select(OrgSettings).limit(1)).first()


def work_weekdays(spec: str) -> set[int]:
    """'Mon-Fri' or 'Mon,Tue,Wed' as weekday numbers (Monday is 0). Falls back to Mon-Fri."""
    try:
        if "-" in spec:
            first, last = (DAY_NAMES.index(p.strip()[:3].title()) for p in spec.split("-", 1))
            days = {d % 7 for d in range(first, last + 1 if last >= first else last + 8)}
        else:
            days = {DAY_NAMES.index(p.strip()[:3].title()) for p in spec.split(",")}
    except ValueError:
        days = set()
    return days or {0, 1, 2, 3, 4}


def add_working_days(
    session: Session,
    start: datetime,
    days: int,
    location_id: int | None,
    work_week: str = "Mon-Fri",
) -> datetime:
    """`start` plus `days` working days: skips non-working weekdays and that location's holidays."""
    weekdays = work_weekdays(work_week)
    holidays: set[date] = set()
    if location_id is not None:
        holidays = set(
            session.scalars(select(Holiday.on_date).where(Holiday.location_id == location_id))
        )
    moment = start
    while days > 0:
        moment += timedelta(days=1)
        if moment.weekday() in weekdays and moment.date() not in holidays:
            days -= 1
    return moment


def due_at_for(session: Session, requester: User, now: datetime | None = None) -> datetime:
    org = org_settings(session)
    return add_working_days(
        session,
        now or datetime.now(UTC),
        org.approval_due_working_days if org else DEFAULT_DUE_DAYS,
        requester.location_id,
        org.work_week_days if org else "Mon-Fri",
    )


def active_delegate(session: Session, user_id: int, day: date) -> int | None:
    """Who `user_id` has handed approvals to on `day` (the newest delegation wins)."""
    row = session.scalars(
        select(Delegation)
        .where(
            Delegation.from_user_id == user_id,
            Delegation.starts_on <= day,
            Delegation.ends_on >= day,
        )
        .order_by(Delegation.id.desc())
        .limit(1)
    ).first()
    return row.to_user_id if row else None


def approver_for(
    session: Session, manager_id: int, requester_id: int, day: date | None = None
) -> int:
    """The manager, or their delegate. Nobody approves their own request."""
    delegate = active_delegate(session, manager_id, day or date.today())
    return delegate if delegate is not None and delegate != requester_id else manager_id


def _move(session: Session, approval: Approval, to_id: int, action: str) -> None:
    before = snapshot(approval)
    from_id = approval.approver_id
    approval.approver_id = to_id
    session.add(
        ApprovalStep(
            approval_id=approval.id, actor_id=from_id, action=action, comment=f"to user {to_id}"
        )
    )
    session.flush()
    record(
        session,
        actor_id=from_id,
        entity="approval",
        entity_id=approval.id,
        action=action,
        before=before,
        after=snapshot(approval),
    )


def apply_delegations(session: Session) -> int:
    """Move pending approvals whose approver has an active delegation. Returns how many moved."""
    today = date.today()
    moved = 0
    pending = session.scalars(
        select(Approval).where(Approval.status == "pending").with_for_update(skip_locked=True)
    ).all()
    for approval in pending:
        to_id = approver_for(session, approval.approver_id, approval.requester_id, today)
        if to_id == approval.approver_id:
            continue
        last = session.scalars(
            select(ApprovalStep.action)
            .where(ApprovalStep.approval_id == approval.id)
            .order_by(ApprovalStep.id.desc())
            .limit(1)
        ).first()
        if last == "delegated":  # single hop: no handing it back and forth
            continue
        _move(session, approval, to_id, "delegated")
        moved += 1
    return moved


def escalate_overdue(session: Session) -> int:
    """Move approvals past their due date up to the approver's manager. Returns how many moved."""
    now = datetime.now(UTC)
    overdue = session.scalars(
        select(Approval)
        .where(Approval.status == "pending", Approval.due_at.is_not(None), Approval.due_at < now)
        .with_for_update(skip_locked=True)
    ).all()
    moved = 0
    for approval in overdue:
        approver = session.get(User, approval.approver_id)
        requester = session.get(User, approval.requester_id)
        boss_id = approver.manager_id if approver else None
        if requester is None or boss_id is None or boss_id == approval.requester_id:
            continue  # nobody above to escalate to
        _move(session, approval, boss_id, "escalated")
        approval.level += 1
        approval.due_at = due_at_for(session, requester, now)
        session.flush()
        moved += 1
    return moved


@handler(HOUSEKEEPING)
def housekeeping(session: Session, payload: dict[str, Any]) -> None:
    apply_delegations(session)
    escalate_overdue(session)
    enqueue(session, HOUSEKEEPING, run_at=datetime.now(UTC) + HOUSEKEEPING_EVERY)


def ensure_housekeeping(session: Session) -> bool:
    """Start (or restart) the repeating job. The worker calls this, so a failed chain heals."""
    return ensure_queued(session, HOUSEKEEPING)
