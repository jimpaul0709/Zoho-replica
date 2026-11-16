"""day decision (per-day approval)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-16 15:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "day_decision",
        sa.Column("week_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "status in ('approved','sent_back')", name=op.f("ck_day_decision_status")
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["app_user.id"], name=op.f("fk_day_decision_decided_by_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["week_id"], ["timesheet_week.id"], name=op.f("fk_day_decision_week_id_timesheet_week")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_day_decision")),
        sa.UniqueConstraint("week_id", "work_date", name=op.f("uq_day_decision_week_id")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("day_decision")
