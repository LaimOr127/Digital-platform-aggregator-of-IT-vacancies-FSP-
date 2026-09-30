"""RLS (вторая линия защиты от IDOR) и стартовый справочник навыков

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Контекст задаёт приложение: app.user_id / app.role (app/db/session.py).
# Права роли приложения на таблицы (включая append-only аудит) выдаёт app/db/provision.py.
_UID = "current_setting('app.user_id', true)"
_ROLE = "current_setting('app.role', true)"
_PRIVILEGED = f"{_ROLE} IN ('admin', 'system')"
_APPROVED_EMPLOYER = (
    f"{_ROLE} = 'employer' AND EXISTS (SELECT 1 FROM company_members m "
    "JOIN employer_companies c ON c.id = m.company_id "
    f"WHERE m.user_id::text = {_UID} AND c.status = 'approved')"
)
_PUBLISHED = (
    "status = 'active' AND (expires_at IS NULL OR expires_at > now()) "
    "AND company_id IN (SELECT c.id FROM employer_companies c WHERE c.status = 'approved')"
)


def _owns_profile(user_col: str) -> str:
    return f"({user_col}::text = {_UID} OR {_PRIVILEGED})"


def _member_of(company_col: str) -> str:
    members = f"SELECT m.company_id FROM company_members m WHERE m.user_id::text = {_UID}"
    return f"({company_col} IN ({members}) OR {_PRIVILEGED})"


def _policy(
    name: str, table: str, command: str, using: str, check: bool = True
) -> tuple[str, str, str]:
    """(имя, таблица, CREATE POLICY ...) — имя и таблица нужны для downgrade."""
    with_check = f" WITH CHECK ({using})" if check else ""
    sql = f"CREATE POLICY {name} ON {table} FOR {command} USING ({using}){with_check}"
    return name, table, sql


_OWNED_PROFILE = (
    f"SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id AND {_owns_profile('p.user_id')}"
)
_OWNED_VACANCY = (
    f"SELECT 1 FROM vacancies v WHERE v.id = vacancy_id AND {_member_of('v.company_id')}"
)

_RLS_TABLES = ("candidate_profiles", "profile_skills", "vacancies", "vacancy_skills")

_POLICIES = [
    # Профили: владелец, админ/system; работодатель одобренной компании — только нескрытые.
    _policy(
        "profile_read",
        "candidate_profiles",
        "SELECT",
        f"{_owns_profile('user_id')} OR (NOT is_hidden AND {_APPROVED_EMPLOYER})",
        check=False,
    ),
    _policy("profile_write", "candidate_profiles", "ALL", _owns_profile("user_id")),
    # Навыки профиля видны тем, кому виден профиль; меняет — владелец профиля.
    _policy(
        "profile_skills_read",
        "profile_skills",
        "SELECT",
        "EXISTS (SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id)",
        check=False,
    ),
    _policy("profile_skills_write", "profile_skills", "ALL", f"EXISTS ({_OWNED_PROFILE})"),
    # Вакансии: опубликованные (активные, не истёкшие, компания одобрена) видят все;
    # остальные — только своя компания; менять — только своя компания.
    _policy(
        "vacancy_read",
        "vacancies",
        "SELECT",
        f"({_PUBLISHED}) OR {_member_of('company_id')}",
        check=False,
    ),
    _policy("vacancy_write", "vacancies", "ALL", _member_of("company_id")),
    _policy(
        "vacancy_skills_read",
        "vacancy_skills",
        "SELECT",
        "EXISTS (SELECT 1 FROM vacancies v WHERE v.id = vacancy_id)",
        check=False,
    ),
    _policy("vacancy_skills_write", "vacancy_skills", "ALL", f"EXISTS ({_OWNED_VACANCY})"),
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
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    for _name, _table, sql in _POLICIES:
        op.execute(sql)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for name, table, _sql in _POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
        for table in _RLS_TABLES:
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DELETE FROM skills")
