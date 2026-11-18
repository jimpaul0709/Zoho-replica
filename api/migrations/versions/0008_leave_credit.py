"""leave credit ledger for the monthly accrual and carry-forward job

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18 17:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "leave_credit",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=20), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["leave_type_id"],
            ["leave_type.id"],
            name=op.f("fk_leave_credit_leave_type_id_leave_type"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name=op.f("fk_leave_credit_user_id_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leave_credit")),
        sa.UniqueConstraint(
            "user_id", "leave_type_id", "key", name=op.f("uq_leave_credit_user_id")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("leave_credit")
