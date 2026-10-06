"""Защита заданий: снимок экрана во время теста или задачи

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("violation", sa.String(length=32), nullable=True))
    op.add_column(
        "task_answers",
        sa.Column("blocked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("task_answers", "blocked")
    op.drop_column("assessments", "violation")
