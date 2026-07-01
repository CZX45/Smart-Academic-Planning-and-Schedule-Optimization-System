"""allow browser extension source type for staged imports

Revision ID: 20260701_0012
Revises: 20260630_0011
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260701_0012"
down_revision: str | None = "20260630_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPE_TABLES = (
    "institutions",
    "campuses",
    "academic_terms",
    "academic_programs",
    "program_versions",
    "courses",
    "course_offering_patterns",
    "sections",
    "section_meetings",
    "course_rules",
    "course_rule_expressions",
    "course_equivalencies",
    "requirement_nodes",
    "requirement_course_options",
    "student_profiles",
    "student_academic_programs",
    "student_course_attempts",
    "transfer_credits",
    "course_waivers",
    "course_substitutions",
    "program_combination_rules",
    "data_import_runs",
)
OLD_SOURCE_TYPES = ("MOCK", "OFFICIAL", "IMPORTED", "STUDENT_PROVIDED", "INFERRED")
NEW_SOURCE_TYPES = (
    "MOCK",
    "OFFICIAL",
    "IMPORTED",
    "BROWSER_EXTENSION",
    "STUDENT_PROVIDED",
    "INFERRED",
)
OLD_SOURCE_TYPE_LENGTH = 16
NEW_SOURCE_TYPE_LENGTH = 17


def source_type_check(values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"source_type IN ({quoted})"


def replace_source_type_constraints(values: tuple[str, ...]) -> None:
    for table_name in SOURCE_TYPE_TABLES:
        op.drop_constraint("source_type", table_name, type_="check")
        op.create_check_constraint(
            "source_type",
            table_name,
            source_type_check(values),
        )


def alter_source_type_length(length: int, existing_length: int) -> None:
    for table_name in SOURCE_TYPE_TABLES:
        op.alter_column(
            table_name,
            "source_type",
            existing_type=sa.String(length=existing_length),
            type_=sa.String(length=length),
            existing_nullable=False,
        )


def upgrade() -> None:
    alter_source_type_length(NEW_SOURCE_TYPE_LENGTH, OLD_SOURCE_TYPE_LENGTH)
    replace_source_type_constraints(NEW_SOURCE_TYPES)


def downgrade() -> None:
    connection = op.get_bind()
    for table_name in SOURCE_TYPE_TABLES:
        count = connection.scalar(
            sa.text(f"SELECT count(*) FROM {table_name} WHERE source_type = 'BROWSER_EXTENSION'")
        )
        if count:
            raise RuntimeError(
                f"Cannot downgrade while BROWSER_EXTENSION source rows exist in {table_name}."
            )
    replace_source_type_constraints(OLD_SOURCE_TYPES)
    alter_source_type_length(OLD_SOURCE_TYPE_LENGTH, NEW_SOURCE_TYPE_LENGTH)
