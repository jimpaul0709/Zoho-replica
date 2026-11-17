"""leave: types, balances, requests, blackout days

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-17 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _stamps() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "leave_type",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("paid", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("charge_code_id", sa.Integer(), nullable=False),
        sa.Column("accrual_per_month", sa.Integer(), server_default="0", nullable=False),
        sa.Column("carry_forward_cap", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attachment_after_days", sa.Integer(), nullable=True),
        *_stamps(),
        sa.ForeignKeyConstraint(
            ["charge_code_id"],
            ["charge_code.id"],
            name=op.f("fk_leave_type_charge_code_id_charge_code"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leave_type")),
        sa.UniqueConstraint("name", name=op.f("uq_leave_type_name")),
    )
    op.create_table(
        "leave_balance",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), nullable=False),
        sa.Column("leave_year", sa.Integer(), nullable=False),
        sa.Column("opening", sa.Integer(), server_default="0", nullable=False),
        sa.Column("accrued", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("adjusted", sa.Integer(), server_default="0", nullable=False),
        *_stamps(),
        sa.ForeignKeyConstraint(
            ["leave_type_id"],
            ["leave_type.id"],
            name=op.f("fk_leave_balance_leave_type_id_leave_type"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name=op.f("fk_leave_balance_user_id_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leave_balance")),
        sa.UniqueConstraint(
            "user_id", "leave_type_id", "leave_year", name=op.f("uq_leave_balance_user_id")
        ),
    )
    op.create_table(
        "leave_request",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("day_portions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("attachment_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="applied", nullable=False),
        sa.Column(
            "applied_after_dates", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        *_stamps(),
        sa.CheckConstraint(
            "status in ('applied','approved','rejected','withdrawn','cancelled')",
            name=op.f("ck_leave_request_status"),
        ),
        sa.CheckConstraint("from_date <= to_date", name=op.f("ck_leave_request_dates")),
        sa.ForeignKeyConstraint(
            ["leave_type_id"],
            ["leave_type.id"],
            name=op.f("fk_leave_request_leave_type_id_leave_type"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name=op.f("fk_leave_request_user_id_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leave_request")),
    )
    op.create_index(op.f("ix_leave_request_user_id"), "leave_request", ["user_id"], unique=False)
    op.create_table(
        "blackout_day",
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        *_stamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blackout_day")),
        sa.UniqueConstraint("on_date", name=op.f("uq_blackout_day_on_date")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("blackout_day")
    op.drop_index(op.f("ix_leave_request_user_id"), table_name="leave_request")
    op.drop_table("leave_request")
    op.drop_table("leave_balance")
    op.drop_table("leave_type")
