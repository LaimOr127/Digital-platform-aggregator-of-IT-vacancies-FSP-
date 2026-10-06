"""Построители политик Row Level Security для миграций.

Контекст задаёт приложение: app.user_id / app.role (app/db/session.py).
Права роли приложения на таблицы выдаёт app/db/provision.py.
"""

from alembic import op

UID = "current_setting('app.user_id', true)"
ROLE = "current_setting('app.role', true)"
PRIVILEGED = f"{ROLE} IN ('admin', 'system')"

Policy = tuple[str, str, str]  # (имя, таблица, CREATE POLICY ...)


def owns_profile(user_col: str) -> str:
    return f"({user_col}::text = {UID} OR {PRIVILEGED})"


def member_of(company_col: str) -> str:
    members = f"SELECT m.company_id FROM company_members m WHERE m.user_id::text = {UID}"
    return f"({company_col} IN ({members}) OR {PRIVILEGED})"


def policy(name: str, table: str, command: str, using: str, check: bool = True) -> Policy:
    if command == "INSERT":  # для вставки PostgreSQL допускает только WITH CHECK
        return name, table, f"CREATE POLICY {name} ON {table} FOR INSERT WITH CHECK ({using})"
    with_check = f" WITH CHECK ({using})" if check else ""
    return name, table, f"CREATE POLICY {name} ON {table} FOR {command} USING ({using}){with_check}"


VISIBLE_PROFILE = "EXISTS (SELECT 1 FROM candidate_profiles p WHERE p.id = profile_id)"
OWNED_PROFILE = (
    "EXISTS (SELECT 1 FROM candidate_profiles p "
    f"WHERE p.id = profile_id AND {owns_profile('p.user_id')})"
)


def profile_child(table: str, readable_by_viewers: bool = True) -> list[Policy]:
    """Данные, принадлежащие профилю (profile_id): читает тот, кому виден профиль
    (или только владелец), меняет только владелец профиля / admin / system."""
    read = VISIBLE_PROFILE if readable_by_viewers else OWNED_PROFILE
    return [
        policy(f"{table}_read", table, "SELECT", read, check=False),
        policy(f"{table}_write", table, "ALL", OWNED_PROFILE),
    ]


def is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def enable(tables: tuple[str, ...], policies: list[Policy]) -> None:
    if not is_postgres():
        return
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    for _name, _table, sql in policies:
        op.execute(sql)


def disable(tables: tuple[str, ...], policies: list[Policy]) -> None:
    if not is_postgres():
        return
    for name, table, _sql in policies:
        op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
    for table in tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
