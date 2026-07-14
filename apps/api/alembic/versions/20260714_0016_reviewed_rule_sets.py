"""add staged reviewed Program/Catalog rule sets

Revision ID: 20260714_0016
Revises: 20260712_0015
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260714_0016"
down_revision: str | None = "20260712_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_column(name: str) -> sa.Column[Any]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=False)


def lifecycle_enum() -> sa.Enum:
    return sa.Enum(
        "DRAFT",
        "REQUIRES_REVIEW",
        "REVIEWED",
        "ACTIVE",
        "SUPERSEDED",
        "RETIRED",
        "REJECTED",
        name="rule_lifecycle",
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


def upgrade() -> None:
    op.create_table(
        "reviewed_rule_sets",
        uuid_column("id"),
        sa.Column("institution_identifier", sa.String(120), nullable=False),
        sa.Column("program_identifier", sa.String(120), nullable=False),
        sa.Column("catalog_year", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lifecycle", lifecycle_enum(), nullable=False),
        sa.Column("source_title", sa.String(255), nullable=False),
        sa.Column("source_location", sa.String(500), nullable=False),
        sa.Column("source_evidence", sa.Text(), nullable=False),
        sa.Column("source_fingerprint", sa.String(128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("validation_warnings", sa.JSON(), nullable=False),
        sa.Column("reviewer_confirmed", sa.Boolean(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_reviewed_rule_sets_identity_version",
        "reviewed_rule_sets",
        ["institution_identifier", "program_identifier", "catalog_year", "version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_reviewed_rule_sets_identity_version", table_name="reviewed_rule_sets")
    op.drop_table("reviewed_rule_sets")
