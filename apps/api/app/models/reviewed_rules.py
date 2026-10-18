from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.services.reviewed_rules.contracts import RuleLifecycle

rule_lifecycle_enum = Enum(
    RuleLifecycle,
    name="rule_lifecycle",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)


class ReviewedRuleSetRecord(Base):
    """Durable staged rule payload; consumers are intentionally not attached."""

    __tablename__ = "reviewed_rule_sets"
    __table_args__ = (
        Index(
            "uq_reviewed_rule_sets_identity_version",
            "institution_identifier",
            "program_identifier",
            "catalog_year",
            "version",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    institution_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    program_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    catalog_year: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    lifecycle: Mapped[RuleLifecycle] = mapped_column(rule_lifecycle_enum, nullable=False)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_location: Mapped[str] = mapped_column(String(500), nullable=False)
    source_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    source_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reviewer_confirmed: Mapped[bool] = mapped_column(nullable=False, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
