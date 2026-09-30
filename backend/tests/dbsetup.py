"""Тестовая БД: SQLite (create_all) или PostgreSQL (миграции + роль без прав владельца)."""

import asyncio
import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.provision import provision_app_role
from app.db.session import Database
from app.models import Base, Skill

APP_ROLE = "itmatch_test_app"
TEST_SKILLS = [("python", "Python"), ("go", "Go"), ("postgresql", "PostgreSQL"), ("react", "React")]
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_TRUNCATE = "TRUNCATE users, employer_companies, audit_log RESTART IDENTITY CASCADE"


async def create_sqlite_schema(database: Database) -> None:
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with database.sessionmaker() as session:
        session.add_all(Skill(id=uuid.uuid4(), slug=s, name=n) for s, n in TEST_SKILLS)
        await session.commit()


async def _execute(owner_url: str, *statements: str) -> None:
    engine = create_async_engine(owner_url)
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))
    await engine.dispose()


async def _provision(owner_url: str, password: str) -> None:
    engine = create_async_engine(owner_url)
    async with engine.begin() as conn:
        await provision_app_role(conn, APP_ROLE, password)
    await engine.dispose()


def prepare_postgres(owner_url: str) -> str:
    """Чистая схема -> миграции -> роль приложения (как в migrate). Возвращает URL этой роли."""
    database = make_url(owner_url).database or ""
    if not database.endswith("_test"):
        # схема public пересоздаётся с нуля: защита от случайного запуска на рабочей БД
        msg = f"TEST_POSTGRES_URL должен указывать на БД с суффиксом _test, а не {database!r}"
        raise RuntimeError(msg)
    password = secrets.token_hex(16)
    asyncio.run(_execute(owner_url, "DROP SCHEMA public CASCADE", "CREATE SCHEMA public"))
    env = {**os.environ, "DATABASE_URL_OVERRIDE": owner_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=_BACKEND_DIR, env=env, check=True
    )
    asyncio.run(_provision(owner_url, password))
    url = make_url(owner_url).set(username=APP_ROLE, password=password)
    return url.render_as_string(hide_password=False)


async def truncate_postgres(owner_url: str) -> None:
    await _execute(owner_url, _TRUNCATE)
