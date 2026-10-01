"""Счётчики лимитов запросов в PostgreSQL: общие для всех процессов и реплик api

Таблица нежурналируемая (UNLOGGED): быстрая запись, после сбоя БД счётчики обнуляются.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE UNLOGGED TABLE rate_limit_buckets (
            key text NOT NULL,
            bucket bigint NOT NULL,
            hits integer NOT NULL,
            expires_at timestamptz NOT NULL,
            PRIMARY KEY (key, bucket)
        )
        """
    )
    op.execute("CREATE INDEX ix_rate_limit_buckets_expires_at ON rate_limit_buckets (expires_at)")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TABLE rate_limit_buckets")
