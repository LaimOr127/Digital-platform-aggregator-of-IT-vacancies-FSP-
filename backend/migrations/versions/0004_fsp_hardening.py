"""ФСП: имя из ФСП, расписание синхронизации, один действующий паспорт, справочник категорий,
строже RLS (паспорта и привязки читает только владелец; категории меняет только system/admin)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-01
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.services.categorization import all_categories
from migrations.rls import (
    OWNED_PROFILE,
    PRIVILEGED,
    VISIBLE_PROFILE,
    disable,
    enable,
    is_postgres,
    policy,
)

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_POLICIES = [
    ("passports_read", "passports"),
    ("fsp_links_read", "fsp_links"),
]
_NEW_POLICIES = [
    # публичная проверка паспорта идёт через контекст system и отдаёт минимум по отозванным
    policy("passports_read", "passports", "SELECT", OWNED_PROFILE, check=False),
    # athlete_id/регион деанонимизируют кандидата — привязку видит только владелец
    policy("fsp_links_read", "fsp_links", "SELECT", OWNED_PROFILE, check=False),
]
_PREVIOUS_POLICIES = [
    policy("passports_read", "passports", "SELECT", "true", check=False),
    policy("fsp_links_read", "fsp_links", "SELECT", VISIBLE_PROFILE, check=False),
]
_CATEGORY_POLICIES = [
    policy("categories_read", "categories", "SELECT", "true", check=False),
    policy("categories_write", "categories", "ALL", PRIVILEGED),
]

# дубли действующих паспортов (до индекса) отзываются, остаётся самый свежий
_REVOKE_DUPLICATES = """
UPDATE passports p SET revoked_at = now()
WHERE p.revoked_at IS NULL AND EXISTS (
  SELECT 1 FROM passports q
  WHERE q.profile_id = p.profile_id AND q.revoked_at IS NULL AND q.created_at > p.created_at
)
"""


def upgrade() -> None:
    op.add_column("fsp_links", sa.Column("full_name", sa.String(length=200), nullable=True))
    op.add_column("fsp_links", sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "fsp_links",
        sa.Column("sync_failures", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(op.f("ix_fsp_links_next_sync_at"), "fsp_links", ["next_sync_at"], unique=False)
    if is_postgres():
        op.execute(_REVOKE_DUPLICATES)
    op.create_index(
        "uq_passports_active_profile",
        "passports",
        ["profile_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
        sqlite_where=sa.text("revoked_at IS NULL"),
    )
    _seed_categories()
    if is_postgres():
        for name, table in _OLD_POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
        for _name, _table, sql in _NEW_POLICIES:
            op.execute(sql)
    enable(("categories",), _CATEGORY_POLICIES)


def downgrade() -> None:
    disable(("categories",), _CATEGORY_POLICIES)
    if is_postgres():
        for name, table, _sql in _NEW_POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
        for _name, _table, sql in _PREVIOUS_POLICIES:
            op.execute(sql)
    op.drop_index(
        "uq_passports_active_profile",
        table_name="passports",
        postgresql_where=sa.text("revoked_at IS NULL"),
        sqlite_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_index(op.f("ix_fsp_links_next_sync_at"), table_name="fsp_links")
    op.drop_column("fsp_links", "sync_failures")
    op.drop_column("fsp_links", "next_sync_at")
    op.drop_column("fsp_links", "full_name")


def _seed_categories() -> None:
    conn = op.get_bind()
    existing = {row[0] for row in conn.execute(sa.text("SELECT slug FROM categories"))}
    table = sa.table(
        "categories",
        sa.column("id", sa.Uuid()),
        sa.column("slug"),
        sa.column("discipline"),
        sa.column("tier"),
        sa.column("title"),
    )
    rows = [
        {
            "id": uuid.uuid4(),
            "slug": c.slug,
            "discipline": c.discipline,
            "tier": c.tier,
            "title": c.title,
        }
        for c in all_categories()
        if c.slug not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)
