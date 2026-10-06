"""Очередь исходящих писем и токены из писем (подтверждение почты, сброс пароля)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column(
            "recipient_type", _enum("recipient_type", "user", "profile", "company"), nullable=False
        ),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("payload_enc", sa.Text(), nullable=True),
        sa.Column(
            "status",
            _enum("outbox_status", "pending", "sent", "failed", "dropped"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_messages")),
    )
    for column in ("status", "next_attempt_at", "created_at"):
        op.create_index(
            op.f(f"ix_outbox_messages_{column}"), "outbox_messages", [column], unique=False
        )

    op.create_table(
        "email_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", _enum("email_token_purpose", "verify", "reset"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_email_tokens_token_hash")),
    )
    for column in ("user_id", "created_at"):
        op.create_index(op.f(f"ix_email_tokens_{column}"), "email_tokens", [column], unique=False)

    # пользователи, зарегистрированные до подтверждения почты, считаются подтверждёнными
    op.execute("UPDATE users SET email_verified = true")


def downgrade() -> None:
    op.drop_table("email_tokens")
    op.drop_table("outbox_messages")
