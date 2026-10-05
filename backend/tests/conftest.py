"""Фикстуры тестов.

БД: по умолчанию in-memory SQLite (быстро, без Docker). Если задан TEST_POSTGRES_URL
(владелец тестовой БД), схема создаётся миграциями Alembic, а приложение подключается
отдельной ролью без прав владельца — так в тестах работают настоящие политики RLS.
"""

import os
import secrets

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", secrets.token_hex(32))
os.environ.setdefault("FIELD_ENCRYPTION_KEY", secrets.token_hex(32))
os.environ.setdefault("PASSPORT_SIGNING_KEY", secrets.token_hex(32))
os.environ.setdefault("FSP_API_KEY", secrets.token_hex(16))

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_fsp_client
from app.core.config import Settings, get_settings
from app.db.session import Database, get_database
from app.main import create_app
from tests import dbsetup
from tests.fake_fsp import FakeFspClient

POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL", "")


class FakeDatabase:
    def __init__(self, alive: bool) -> None:
        self.alive = alive

    async def ping(self) -> bool:
        return self.alive


@pytest.fixture
def make_client():
    """Синхронный клиент без БД (health-проверки)."""

    def _make(db_alive: bool = True) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_database] = lambda: FakeDatabase(db_alive)
        return TestClient(app)

    return _make


@pytest.fixture(scope="session")
def pg_app_url() -> str | None:
    """Один раз за сессию: миграции + роль приложения. None — если Postgres не задан."""
    return dbsetup.prepare_postgres(POSTGRES_URL) if POSTGRES_URL else None


@pytest.fixture
def settings() -> Settings:
    return get_settings()


@pytest.fixture
def premoderation(settings: Settings):
    """Режим предмодерации: новая компания ждёт одобрения (по умолчанию — постмодерация)."""
    settings.company_premoderation = True
    yield
    settings.company_premoderation = False


@pytest.fixture
async def db(pg_app_url: str | None):
    if pg_app_url:
        await dbsetup.truncate_postgres(POSTGRES_URL)
        database = Database(pg_app_url)
    else:
        database = Database("sqlite+aiosqlite:///:memory:")
        await dbsetup.create_sqlite_schema(database)
    yield database
    await database.dispose()


@pytest.fixture
def fsp() -> FakeFspClient:
    return FakeFspClient()


@pytest.fixture
def app(db: Database, settings: Settings, fsp: FakeFspClient):
    application = create_app(settings)
    application.dependency_overrides[get_database] = lambda: db
    application.dependency_overrides[get_fsp_client] = lambda: fsp
    # сценарии регистрируют много пользователей с одного «IP»; лимиты проверяют отдельные тесты
    application.state.rate_limits["auth"] = (1000, 60)
    application.state.rate_limits["email"] = (1000, 3600)
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
