"""create dev seed records

Revision ID: 20260622_0001
Revises:
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260622_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dev_seed_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seed_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seed_key"),
    )


def downgrade() -> None:
    op.drop_table("dev_seed_records")
