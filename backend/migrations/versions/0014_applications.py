"""Выход на контакт: приглашения и отклики со статусами; профиль компании; согласие; приватность

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import UID, disable, enable, member_of, policy

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OPEN = "status IN ('sent', 'viewed')"
# приглашение или отклик видят только его стороны: кандидат и сотрудники компании
_PARTY = (
    "(EXISTS (SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id "
    f"AND p.user_id::text = {UID}) OR {member_of('company_id')})"
)
_TABLES = ("applications",)
_POLICIES = [policy("applications_party", "applications", "ALL", _PARTY)]
_COMPANY_COLUMNS = (
    ("description", sa.Text(), sa.text("''"), False),
    ("industry", sa.String(length=120), None, True),
    ("contact_email", sa.String(length=254), None, True),
    ("contact_phone", sa.String(length=32), None, True),
    ("contact_telegram", sa.String(length=64), None, True),
)
_PRIVACY = ("show_fsp", "show_salary", "show_about")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def _fk(column: str, table: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{table}.id"], name=op.f(f"fk_applications_{column}_{table}"), ondelete=ondelete
    )


def upgrade() -> None:
    _create_applications()
    enable(_TABLES, _POLICIES)
    for name, column_type, default, nullable in _COMPANY_COLUMNS:
        op.add_column(
            "employer_companies",
            sa.Column(name, column_type, server_default=default, nullable=nullable),
        )
    for name in _PRIVACY:
        op.add_column(
            "candidate_profiles",
            sa.Column(name, sa.Boolean(), server_default=sa.true(), nullable=False),
        )
    op.add_column("users", sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True))
    # прежние пользователи соглашались с условиями при регистрации (текст под формой)
    op.execute("UPDATE users SET consent_at = created_at")
    op.add_column("interviews", sa.Column("application_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_interviews_application_id_applications"),
        "interviews",
        "applications",
        ["application_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_interviews_application_id"), "interviews", ["application_id"])


def _create_applications() -> None:
    now = sa.text("now()")
    op.create_table(
        "applications",
        sa.Column(
            "direction", _enum("application_direction", "invitation", "response"), nullable=False
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            _enum(
                "application_status",
                "sent",
                "viewed",
                "accepted",
                "declined",
                "withdrawn",
                "expired",
            ),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "grade", _enum("grade", "intern", "junior", "middle", "senior", "lead"), nullable=False
        ),
        sa.Column(
            "work_format", _enum("work_format", "office", "hybrid", "remote"), nullable=False
        ),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("contact_method", sa.String(length=300), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("decline_reason", sa.String(length=500), nullable=True),
        sa.Column("contact_name_enc", sa.Text(), nullable=True),
        sa.Column("contacts_enc", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.CheckConstraint(
            "salary_min > 0 AND salary_max >= salary_min", name=op.f("ck_applications_salary_range")
        ),
        _fk("company_id", "employer_companies", "CASCADE"),
        _fk("profile_id", "candidate_profiles", "CASCADE"),
        _fk("vacancy_id", "vacancies", "SET NULL"),
        _fk("created_by", "users", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    for column in ("direction", "company_id", "profile_id", "vacancy_id", "status", "created_at"):
        op.create_index(op.f(f"ix_applications_{column}"), "applications", [column], unique=False)
    op.create_index(
        "uq_applications_open_pair",
        "applications",
        ["company_id", "profile_id"],
        unique=True,
        postgresql_where=sa.text(_OPEN),
        sqlite_where=sa.text(_OPEN),
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_interviews_application_id"), table_name="interviews")
    op.drop_constraint(
        op.f("fk_interviews_application_id_applications"), "interviews", type_="foreignkey"
    )
    op.drop_column("interviews", "application_id")
    op.drop_column("users", "consent_at")
    for name in _PRIVACY:
        op.drop_column("candidate_profiles", name)
    for name, *_ in _COMPANY_COLUMNS:
        op.drop_column("employer_companies", name)
    disable(_TABLES, _POLICIES)
    op.drop_table("applications")
