from collections.abc import Generator
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AcademicPlanScenario,
    AcademicPlanScenarioStatus,
    ProgramCombinationRule,
    ScenarioProgram,
    ScenarioRelationshipType,
    ScenarioType,
    SourceType,
    StudentAcademicProgram,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.academic_scenarios.allocator import (
    AllocationCandidate,
    DeterministicMultiProgramAllocator,
    ProgramCombinationPolicy,
)


def uid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"sapsos-scenario-test:{name}")


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
        seed_mock_data(db)
        yield db


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as seed_session:
        seed_mock_data(seed_session)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def candidate(
    name: str,
    *,
    source_name: str,
    program_name: str,
    relationship_type: ScenarioRelationshipType,
    requirement_name: str,
    display_order: int,
    priority: int,
    allows_overlap: bool = False,
) -> AllocationCandidate:
    return AllocationCandidate(
        candidate_id=uid(f"candidate:{name}"),
        source_key=("attempt", uid(f"attempt:{source_name}")),
        course_id=uid(f"course:{source_name}"),
        course_code=source_name,
        program_version_id=uid(f"program:{program_name}"),
        relationship_type=relationship_type,
        requirement_node_id=uid(f"requirement:{requirement_name}"),
        requirement_code=requirement_name,
        requirement_display_order=display_order,
        requirement_allows_overlap=allows_overlap,
        program_priority=priority,
        credit_amount=Decimal("3.0"),
        is_earned=True,
        is_completed=True,
        is_in_progress=False,
        is_planned=False,
        attempt_number=1,
        explanation=f"{source_name} can satisfy {requirement_name}.",
    )


def policy(
    *,
    primary_name: str = "primary",
    secondary_name: str = "minor",
    allows_double_counting: bool,
    maximum_shared_credits: str = "3.0",
    minimum_unique_secondary_credits: str = "0.0",
) -> ProgramCombinationPolicy:
    return ProgramCombinationPolicy(
        primary_program_version_id=uid(f"program:{primary_name}"),
        secondary_program_version_id=uid(f"program:{secondary_name}"),
        relationship_type=ScenarioRelationshipType.MINOR,
        maximum_shared_credits=Decimal(maximum_shared_credits),
        minimum_unique_secondary_credits=Decimal(minimum_unique_secondary_credits),
        minimum_unique_courses=0,
        allows_double_counting=allows_double_counting,
        requires_manual_confirmation=False,
        source_type=SourceType.MOCK,
        is_official=False,
    )


def test_allocator_uses_global_objective_instead_of_local_greedy() -> None:
    allocator = DeterministicMultiProgramAllocator(search_limit=128)
    primary = ScenarioRelationshipType.PRIMARY_MAJOR
    minor = ScenarioRelationshipType.MINOR

    result = allocator.allocate(
        [
            candidate(
                "shared-course-primary",
                source_name="BUS 201",
                program_name="primary",
                relationship_type=primary,
                requirement_name="PRIMARY-REQ",
                display_order=10,
                priority=0,
            ),
            candidate(
                "shared-course-minor",
                source_name="BUS 201",
                program_name="minor",
                relationship_type=minor,
                requirement_name="MINOR-REQ",
                display_order=10,
                priority=10,
            ),
            candidate(
                "primary-only-course",
                source_name="FIN 210",
                program_name="primary",
                relationship_type=primary,
                requirement_name="PRIMARY-REQ",
                display_order=10,
                priority=0,
            ),
        ],
        [policy(allows_double_counting=False)],
    )

    selected = {
        allocation.candidate_id for allocation in result.allocations if allocation.is_selected
    }
    assert uid("candidate:primary-only-course") in selected
    assert uid("candidate:shared-course-minor") in selected
    assert uid("candidate:shared-course-primary") not in selected
    assert result.objective.satisfied_required_requirements == 2
    assert result.objective.total_earned_credits == Decimal("6.0")


def test_allocator_requires_requirement_overlap_and_directional_policy_for_shared_credit() -> None:
    allocator = DeterministicMultiProgramAllocator(search_limit=128)
    primary_candidate = candidate(
        "overlap-primary",
        source_name="ACCT 300",
        program_name="primary",
        relationship_type=ScenarioRelationshipType.PRIMARY_MAJOR,
        requirement_name="PRIMARY-ELECTIVE",
        display_order=20,
        priority=0,
        allows_overlap=True,
    )
    minor_candidate = candidate(
        "overlap-minor",
        source_name="ACCT 300",
        program_name="minor",
        relationship_type=ScenarioRelationshipType.MINOR,
        requirement_name="MINOR-CORE",
        display_order=10,
        priority=10,
        allows_overlap=True,
    )

    result = allocator.allocate(
        [primary_candidate, minor_candidate],
        [policy(allows_double_counting=True, maximum_shared_credits="3.0")],
    )

    assert {
        allocation.candidate_id for allocation in result.allocations if allocation.is_shared
    } == {
        primary_candidate.candidate_id,
        minor_candidate.candidate_id,
    }
    assert result.objective.shared_credits == Decimal("3.0")
    assert result.objective.total_earned_credits == Decimal("3.0")

    blocked = allocator.allocate(
        [
            primary_candidate,
            candidate(
                "blocked-minor",
                source_name="ACCT 300",
                program_name="minor",
                relationship_type=ScenarioRelationshipType.MINOR,
                requirement_name="MINOR-CORE",
                display_order=10,
                priority=10,
                allows_overlap=False,
            ),
        ],
        [policy(allows_double_counting=True, maximum_shared_credits="3.0")],
    )
    assert blocked.objective.shared_credits == Decimal("0.0")
    assert all(not allocation.is_shared for allocation in blocked.allocations)


def test_scenario_database_constraints_reject_invalid_combination_rules(
    session: Session,
) -> None:
    finance_version_id = seed_uuid("program-version:bs-finance-2024")
    rule = ProgramCombinationRule(
        id=uid("combination-rule:same-program"),
        primary_program_version_id=finance_version_id,
        secondary_program_version_id=finance_version_id,
        combination_type=ScenarioRelationshipType.MINOR,
        maximum_shared_credits=Decimal("3.0"),
        minimum_unique_secondary_credits=Decimal("6.0"),
        minimum_unique_courses=2,
        allows_double_counting=True,
        requires_manual_confirmation=False,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(rule)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()

    rule = ProgramCombinationRule(
        id=uid("combination-rule:negative"),
        primary_program_version_id=finance_version_id,
        secondary_program_version_id=seed_uuid("program-version:accounting-minor-2024"),
        combination_type=ScenarioRelationshipType.MINOR,
        maximum_shared_credits=Decimal("-1.0"),
        minimum_unique_secondary_credits=Decimal("6.0"),
        minimum_unique_courses=2,
        allows_double_counting=True,
        requires_manual_confirmation=False,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(rule)

    with pytest.raises(IntegrityError):
        session.commit()


def test_scenario_programs_do_not_change_declared_programs(session: Session) -> None:
    student_id = seed_uuid("student-profile:mock-student")
    declared_before = session.scalar(
        select(func.count())
        .select_from(StudentAcademicProgram)
        .where(StudentAcademicProgram.student_profile_id == student_id)
    )
    scenario = AcademicPlanScenario(
        id=uid("scenario:add-accounting-minor"),
        student_profile_id=student_id,
        name="Add Accounting Minor",
        scenario_type=ScenarioType.ADD_MINOR,
        status=AcademicPlanScenarioStatus.DRAFT,
        base_program_version_id=seed_uuid("program-version:bs-finance-2024"),
        engine_version="phase-3b-academic-scenario-v1",
    )
    session.add(scenario)
    session.flush()
    session.add(
        ScenarioProgram(
            id=uid("scenario-program:accounting-minor"),
            academic_plan_scenario_id=scenario.id,
            program_version_id=seed_uuid("program-version:accounting-minor-2024"),
            relationship_type=ScenarioRelationshipType.MINOR,
            is_existing_program=False,
            is_hypothetical=True,
            priority=10,
        )
    )
    session.commit()

    declared_after = session.scalar(
        select(func.count())
        .select_from(StudentAcademicProgram)
        .where(StudentAcademicProgram.student_profile_id == student_id)
    )

    assert declared_after == declared_before


def test_scenario_api_creates_snapshot_and_exposes_comparison(client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    finance_version_id = str(seed_uuid("program-version:bs-finance-2024"))
    accounting_minor_id = str(seed_uuid("program-version:accounting-minor-2024"))

    before_student = client.get(f"/api/v1/students/{student_id}").json()

    response = client.post(
        "/api/v1/academic-scenarios",
        json={
            "student_profile_id": student_id,
            "scenario_name": "Add Accounting Minor",
            "scenario_type": "ADD_MINOR",
            "calculation_mode": "PROJECTED",
            "programs": [
                {
                    "program_version_id": finance_version_id,
                    "relationship_type": "PRIMARY_MAJOR",
                    "priority": 0,
                },
                {
                    "program_version_id": accounting_minor_id,
                    "relationship_type": "MINOR",
                    "priority": 10,
                },
            ],
        },
    )

    assert response.status_code == 201
    scenario = response.json()
    scenario_id = scenario["id"]
    UUID(scenario_id)
    assert scenario["scenario_type"] == "ADD_MINOR"
    assert scenario["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    assert scenario["engine_version"] == "phase-3b-academic-scenario-v1"
    assert "eligibility" not in scenario

    after_student = client.get(f"/api/v1/students/{student_id}").json()
    assert after_student["programs"] == before_student["programs"]

    programs = client.get(f"/api/v1/academic-scenarios/{scenario_id}/programs")
    assert programs.status_code == 200
    assert [program["relationship_type"] for program in programs.json()] == [
        "PRIMARY_MAJOR",
        "MINOR",
    ]
    assert programs.json()[1]["is_hypothetical"] is True

    audits = client.get(f"/api/v1/academic-scenarios/{scenario_id}/audits")
    assert audits.status_code == 200
    assert len(audits.json()) == 2
    assert all(
        item["degree_audit_run"]["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
        for item in audits.json()
    )

    allocations = client.get(f"/api/v1/academic-scenarios/{scenario_id}/allocations")
    assert allocations.status_code == 200
    allocation_payload = allocations.json()
    assert any(allocation["allocation_type"] == "SHARED" for allocation in allocation_payload)
    assert any(
        allocation["allocation_type"] == "UNIQUE_SECONDARY" for allocation in allocation_payload
    )
    assert all("explanation" in allocation for allocation in allocation_payload)

    comparison = client.get(f"/api/v1/academic-scenarios/{scenario_id}/comparison")
    assert comparison.status_code == 200
    summary = comparison.json()
    assert summary["academic_plan_scenario_id"] == scenario_id
    assert Decimal(summary["shared_credits"]) >= Decimal("3.0")
    assert Decimal(summary["unique_secondary_credits"]) >= Decimal("3.0")
    assert Decimal(summary["estimated_additional_credits"]) >= Decimal("0.0")
    assert summary["is_estimate"] is True
    assert "graduation" not in str(summary).lower()


def test_scenario_api_reports_missing_directional_combination_rule(client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))

    response = client.post(
        "/api/v1/academic-scenarios",
        json={
            "student_profile_id": student_id,
            "scenario_name": "Add Mock Second Major",
            "scenario_type": "ADD_SECOND_MAJOR",
            "calculation_mode": "PROJECTED",
            "programs": [
                {
                    "program_version_id": str(seed_uuid("program-version:bs-finance-2024")),
                    "relationship_type": "PRIMARY_MAJOR",
                    "priority": 0,
                },
                {
                    "program_version_id": str(seed_uuid("program-version:second-major-2024")),
                    "relationship_type": "SECOND_MAJOR",
                    "priority": 10,
                },
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED_WITH_WARNINGS"

    warnings = client.get(f"/api/v1/academic-scenarios/{response.json()['id']}/warnings")
    assert warnings.status_code == 200
    assert any(
        warning["warning_code"] == "MISSING_PROGRAM_COMBINATION_RULE"
        and warning["requires_advisor_confirmation"]
        for warning in warnings.json()
    )


def test_scenario_api_rejects_duplicate_program_and_compares_saved_scenarios(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    finance_version_id = str(seed_uuid("program-version:bs-finance-2024"))

    duplicate = client.post(
        "/api/v1/academic-scenarios",
        json={
            "student_profile_id": student_id,
            "scenario_name": "Duplicate Program",
            "scenario_type": "CUSTOM_COMBINATION",
            "calculation_mode": "PROJECTED",
            "programs": [
                {
                    "program_version_id": finance_version_id,
                    "relationship_type": "PRIMARY_MAJOR",
                    "priority": 0,
                },
                {
                    "program_version_id": finance_version_id,
                    "relationship_type": "MINOR",
                    "priority": 10,
                },
            ],
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["code"] == "duplicate_program_version"

    scenario_ids: list[str] = []
    for name, program_id in [
        ("Accounting Minor", "program-version:accounting-minor-2024"),
        ("Economics Minor", "program-version:economics-minor-2024"),
    ]:
        response = client.post(
            "/api/v1/academic-scenarios",
            json={
                "student_profile_id": student_id,
                "scenario_name": name,
                "scenario_type": "ADD_MINOR",
                "calculation_mode": "PROJECTED",
                "programs": [
                    {
                        "program_version_id": finance_version_id,
                        "relationship_type": "PRIMARY_MAJOR",
                        "priority": 0,
                    },
                    {
                        "program_version_id": str(seed_uuid(program_id)),
                        "relationship_type": "MINOR",
                        "priority": 10,
                    },
                ],
            },
        )
        assert response.status_code == 201
        scenario_ids.append(response.json()["id"])

    list_response = client.get(f"/api/v1/students/{student_id}/academic-scenarios")
    assert list_response.status_code == 200
    assert set(scenario_ids).issubset({scenario["id"] for scenario in list_response.json()})

    compare = client.post(
        "/api/v1/academic-scenarios/compare",
        json={"scenario_ids": scenario_ids},
    )
    assert compare.status_code == 200
    assert [summary["academic_plan_scenario_id"] for summary in compare.json()] == scenario_ids
