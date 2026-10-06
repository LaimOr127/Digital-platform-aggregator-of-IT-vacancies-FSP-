"""Регулярные короткие задания от компаний и ответы кандидатов

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import ROLE, UID, disable, enable, member_of, policy

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SPECIALIZATIONS = ("backend", "frontend", "mobile", "data", "devops", "qa", "security")
GRADES = ("intern", "junior", "middle", "senior", "lead")
_OWN_PROFILE = (
    "EXISTS (SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id "
    f"AND p.user_id::text = {UID})"
)
_TABLES = ("employer_tasks", "task_answers")
_POLICIES = [
    # активные задачи читает любой кандидат (их предлагает система), меняет только компания
    policy(
        "employer_tasks_read",
        "employer_tasks",
        "SELECT",
        f"({member_of('company_id')} OR ({ROLE} = 'candidate' AND is_active))",
        check=False,
    ),
    policy("employer_tasks_write", "employer_tasks", "ALL", member_of("company_id")),
    # ответ видят его автор и компания-автор задачи
    policy(
        "task_answers_party",
        "task_answers",
        "ALL",
        f"({_OWN_PROFILE} OR {member_of('company_id')})",
    ),
]


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def _timestamps() -> list[sa.Column]:
    now = sa.text("now()")
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    ]


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"), ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "employer_tasks",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("specialization", _enum("specialization", *SPECIALIZATIONS), nullable=False),
        sa.Column("grade", _enum("grade", *GRADES), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        _fk("employer_tasks", "company_id", "employer_companies", "CASCADE"),
        _fk("employer_tasks", "created_by", "users", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employer_tasks")),
    )
    for column in ("company_id", "specialization", "is_active", "created_at"):
        op.create_index(op.f(f"ix_employer_tasks_{column}"), "employer_tasks", [column])
    op.create_table(
        "task_answers",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("task_title", sa.String(length=160), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name=op.f("ck_task_answers_rating_range")
        ),
        _fk("task_answers", "task_id", "employer_tasks", "CASCADE"),
        _fk("task_answers", "company_id", "employer_companies", "CASCADE"),
        _fk("task_answers", "profile_id", "candidate_profiles", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_answers")),
        sa.UniqueConstraint("task_id", "profile_id", name=op.f("uq_task_answers_task_id")),
    )
    for column in ("task_id", "company_id", "profile_id", "created_at"):
        op.create_index(op.f(f"ix_task_answers_{column}"), "task_answers", [column])
    enable(_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_TABLES, _POLICIES)
    op.drop_table("task_answers")
    op.drop_table("employer_tasks")
