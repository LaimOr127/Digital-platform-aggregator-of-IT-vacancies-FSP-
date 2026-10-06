"""Жалобы кандидатов на вакансии

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import disable, enable, profile_child

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("vacancy_complaints",)
# жалобу видят и меняют только её автор, модератор (admin) и система
_POLICIES = profile_child("vacancy_complaints", readable_by_viewers=False)


def upgrade() -> None:
    op.create_table(
        "vacancy_complaints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name=op.f("fk_vacancy_complaints_vacancy_id_vacancies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_vacancy_complaints_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vacancy_complaints")),
        sa.UniqueConstraint(
            "vacancy_id", "profile_id", name=op.f("uq_vacancy_complaints_vacancy_id")
        ),
    )
    for column in ("vacancy_id", "profile_id", "created_at"):
        op.create_index(
            op.f(f"ix_vacancy_complaints_{column}"), "vacancy_complaints", [column], unique=False
        )
    enable(_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_TABLES, _POLICIES)
    op.drop_table("vacancy_complaints")
