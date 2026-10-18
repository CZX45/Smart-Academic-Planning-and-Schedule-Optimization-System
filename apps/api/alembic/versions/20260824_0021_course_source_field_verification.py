"""track whether source evidence proves optional Course fields

Revision ID: 20260824_0021
Revises: 20260715_0020
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260824_0021"
down_revision: str | None = "20260715_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column(
            "course_level_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "courses",
        sa.Column(
            "repeatable_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute(
        "UPDATE courses SET course_level_verified = false, repeatable_verified = false "
        "WHERE source_type IN ("
        "'BROWSER_EXTENSION', 'IMPORTED', 'STUDENT_PROVIDED', 'INFERRED'"
        ")"
    )
    op.alter_column("courses", "course_level_verified", server_default=None)
    op.alter_column("courses", "repeatable_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("courses", "repeatable_verified")
    op.drop_column("courses", "course_level_verified")
