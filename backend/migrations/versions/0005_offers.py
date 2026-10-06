"""Офферы работодателей и журнал раскрытия контактов + RLS

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import PRIVILEGED, UID, disable, enable, member_of, policy

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# оффер: кандидат-адресат или сотрудник компании-отправителя (бизнес-правила — в приложении)
_OFFER_PARTY = (
    "(EXISTS (SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id "
    f"AND p.user_id::text = {UID}) OR {member_of('company_id')})"
)
_REVEAL_READ = "EXISTS (SELECT 1 FROM offers o WHERE o.id = offer_id)"
_REVEAL_WRITE = (
    f"EXISTS (SELECT 1 FROM offers o WHERE o.id = offer_id AND {member_of('o.company_id')})"
    f" OR {PRIVILEGED}"
)
_RLS_TABLES = ("offers", "contact_reveals")
_POLICIES = [
    policy("offers_party", "offers", "ALL", _OFFER_PARTY),
    policy("contact_reveals_read", "contact_reveals", "SELECT", _REVEAL_READ, check=False),
    policy("contact_reveals_write", "contact_reveals", "INSERT", _REVEAL_WRITE),
]


def upgrade() -> None:
    _create_tables()
    enable(_RLS_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_RLS_TABLES, _POLICIES)
    _drop_tables()


def _create_tables() -> None:
    op.create_table(
        "offers",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=True),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "sent",
                "accepted",
                "declined",
                "withdrawn",
                "expired",
                name="offer_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("vacancy_title", sa.String(length=160), nullable=False),
        sa.Column(
            "grade",
            sa.Enum(
                "intern",
                "junior",
                "middle",
                "senior",
                "lead",
                name="grade",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "work_format",
            sa.Enum(
                "office",
                "hybrid",
                "remote",
                name="work_format",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("decline_reason", sa.String(length=500), nullable=True),
        sa.Column("contact_name_enc", sa.Text(), nullable=True),
        sa.Column("contacts_enc", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
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
            ["company_id"],
            ["employer_companies.id"],
            name=op.f("fk_offers_company_id_employer_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_offers_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_offers_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name=op.f("fk_offers_vacancy_id_vacancies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_offers")),
        sa.UniqueConstraint("company_id", "idempotency_key", name="company_idempotency"),
    )
    op.create_index(op.f("ix_offers_company_id"), "offers", ["company_id"], unique=False)
    op.create_index(op.f("ix_offers_created_at"), "offers", ["created_at"], unique=False)
    op.create_index(op.f("ix_offers_profile_id"), "offers", ["profile_id"], unique=False)
    op.create_index(op.f("ix_offers_status"), "offers", ["status"], unique=False)
    op.create_index(
        "uq_offers_pending_pair",
        "offers",
        ["vacancy_id", "profile_id"],
        unique=True,
        postgresql_where=sa.text("status = 'sent'"),
        sqlite_where=sa.text("status = 'sent'"),
    )
    op.create_table(
        "contact_reveals",
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("viewer_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name=op.f("fk_contact_reveals_offer_id_offers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["viewer_id"],
            ["users.id"],
            name=op.f("fk_contact_reveals_viewer_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contact_reveals")),
    )
    op.create_index(
        op.f("ix_contact_reveals_created_at"), "contact_reveals", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_contact_reveals_offer_id"), "contact_reveals", ["offer_id"], unique=False
    )


def _drop_tables() -> None:
    op.drop_index(op.f("ix_contact_reveals_offer_id"), table_name="contact_reveals")
    op.drop_index(op.f("ix_contact_reveals_created_at"), table_name="contact_reveals")
    op.drop_table("contact_reveals")
    op.drop_index(
        "uq_offers_pending_pair",
        table_name="offers",
        postgresql_where=sa.text("status = 'sent'"),
        sqlite_where=sa.text("status = 'sent'"),
    )
    op.drop_index(op.f("ix_offers_status"), table_name="offers")
    op.drop_index(op.f("ix_offers_profile_id"), table_name="offers")
    op.drop_index(op.f("ix_offers_created_at"), table_name="offers")
    op.drop_index(op.f("ix_offers_company_id"), table_name="offers")
    op.drop_table("offers")
