"""core schema: пользователи, профили, компании, вакансии, аудит

Revision ID: 0001
Revises:
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_log_created_at"), "audit_log", ["created_at"], unique=False)
    op.create_table(
        "employer_companies",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "blocked",
                name="company_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employer_companies")),
    )
    op.create_index(
        op.f("ix_employer_companies_created_at"), "employer_companies", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_employer_companies_status"), "employer_companies", ["status"], unique=False
    )
    op.create_table(
        "skills",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("slug", name=op.f("uq_skills_slug")),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "candidate",
                "employer",
                "admin",
                name="user_role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("anon_id", sa.Uuid(), nullable=False),
        sa.Column("full_name_enc", sa.Text(), nullable=True),
        sa.Column("contacts_enc", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
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
            nullable=True,
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
            nullable=True,
        ),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column(
            "verification_tier",
            sa.Enum(
                "self_declared",
                "resume_parsed",
                "verified_fsp",
                name="verification_tier",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
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
            ["user_id"],
            ["users.id"],
            name=op.f("fk_candidate_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_profiles")),
        sa.UniqueConstraint("anon_id", name=op.f("uq_candidate_profiles_anon_id")),
        sa.UniqueConstraint("user_id", name=op.f("uq_candidate_profiles_user_id")),
    )
    op.create_index(
        op.f("ix_candidate_profiles_created_at"), "candidate_profiles", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_candidate_profiles_grade"), "candidate_profiles", ["grade"], unique=False
    )
    op.create_table(
        "company_members",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "owner",
                "recruiter",
                name="member_role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
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
            name=op.f("fk_company_members_company_id_employer_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_company_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_members")),
        sa.UniqueConstraint("company_id", "user_id", name="company_user"),
        sa.UniqueConstraint("user_id", name=op.f("uq_company_members_user_id")),
    )
    op.create_index(
        op.f("ix_company_members_company_id"), "company_members", ["company_id"], unique=False
    )
    op.create_index(
        op.f("ix_company_members_created_at"), "company_members", ["created_at"], unique=False
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_refresh_tokens_created_at"), "refresh_tokens", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_table(
        "vacancies",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
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
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "active",
                "closed",
                "blocked",
                name="vacancy_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "salary_min > 0 AND salary_max >= salary_min", name=op.f("ck_vacancies_salary_range")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["employer_companies.id"],
            name=op.f("fk_vacancies_company_id_employer_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_vacancies_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vacancies")),
    )
    op.create_index(op.f("ix_vacancies_company_id"), "vacancies", ["company_id"], unique=False)
    op.create_index(op.f("ix_vacancies_created_at"), "vacancies", ["created_at"], unique=False)
    op.create_index(op.f("ix_vacancies_grade"), "vacancies", ["grade"], unique=False)
    op.create_index(op.f("ix_vacancies_status"), "vacancies", ["status"], unique=False)
    op.create_table(
        "profile_skills",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_profile_skills_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name=op.f("fk_profile_skills_skill_id_skills"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "skill_id", name=op.f("pk_profile_skills")),
    )
    op.create_index(
        op.f("ix_profile_skills_skill_id"), "profile_skills", ["skill_id"], unique=False
    )
    op.create_table(
        "vacancy_skills",
        sa.Column("vacancy_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name=op.f("fk_vacancy_skills_skill_id_skills"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name=op.f("fk_vacancy_skills_vacancy_id_vacancies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("vacancy_id", "skill_id", name=op.f("pk_vacancy_skills")),
    )
    op.create_index(
        op.f("ix_vacancy_skills_skill_id"), "vacancy_skills", ["skill_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_vacancy_skills_skill_id"), table_name="vacancy_skills")
    op.drop_table("vacancy_skills")
    op.drop_index(op.f("ix_profile_skills_skill_id"), table_name="profile_skills")
    op.drop_table("profile_skills")
    op.drop_index(op.f("ix_vacancies_status"), table_name="vacancies")
    op.drop_index(op.f("ix_vacancies_grade"), table_name="vacancies")
    op.drop_index(op.f("ix_vacancies_created_at"), table_name="vacancies")
    op.drop_index(op.f("ix_vacancies_company_id"), table_name="vacancies")
    op.drop_table("vacancies")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_created_at"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_company_members_created_at"), table_name="company_members")
    op.drop_index(op.f("ix_company_members_company_id"), table_name="company_members")
    op.drop_table("company_members")
    op.drop_index(op.f("ix_candidate_profiles_grade"), table_name="candidate_profiles")
    op.drop_index(op.f("ix_candidate_profiles_created_at"), table_name="candidate_profiles")
    op.drop_table("candidate_profiles")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_table("users")
    op.drop_table("skills")
    op.drop_index(op.f("ix_employer_companies_status"), table_name="employer_companies")
    op.drop_index(op.f("ix_employer_companies_created_at"), table_name="employer_companies")
    op.drop_table("employer_companies")
    op.drop_index(op.f("ix_audit_log_created_at"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_table("audit_log")
