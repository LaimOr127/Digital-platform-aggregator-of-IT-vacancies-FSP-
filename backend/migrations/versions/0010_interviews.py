"""Собеседования перед оффером (RLS: стороны собеседования) и связь оффера с собеседованием

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import UID, disable, enable, member_of, policy

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# собеседование видят кандидат-адресат и сотрудники компании (бизнес-правила — в приложении)
_PARTY = (
    "(EXISTS (SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id "
    f"AND p.user_id::text = {UID}) OR {member_of('company_id')})"
)
_TABLES = ("interviews",)
_POLICIES = [policy("interviews_party", "interviews", "ALL", _PARTY)]
_ACTIVE = "status IN ('invited', 'scheduled')"


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def _fk(column: str, table: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{table}.id"], name=op.f(f"fk_interviews_{column}_{table}"), ondelete=ondelete
    )


def upgrade() -> None:
    now = sa.text("now()")
    op.create_table(
        "interviews",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=True),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            _enum(
                "interview_status",
                "invited",
                "scheduled",
                "declined",
                "cancelled",
                "completed",
                "expired",
            ),
            nullable=False,
        ),
        sa.Column("result", _enum("interview_result", "passed", "failed"), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("vacancy_title", sa.String(length=160), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("format", _enum("interview_format", "online", "office"), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("interviewer", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("decline_reason", sa.String(length=500), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        _fk("company_id", "employer_companies", "CASCADE"),
        _fk("vacancy_id", "vacancies", "SET NULL"),
        _fk("profile_id", "candidate_profiles", "CASCADE"),
        _fk("created_by", "users", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviews")),
    )
    for column in ("company_id", "profile_id", "status", "created_at"):
        op.create_index(op.f(f"ix_interviews_{column}"), "interviews", [column], unique=False)
    op.create_index(
        "uq_interviews_active_pair",
        "interviews",
        ["vacancy_id", "profile_id"],
        unique=True,
        postgresql_where=sa.text(_ACTIVE),
        sqlite_where=sa.text(_ACTIVE),
    )
    op.add_column("offers", sa.Column("interview_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_offers_interview_id_interviews"),
        "offers",
        "interviews",
        ["interview_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(op.f("uq_offers_interview_id"), "offers", ["interview_id"])
    enable(_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_TABLES, _POLICIES)
    op.drop_constraint(op.f("uq_offers_interview_id"), "offers", type_="unique")
    op.drop_constraint(op.f("fk_offers_interview_id_interviews"), "offers", type_="foreignkey")
    op.drop_column("offers", "interview_id")
    op.drop_table("interviews")
