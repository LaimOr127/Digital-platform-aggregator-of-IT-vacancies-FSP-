"""Категории «специализация x грейд»: опрос, тестирование, подтверждённый грейд кандидата

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import disable, enable, profile_child

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SPECIALIZATIONS = ("backend", "frontend", "mobile", "data", "devops", "qa", "security")
GRADES = ("intern", "junior", "middle", "senior", "lead")
_EMPTY_LIST = sa.text("'[]'")
_TABLES = ("assessments",)
# попытки и ответы видит только сам кандидат: работодатель видит итог в профиле
_POLICIES = profile_child("assessments", readable_by_viewers=False)


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def _profile_columns() -> list[sa.Column]:
    return [
        sa.Column("specialization", _enum("specialization", *SPECIALIZATIONS), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("industries", sa.JSON(), server_default=_EMPTY_LIST, nullable=False),
        sa.Column("roles", sa.JSON(), server_default=_EMPTY_LIST, nullable=False),
        sa.Column("soft_skills", sa.JSON(), server_default=_EMPTY_LIST, nullable=False),
        sa.Column("survey_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_grade", _enum("confirmed_grade", *GRADES), nullable=True),
        sa.Column("grade_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assessment_score", sa.Integer(), nullable=True),
        sa.Column("confirmed_skills", sa.JSON(), server_default=_EMPTY_LIST, nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    for column in _profile_columns():
        op.add_column("candidate_profiles", column)
    for column in ("specialization", "confirmed_grade"):
        op.create_index(
            op.f(f"ix_candidate_profiles_{column}"), "candidate_profiles", [column], unique=False
        )
    op.add_column(
        "vacancies",
        sa.Column("specialization", _enum("specialization", *SPECIALIZATIONS), nullable=True),
    )
    op.create_index(op.f("ix_vacancies_specialization"), "vacancies", ["specialization"])
    _create_assessments()
    enable(_TABLES, _POLICIES)


def _create_assessments() -> None:
    now = sa.text("now()")
    op.create_table(
        "assessments",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("specialization", _enum("specialization", *SPECIALIZATIONS), nullable=False),
        sa.Column("grade", _enum("grade", *GRADES), nullable=False),
        sa.Column(
            "status",
            _enum("assessment_status", "in_progress", "completed", "expired"),
            nullable=False,
        ),
        sa.Column("seed", sa.String(length=32), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("responses", sa.JSON(), nullable=True),
        sa.Column("survey", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", _enum("assessment_result", "passed", "failed"), nullable=True),
        sa.Column("theta", sa.Float(), nullable=True),
        sa.Column("theta_error", sa.Float(), nullable=True),
        sa.Column("correct", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("confident", sa.Boolean(), nullable=False),
        sa.Column("topics", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_assessments_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
    )
    for column in ("profile_id", "created_at"):
        op.create_index(op.f(f"ix_assessments_{column}"), "assessments", [column], unique=False)


def downgrade() -> None:
    disable(_TABLES, _POLICIES)
    op.drop_table("assessments")
    op.drop_index(op.f("ix_vacancies_specialization"), table_name="vacancies")
    op.drop_column("vacancies", "specialization")
    for column in ("specialization", "confirmed_grade"):
        op.drop_index(op.f(f"ix_candidate_profiles_{column}"), table_name="candidate_profiles")
    for column in reversed(_profile_columns()):
        op.drop_column("candidate_profiles", column.name)
