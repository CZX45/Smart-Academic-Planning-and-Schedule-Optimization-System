from __future__ import annotations

import re
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.academic import (
    campus_response,
    institution_response,
    student_profile_response,
)
from app.config import settings
from app.db.session import get_db
from app.models.academic import Campus, Institution, SourceType, StudentProfile
from app.schemas.academic import CampusResponse, InstitutionResponse, StudentProfileResponse
from app.services.local_onboarding import (
    LocalOnboardingError,
    LocalOnboardingInput,
    LocalOnboardingResult,
    create_local_student_profile,
)

router = APIRouter(prefix="/api/v1/local-onboarding", tags=["local-onboarding"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]*$")
ADVISOR_WARNING = (
    "This profile and its school details are student-provided and unverified. "
    "Confirm high-impact academic decisions with the school or an advisor."
)
UNVERIFIED_ASSUMPTION = (
    "Institution and campus details were entered by the local user and were not verified."
)
EXISTING_PROFILE_ASSUMPTION = (
    "Profile provenance is reported from stored source metadata; no official status was inferred."
)


class LocalOnboardingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledge_non_official: Literal[True]
    display_name: str = Field(min_length=1, max_length=120)
    institution_code: str = Field(min_length=1, max_length=32)
    institution_name: str = Field(min_length=1, max_length=255)
    campus_code: str = Field(min_length=1, max_length=32)
    campus_name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=2, max_length=2)
    timezone: str = Field(min_length=1, max_length=80)

    @field_validator("display_name", "institution_name", "campus_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(ord(character) < 32 for character in normalized):
            raise ValueError("Names must contain visible text without control characters.")
        return normalized

    @field_validator("institution_code", "campus_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not CODE_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Codes may contain only letters, numbers, period, underscore, and dash."
            )
        return normalized

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError("Country must be a two-letter code.")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        normalized = value.strip()
        try:
            ZoneInfo(normalized)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Timezone must be a valid IANA timezone name.") from error
        return normalized


class LocalStudentProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: InstitutionResponse
    campus: CampusResponse
    student: StudentProfileResponse
    reason_codes: list[str]
    warnings: list[str]
    assumptions: list[str]
    source_references: list[str]


def _ensure_local_desktop() -> None:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "local_onboarding_unavailable",
                "message": "Local onboarding is unavailable in SERVER mode.",
            },
        )


def _response(
    db: Session,
    result: LocalOnboardingResult,
    *,
    reason_code: str,
    assumptions: list[str],
) -> LocalStudentProfileResponse:
    source_references = sorted(
        {
            reference
            for reference in (
                result.institution.source_reference,
                result.campus.source_reference,
                result.student.source_reference,
            )
            if reference
        }
    )
    return LocalStudentProfileResponse(
        institution=institution_response(result.institution),
        campus=campus_response(result.campus),
        student=student_profile_response(result.student, db),
        reason_codes=[reason_code],
        warnings=[ADVISOR_WARNING],
        assumptions=assumptions,
        source_references=source_references,
    )


@router.get("/student-profiles", response_model=list[LocalStudentProfileResponse])
def list_local_student_profiles(db: DatabaseSession) -> list[LocalStudentProfileResponse]:
    _ensure_local_desktop()
    students = db.scalars(
        select(StudentProfile)
        .where(StudentProfile.source_type != SourceType.MOCK)
        .order_by(StudentProfile.created_at, StudentProfile.id)
    ).all()
    responses: list[LocalStudentProfileResponse] = []
    for student in students:
        institution = db.get(Institution, student.home_institution_id)
        campus = db.get(Campus, student.home_campus_id)
        if institution is None or campus is None:
            continue
        responses.append(
            _response(
                db,
                LocalOnboardingResult(
                    institution=institution,
                    campus=campus,
                    student=student,
                ),
                reason_code="EXISTING_LOCAL_PROFILE",
                assumptions=[EXISTING_PROFILE_ASSUMPTION],
            )
        )
    return responses


@router.post(
    "/student-profiles",
    response_model=LocalStudentProfileResponse,
    status_code=201,
)
def create_local_student_profile_endpoint(
    request: LocalOnboardingRequest,
    db: DatabaseSession,
) -> LocalStudentProfileResponse:
    _ensure_local_desktop()
    try:
        result = create_local_student_profile(
            db,
            LocalOnboardingInput(
                display_name=request.display_name,
                institution_code=request.institution_code,
                institution_name=request.institution_name,
                campus_code=request.campus_code,
                campus_name=request.campus_name,
                country=request.country,
                timezone=request.timezone,
            ),
        )
    except LocalOnboardingError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message},
        ) from error
    return _response(
        db,
        result,
        reason_code="STUDENT_PROVIDED_PROFILE_CREATED",
        assumptions=[UNVERIFIED_ASSUMPTION],
    )
