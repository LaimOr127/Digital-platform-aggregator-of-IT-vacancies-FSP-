"""Общие шаги сценариев: регистрация, вход, админ. Используются всеми API-тестами."""

import secrets
import uuid

from httpx import AsyncClient

from app.db.session import Database
from app.services.auth import AuthService

# Генерируется при запуске: в репозитории нет строк, похожих на секреты (gitleaks)
PASSWORD = f"Pw-{secrets.token_hex(8)}"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.org"


async def register_candidate(client: AsyncClient, name: str = "Иван Петров") -> str:
    r = await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": unique_email("cand"), "password": PASSWORD, "full_name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def register_employer(client: AsyncClient, company: str = "ООО Ромашка") -> str:
    r = await client.post(
        "/api/v1/auth/register/employer",
        json={"email": unique_email("emp"), "password": PASSWORD, "company_name": company},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def create_admin(db: Database, app, superadmin: bool = False) -> str:
    """Админ создаётся как в CLI (через сервис), затем входит через API."""
    email = unique_email("admin")
    async with db.sessionmaker() as session:
        service = AuthService(session, app.state.tokens, app.state.cipher)
        await service.create_admin(email, PASSWORD, superadmin)
        pair = await service.login(email, PASSWORD)
    return pair.access_token


async def company_id(client: AsyncClient, token: str) -> str:
    r = await client.get("/api/v1/employer/company", headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def approve_company(client: AsyncClient, admin_token: str, cid: str) -> None:
    r = await client.post(
        f"/api/v1/admin/companies/{cid}/status",
        json={"status": "approved", "reason": "проверено"},
        headers=bearer(admin_token),
    )
    assert r.status_code == 200, r.text


VACANCY = {
    "title": "Backend-разработчик",
    "description": "FastAPI, PostgreSQL",
    "grade": "middle",
    "work_format": "remote",
    "salary_min": 200_000,
    "salary_max": 300_000,
    "skills": ["python", "postgresql"],
}


async def create_vacancy(client: AsyncClient, token: str, **overrides) -> dict:
    r = await client.post(
        "/api/v1/employer/vacancies", json={**VACANCY, **overrides}, headers=bearer(token)
    )
    assert r.status_code == 201, r.text
    return r.json()
