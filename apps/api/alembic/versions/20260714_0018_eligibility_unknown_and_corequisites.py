"""allow advisory UNKNOWN eligibility results and persist reviewed corequisites

Revision ID: 20260714_0018
Revises: 20260714_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_0018"
down_revision: str | None = "20260714_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESULTS_WITH_UNKNOWN = (
    "ELIGIBLE",
    "CONDITIONALLY_ELIGIBLE",
    "NOT_ELIGIBLE",
    "PERMISSION_REQUIRED",
    "MANUAL_REVIEW_REQUIRED",
    "UNKNOWN",
)
RESULTS_WITHOUT_UNKNOWN = RESULTS_WITH_UNKNOWN[:-1]


def _replace_constraints(table_name: str, values: tuple[str, ...]) -> None:
    bind = op.get_bind()
    constraints = (
        ("eligibility_overall_result", "overall_result"),
        ("eligibility_academic_result", "academic_eligibility_result"),
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            for name, column in constraints:
                batch_op.drop_constraint(name, type_="check")
                batch_op.create_check_constraint(
                    name,
                    f"{column} IN ({', '.join(repr(value) for value in values)})",
                )
        return
    for name, column in constraints:
        op.drop_constraint(name, table_name=table_name, type_="check")
        op.create_check_constraint(
            name,
            table_name,
            f"{column} IN ({', '.join(repr(value) for value in values)})",
        )


def upgrade() -> None:
    _replace_constraints("eligibility_check_runs", RESULTS_WITH_UNKNOWN)
    op.add_column(
        "eligibility_check_runs",
        sa.Column("reviewed_corequisite_summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    unknown_count = bind.execute(
        sa.text(
            "select count(*) from eligibility_check_runs "
            "where overall_result = 'UNKNOWN' or academic_eligibility_result = 'UNKNOWN'"
        )
    ).scalar_one()
    if unknown_count:
        raise RuntimeError(
            "Cannot downgrade eligibility result constraints while UNKNOWN records exist; "
            "review or migrate those advisory records first."
        )
    op.drop_column("eligibility_check_runs", "reviewed_corequisite_summary")
    _replace_constraints("eligibility_check_runs", RESULTS_WITHOUT_UNKNOWN)
