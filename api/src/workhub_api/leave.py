"""Leave (WH-40, WH-41): types, balances, blackout days, apply, withdraw, approve, cancel.

The API speaks hours (a full day is `org_settings.daily_expected_minutes`, normally 8 h; a half day
is half of it). The database keeps whole minutes, like time entries, and `_hours` / `_minutes`
convert at the edge. The leave year runs from `fy_start_month` (April) to the month before it.

Applying creates a `leave_request` and an approval (subject_type `leave`) for the manager, so the
inbox, delegation, escalation and bulk approve work as they do for weeks. Approving
(`approve_leave`, called from approvals.py) does three things in one transaction: deducts the
balance, writes one read-only time entry (source `leave`) per day, and records the steps and audit
rows. Cancelling an approved leave reverses all three.

Left for later: monthly accrual by the worker, year-end carry forward, comp-off, the team calendar,
and cancelling leave whose week is already approved (that needs HR; leave entries are read-only).
"""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.day_decisions import check_day_open
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import (
    Approval,
    ApprovalStep,
    BlackoutDay,
    ChargeCode,
    Holiday,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    OrgSettings,
    TimeEntry,
    TimesheetWeek,
    User,
)
from workhub_api.permissions import require_roles, roles_of
from workhub_api.routing import approver_for, due_at_for, org_settings, work_weekdays
from workhub_api.timesheets import _day_total, week_start_for

router = APIRouter(prefix="/leave", tags=["leave"])

HR = Annotated[User, Depends(require_roles("hr"))]
HalfDay = Literal["first_half", "second_half"]
DEFAULT_DAY = 480


def _hours(minutes: int) -> float:
    return round(minutes / 60, 2)


def _minutes(hours: float) -> int:
    return round(hours * 60)


class TypeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    paid: bool = True  # false means LOP (loss of pay)
    charge_code_id: int  # the charge code the leave time entries are booked to
    accrual_per_month: float = Field(default=0, ge=0)  # hours
    carry_forward_cap: float = Field(default=0, ge=0)  # hours
    attachment_after_days: int | None = Field(default=None, ge=0)


class TypeOut(TypeIn):
    id: int


def _type_out(kind: LeaveType) -> TypeOut:
    return TypeOut(
        id=kind.id,
        name=kind.name,
        paid=kind.paid,
        charge_code_id=kind.charge_code_id,
        accrual_per_month=_hours(kind.accrual_per_month),
        carry_forward_cap=_hours(kind.carry_forward_cap),
        attachment_after_days=kind.attachment_after_days,
    )


class BalanceIn(BaseModel):
    user_id: int
    leave_type_id: int
    leave_year: int
    opening: float | None = None  # hours; only the fields you send are changed
    accrued: float | None = None
    adjusted: float | None = None  # can be negative


class BalanceOut(BaseModel):
    """All amounts are in hours."""

    leave_type_id: int
    leave_type: str
    leave_year: int
    opening: float
    accrued: float
    adjusted: float
    used: float
    pending: float  # asked for and waiting for the manager
    available: float  # opening + accrued + adjusted - used - pending


class BlackoutIn(BaseModel):
    on_date: date
    note: str = Field(min_length=1)


class BlackoutOut(BlackoutIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LeaveIn(BaseModel):
    leave_type_id: int
    from_date: date
    to_date: date
    half_days: dict[date, HalfDay] = {}  # days that are only half; every other day is a full day
    reason: str | None = None
    attachment_key: str | None = None


class LeaveOut(BaseModel):
    id: int
    leave_type_id: int
    from_date: date
    to_date: date
    day_portions: dict[str, str]
    hours: float
    reason: str | None
    attachment_key: str | None
    status: str
    applied_after_dates: bool
    approval_id: int | None


class LeaveBrief(BaseModel):
    """What the manager sees in the inbox for a leave approval."""

    leave_type: str
    from_date: date
    to_date: date
    hours: float
    reason: str | None
    applied_after_dates: bool


def leave_year_of(org: OrgSettings | None, day: date) -> int:
    start = org.fy_start_month if org else 4
    return day.year if day.month >= start else day.year - 1


def _full_day(org: OrgSettings | None) -> int:
    return org.daily_expected_minutes if org else DEFAULT_DAY


def _lock_user(session: Session, user_id: int) -> None:
    session.execute(select(func.pg_advisory_xact_lock(user_id)))  # as the time API does


def _balance(
    session: Session, user_id: int, type_id: int, year: int, lock: bool = False
) -> LeaveBalance | None:
    query = select(LeaveBalance).where(
        LeaveBalance.user_id == user_id,
        LeaveBalance.leave_type_id == type_id,
        LeaveBalance.leave_year == year,
    )
    return session.scalars(query.with_for_update() if lock else query).first()


def _left(balance: LeaveBalance | None) -> int:
    return balance.opening + balance.accrued + balance.adjusted - balance.used if balance else 0


def _pending(
    session: Session, org: OrgSettings | None, user_id: int, type_id: int, year: int
) -> int:
    """Minutes already asked for in this type and leave year and still waiting."""
    rows = session.scalars(
        select(LeaveRequest).where(
            LeaveRequest.user_id == user_id,
            LeaveRequest.leave_type_id == type_id,
            LeaveRequest.status == "applied",
        )
    )
    return sum(r.minutes for r in rows if leave_year_of(org, r.from_date) == year)


def _approval_of(session: Session, request_id: int, lock: bool = False) -> Approval | None:
    query = (
        select(Approval)
        .where(Approval.subject_type == "leave", Approval.subject_id == request_id)
        .order_by(Approval.id.desc())
    )
    return session.scalars(query.with_for_update() if lock else query).first()


def _out(req: LeaveRequest, approval_id: int | None) -> LeaveOut:
    return LeaveOut(
        id=req.id,
        leave_type_id=req.leave_type_id,
        from_date=req.from_date,
        to_date=req.to_date,
        day_portions=req.day_portions,
        hours=_hours(req.minutes),
        reason=req.reason,
        attachment_key=req.attachment_key,
        status=req.status,
        applied_after_dates=req.applied_after_dates,
        approval_id=approval_id,
    )


def _step(session: Session, approval: Approval, actor: User, action: str, note: str | None) -> None:
    session.add(
        ApprovalStep(approval_id=approval.id, actor_id=actor.id, action=action, comment=note)
    )


# ---------- HR sets up types, balances and blackout days ----------


@router.get("/types", response_model=list[TypeOut])
def list_types(session: SessionDep, user: CurrentUser) -> list[TypeOut]:
    return [_type_out(k) for k in session.scalars(select(LeaveType).order_by(LeaveType.name))]


@router.post("/types", response_model=TypeOut, status_code=201)
def create_type(body: TypeIn, session: SessionDep, hr: HR) -> TypeOut:
    if session.get(ChargeCode, body.charge_code_id) is None:
        raise HTTPException(422, "Unknown charge code")
    if session.scalar(select(LeaveType.id).where(LeaveType.name == body.name)):
        raise HTTPException(409, "A leave type with this name already exists")
    kind = LeaveType(
        **body.model_dump(exclude={"accrual_per_month", "carry_forward_cap"}),
        accrual_per_month=_minutes(body.accrual_per_month),
        carry_forward_cap=_minutes(body.carry_forward_cap),
    )
    session.add(kind)
    session.flush()
    record(
        session,
        actor_id=hr.id,
        entity="leave_type",
        entity_id=kind.id,
        action="created",
        after=snapshot(kind),
    )
    out = _type_out(kind)
    session.commit()
    return out


@router.put("/balances", response_model=BalanceOut)
def set_balance(body: BalanceIn, session: SessionDep, hr: HR) -> BalanceOut:
    """Set the opening, accrued or adjusted hours of someone's balance (creates it if new)."""
    kind = session.get(LeaveType, body.leave_type_id)
    if kind is None or session.get(User, body.user_id) is None:
        raise HTTPException(404, "Unknown user or leave type")
    balance = _balance(session, body.user_id, kind.id, body.leave_year, lock=True)
    before = snapshot(balance) if balance else None
    if balance is None:
        balance = LeaveBalance(
            user_id=body.user_id, leave_type_id=kind.id, leave_year=body.leave_year
        )
        session.add(balance)
    for field in body.model_fields_set & {"opening", "accrued", "adjusted"}:
        value = getattr(body, field)
        if value is None:
            raise HTTPException(422, f"{field} can't be null")
        setattr(balance, field, _minutes(value))
    session.flush()
    record(
        session,
        actor_id=hr.id,
        entity="leave_balance",
        entity_id=balance.id,
        action="set",
        before=before,
        after=snapshot(balance),
    )
    out = _balance_out(session, balance, kind)
    session.commit()
    return out


@router.get("/balances", response_model=list[BalanceOut])
def balances(
    session: SessionDep, user: CurrentUser, year: int | None = None, user_id: int | None = None
) -> list[BalanceOut]:
    """Your balances for a leave year (default: this one). HR can ask for anyone's."""
    if user_id is not None and user_id != user.id and "hr" not in roles_of(session, user.id):
        raise HTTPException(403, "You need the hr role to see someone else's balances")
    owner = user_id or user.id
    org = org_settings(session)
    year = year if year is not None else leave_year_of(org, date.today())
    rows = session.execute(
        select(LeaveBalance, LeaveType)
        .join(LeaveType, LeaveType.id == LeaveBalance.leave_type_id)
        .where(LeaveBalance.user_id == owner, LeaveBalance.leave_year == year)
        .order_by(LeaveType.name)
    ).all()
    return [_balance_out(session, balance, kind, org) for balance, kind in rows]


def _balance_out(
    session: Session, balance: LeaveBalance, kind: LeaveType, org: OrgSettings | None = None
) -> BalanceOut:
    waiting = _pending(
        session, org or org_settings(session), balance.user_id, kind.id, balance.leave_year
    )
    return BalanceOut(
        leave_type_id=kind.id,
        leave_type=kind.name,
        leave_year=balance.leave_year,
        opening=_hours(balance.opening),
        accrued=_hours(balance.accrued),
        adjusted=_hours(balance.adjusted),
        used=_hours(balance.used),
        pending=_hours(waiting),
        available=_hours(_left(balance) - waiting),
    )


@router.post("/blackout-days", response_model=BlackoutOut, status_code=201)
def add_blackout(body: BlackoutIn, session: SessionDep, hr: HR) -> BlackoutDay:
    if session.scalar(select(BlackoutDay.id).where(BlackoutDay.on_date == body.on_date)):
        raise HTTPException(409, "That day is already a blackout day")
    day = BlackoutDay(on_date=body.on_date, note=body.note)
    session.add(day)
    session.flush()
    record(
        session,
        actor_id=hr.id,
        entity="blackout_day",
        entity_id=day.id,
        action="created",
        after=snapshot(day),
    )
    session.commit()
    return day


@router.get("/blackout-days", response_model=list[BlackoutOut])
def list_blackouts(session: SessionDep, user: CurrentUser) -> list[BlackoutDay]:
    return list(session.scalars(select(BlackoutDay).order_by(BlackoutDay.on_date)))


# ---------- Employee: apply, list, withdraw, cancel ----------


def _working_days(
    session: Session, user: User, org: OrgSettings | None, start: date, end: date
) -> list[date]:
    weekdays = work_weekdays(org.work_week_days if org else "Mon-Fri")
    holidays: set[date] = set()
    if user.location_id is not None:
        holidays = set(
            session.scalars(
                select(Holiday.on_date).where(
                    Holiday.location_id == user.location_id, Holiday.on_date.between(start, end)
                )
            )
        )
    days = (start + timedelta(days=n) for n in range((end - start).days + 1))
    return [d for d in days if d.weekday() in weekdays and d not in holidays]


@router.post("/requests", response_model=LeaveOut, status_code=201)
def apply(body: LeaveIn, session: SessionDep, user: CurrentUser) -> LeaveOut:
    if user.manager_id is None:
        raise HTTPException(422, "You have no manager to approve this")
    _lock_user(session, user.id)  # two applications at the same moment can't both pass the checks
    kind = session.get(LeaveType, body.leave_type_id)
    if kind is None:
        raise HTTPException(422, "Unknown leave type")
    if body.to_date < body.from_date:
        raise HTTPException(422, "to_date is before from_date")
    org = org_settings(session)
    year = leave_year_of(org, body.from_date)
    if leave_year_of(org, body.to_date) != year:
        raise HTTPException(422, "A request must stay inside one leave year; split it in two")
    days = _working_days(session, user, org, body.from_date, body.to_date)
    if not days:
        raise HTTPException(422, "There are no working days in that range")
    if set(body.half_days) - set(days):
        raise HTTPException(422, "A half day must be one of the working days of the request")
    full = _full_day(org)
    portions = {d.isoformat(): body.half_days.get(d, "full") for d in days}
    minutes = sum(full if p == "full" else full // 2 for p in portions.values())

    blackout = session.scalars(
        select(BlackoutDay).where(BlackoutDay.on_date.in_(days)).order_by(BlackoutDay.on_date)
    ).first()
    if blackout is not None:
        raise HTTPException(422, f"{blackout.on_date} is a blackout day: {blackout.note}")
    for other in session.scalars(
        select(LeaveRequest).where(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status.in_(("applied", "approved")),
            LeaveRequest.from_date <= body.to_date,
            LeaveRequest.to_date >= body.from_date,
        )
    ):
        for day, portion in portions.items():
            theirs = other.day_portions.get(day)
            two_halves = (
                theirs in ("first_half", "second_half")
                and portion in ("first_half", "second_half")
                and theirs != portion
            )
            if theirs and not two_halves:
                raise HTTPException(409, f"You already have leave on {day}")
    if not kind.paid and not (body.reason and body.reason.strip()):
        raise HTTPException(422, "A reason is required for LOP leave")
    if (
        kind.attachment_after_days is not None
        and len(days) > kind.attachment_after_days
        and not body.attachment_key
    ):
        raise HTTPException(
            422, f"{kind.name} longer than {kind.attachment_after_days} days needs an attachment"
        )
    if kind.paid:
        left = _left(_balance(session, user.id, kind.id, year)) - _pending(
            session, org, user.id, kind.id, year
        )
        if left < minutes:
            raise HTTPException(
                422,
                f"Not enough {kind.name} balance: {_hours(left)} hours available, "
                f"this needs {_hours(minutes)}",
            )

    req = LeaveRequest(
        user_id=user.id,
        leave_type_id=kind.id,
        from_date=body.from_date,
        to_date=body.to_date,
        day_portions=portions,
        minutes=minutes,
        reason=body.reason,
        attachment_key=body.attachment_key,
        status="applied",
        applied_after_dates=body.from_date < date.today(),  # allowed, but flagged
    )
    session.add(req)
    session.flush()
    approval = Approval(
        subject_type="leave",
        subject_id=req.id,
        requester_id=user.id,
        approver_id=approver_for(session, user.manager_id, user.id),
        due_at=due_at_for(session, user),
        status="pending",
    )
    session.add(approval)
    session.flush()
    _step(session, approval, user, "submitted", body.reason)
    for entity, row in (("leave_request", req), ("approval", approval)):
        record(
            session,
            actor_id=user.id,
            entity=entity,
            entity_id=row.id,
            action="created",
            after=snapshot(row),
        )
    session.commit()
    return _out(req, approval.id)


@router.get("/requests", response_model=list[LeaveOut])
def my_requests(session: SessionDep, user: CurrentUser) -> list[LeaveOut]:
    rows = list(
        session.scalars(
            select(LeaveRequest)
            .where(LeaveRequest.user_id == user.id)
            .order_by(LeaveRequest.id.desc())
        )
    )
    approvals = {
        a.subject_id: a.id
        for a in session.scalars(
            select(Approval)
            .where(Approval.subject_type == "leave", Approval.subject_id.in_([r.id for r in rows]))
            .order_by(Approval.id)
        )
    }
    return [_out(r, approvals.get(r.id)) for r in rows]


def _own(session: Session, user: User, request_id: int) -> LeaveRequest:
    req = session.scalars(
        select(LeaveRequest).where(LeaveRequest.id == request_id).with_for_update()
    ).first()
    if req is None or req.user_id != user.id:
        raise HTTPException(404, "Leave request not found")
    return req


@router.post("/requests/{request_id}/withdraw", response_model=LeaveOut)
def withdraw(request_id: int, session: SessionDep, user: CurrentUser) -> LeaveOut:
    """Take back a request the manager hasn't decided yet."""
    req = _own(session, user, request_id)
    approval = _approval_of(session, req.id, lock=True)
    if req.status != "applied" or approval is None or approval.status != "pending":
        raise HTTPException(409, f"This request is already {req.status}")
    before = (snapshot(req), snapshot(approval))
    req.status = "withdrawn"
    approval.status = "cancelled"
    _step(session, approval, user, "cancelled", None)
    session.flush()
    for entity, row, old, action in (
        ("leave_request", req, before[0], "withdrawn"),
        ("approval", approval, before[1], "cancelled"),
    ):
        record(
            session,
            actor_id=user.id,
            entity=entity,
            entity_id=row.id,
            action=action,
            before=old,
            after=snapshot(row),
        )
    session.commit()
    return _out(req, approval.id)


@router.post("/requests/{request_id}/cancel", response_model=LeaveOut)
def cancel(request_id: int, session: SessionDep, user: CurrentUser) -> LeaveOut:
    """Cancel approved leave: gives the balance back and removes its time entries, in one step.
    Refused when one of its weeks is already approved (HR has to sort that out)."""
    req = _own(session, user, request_id)
    if req.status != "approved":
        raise HTTPException(409, f"Only approved leave can be cancelled; this one is {req.status}")
    _lock_user(session, user.id)
    kind = session.get(LeaveType, req.leave_type_id)
    if kind is None:
        raise HTTPException(409, "The leave type no longer exists")
    entries = list(
        session.scalars(
            select(TimeEntry).where(
                TimeEntry.user_id == user.id,
                TimeEntry.source == "leave",
                TimeEntry.charge_code_id == kind.charge_code_id,
                TimeEntry.work_date.in_([date.fromisoformat(d) for d in req.day_portions]),
            )
        )
    )
    for week_id in sorted({e.week_id for e in entries}):
        week = session.get(TimesheetWeek, week_id, with_for_update=True)
        if week is not None and week.status == "approved":
            raise HTTPException(
                409, f"The week of {week.week_start} is already approved; ask HR to correct it"
            )
    for entry in entries:
        check_day_open(session, entry.week_id, entry.work_date)
    for entry in entries:
        old = snapshot(entry)
        session.delete(entry)
        session.flush()
        record(
            session,
            actor_id=user.id,
            entity="time_entry",
            entity_id=entry.id,
            action="deleted",
            before=old,
        )
    org = org_settings(session)
    balance = _balance(session, user.id, kind.id, leave_year_of(org, req.from_date), lock=True)
    if balance is not None:
        old_balance = snapshot(balance)
        balance.used = max(0, balance.used - req.minutes)
        session.flush()
        record(
            session,
            actor_id=user.id,
            entity="leave_balance",
            entity_id=balance.id,
            action="restored",
            before=old_balance,
            after=snapshot(balance),
        )
    old_req = snapshot(req)
    req.status = "cancelled"
    approval = _approval_of(session, req.id)
    if approval is not None:
        _step(session, approval, user, "leave_cancelled", None)
    session.flush()
    record(
        session,
        actor_id=user.id,
        entity="leave_request",
        entity_id=req.id,
        action="cancelled",
        before=old_req,
        after=snapshot(req),
    )
    session.commit()
    return _out(req, approval.id if approval else None)


# ---------- Called by the approval engine (approvals.py) ----------


def briefs(session: Session, request_ids: list[int]) -> dict[int, LeaveBrief]:
    """Leave summaries for the manager's inbox, in one query."""
    rows = session.execute(
        select(LeaveRequest, LeaveType.name)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .where(LeaveRequest.id.in_(request_ids))
    ).all()
    return {
        r.id: LeaveBrief(
            leave_type=name,
            from_date=r.from_date,
            to_date=r.to_date,
            hours=_hours(r.minutes),
            reason=r.reason,
            applied_after_dates=r.applied_after_dates,
        )
        for r, name in rows
    }


def _pending_request(session: Session, approval: Approval) -> LeaveRequest:
    req = session.scalars(
        select(LeaveRequest).where(LeaveRequest.id == approval.subject_id).with_for_update()
    ).first()
    if req is None or req.status != "applied":
        raise HTTPException(409, "This leave request is no longer waiting")
    return req


def approve_leave(session: Session, actor: User, approval: Approval) -> None:
    """Deduct the balance, write the leave time entries, close the approval. The caller commits."""
    req = _pending_request(session, approval)
    employee = session.get(User, req.user_id)
    kind = session.get(LeaveType, req.leave_type_id)
    if employee is None or kind is None:
        raise HTTPException(409, "The employee or the leave type no longer exists")
    _lock_user(session, employee.id)
    org = org_settings(session)
    year = leave_year_of(org, req.from_date)
    balance = _balance(session, employee.id, kind.id, year, lock=True)
    if kind.paid and _left(balance) < req.minutes:
        raise HTTPException(
            409, f"Not enough {kind.name} balance now: {_hours(_left(balance))} hours available"
        )
    before = (snapshot(req), snapshot(approval))
    full = _full_day(org)
    for iso, portion in sorted(req.day_portions.items()):
        day = date.fromisoformat(iso)
        week = session.scalars(
            select(TimesheetWeek)
            .where(
                TimesheetWeek.user_id == employee.id,
                TimesheetWeek.week_start == week_start_for(session, day),
            )
            .with_for_update()
        ).first()
        if week is None:
            week = TimesheetWeek(
                user_id=employee.id, week_start=week_start_for(session, day), status="draft"
            )
            session.add(week)
            session.flush()
        if week.status == "approved":
            raise HTTPException(
                409, f"The week of {week.week_start} is already approved; HR has to add this leave"
            )
        check_day_open(session, week.id, day)
        minutes = full if portion == "full" else full // 2
        if _day_total(session, employee, day) + minutes > 1440:
            raise HTTPException(409, f"{day} would go over 24 hours with this leave")
        entry = TimeEntry(
            user_id=employee.id,
            week_id=week.id,
            work_date=day,
            minutes=minutes,
            charge_code_id=kind.charge_code_id,
            source="leave",
            notes=f"{kind.name} leave",
        )
        session.add(entry)
        session.flush()
        record(
            session,
            actor_id=actor.id,
            entity="time_entry",
            entity_id=entry.id,
            action="created",
            after=snapshot(entry),
        )
    if balance is None:  # LOP leave with no balance row yet: keep count of what was taken
        balance = LeaveBalance(user_id=employee.id, leave_type_id=kind.id, leave_year=year)
        session.add(balance)
        session.flush()
    old_balance = snapshot(balance)
    balance.used += req.minutes
    req.status = "approved"
    approval.status = "approved"
    _step(session, approval, actor, "approved", None)
    session.flush()
    for entity, row, old, action in (
        ("leave_balance", balance, old_balance, "used"),
        ("leave_request", req, before[0], "approved"),
        ("approval", approval, before[1], "approved"),
    ):
        record(
            session,
            actor_id=actor.id,
            entity=entity,
            entity_id=row.id,
            action=action,
            before=old,
            after=snapshot(row),
        )


def reject_leave(session: Session, actor: User, approval: Approval, reason: str) -> None:
    """The manager sends the request back: nothing is deducted or written. The caller commits."""
    req = _pending_request(session, approval)
    before = (snapshot(req), snapshot(approval))
    req.status = "rejected"
    approval.status = "sent_back"
    approval.reason = reason
    _step(session, approval, actor, "sent_back", reason)
    session.flush()
    for entity, row, old in (("leave_request", req, before[0]), ("approval", approval, before[1])):
        record(
            session,
            actor_id=actor.id,
            entity=entity,
            entity_id=row.id,
            action="sent_back",
            before=old,
            after=snapshot(row),
        )
