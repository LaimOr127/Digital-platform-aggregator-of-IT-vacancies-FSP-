"""Подключаемые языковые модели (настраиваются в интерфейсе суперадмином)

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = sa.text("now()")
    op.create_table(
        "ai_providers",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "openai",
                "anthropic",
                name="ai_provider_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=300), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("api_key_enc", sa.Text(), nullable=True),
        sa.Column("key_hint", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_providers")),
    )
    op.create_index(
        op.f("ix_ai_providers_created_at"), "ai_providers", ["created_at"], unique=False
    )
    op.create_index(
        "uq_ai_providers_active",
        "ai_providers",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_table("ai_providers")
