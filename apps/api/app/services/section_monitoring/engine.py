from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AuditWarningSeverity,
    DataImportRun,
    SectionMonitorAlert,
    SectionMonitorAlertType,
    SectionMonitorSnapshot,
    SectionMonitorTarget,
    SourceType,
    StudentProfile,
)
from app.services.section_monitoring.exceptions import SectionMonitoringValidationError

SECTION_MONITORING_DISCLAIMERS = [
    (
        "Section monitoring is based on user-triggered imported data, is not official, and may "
        "differ from the official portal. Always verify information manually in the "
        "official registration portal."
    ),
    (
        "This system does not register, drop, swap, waitlist, submit forms, or perform any "
        "portal action."
    ),
]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnapshotCompareResult:
    snapshots: list[SectionMonitorSnapshot]
    alerts: list[SectionMonitorAlert]
    disclaimers: list[str]


@dataclass(frozen=True)
class AlertSpec:
    alert_type: SectionMonitorAlertType
    severity: AuditWarningSeverity
    field_name: str
    previous_value: str | None
    current_value: str | None


class SectionMonitoringApplicationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_target(
        self,
        *,
        student_profile_id: UUID,
        course_code: str,
        section_code: str,
        term: str,
        title: str | None = None,
        instructor: str | None = None,
        status: str | None = None,
        source_type: SourceType = SourceType.STUDENT_PROVIDED,
    ) -> SectionMonitorTarget:
        self._require_student(student_profile_id)
        if source_type is SourceType.OFFICIAL:
            raise SectionMonitoringValidationError(
                "official_source_not_allowed",
                "Section monitoring targets are advisory and cannot use official source type.",
            )
        normalized_course_code = normalize_code(course_code)
        normalized_section_code = normalize_code(section_code)
        normalized_term = normalize_code(term)
        existing = self.db.scalar(
            select(SectionMonitorTarget).where(
                SectionMonitorTarget.student_profile_id == student_profile_id,
                SectionMonitorTarget.course_code == normalized_course_code,
                SectionMonitorTarget.section_code == normalized_section_code,
                SectionMonitorTarget.term == normalized_term,
            )
        )
        if existing is not None:
            raise SectionMonitoringValidationError(
                "duplicate_target",
                (
                    "A section monitor target already exists for this student, course, "
                    "section, and term."
                ),
            )
        target = SectionMonitorTarget(
            student_profile_id=student_profile_id,
            course_code=normalized_course_code,
            section_code=normalized_section_code,
            term=normalized_term,
            title=clean_optional(title),
            instructor=clean_optional(instructor),
            status=normalize_optional(status),
            is_active=True,
            is_advisory=True,
            source_type=source_type,
            is_official=False,
            source_confidence=source_type.value.lower(),
        )
        self.db.add(target)
        self.db.flush()
        return target

    def list_targets(self, student_profile_id: UUID) -> list[SectionMonitorTarget]:
        self._require_student(student_profile_id)
        return list(
            self.db.scalars(
                select(SectionMonitorTarget)
                .where(SectionMonitorTarget.student_profile_id == student_profile_id)
                .order_by(
                    SectionMonitorTarget.course_code,
                    SectionMonitorTarget.section_code,
                    SectionMonitorTarget.term,
                )
            ).all()
        )

    def update_target(
        self,
        target_id: UUID,
        *,
        is_active: bool | None = None,
        title: str | None = None,
        instructor: str | None = None,
        status: str | None = None,
    ) -> SectionMonitorTarget:
        target = self.db.get(SectionMonitorTarget, target_id)
        if target is None:
            raise SectionMonitoringValidationError(
                "not_found",
                f"Section monitor target {target_id} was not found.",
            )
        if is_active is not None:
            target.is_active = is_active
        if title is not None:
            target.title = clean_optional(title)
        if instructor is not None:
            target.instructor = clean_optional(instructor)
        if status is not None:
            target.status = normalize_optional(status)
        self.db.flush()
        return target

    def compare_snapshots(
        self,
        *,
        student_profile_id: UUID,
        snapshots: Sequence[Mapping[str, object]],
        source_type: SourceType,
    ) -> SnapshotCompareResult:
        self._require_student(student_profile_id)
        if source_type is SourceType.OFFICIAL:
            raise SectionMonitoringValidationError(
                "official_source_not_allowed",
                "Section monitoring snapshots must be imported non-official data.",
            )
        stored_snapshots: list[SectionMonitorSnapshot] = []
        alerts: list[SectionMonitorAlert] = []
        for payload in snapshots:
            stored_snapshot, created = self._store_snapshot(
                student_profile_id=student_profile_id,
                payload=payload,
                source_type=source_type,
            )
            stored_snapshots.append(stored_snapshot)
            if not created:
                continue
            previous = self._previous_snapshot(stored_snapshot)
            if previous is None or stored_snapshot.target_id is None:
                continue
            alerts.extend(self._create_alerts(previous, stored_snapshot))
        logger.info(
            "section_monitoring.snapshots_compared",
            extra={
                "student_profile_id": str(student_profile_id),
                "source_type": source_type.value,
                "snapshot_count": len(stored_snapshots),
                "alert_count": len(alerts),
            },
        )
        return SnapshotCompareResult(
            snapshots=stored_snapshots,
            alerts=alerts,
            disclaimers=list(SECTION_MONITORING_DISCLAIMERS),
        )

    def list_alerts(self, student_profile_id: UUID) -> list[SectionMonitorAlert]:
        self._require_student(student_profile_id)
        return list(
            self.db.scalars(
                select(SectionMonitorAlert)
                .join(
                    SectionMonitorTarget,
                    SectionMonitorAlert.target_id == SectionMonitorTarget.id,
                )
                .where(SectionMonitorTarget.student_profile_id == student_profile_id)
                .order_by(SectionMonitorAlert.created_at.desc(), SectionMonitorAlert.id.desc())
            ).all()
        )

    def acknowledge_alert(
        self,
        alert_id: UUID,
        *,
        is_acknowledged: bool,
    ) -> SectionMonitorAlert:
        alert = self.db.get(SectionMonitorAlert, alert_id)
        if alert is None:
            raise SectionMonitoringValidationError(
                "not_found",
                f"Section monitor alert {alert_id} was not found.",
            )
        alert.is_acknowledged = is_acknowledged
        alert.acknowledged_at = datetime.now(UTC) if is_acknowledged else None
        self.db.flush()
        return alert

    def _store_snapshot(
        self,
        *,
        student_profile_id: UUID,
        payload: Mapping[str, object],
        source_type: SourceType,
    ) -> tuple[SectionMonitorSnapshot, bool]:
        course_code = normalize_code(required_string(payload, "course_code"))
        section_code = normalize_code(required_string(payload, "section_code"))
        term = normalize_code(required_string(payload, "term"))
        raw_payload = raw_payload_from(payload)
        normalized = {
            "course_code": course_code,
            "section_code": section_code,
            "term": term,
            "status": normalize_optional(value_string(payload.get("status"))),
            "seats_available": int_value(payload.get("seats_available")),
            "seats_capacity": int_value(payload.get("seats_capacity")),
            "waitlist_available": int_value(payload.get("waitlist_available")),
            "waitlist_capacity": int_value(payload.get("waitlist_capacity")),
            "meeting_days": normalize_optional(value_string(payload.get("meeting_days"))),
            "meeting_time": clean_optional(value_string(payload.get("meeting_time"))),
            "location": clean_optional(value_string(payload.get("location"))),
            "instructor": clean_optional(
                value_string(payload.get("instructor"))
                or value_string(payload.get("instructor_display"))
            ),
            "raw_payload": raw_payload,
        }
        snapshot_hash = snapshot_hash_for(normalized)
        existing = self.db.scalar(
            select(SectionMonitorSnapshot).where(
                SectionMonitorSnapshot.student_profile_id == student_profile_id,
                SectionMonitorSnapshot.course_code == course_code,
                SectionMonitorSnapshot.section_code == section_code,
                SectionMonitorSnapshot.term == term,
                SectionMonitorSnapshot.snapshot_hash == snapshot_hash,
            )
        )
        if existing is not None:
            return existing, False

        target = self._resolve_target(
            student_profile_id=student_profile_id,
            payload=payload,
            course_code=course_code,
            section_code=section_code,
            term=term,
            source_type=source_type,
        )
        data_import_id = uuid_value(payload.get("data_import_id"))
        if data_import_id is not None:
            self._validate_data_import(data_import_id, student_profile_id)

        snapshot = SectionMonitorSnapshot(
            student_profile_id=student_profile_id,
            target_id=target.id if target is not None else None,
            data_import_id=data_import_id,
            course_code=course_code,
            section_code=section_code,
            term=term,
            status=cast(str | None, normalized["status"]),
            seats_available=cast(int | None, normalized["seats_available"]),
            seats_capacity=cast(int | None, normalized["seats_capacity"]),
            waitlist_available=cast(int | None, normalized["waitlist_available"]),
            waitlist_capacity=cast(int | None, normalized["waitlist_capacity"]),
            meeting_days=cast(str | None, normalized["meeting_days"]),
            meeting_time=cast(str | None, normalized["meeting_time"]),
            location=cast(str | None, normalized["location"]),
            instructor=cast(str | None, normalized["instructor"]),
            raw_payload=raw_payload,
            snapshot_hash=snapshot_hash,
            source_type=source_type,
            is_official=False,
            source_reference=clean_optional(value_string(payload.get("source_reference"))),
            source_confidence=source_type.value.lower(),
            created_at=datetime.now(UTC),
        )
        self.db.add(snapshot)
        self.db.flush()
        if target is not None:
            if snapshot.status is not None:
                target.status = snapshot.status
            if snapshot.instructor is not None:
                target.instructor = snapshot.instructor
        return snapshot, True

    def _resolve_target(
        self,
        *,
        student_profile_id: UUID,
        payload: Mapping[str, object],
        course_code: str,
        section_code: str,
        term: str,
        source_type: SourceType,
    ) -> SectionMonitorTarget:
        target_id = uuid_value(payload.get("target_id"))
        if target_id is not None:
            target = self.db.get(SectionMonitorTarget, target_id)
            if target is None or target.student_profile_id != student_profile_id:
                raise SectionMonitoringValidationError(
                    "not_found",
                    f"Section monitor target {target_id} was not found.",
                )
            return target
        target = self.db.scalar(
            select(SectionMonitorTarget).where(
                SectionMonitorTarget.student_profile_id == student_profile_id,
                SectionMonitorTarget.course_code == course_code,
                SectionMonitorTarget.section_code == section_code,
                SectionMonitorTarget.term == term,
            )
        )
        if target is not None:
            return target
        return self.create_target(
            student_profile_id=student_profile_id,
            course_code=course_code,
            section_code=section_code,
            term=term,
            title=clean_optional(value_string(payload.get("title"))),
            instructor=clean_optional(
                value_string(payload.get("instructor"))
                or value_string(payload.get("instructor_display"))
            ),
            status=normalize_optional(value_string(payload.get("status"))),
            source_type=source_type,
        )

    def _previous_snapshot(
        self,
        snapshot: SectionMonitorSnapshot,
    ) -> SectionMonitorSnapshot | None:
        return self.db.scalar(
            select(SectionMonitorSnapshot)
            .where(
                SectionMonitorSnapshot.student_profile_id == snapshot.student_profile_id,
                SectionMonitorSnapshot.course_code == snapshot.course_code,
                SectionMonitorSnapshot.section_code == snapshot.section_code,
                SectionMonitorSnapshot.term == snapshot.term,
                SectionMonitorSnapshot.id != snapshot.id,
            )
            .order_by(SectionMonitorSnapshot.created_at.desc(), SectionMonitorSnapshot.id.desc())
            .limit(1)
        )

    def _create_alerts(
        self,
        previous: SectionMonitorSnapshot,
        current: SectionMonitorSnapshot,
    ) -> list[SectionMonitorAlert]:
        specs = alert_specs(previous, current)
        alerts: list[SectionMonitorAlert] = []
        for spec in specs:
            existing = self.db.scalar(
                select(SectionMonitorAlert).where(
                    SectionMonitorAlert.previous_snapshot_id == previous.id,
                    SectionMonitorAlert.current_snapshot_id == current.id,
                    SectionMonitorAlert.alert_type == spec.alert_type,
                    SectionMonitorAlert.field_name == spec.field_name,
                )
            )
            if existing is not None:
                continue
            alert = SectionMonitorAlert(
                target_id=cast(UUID, current.target_id),
                previous_snapshot_id=previous.id,
                current_snapshot_id=current.id,
                alert_type=spec.alert_type,
                severity=spec.severity,
                field_name=spec.field_name,
                previous_value=spec.previous_value,
                current_value=spec.current_value,
                message=alert_message(current, spec),
                is_acknowledged=False,
                is_advisory=True,
                requires_manual_review=True,
            )
            self.db.add(alert)
            alerts.append(alert)
        self.db.flush()
        return alerts

    def _require_student(self, student_profile_id: UUID) -> None:
        if self.db.get(StudentProfile, student_profile_id) is None:
            raise SectionMonitoringValidationError(
                "not_found",
                f"StudentProfile {student_profile_id} was not found.",
            )

    def _validate_data_import(self, data_import_id: UUID, student_profile_id: UUID) -> None:
        data_import = self.db.get(DataImportRun, data_import_id)
        if data_import is None or data_import.student_profile_id != student_profile_id:
            raise SectionMonitoringValidationError(
                "not_found",
                f"DataImportRun {data_import_id} was not found.",
            )
        if data_import.is_official or data_import.source_type is SourceType.OFFICIAL:
            raise SectionMonitoringValidationError(
                "official_source_not_allowed",
                "Section monitoring can only compare non-official imported data.",
            )


def alert_specs(
    previous: SectionMonitorSnapshot,
    current: SectionMonitorSnapshot,
) -> list[AlertSpec]:
    specs: list[AlertSpec] = []
    previous_status = normalize_optional(previous.status)
    current_status = normalize_optional(current.status)
    if previous_status != current_status:
        if previous_status == "CLOSED" and current_status == "OPEN":
            specs.append(
                AlertSpec(
                    SectionMonitorAlertType.SECTION_OPENED,
                    AuditWarningSeverity.INFO,
                    "status",
                    previous_status,
                    current_status,
                )
            )
        elif previous_status == "OPEN" and current_status == "CLOSED":
            specs.append(
                AlertSpec(
                    SectionMonitorAlertType.SECTION_CLOSED,
                    AuditWarningSeverity.WARNING,
                    "status",
                    previous_status,
                    current_status,
                )
            )
        else:
            specs.append(
                AlertSpec(
                    SectionMonitorAlertType.STATUS_CHANGED,
                    AuditWarningSeverity.INFO,
                    "status",
                    previous_status,
                    current_status,
                )
            )
    specs.extend(
        compare_field(
            previous.seats_available,
            current.seats_available,
            SectionMonitorAlertType.SEATS_CHANGED,
            "seats_available",
            AuditWarningSeverity.INFO,
        )
    )
    specs.extend(
        compare_field(
            previous.waitlist_available,
            current.waitlist_available,
            SectionMonitorAlertType.WAITLIST_CHANGED,
            "waitlist_available",
            AuditWarningSeverity.INFO,
        )
    )
    specs.extend(
        compare_field(
            previous.meeting_time,
            current.meeting_time,
            SectionMonitorAlertType.MEETING_TIME_CHANGED,
            "meeting_time",
            AuditWarningSeverity.WARNING,
        )
    )
    specs.extend(
        compare_field(
            previous.instructor,
            current.instructor,
            SectionMonitorAlertType.INSTRUCTOR_CHANGED,
            "instructor",
            AuditWarningSeverity.WARNING,
        )
    )
    specs.extend(
        compare_field(
            previous.location,
            current.location,
            SectionMonitorAlertType.LOCATION_CHANGED,
            "location",
            AuditWarningSeverity.WARNING,
        )
    )
    if not specs and previous.raw_payload != current.raw_payload:
        specs.append(
            AlertSpec(
                SectionMonitorAlertType.UNKNOWN_CHANGE,
                AuditWarningSeverity.INFO,
                "raw_payload",
                "changed",
                "changed",
            )
        )
    return specs


def compare_field(
    previous: object,
    current: object,
    alert_type: SectionMonitorAlertType,
    field_name: str,
    severity: AuditWarningSeverity,
) -> list[AlertSpec]:
    previous_value = normalized_compare_value(previous)
    current_value = normalized_compare_value(current)
    if previous_value == current_value:
        return []
    if previous_value is None and current_value is None:
        return []
    return [AlertSpec(alert_type, severity, field_name, previous_value, current_value)]


def alert_message(snapshot: SectionMonitorSnapshot, spec: AlertSpec) -> str:
    label = f"{snapshot.course_code} {snapshot.section_code}"
    previous_value = spec.previous_value if spec.previous_value is not None else "unknown"
    current_value = spec.current_value if spec.current_value is not None else "unknown"
    return (
        f"{label} {spec.field_name.replace('_', ' ')} changed from "
        f"{previous_value} to {current_value} in imported "
        "section-search data. Manually verify in the official portal; this advisory system "
        "does not take portal actions."
    )


def snapshot_hash_for(normalized: Mapping[str, object]) -> str:
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def raw_payload_from(payload: Mapping[str, object]) -> dict[str, object]:
    raw_payload = payload.get("raw_payload")
    if isinstance(raw_payload, dict):
        return cast(dict[str, object], raw_payload)
    return dict(payload)


def required_string(payload: Mapping[str, object], key: str) -> str:
    value = value_string(payload.get(key))
    if value is None:
        raise SectionMonitoringValidationError(
            "invalid_snapshot",
            f"Section monitoring snapshot requires {key}.",
        )
    return value


def value_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text if text else None


def normalize_optional(value: str | None) -> str | None:
    cleaned = clean_optional(value)
    if cleaned is None:
        return None
    return normalize_code(cleaned)


def normalize_code(value: str) -> str:
    return " ".join(value.strip().upper().split())


def int_value(value: object) -> int | None:
    text = value_string(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError as error:
        raise SectionMonitoringValidationError(
            "invalid_snapshot",
            f"Expected integer section monitoring value, got {text}.",
        ) from error


def uuid_value(value: object) -> UUID | None:
    text = value_string(value)
    if text is None:
        return None
    try:
        return UUID(text)
    except ValueError as error:
        raise SectionMonitoringValidationError(
            "invalid_snapshot",
            f"Expected UUID section monitoring value, got {text}.",
        ) from error


def normalized_compare_value(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
