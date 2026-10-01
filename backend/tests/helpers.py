"""Общие шаги сценариев: регистрация, вход, админ. Используются всеми API-тестами."""

import secrets
import time
import uuid
from dataclasses import dataclass

from httpx import ASGITransport, AsyncClient

from app.core import totp
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


@dataclass(frozen=True)
class NewAdmin:
    id: uuid.UUID
    email: str
    enrollment_code: str


async def new_admin(db: Database, app, superadmin: bool = False) -> NewAdmin:
    """Администратор, как из CLI: ещё без 2FA, с кодом подключения."""
    email = unique_email("admin")
    async with db.sessionmaker() as session:
        user, code = await AuthService(session, app.state.tokens, app.state.cipher).create_admin(
            email, PASSWORD, superadmin
        )
    return NewAdmin(user.id, email, code)


async def create_admin(db: Database, app, superadmin: bool = False) -> str:
    """Админ создаётся как в CLI и входит по-настоящему: пароль -> настройка 2FA -> код."""
    admin = await new_admin(db, app, superadmin)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await admin_login(client, admin.email, enrollment_code=admin.enrollment_code)


async def admin_login(
    client: AsyncClient, email: str, *, enrollment_code: str | None = None, secret: str = ""
) -> str:
    """Вход администратора: первый — с кодом подключения (настройка), далее — по секрету."""
    challenge = (
        await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    ).json()
    assert challenge["mfa_required"] is True, challenge
    if enrollment_code is not None:
        setup = await client.post(
            "/api/v1/auth/2fa/setup",
            json={"mfa_token": challenge["mfa_token"], "enrollment_code": enrollment_code},
        )
        assert setup.status_code == 200, setup.text
        secret = setup.json()["secret"]
    code = totp.code_at(secret, int(time.time()) // totp.STEP_SECONDS)
    r = await client.post(
        "/api/v1/auth/2fa/verify", json={"mfa_token": challenge["mfa_token"], "code": code}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


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


async def link_fsp(client: AsyncClient, token: str, athlete_id: str = "FSP-1") -> dict:
    """Привязка ФСП через API с кодом фейкового клиента (общий шаг тестов ФСП и worker)."""
    from tests.fake_fsp import CODE

    r = await client.post(
        "/api/v1/candidate/fsp/link", json={"athlete_id": athlete_id}, headers=bearer(token)
    )
    assert r.status_code == 200, r.text
    r = await client.post(
        "/api/v1/candidate/fsp/confirm", json={"code": CODE}, headers=bearer(token)
    )
    assert r.status_code == 200, r.text
    return r.json()
