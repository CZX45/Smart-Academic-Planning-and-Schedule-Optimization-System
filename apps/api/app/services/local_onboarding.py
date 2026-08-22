from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.academic import Campus, Institution, SourceType, StudentProfile

LOCAL_ONBOARDING_SOURCE_REFERENCE = "Local onboarding form"
LOCAL_ONBOARDING_SOURCE_CONFIDENCE = "student-provided-unverified"


@dataclass(frozen=True)
class LocalOnboardingInput:
    display_name: str
    institution_code: str
    institution_name: str
    campus_code: str
    campus_name: str
    country: str
    timezone: str


@dataclass(frozen=True)
class LocalOnboardingResult:
    institution: Institution
    campus: Campus
    student: StudentProfile


class LocalOnboardingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _student_provided_metadata(now: datetime) -> dict[str, object]:
    return {
        "source_type": SourceType.STUDENT_PROVIDED,
        "is_official": False,
        "source_reference": LOCAL_ONBOARDING_SOURCE_REFERENCE,
        "source_retrieved_at": now,
        "source_confidence": LOCAL_ONBOARDING_SOURCE_CONFIDENCE,
    }


def _matching_student_provided_institution(
    institution: Institution,
    request: LocalOnboardingInput,
) -> bool:
    return (
        institution.source_type is SourceType.STUDENT_PROVIDED
        and not institution.is_official
        and institution.source_reference == LOCAL_ONBOARDING_SOURCE_REFERENCE
        and institution.name == request.institution_name
        and institution.country == request.country
        and institution.timezone == request.timezone
    )


def _matching_student_provided_campus(campus: Campus, request: LocalOnboardingInput) -> bool:
    return (
        campus.source_type is SourceType.STUDENT_PROVIDED
        and not campus.is_official
        and campus.source_reference == LOCAL_ONBOARDING_SOURCE_REFERENCE
        and campus.name == request.campus_name
    )


def create_local_student_profile(
    db: Session,
    request: LocalOnboardingInput,
) -> LocalOnboardingResult:
    existing_student_count = db.scalar(
        select(func.count())
        .select_from(StudentProfile)
        .where(StudentProfile.source_type != SourceType.MOCK)
    )
    if existing_student_count:
        raise LocalOnboardingError(
            "student_profile_already_exists",
            "Local onboarding is only available before the first non-demo "
            "student profile is created.",
        )

    now = datetime.now(UTC)
    institution = db.scalar(select(Institution).where(Institution.code == request.institution_code))
    if institution is None:
        institution = Institution(
            code=request.institution_code,
            name=request.institution_name,
            country=request.country,
            timezone=request.timezone,
            **_student_provided_metadata(now),
        )
        db.add(institution)
        db.flush()
    elif not _matching_student_provided_institution(institution, request):
        raise LocalOnboardingError(
            "institution_code_conflict",
            "The institution code already belongs to different or reviewed data "
            "and was not changed.",
        )

    campus = db.scalar(
        select(Campus).where(
            Campus.institution_id == institution.id,
            Campus.code == request.campus_code,
        )
    )
    if campus is None:
        campus = Campus(
            institution_id=institution.id,
            code=request.campus_code,
            name=request.campus_name,
            location=None,
            **_student_provided_metadata(now),
        )
        db.add(campus)
        db.flush()
    elif not _matching_student_provided_campus(campus, request):
        raise LocalOnboardingError(
            "campus_code_conflict",
            "The campus code already belongs to different or reviewed data and was not changed.",
        )

    student = StudentProfile(
        home_institution_id=institution.id,
        home_campus_id=campus.id,
        expected_graduation_term_id=None,
        external_ref=None,
        display_name=request.display_name,
        class_standing=None,
        **_student_provided_metadata(now),
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise LocalOnboardingError(
            "local_onboarding_conflict",
            "Local onboarding conflicted with an existing record; no record was overwritten.",
        ) from error
    db.refresh(institution)
    db.refresh(campus)
    db.refresh(student)
    return LocalOnboardingResult(institution=institution, campus=campus, student=student)
