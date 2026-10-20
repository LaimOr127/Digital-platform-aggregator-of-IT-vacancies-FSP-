"""Уходы со вкладки во время теста: сигнал в результате, без автоматического провала

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("focus_losses", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("assessments", "focus_losses")
