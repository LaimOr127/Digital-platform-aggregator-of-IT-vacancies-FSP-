"""Идемпотентная настройка роли приложения. Выполняется владельцем схемы после миграций:

    alembic upgrade head && python -m app.db.provision

Роль приложения: вход по паролю из окружения, только DML на таблицы схемы public,
без DDL, без суперпользователя, без доступа к служебным БД; аудит — только вставка/чтение.
Повторный запуск безопасен и синхронизирует пароль после смены .env.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.core.config import get_settings

# Имена и пароль подставляет сам PostgreSQL через format(%I, %L) — без склейки строк в Python
_ENSURE_ROLE = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = current_setting('provision.app_user')) THEN
    EXECUTE format('CREATE ROLE %I LOGIN', current_setting('provision.app_user'));
  END IF;
  EXECUTE format(
    'ALTER ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
    current_setting('provision.app_user'), current_setting('provision.app_password'));
END $$
"""

_GRANTS = """
DO $$ DECLARE app text := current_setting('provision.app_user'); BEGIN
  EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
  REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
  REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), app);
  REVOKE ALL ON SCHEMA public FROM PUBLIC;
  EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', app);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I', app);
  EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', app);
  EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', app);
  EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                 'GRANT USAGE, SELECT ON SEQUENCES TO %I', app);
  -- служебная таблица миграций: только чтение (иначе приложение могло бы сбить версию схемы)
  IF to_regclass('public.alembic_version') IS NOT NULL THEN
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON alembic_version FROM %I', app);
  END IF;
  IF to_regclass('public.audit_log') IS NOT NULL THEN
    EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM %I', app);
  END IF;
END $$
"""


async def provision_app_role(conn: AsyncConnection, app_user: str, app_password: str) -> None:
    if not app_user or len(app_password) < 16:
        msg = "APP_DB_USER/APP_DB_PASSWORD не заданы или пароль короче 16 символов"
        raise RuntimeError(msg)
    await conn.execute(
        text(
            "SELECT set_config('provision.app_user', :u, true), "
            "set_config('provision.app_password', :p, true)"
        ),
        {"u": app_user, "p": app_password},
    )
    await conn.execute(text(_ENSURE_ROLE))
    await conn.execute(text(_GRANTS))


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.migration_database_url)
    async with engine.begin() as conn:
        await provision_app_role(conn, settings.app_db_user, settings.secret("app_db_password"))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
