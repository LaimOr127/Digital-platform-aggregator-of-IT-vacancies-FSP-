"""IDOR и разделение ролей: пользователь A не читает и не меняет данные B.

Проверки перечисляют маршруты приложения автоматически: новый эндпоинт без авторизации
или без проверки роли уронит тест, даже если для него забыли написать отдельный.
"""

import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import set_rls_context
from app.main import create_app
from app.models import CandidateProfile, User
from app.repositories.candidates import CandidateProfileRepository
from tests.helpers import (
    approve_company,
    bearer,
    company_id,
    create_admin,
    create_vacancy,
    register_candidate,
    register_employer,
)

PUBLIC_PREFIXES = (
    "/api/v1/health",
    "/api/v1/public/",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
)
# refresh/logout защищены cookie + CSRF, а не access-токеном (проверяется в test_auth)
COOKIE_AUTH = ("/api/v1/auth/refresh", "/api/v1/auth/logout")


def _routes(prefix: str = "/api/v1/") -> list[tuple[str, str]]:
    """Все эндпоинты из OpenAPI-схемы (публичный контракт приложения)."""
    result = []
    for path, operations in create_app().openapi()["paths"].items():
        if not path.startswith(prefix) or path.startswith(PUBLIC_PREFIXES) or path in COOKIE_AUTH:
            continue
        concrete = re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), path)
        result.extend((method.upper(), concrete) for method in sorted(operations))
    return result


def test_route_discovery_finds_endpoints():
    assert len(_routes()) >= 10


@pytest.mark.parametrize(("method", "path"), _routes())
async def test_protected_routes_require_token(client: AsyncClient, method: str, path: str):
    r = await client.request(method, path, json={})
    assert r.status_code == 401, (method, path, r.text)


@pytest.mark.parametrize(
    ("method", "path"), _routes("/api/v1/employer/") + _routes("/api/v1/admin/")
)
async def test_candidate_forbidden_outside_own_portal(client: AsyncClient, method: str, path: str):
    token = await register_candidate(client)
    r = await client.request(method, path, json={}, headers=bearer(token))
    assert r.status_code == 403, (method, path, r.text)


@pytest.mark.parametrize(
    ("method", "path"), _routes("/api/v1/candidate/") + _routes("/api/v1/admin/")
)
async def test_employer_forbidden_outside_own_portal(client: AsyncClient, method: str, path: str):
    token = await register_employer(client)
    r = await client.request(method, path, json={}, headers=bearer(token))
    assert r.status_code == 403, (method, path, r.text)


async def test_employer_cannot_touch_foreign_vacancy(client: AsyncClient, db, app):
    owner = await register_employer(client, company="Компания A")
    intruder = await register_employer(client, company="Компания B")
    admin = await create_admin(db, app)
    await approve_company(client, admin, await company_id(client, intruder))
    vacancy = await create_vacancy(client, owner)
    url = f"/api/v1/employer/vacancies/{vacancy['id']}"
    attempts = [
        ("GET", url, None),
        ("PATCH", url, {"title": "Взломано"}),
        ("POST", f"{url}/publish", None),
        ("POST", f"{url}/close", None),
        ("DELETE", url, None),
    ]
    for method, path, body in attempts:
        r = await client.request(method, path, json=body, headers=bearer(intruder))
        assert r.status_code == 404, (method, path, r.text)

    listing = await client.get("/api/v1/employer/vacancies", headers=bearer(intruder))
    assert listing.json()["items"] == []
    unchanged = (await client.get(url, headers=bearer(owner))).json()
    assert unchanged["title"] == vacancy["title"] and unchanged["status"] == "draft"


async def test_candidates_see_only_own_profile(client: AsyncClient):
    alice = await register_candidate(client, name="Алиса")
    bob = await register_candidate(client, name="Боб")
    await client.patch("/api/v1/candidate/profile", json={"city": "Томск"}, headers=bearer(bob))
    r = await client.get("/api/v1/candidate/profile", headers=bearer(alice))
    assert r.json()["full_name"] == "Алиса" and r.json()["city"] is None


async def test_profile_repository_scoped_to_owner(client: AsyncClient, db):
    await register_candidate(client, name="Алиса")
    await register_candidate(client, name="Боб")
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        profiles = (await session.execute(select(CandidateProfile))).scalars().all()
        alice, bob = profiles
        repo = CandidateProfileRepository(session, owner_id=alice.user_id)
        assert await repo.get(bob.id) is None
        assert (await repo.get(alice.id)).id == alice.id


async def test_anon_id_not_linked_to_user_id(client: AsyncClient, db):
    token = await register_candidate(client)
    anon_id = (await client.get("/api/v1/candidate/profile", headers=bearer(token))).json()[
        "anon_id"
    ]
    async with db.sessionmaker() as session:
        user_ids = {str(u) for u in (await session.execute(select(User.id))).scalars()}
    assert anon_id not in user_ids
