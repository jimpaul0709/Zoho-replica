"""edit request

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16 12:54:18.968603

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "edit_request",
        sa.Column("week_id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
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
            "status in ('pending','approved','rejected','cancelled')",
            name=op.f("ck_edit_request_status"),
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"], ["app_user.id"], name=op.f("fk_edit_request_requester_id_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["week_id"], ["timesheet_week.id"], name=op.f("fk_edit_request_week_id_timesheet_week")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_edit_request")),
    )
    op.create_index(op.f("ix_edit_request_week_id"), "edit_request", ["week_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_edit_request_week_id"), table_name="edit_request")
    op.drop_table("edit_request")
