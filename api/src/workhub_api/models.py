"""Core database tables (WH-03). Mirrors api/docs/erd.md diagrams 1 and 2.

Time is stored as integer minutes. `user` is reserved in Postgres, so the table is `app_user`.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint names so Alembic can drop/alter them later.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def _fk(target: str, **kw: Any) -> Mapped[int]:
    return mapped_column(ForeignKey(target), **kw)


class Stamped:
    """id + created_at + updated_at, on every table except the pure link tables."""

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------- 1. Organisation, people and work ----------


class OrgSettings(Stamped, Base):
    __tablename__ = "org_settings"

    work_week_days: Mapped[str] = mapped_column(String(20), server_default="Mon-Fri")
    week_start: Mapped[str] = mapped_column(String(10), server_default="Monday")
    daily_expected_minutes: Mapped[int] = mapped_column(Integer, server_default="480")
    fy_start_month: Mapped[int] = mapped_column(Integer, server_default="4")
    client_portal_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    approval_due_working_days: Mapped[int] = mapped_column(Integer, server_default="2")


class Location(Stamped, Base):
    __tablename__ = "location"

    name: Mapped[str] = mapped_column(String(100), unique=True)


class Holiday(Stamped, Base):
    __tablename__ = "holiday"
    __table_args__ = (UniqueConstraint("location_id", "on_date"),)

    location_id: Mapped[int] = _fk("location.id")
    on_date: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(100))


class User(Stamped, Base):
    __tablename__ = "app_user"

    employee_code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    designation: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    location_id: Mapped[int | None] = _fk("location.id", nullable=True)
    manager_id: Mapped[int | None] = _fk("app_user.id", nullable=True)
    joined_on: Mapped[date | None] = mapped_column(Date)
    exited_on: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class RoleAssignment(Stamped, Base):
    __tablename__ = "role_assignment"
    __table_args__ = (
        UniqueConstraint("user_id", "role"),
        CheckConstraint("role in ('employee','manager','hr','finance','admin')", name="role"),
    )

    user_id: Mapped[int] = _fk("app_user.id")
    role: Mapped[str] = mapped_column(String(20))


class Team(Stamped, Base):
    __tablename__ = "team"

    name: Mapped[str] = mapped_column(String(100), unique=True)


class TeamMember(Base):
    __tablename__ = "team_member"

    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), primary_key=True)


class Client(Stamped, Base):
    __tablename__ = "client"

    name: Mapped[str] = mapped_column(String(150), unique=True)


class WorkOrder(Stamped, Base):
    __tablename__ = "work_order"

    client_id: Mapped[int] = _fk("client.id")
    code: Mapped[str] = mapped_column(String(50), unique=True)
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)


class Project(Stamped, Base):
    __tablename__ = "project"
    __table_args__ = (CheckConstraint("visibility in ('public','private')", name="visibility"),)

    key: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    group_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), server_default="active")
    visibility: Mapped[str] = mapped_column(String(10), server_default="public")
    manager_id: Mapped[int | None] = _fk("app_user.id", nullable=True)
    work_order_id: Mapped[int | None] = _fk("work_order.id", nullable=True)


class ProjectMember(Base):
    __tablename__ = "project_member"

    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    project_role: Mapped[str | None] = mapped_column(String(50))


class ProjectTeam(Base):
    __tablename__ = "project_team"

    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), primary_key=True)


class TaskList(Stamped, Base):
    __tablename__ = "task_list"

    project_id: Mapped[int] = _fk("project.id")
    name: Mapped[str] = mapped_column(String(150))
    position: Mapped[int] = mapped_column(Integer, server_default="0")


class TaskStatus(Stamped, Base):
    __tablename__ = "task_status"

    project_id: Mapped[int] = _fk("project.id")
    name: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer, server_default="0")
    is_closed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class Task(Stamped, Base):
    __tablename__ = "task"

    task_list_id: Mapped[int] = _fk("task_list.id")
    status_id: Mapped[int] = _fk("task_status.id")
    key: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(20))
    start_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
    parent_id: Mapped[int | None] = _fk("task.id", nullable=True)
    is_milestone: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class TaskOwner(Stamped, Base):
    __tablename__ = "task_owner"
    __table_args__ = (
        CheckConstraint("(user_id is null) <> (team_id is null)", name="user_or_team"),
    )

    task_id: Mapped[int] = _fk("task.id")
    user_id: Mapped[int | None] = _fk("app_user.id", nullable=True)
    team_id: Mapped[int | None] = _fk("team.id", nullable=True)


class ChargeCode(Stamped, Base):
    __tablename__ = "charge_code"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class ChargeCodeTeam(Base):
    __tablename__ = "charge_code_team"

    charge_code_id: Mapped[int] = mapped_column(ForeignKey("charge_code.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), primary_key=True)


# ---------- 2. Time, approvals, audit and jobs ----------


class TimesheetWeek(Stamped, Base):
    __tablename__ = "timesheet_week"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start"),
        CheckConstraint("status in ('draft','submitted','approved','sent_back')", name="status"),
    )

    user_id: Mapped[int] = _fk("app_user.id")
    week_start: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), server_default="draft")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TimeEntry(Stamped, Base):
    __tablename__ = "time_entry"
    __table_args__ = (
        CheckConstraint("(task_id is null) <> (charge_code_id is null)", name="task_or_charge"),
        CheckConstraint("minutes between 1 and 1440", name="minutes"),
        CheckConstraint(
            "source in ('manual','timer','calendar','git','leave','holiday')", name="source"
        ),
        Index("ix_time_entry_user_id_work_date", "user_id", "work_date"),
    )

    user_id: Mapped[int] = _fk("app_user.id")
    week_id: Mapped[int] = _fk("timesheet_week.id", index=True)
    work_date: Mapped[date] = mapped_column(Date)
    minutes: Mapped[int] = mapped_column(Integer)
    task_id: Mapped[int | None] = _fk("task.id", nullable=True)
    charge_code_id: Mapped[int | None] = _fk("charge_code.id", nullable=True)
    billable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), server_default="manual")
    sent_back_reason: Mapped[str | None] = mapped_column(Text)


class Approval(Stamped, Base):
    __tablename__ = "approval"
    __table_args__ = (
        CheckConstraint("status in ('pending','approved','sent_back','cancelled')", name="status"),
        Index("ix_approval_subject_type_subject_id", "subject_type", "subject_id"),
        Index("ix_approval_approver_id_status", "approver_id", "status"),
    )

    # Polymorphic reference (week, leave, comp_off, edit_request): no real FK, the API checks it.
    subject_type: Mapped[str] = mapped_column(String(30))
    subject_id: Mapped[int] = mapped_column(Integer)
    requester_id: Mapped[int] = _fk("app_user.id")
    approver_id: Mapped[int] = _fk("app_user.id")
    level: Mapped[int] = mapped_column(Integer, server_default="1")
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)


class ApprovalStep(Stamped, Base):
    __tablename__ = "approval_step"

    approval_id: Mapped[int] = _fk("approval.id", index=True)
    actor_id: Mapped[int] = _fk("app_user.id")
    action: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Delegation(Stamped, Base):
    __tablename__ = "delegation"
    __table_args__ = (CheckConstraint("from_user_id <> to_user_id", name="not_self"),)

    from_user_id: Mapped[int] = _fk("app_user.id")
    to_user_id: Mapped[int] = _fk("app_user.id")
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)


class EditRequest(Stamped, Base):
    """A request to change a locked (approved) week. It goes through approval (WH-22)."""

    __tablename__ = "edit_request"
    __table_args__ = (
        CheckConstraint("status in ('pending','approved','rejected','cancelled')", name="status"),
    )

    week_id: Mapped[int] = _fk("timesheet_week.id", index=True)
    requester_id: Mapped[int] = _fk("app_user.id")
    reason: Mapped[str] = mapped_column(Text)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # add / update / delete entries
    status: Mapped[str] = mapped_column(String(20), server_default="pending")


class DayDecision(Stamped, Base):
    """The manager's decision on one day of a week: approved (locked) or sent back to fix.

    No row means the day is still waiting (or still a draft). Rows for sent-back days are removed
    when the employee resubmits; rows for approved days stay.
    """

    __tablename__ = "day_decision"
    __table_args__ = (
        UniqueConstraint("week_id", "work_date"),
        CheckConstraint("status in ('approved','sent_back')", name="status"),
    )

    week_id: Mapped[int] = _fk("timesheet_week.id")
    work_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[int] = _fk("app_user.id")


# ---------- Sign-in version 1: email and password (migration 0006) ----------


class Credential(Stamped, Base):
    """A user's password. A user with no row here cannot sign in."""

    __tablename__ = "credential"

    user_id: Mapped[int] = _fk("app_user.id", unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # "scrypt$<salt hex>$<hash hex>"
    must_change: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    failed_attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Stamped, Base):
    """One signed-in browser. Only the SHA-256 of the token is stored, never the token."""

    __tablename__ = "auth_session"

    user_id: Mapped[int] = _fk("app_user.id")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------- 3. Leave (WH-40, WH-41). Minutes; a full day is daily_expected_minutes ----------


class LeaveType(Stamped, Base):
    __tablename__ = "leave_type"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    paid: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    charge_code_id: Mapped[int] = _fk("charge_code.id")  # the time entries written on approval
    accrual_per_month: Mapped[int] = mapped_column(Integer, server_default="0")
    carry_forward_cap: Mapped[int] = mapped_column(Integer, server_default="0")
    attachment_after_days: Mapped[int | None] = mapped_column(Integer)  # needs a file beyond this


class LeaveBalance(Stamped, Base):
    """available = opening + accrued + adjusted - used, for one person, type and leave year."""

    __tablename__ = "leave_balance"
    __table_args__ = (UniqueConstraint("user_id", "leave_type_id", "leave_year"),)

    user_id: Mapped[int] = _fk("app_user.id")
    leave_type_id: Mapped[int] = _fk("leave_type.id")
    leave_year: Mapped[int] = mapped_column(Integer)  # the year the leave year starts in
    opening: Mapped[int] = mapped_column(Integer, server_default="0")
    accrued: Mapped[int] = mapped_column(Integer, server_default="0")
    used: Mapped[int] = mapped_column(Integer, server_default="0")
    adjusted: Mapped[int] = mapped_column(Integer, server_default="0")


class LeaveRequest(Stamped, Base):
    __tablename__ = "leave_request"
    __table_args__ = (
        CheckConstraint(
            "status in ('applied','approved','rejected','withdrawn','cancelled')", name="status"
        ),
        CheckConstraint("from_date <= to_date", name="dates"),
    )

    user_id: Mapped[int] = _fk("app_user.id", index=True)
    leave_type_id: Mapped[int] = _fk("leave_type.id")
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)
    day_portions: Mapped[dict[str, str]] = mapped_column(
        JSONB
    )  # date -> full/first_half/second_half
    minutes: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    attachment_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), server_default="applied")
    applied_after_dates: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class BlackoutDay(Stamped, Base):
    """A day nobody can take leave on (organisation-wide for now; team scope comes later)."""

    __tablename__ = "blackout_day"

    on_date: Mapped[date] = mapped_column(Date, unique=True)
    note: Mapped[str] = mapped_column(Text)


class AuditEvent(Base):
    """Append-only: a trigger in the migration rejects UPDATE and DELETE."""

    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_audit_event_entity_entity_id", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[int | None] = _fk("app_user.id", nullable=True)
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(50))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Stamped, Base):
    """Postgres-backed queue; the worker (WH-07) picks rows with FOR UPDATE SKIP LOCKED."""

    __tablename__ = "job"
    __table_args__ = (Index("ix_job_status_run_at", "status", "run_at"),)

    kind: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default="queued")
