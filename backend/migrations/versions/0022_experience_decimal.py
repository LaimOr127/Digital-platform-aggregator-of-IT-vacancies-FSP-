"""Стаж с десятыми: 3 года 5 месяцев хранится как 3.4, а не 3

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "candidate_profiles", "experience_years", type_=sa.Float(), existing_nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "candidate_profiles",
        "experience_years",
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="round(experience_years)::integer",
    )
