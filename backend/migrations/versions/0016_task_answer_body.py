"""Текст задачи в ответе кандидата: своё задание видно и после снятия задачи

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_answers", sa.Column("task_body", sa.Text(), nullable=False, server_default="")
    )
    op.execute(
        "UPDATE task_answers a SET task_body = t.body FROM employer_tasks t WHERE t.id = a.task_id"
    )


def downgrade() -> None:
    op.drop_column("task_answers", "task_body")
