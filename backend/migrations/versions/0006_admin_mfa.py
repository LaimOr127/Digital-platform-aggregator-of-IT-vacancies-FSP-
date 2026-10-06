"""2FA (TOTP) администраторов: секрет, код подключения, блокировка после неверных кодов

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret_enc", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("totp_enabled", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column("users", sa.Column("totp_last_step", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("totp_enroll_hash", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("totp_enroll_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users", sa.Column("totp_failures", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "users", sa.Column("totp_locked_until", sa.DateTime(timezone=True), nullable=True)
    )
    # сессии администраторов, выданные до 2FA, недействительны: вход заново — уже с 2FA
    op.execute(
        "UPDATE refresh_tokens SET revoked_at = now() WHERE revoked_at IS NULL "
        "AND user_id IN (SELECT id FROM users WHERE role = 'admin')"
    )


def downgrade() -> None:
    op.drop_column("users", "totp_locked_until")
    op.drop_column("users", "totp_failures")
    op.drop_column("users", "totp_enroll_expires_at")
    op.drop_column("users", "totp_enroll_hash")
    op.drop_column("users", "totp_last_step")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_enc")
