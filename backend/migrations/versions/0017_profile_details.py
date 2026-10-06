"""Профиль: несколько форматов работы, готовность к переезду, образование, свои навыки

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPTY_LIST = sa.text("'[]'")
EDUCATION = (
    "secondary",
    "vocational",
    "incomplete_higher",
    "bachelor",
    "specialist",
    "master",
    "phd",
)


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def upgrade() -> None:
    table = "candidate_profiles"
    op.add_column(
        table, sa.Column("work_formats", sa.JSON(), server_default=_EMPTY_LIST, nullable=False)
    )
    op.execute(
        "UPDATE candidate_profiles SET work_formats = json_build_array(work_format) "
        "WHERE work_format IS NOT NULL"
    )
    op.drop_column(table, "work_format")
    op.add_column(
        table, sa.Column("relocation", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column(table, sa.Column("education", _enum("education", *EDUCATION), nullable=True))
    op.add_column(
        table, sa.Column("custom_skills", sa.JSON(), server_default=_EMPTY_LIST, nullable=False)
    )


def downgrade() -> None:
    table = "candidate_profiles"
    op.drop_column(table, "custom_skills")
    op.drop_column(table, "education")
    op.drop_column(table, "relocation")
    op.add_column(
        table,
        sa.Column("work_format", _enum("work_format", "office", "hybrid", "remote"), nullable=True),
    )
    op.execute("UPDATE candidate_profiles SET work_format = work_formats->>0")
    op.drop_column(table, "work_formats")
