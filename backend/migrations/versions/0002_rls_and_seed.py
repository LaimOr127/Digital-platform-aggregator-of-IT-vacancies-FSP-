"""RLS (вторая линия защиты от IDOR) и стартовый справочник навыков

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import (
    ROLE,
    UID,
    disable,
    enable,
    member_of,
    owns_profile,
    policy,
    profile_child,
)

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPROVED_EMPLOYER = (
    f"{ROLE} = 'employer' AND EXISTS (SELECT 1 FROM company_members m "
    "JOIN employer_companies c ON c.id = m.company_id "
    f"WHERE m.user_id::text = {UID} AND c.status = 'approved')"
)
_PUBLISHED = (
    "status = 'active' AND (expires_at IS NULL OR expires_at > now()) "
    "AND company_id IN (SELECT c.id FROM employer_companies c WHERE c.status = 'approved')"
)
_OWNED_VACANCY = (
    f"EXISTS (SELECT 1 FROM vacancies v WHERE v.id = vacancy_id AND {member_of('v.company_id')})"
)

_RLS_TABLES = ("candidate_profiles", "profile_skills", "vacancies", "vacancy_skills")

_POLICIES = [
    # Профили: владелец, админ/system; работодатель одобренной компании — только нескрытые.
    policy(
        "profile_read",
        "candidate_profiles",
        "SELECT",
        f"{owns_profile('user_id')} OR (NOT is_hidden AND {_APPROVED_EMPLOYER})",
        check=False,
    ),
    policy("profile_write", "candidate_profiles", "ALL", owns_profile("user_id")),
    *profile_child("profile_skills"),
    # Вакансии: опубликованные (активные, не истёкшие, компания одобрена) видят все;
    # остальные — только своя компания; менять — только своя компания.
    policy(
        "vacancy_read",
        "vacancies",
        "SELECT",
        f"({_PUBLISHED}) OR {member_of('company_id')}",
        check=False,
    ),
    policy("vacancy_write", "vacancies", "ALL", member_of("company_id")),
    policy(
        "vacancy_skills_read",
        "vacancy_skills",
        "SELECT",
        "EXISTS (SELECT 1 FROM vacancies v WHERE v.id = vacancy_id)",
        check=False,
    ),
    policy("vacancy_skills_write", "vacancy_skills", "ALL", _OWNED_VACANCY),
]

_SKILLS = [
    ("python", "Python"),
    ("go", "Go"),
    ("java", "Java"),
    ("kotlin", "Kotlin"),
    ("c++", "C++"),
    ("c#", "C#"),
    ("rust", "Rust"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("php", "PHP"),
    ("swift", "Swift"),
    ("scala", "Scala"),
    ("react", "React"),
    ("vue", "Vue"),
    ("angular", "Angular"),
    ("node.js", "Node.js"),
    ("fastapi", "FastAPI"),
    ("django", "Django"),
    ("spring", "Spring"),
    (".net", ".NET"),
    ("postgresql", "PostgreSQL"),
    ("mysql", "MySQL"),
    ("mongodb", "MongoDB"),
    ("redis", "Redis"),
    ("kafka", "Kafka"),
    ("clickhouse", "ClickHouse"),
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
    ("linux", "Linux"),
    ("git", "Git"),
    ("ci-cd", "CI/CD"),
    ("terraform", "Terraform"),
    ("aws", "AWS"),
    ("algorithms", "Алгоритмы и структуры данных"),
    ("sql", "SQL"),
    ("machine-learning", "Machine Learning"),
    ("pytorch", "PyTorch"),
    ("data-analysis", "Анализ данных"),
    ("information-security", "Информационная безопасность"),
    ("pentest", "Пентест"),
    ("reverse-engineering", "Реверс-инжиниринг"),
    ("android", "Android"),
    ("ios", "iOS"),
    ("unity", "Unity"),
    ("qa-automation", "Автотесты"),
    ("system-design", "System Design"),
    ("robotics", "Робототехника"),
    ("drones", "БПЛА"),
]


def upgrade() -> None:
    skills = sa.table("skills", sa.column("id", sa.Uuid()), sa.column("slug"), sa.column("name"))
    op.bulk_insert(skills, [{"id": uuid.uuid4(), "slug": s, "name": n} for s, n in _SKILLS])
    enable(_RLS_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_RLS_TABLES, _POLICIES)
    op.execute("DELETE FROM skills")
