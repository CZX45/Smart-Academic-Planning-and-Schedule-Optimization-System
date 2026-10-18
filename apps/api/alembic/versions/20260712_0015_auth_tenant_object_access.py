"""add auth tenants users tokens and student access grants

Revision ID: 20260712_0015
Revises: 20260711_0014
Create Date: 2026-07-12
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260712_0015"
down_revision: str | None = "20260711_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_USER_ROLES = ("STUDENT", "ADVISOR", "TENANT_ADMIN", "SYSTEM_ADMIN")


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


def uuid_column(name: str, *, nullable: bool = False) -> sa.Column[Any]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "auth_tenants",
        uuid_column("id"),
        uuid_column("institution_id", nullable=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("length(slug) > 0", name="ck_auth_tenants_slug_not_empty"),
        sa.CheckConstraint("length(display_name) > 0", name="ck_auth_tenants_name_not_empty"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_auth_tenants_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_auth_tenants_slug", "auth_tenants", ["slug"], unique=True)
    op.create_index("ix_auth_tenants_institution", "auth_tenants", ["institution_id"])

    op.create_table(
        "auth_users",
        uuid_column("id"),
        uuid_column("tenant_id", nullable=True),
        sa.Column("external_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", enum(AUTH_USER_ROLES, "auth_user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "length(external_subject) > 0",
            name="ck_auth_users_subject_not_empty",
        ),
        sa.CheckConstraint(
            "email IS NULL OR length(email) > 0",
            name="ck_auth_users_email_not_empty",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["auth_tenants.id"],
            name="fk_auth_users_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_auth_users_tenant_subject",
        "auth_users",
        ["tenant_id", "external_subject"],
        unique=True,
    )
    op.create_index("ix_auth_users_tenant_role", "auth_users", ["tenant_id", "role"])

    op.create_table(
        "auth_api_tokens",
        uuid_column("id"),
        uuid_column("user_id"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("length(token_hash) = 64", name="ck_auth_api_tokens_hash_length"),
        sa.CheckConstraint("length(label) > 0", name="ck_auth_api_tokens_label_not_empty"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_auth_api_tokens_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_auth_api_tokens_hash", "auth_api_tokens", ["token_hash"], unique=True)
    op.create_index("ix_auth_api_tokens_user", "auth_api_tokens", ["user_id"])

    op.create_table(
        "student_profile_access_grants",
        uuid_column("id"),
        uuid_column("user_id"),
        uuid_column("student_profile_id"),
        sa.Column("role", enum(AUTH_USER_ROLES, "auth_user_role"), nullable=False),
        sa.Column("grant_reason", sa.String(length=255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "length(grant_reason) > 0",
            name="ck_student_profile_access_reason",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_student_profile_access_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_profile_access_student",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_student_profile_access_user_student",
        "student_profile_access_grants",
        ["user_id", "student_profile_id"],
        unique=True,
    )
    op.create_index(
        "ix_student_profile_access_student",
        "student_profile_access_grants",
        ["student_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_profile_access_student", table_name="student_profile_access_grants")
    op.drop_index(
        "uq_student_profile_access_user_student",
        table_name="student_profile_access_grants",
    )
    op.drop_table("student_profile_access_grants")
    op.drop_index("ix_auth_api_tokens_user", table_name="auth_api_tokens")
    op.drop_index("uq_auth_api_tokens_hash", table_name="auth_api_tokens")
    op.drop_table("auth_api_tokens")
    op.drop_index("ix_auth_users_tenant_role", table_name="auth_users")
    op.drop_index("uq_auth_users_tenant_subject", table_name="auth_users")
    op.drop_table("auth_users")
    op.drop_index("ix_auth_tenants_institution", table_name="auth_tenants")
    op.drop_index("uq_auth_tenants_slug", table_name="auth_tenants")
    op.drop_table("auth_tenants")
