import pytest
from fastapi.testclient import TestClient

from app.db.session import get_database
from app.main import create_app


class FakeDatabase:
    def __init__(self, alive: bool) -> None:
        self.alive = alive

    async def ping(self) -> bool:
        return self.alive


@pytest.fixture
def make_client():
    def _make(db_alive: bool = True) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_database] = lambda: FakeDatabase(db_alive)
        return TestClient(app)

    return _make
