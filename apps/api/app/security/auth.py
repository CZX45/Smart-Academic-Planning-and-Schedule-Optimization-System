from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.academic import (
    AcademicPlanRun,
    AcademicPlanScenario,
    AuthApiToken,
    AuthTenant,
    AuthUser,
    AuthUserRole,
    DataApplicationRun,
    DataImportReviewSession,
    DataImportRun,
    DegreeAuditRun,
    EligibilityCheckRun,
    ScheduleOptimizationRun,
    SectionMonitorAlert,
    SectionMonitorTarget,
    StudentProfile,
    StudentProfileAccess,
)

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID | None
    tenant_id: UUID | None
    role: AuthUserRole
    external_subject: str
    tenant_institution_id: UUID | None = None

    @property
    def is_system_admin(self) -> bool:
        return self.role is AuthUserRole.SYSTEM_ADMIN

    @property
    def is_tenant_admin(self) -> bool:
        return self.role is AuthUserRole.TENANT_ADMIN


def token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def auth_error(
    code: str,
    message: str,
    *,
    status_code: int = 401,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@dataclass(frozen=True)
class LocalRuntimeContext:
    mode: Literal["LOCAL_DESKTOP"] = "LOCAL_DESKTOP"


RuntimeContext = LocalRuntimeContext | CurrentUser


def get_runtime_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> RuntimeContext:
    if settings.product_mode == "LOCAL_DESKTOP":
        return LocalRuntimeContext()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise auth_error("missing_bearer_token", "Authorization: Bearer token is required.")
    token = credentials.credentials.strip()
    if len(token) < settings.bearer_token_min_length:
        raise auth_error("invalid_bearer_token", "Bearer token is invalid.")
    api_token = db.scalar(select(AuthApiToken).where(AuthApiToken.token_hash == token_hash(token)))
    now = datetime.now(UTC)
    if api_token is None or api_token.revoked_at is not None:
        raise auth_error("invalid_bearer_token", "Bearer token is invalid.")
    if api_token.expires_at is not None and api_token.expires_at <= now:
        raise auth_error("expired_bearer_token", "Bearer token has expired.")
    user = db.get(AuthUser, api_token.user_id)
    if user is None or not user.is_active:
        raise auth_error("inactive_auth_user", "Authenticated user is not active.", status_code=403)
    tenant_institution_id: UUID | None = None
    if user.tenant_id is not None:
        tenant = db.get(AuthTenant, user.tenant_id)
        if tenant is None or not tenant.is_active:
            raise auth_error(
                "inactive_auth_tenant",
                "Authenticated tenant is not active.",
                status_code=403,
            )
        tenant_institution_id = tenant.institution_id
    api_token.last_used_at = now
    db.flush()
    return CurrentUser(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        external_subject=user.external_subject,
        tenant_institution_id=tenant_institution_id,
    )


def not_found(resource: str, resource_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "not_found",
            "message": f"{resource} {resource_id} was not found.",
        },
    )


def forbidden(message: str = "Access to this student resource is not allowed.") -> HTTPException:
    return auth_error("forbidden", message, status_code=403)


def ensure_student_access(
    db: Session,
    current_user: CurrentUser,
    student_profile_id: UUID,
) -> StudentProfile:
    student = db.get(StudentProfile, student_profile_id)
    if student is None:
        raise not_found("StudentProfile", student_profile_id)
    if current_user.is_system_admin:
        return student
    if current_user.is_tenant_admin:
        if current_user.tenant_institution_id == student.home_institution_id:
            return student
        raise not_found("StudentProfile", student_profile_id)
    if current_user.user_id is None:
        raise forbidden()
    grant = db.scalar(
        select(StudentProfileAccess).where(
            StudentProfileAccess.user_id == current_user.user_id,
            StudentProfileAccess.student_profile_id == student_profile_id,
            StudentProfileAccess.revoked_at.is_(None),
        )
    )
    if grant is None:
        raise not_found("StudentProfile", student_profile_id)
    return student


def ensure_object_student_access(
    db: Session,
    current_user: CurrentUser,
    resource_name: str,
    resource_id: UUID,
    student_profile_id: UUID | None,
) -> None:
    if student_profile_id is None:
        raise not_found(resource_name, resource_id)
    ensure_student_access(db, current_user, student_profile_id)


def _parse_uuid(value: Any) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _body_uuid(body: dict[str, Any], key: str) -> UUID | None:
    return _parse_uuid(body.get(key))


async def _request_json(request: Request) -> dict[str, Any]:
    if request.method not in {"POST", "PATCH"}:
        return {}
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _template_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    return str(path)


def _ensure_path_object_access(
    request: Request,
    db: Session,
    current_user: CurrentUser,
) -> None:
    path = _template_path(request)
    params = request.path_params
    if "student_id" in params:
        student_id = _parse_uuid(params["student_id"])
        if student_id is not None:
            ensure_student_access(db, current_user, student_id)
    if "audit_id" in params:
        audit_id = _parse_uuid(params["audit_id"])
        if audit_id is None:
            return
        audit_run = db.get(DegreeAuditRun, audit_id)
        ensure_object_student_access(
            db,
            current_user,
            "DegreeAuditRun",
            audit_id,
            None if audit_run is None else audit_run.student_profile_id,
        )
    if "eligibility_check_id" in params:
        check_id = _parse_uuid(params["eligibility_check_id"])
        if check_id is None:
            return
        eligibility_run = db.get(EligibilityCheckRun, check_id)
        ensure_object_student_access(
            db,
            current_user,
            "EligibilityCheckRun",
            check_id,
            None if eligibility_run is None else eligibility_run.student_profile_id,
        )
    if "plan_id" in params:
        plan_id = _parse_uuid(params["plan_id"])
        if plan_id is None:
            return
        plan_run = db.get(AcademicPlanRun, plan_id)
        ensure_object_student_access(
            db,
            current_user,
            "AcademicPlanRun",
            plan_id,
            None if plan_run is None else plan_run.student_profile_id,
        )
    if "review_id" in params:
        review_id = _parse_uuid(params["review_id"])
        if review_id is None:
            return
        review = db.get(DataImportReviewSession, review_id)
        ensure_object_student_access(
            db,
            current_user,
            "DataImportReviewSession",
            review_id,
            None if review is None else review.student_profile_id,
        )
    if "application_id" in params:
        application_id = _parse_uuid(params["application_id"])
        if application_id is None:
            return
        application = db.get(DataApplicationRun, application_id)
        review = (
            None
            if application is None
            else db.get(DataImportReviewSession, application.review_session_id)
        )
        ensure_object_student_access(
            db,
            current_user,
            "DataApplicationRun",
            application_id,
            None if review is None else review.student_profile_id,
        )
    if "scenario_id" in params:
        scenario_id = _parse_uuid(params["scenario_id"])
        if scenario_id is None:
            return
        scenario = db.get(AcademicPlanScenario, scenario_id)
        ensure_object_student_access(
            db,
            current_user,
            "AcademicPlanScenario",
            scenario_id,
            None if scenario is None else scenario.student_profile_id,
        )
    if "target_id" in params:
        target_id = _parse_uuid(params["target_id"])
        if target_id is None:
            return
        target = db.get(SectionMonitorTarget, target_id)
        ensure_object_student_access(
            db,
            current_user,
            "SectionMonitorTarget",
            target_id,
            None if target is None else target.student_profile_id,
        )
    if "alert_id" in params:
        alert_id = _parse_uuid(params["alert_id"])
        if alert_id is None:
            return
        alert = db.get(SectionMonitorAlert, alert_id)
        target = None if alert is None else db.get(SectionMonitorTarget, alert.target_id)
        ensure_object_student_access(
            db,
            current_user,
            "SectionMonitorAlert",
            alert_id,
            None if target is None else target.student_profile_id,
        )
    if "run_id" in params:
        run_id = _parse_uuid(params["run_id"])
        if run_id is None:
            return
        if path.startswith("/api/v1/schedule-optimizations/"):
            schedule_run = db.get(ScheduleOptimizationRun, run_id)
            ensure_object_student_access(
                db,
                current_user,
                "ScheduleOptimizationRun",
                run_id,
                None if schedule_run is None else schedule_run.student_profile_id,
            )
        elif path.startswith("/api/v1/data-imports/"):
            import_run = db.get(DataImportRun, run_id)
            ensure_object_student_access(
                db,
                current_user,
                "DataImportRun",
                run_id,
                None if import_run is None else import_run.student_profile_id,
            )


def _ensure_body_object_access(
    body: dict[str, Any],
    db: Session,
    current_user: CurrentUser,
) -> None:
    student_profile_id = _body_uuid(body, "student_profile_id")
    if student_profile_id is not None:
        ensure_student_access(db, current_user, student_profile_id)
    data_import_run_id = _body_uuid(body, "data_import_run_id")
    if data_import_run_id is not None:
        run = db.get(DataImportRun, data_import_run_id)
        ensure_object_student_access(
            db,
            current_user,
            "DataImportRun",
            data_import_run_id,
            None if run is None else run.student_profile_id,
        )
    _ensure_academic_plan_list_access(body, db, current_user)
    _ensure_schedule_run_list_access(body, db, current_user)
    _ensure_scenario_list_access(body, db, current_user)


def _body_uuid_list(body: dict[str, Any], key: str) -> list[UUID]:
    values = body.get(key)
    if not isinstance(values, list):
        return []
    parsed: list[UUID] = []
    for raw_value in values:
        parsed_value = _parse_uuid(raw_value)
        if parsed_value is not None:
            parsed.append(parsed_value)
    return parsed


def _ensure_academic_plan_list_access(
    body: dict[str, Any],
    db: Session,
    current_user: CurrentUser,
) -> None:
    for plan_id in _body_uuid_list(body, "academic_plan_ids"):
        plan = db.get(AcademicPlanRun, plan_id)
        ensure_object_student_access(
            db,
            current_user,
            "AcademicPlanRun",
            plan_id,
            None if plan is None else plan.student_profile_id,
        )


def _ensure_schedule_run_list_access(
    body: dict[str, Any],
    db: Session,
    current_user: CurrentUser,
) -> None:
    for run_id in _body_uuid_list(body, "schedule_optimization_run_ids"):
        run = db.get(ScheduleOptimizationRun, run_id)
        ensure_object_student_access(
            db,
            current_user,
            "ScheduleOptimizationRun",
            run_id,
            None if run is None else run.student_profile_id,
        )


def _ensure_scenario_list_access(
    body: dict[str, Any],
    db: Session,
    current_user: CurrentUser,
) -> None:
    for scenario_id in _body_uuid_list(body, "scenario_ids"):
        scenario = db.get(AcademicPlanScenario, scenario_id)
        ensure_object_student_access(
            db,
            current_user,
            "AcademicPlanScenario",
            scenario_id,
            None if scenario is None else scenario.student_profile_id,
        )


async def enforce_api_authorization(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    runtime_context: Annotated[RuntimeContext, Depends(get_runtime_context)],
) -> None:
    if isinstance(runtime_context, LocalRuntimeContext):
        return
    current_user = runtime_context
    _ensure_path_object_access(request, db, current_user)
    _ensure_body_object_access(await _request_json(request), db, current_user)
    query_student = request.query_params.get("student_profile_id")
    if query_student:
        query_student_id = _parse_uuid(query_student)
        if query_student_id is not None:
            ensure_student_access(db, current_user, query_student_id)
