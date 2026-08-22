from __future__ import annotations

from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, Enum, Integer, MetaData, Table

from app.db.alembic_autogenerate import build_alembic_include_object


class EnrollmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


def test_reflected_check_for_metadata_enum_is_not_reported_as_removed() -> None:
    metadata = MetaData()
    Table(
        "student_profiles",
        metadata,
        Column(
            "status",
            Enum(
                EnrollmentStatus,
                name="enrollment_status",
                native_enum=False,
                create_constraint=True,
            ),
        ),
    )
    reflected_table = Table(
        "student_profiles",
        MetaData(),
        Column("x", Integer),
    )
    reflected_constraint = CheckConstraint(
        "status IN ('ACTIVE', 'INACTIVE')",
        name="enrollment_status",
        table=reflected_table,
    )

    include_object = build_alembic_include_object(metadata)

    assert (
        include_object(
            reflected_constraint,
            "enrollment_status",
            "check_constraint",
            True,
            None,
        )
        is False
    )


def test_unmodeled_reflected_check_remains_visible_to_autogenerate() -> None:
    metadata = MetaData()
    Table("student_profiles", metadata, Column("status", Integer))
    reflected_table = Table(
        "student_profiles",
        MetaData(),
        Column("x", Integer),
    )
    reflected_constraint = CheckConstraint(
        "status >= 0",
        name="ck_student_profiles_status_non_negative",
        table=reflected_table,
    )

    include_object = build_alembic_include_object(metadata)

    assert (
        include_object(
            reflected_constraint,
            "ck_student_profiles_status_non_negative",
            "check_constraint",
            True,
            None,
        )
        is True
    )
