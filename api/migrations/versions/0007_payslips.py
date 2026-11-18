"""payslips: monthly batches and one PDF per employee (WH-50)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18 15:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
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
        "payslip_batch",
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("match_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *_stamps(),
        sa.CheckConstraint("status in ('draft','published')", name=op.f("ck_payslip_batch_status")),
        sa.ForeignKeyConstraint(
            ["uploaded_by"], ["app_user.id"], name=op.f("fk_payslip_batch_uploaded_by_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payslip_batch")),
        sa.UniqueConstraint("month", name=op.f("uq_payslip_batch_month")),
    )
    op.create_table(
        "payslip",
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        *_stamps(),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["payslip_batch.id"], name=op.f("fk_payslip_batch_id_payslip_batch")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name=op.f("fk_payslip_user_id_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payslip")),
        sa.UniqueConstraint("batch_id", "user_id", name=op.f("uq_payslip_batch_id")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("payslip")
    op.drop_table("payslip_batch")
