"""ФСП: привязки, достижения, категории, паспорта навыков + RLS

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import OWNED_PROFILE, disable, enable, policy, profile_child

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RLS_TABLES = (
    "fsp_verifications",
    "fsp_links",
    "fsp_achievements",
    "candidate_categories",
    "passports",
)
_POLICIES = [
    # незавершённая привязка (request_id кода) — только владелец
    *profile_child("fsp_verifications", readable_by_viewers=False),
    # привязка, достижения и категории видны тем, кому виден профиль (каталог работодателя)
    *profile_child("fsp_links"),
    *profile_child("fsp_achievements"),
    *profile_child("candidate_categories"),
    # паспорт — публичный документ по ссылке: читать может любой, выпускать — владелец
    policy("passports_read", "passports", "SELECT", "true", check=False),
    policy("passports_write", "passports", "ALL", OWNED_PROFILE),
]


def upgrade() -> None:
    _create_tables()
    enable(_RLS_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_RLS_TABLES, _POLICIES)
    _drop_tables()


def _create_tables() -> None:
    op.create_table(
        "categories",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("discipline", sa.String(length=32), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_categories_slug")),
    )
    op.create_index(op.f("ix_categories_discipline"), "categories", ["discipline"], unique=False)
    op.create_table(
        "candidate_categories",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_candidate_categories_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_candidate_categories_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "category_id", name=op.f("pk_candidate_categories")),
    )
    op.create_index(
        op.f("ix_candidate_categories_category_id"),
        "candidate_categories",
        ["category_id"],
        unique=False,
    )
    op.create_table(
        "fsp_achievements",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("discipline", sa.String(length=32), nullable=False),
        sa.Column("competition_title", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("place", sa.Integer(), nullable=True),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("team", sa.String(length=120), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_fsp_achievements_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fsp_achievements")),
        sa.UniqueConstraint("profile_id", "external_id", name="profile_result"),
    )
    op.create_index(
        op.f("ix_fsp_achievements_created_at"), "fsp_achievements", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_fsp_achievements_discipline"), "fsp_achievements", ["discipline"], unique=False
    )
    op.create_index(
        op.f("ix_fsp_achievements_profile_id"), "fsp_achievements", ["profile_id"], unique=False
    )
    op.create_table(
        "fsp_links",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("athlete_id", sa.String(length=32), nullable=False),
        sa.Column("rank", sa.String(length=16), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_fsp_links_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fsp_links")),
        sa.UniqueConstraint("athlete_id", name=op.f("uq_fsp_links_athlete_id")),
        sa.UniqueConstraint("profile_id", name=op.f("uq_fsp_links_profile_id")),
    )
    op.create_index(op.f("ix_fsp_links_created_at"), "fsp_links", ["created_at"], unique=False)
    op.create_table(
        "fsp_verifications",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("athlete_id", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_fsp_verifications_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fsp_verifications")),
        sa.UniqueConstraint("profile_id", name=op.f("uq_fsp_verifications_profile_id")),
    )
    op.create_index(
        op.f("ix_fsp_verifications_created_at"), "fsp_verifications", ["created_at"], unique=False
    )
    op.create_table(
        "passports",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("key_id", sa.String(length=32), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_passports_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passports")),
    )
    op.create_index(op.f("ix_passports_created_at"), "passports", ["created_at"], unique=False)
    op.create_index(op.f("ix_passports_profile_id"), "passports", ["profile_id"], unique=False)


def _drop_tables() -> None:
    op.drop_index(op.f("ix_passports_profile_id"), table_name="passports")
    op.drop_index(op.f("ix_passports_created_at"), table_name="passports")
    op.drop_table("passports")
    op.drop_index(op.f("ix_fsp_verifications_created_at"), table_name="fsp_verifications")
    op.drop_table("fsp_verifications")
    op.drop_index(op.f("ix_fsp_links_created_at"), table_name="fsp_links")
    op.drop_table("fsp_links")
    op.drop_index(op.f("ix_fsp_achievements_profile_id"), table_name="fsp_achievements")
    op.drop_index(op.f("ix_fsp_achievements_discipline"), table_name="fsp_achievements")
    op.drop_index(op.f("ix_fsp_achievements_created_at"), table_name="fsp_achievements")
    op.drop_table("fsp_achievements")
    op.drop_index(op.f("ix_candidate_categories_category_id"), table_name="candidate_categories")
    op.drop_table("candidate_categories")
    op.drop_index(op.f("ix_categories_discipline"), table_name="categories")
    op.drop_table("categories")
