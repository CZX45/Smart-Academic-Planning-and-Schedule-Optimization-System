from collections.abc import Generator, Sequence
from typing import Any, cast

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, DevSeedRecord
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    Campus,
    Course,
    CourseEquivalency,
    CourseSubstitution,
    CourseWaiver,
    Institution,
    ProgramVersion,
    RequirementCourseOption,
    RequirementNode,
    SourceType,
    StudentAcademicProgram,
    StudentCourseAttempt,
    StudentProfile,
    TransferCredit,
)
from app.seed_dev import seed_mock_data

SEEDED_MODELS = [
    DevSeedRecord,
    Institution,
    Campus,
    AcademicTerm,
    AcademicProgram,
    ProgramVersion,
    Course,
    CourseEquivalency,
    RequirementNode,
    RequirementCourseOption,
    StudentProfile,
    StudentAcademicProgram,
    StudentCourseAttempt,
    TransferCredit,
    CourseWaiver,
    CourseSubstitution,
]


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as db:
        yield db


def table_counts(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in SEEDED_MODELS:
        counts[model.__tablename__] = session.scalar(select(func.count()).select_from(model)) or 0
    return counts


def test_mock_seed_is_idempotent(session: Session) -> None:
    seed_mock_data(session)
    first_counts = table_counts(session)

    seed_mock_data(session)
    second_counts = table_counts(session)

    assert first_counts == second_counts
    assert first_counts["institutions"] == 1
    assert first_counts["student_course_attempts"] >= 2


def test_seeded_academic_data_is_mock_and_not_official(session: Session) -> None:
    seed_mock_data(session)

    for model in SEEDED_MODELS:
        if model is DevSeedRecord:
            continue
        records = cast(Sequence[Any], session.scalars(select(model)).all())
        assert records, f"{model.__tablename__} should be seeded"
        assert all(record.source_type is SourceType.MOCK for record in records)
        assert all(record.is_official is False for record in records)


def test_mock_finance_requirement_tree_shape(session: Session) -> None:
    seed_mock_data(session)

    version = session.scalar(select(ProgramVersion).where(ProgramVersion.catalog_year == "2024"))
    assert version is not None

    nodes = session.scalars(
        select(RequirementNode)
        .where(RequirementNode.program_version_id == version.id)
        .order_by(RequirementNode.display_order)
    ).all()
    names = {node.name for node in nodes}
    assert {
        "Mock BS Finance",
        "Total Credits",
        "General Education",
        "Business Core",
        "Required Course A",
        "Required Course B",
        "Finance Major",
        "Required Finance Course",
        "Choose 2 from 3 Finance Electives",
        "Free Electives",
    }.issubset(names)

    finance_electives = next(
        node for node in nodes if node.name == "Choose 2 from 3 Finance Electives"
    )
    assert finance_electives.choose_n == 2
    option_count = session.scalar(
        select(func.count())
        .select_from(RequirementCourseOption)
        .where(RequirementCourseOption.requirement_node_id == finance_electives.id)
    )
    assert option_count == 3
