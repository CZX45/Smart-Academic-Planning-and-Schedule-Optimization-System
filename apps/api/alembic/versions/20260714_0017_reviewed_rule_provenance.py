"""add reviewed rule provenance to audit and eligibility snapshots

Revision ID: 20260714_0017
Revises: 20260714_0016
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260714_0017"
down_revision: str | None = "20260714_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_column(name: str) -> sa.Column[Any]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=True)


def add_columns(table_name: str, *, include_reviewed_reasons: bool = False) -> None:
    op.add_column(table_name, uuid_column("reviewed_rule_set_id"))
    op.add_column(
        table_name,
        sa.Column("rule_resolution_state", sa.String(32), nullable=False, server_default="MISSING"),
    )
    op.add_column(table_name, sa.Column("rule_source_reference", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("rule_catalog_year", sa.String(32), nullable=True))
    op.add_column(
        table_name,
        sa.Column(
            "rule_resolution_explanation",
            sa.Text(),
            nullable=False,
            server_default="No reviewed rule set was selected.",
        ),
    )
    if include_reviewed_reasons:
        op.add_column(
            table_name,
            sa.Column(
                "reviewed_rule_reasons",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
        )


def drop_columns(table_name: str) -> None:
    names = [
        "rule_resolution_explanation",
        "rule_catalog_year",
        "rule_source_reference",
        "rule_resolution_state",
        "reviewed_rule_set_id",
    ]
    if table_name == "eligibility_check_runs":
        names.append("reviewed_rule_reasons")
    for name in names:
        op.drop_column(table_name, name)


def upgrade() -> None:
    add_columns("degree_audit_runs")
    add_columns("eligibility_check_runs", include_reviewed_reasons=True)


def downgrade() -> None:
    drop_columns("eligibility_check_runs")
    drop_columns("degree_audit_runs")
