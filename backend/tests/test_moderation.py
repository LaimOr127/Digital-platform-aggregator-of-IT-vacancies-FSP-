"""Модерация: вакансии, пользователи, журнал аудита; права модератора и суперадмина."""

from httpx import AsyncClient

from app.services.auth import AuthService
from tests.helpers import (
    PASSWORD,
    admin_login,
    approve_company,
    bearer,
    company_id,
    create_admin,
    create_vacancy,
    register_candidate,
    register_employer,
    unique_email,
)

ADMIN = "/api/v1/admin"


async def published_vacancy(client: AsyncClient, admin: str) -> tuple[str, dict]:
    employer = await register_employer(client)
    await approve_company(client, admin, await company_id(client, employer))
    vacancy = await create_vacancy(client, employer)
    await client.post(
        f"/api/v1/employer/vacancies/{vacancy['id']}/publish", headers=bearer(employer)
    )
    return employer, vacancy


async def test_block_and_unblock_vacancy(client: AsyncClient, db, app):
    admin = await create_admin(db, app)
    employer, vacancy = await published_vacancy(client, admin)
    listed = (
        await client.get(f"{ADMIN}/vacancies", params={"status": "active"}, headers=bearer(admin))
    ).json()
    assert [v["id"] for v in listed["items"]] == [vacancy["id"]] and listed["items"][0][
        "company_name"
    ]

    url = f"{ADMIN}/vacancies/{vacancy['id']}/moderation"
    blocked = await client.post(
        url, json={"action": "block", "reason": "нет вилки в описании"}, headers=bearer(admin)
    )
    assert blocked.json()["status"] == "blocked"
    own = await client.get(f"/api/v1/employer/vacancies/{vacancy['id']}", headers=bearer(employer))
    assert own.json()["status"] == "blocked"

    unblocked = await client.post(url, json={"action": "unblock"}, headers=bearer(admin))
    assert unblocked.json()["status"] == "draft"  # компания перепроверит и опубликует заново
    again = await client.post(url, json={"action": "unblock"}, headers=bearer(admin))
    assert again.status_code == 409


async def test_block_user_kills_sessions(client: AsyncClient, db, app):
    admin = await create_admin(db, app)
    candidate = await register_candidate(client)
    me = (await client.get("/api/v1/auth/me", headers=bearer(candidate))).json()
    found = (
        await client.get(f"{ADMIN}/users", params={"q": me["email"][:8]}, headers=bearer(admin))
    ).json()
    assert me["id"] in [u["id"] for u in found["items"]]

    r = await client.post(
        f"{ADMIN}/users/{me['id']}/moderation",
        json={"action": "block", "reason": "спам"},
        headers=bearer(admin),
    )
    assert r.json()["is_active"] is False
    assert (await client.get("/api/v1/auth/me", headers=bearer(candidate))).status_code == 401
    login = await client.post(
        "/api/v1/auth/login", json={"email": me["email"], "password": PASSWORD}
    )
    assert login.status_code == 401

    await client.post(
        f"{ADMIN}/users/{me['id']}/moderation", json={"action": "unblock"}, headers=bearer(admin)
    )
    assert (
        await client.post("/api/v1/auth/login", json={"email": me["email"], "password": PASSWORD})
    ).status_code == 200


async def test_search_is_literal_not_a_pattern(client: AsyncClient, db, app):
    admin = await create_admin(db, app)
    await register_candidate(client)
    r = await client.get(f"{ADMIN}/users", params={"q": "%"}, headers=bearer(admin))
    assert r.json()["items"] == []  # «%» ищется как символ, а не «всё подряд»


async def test_moderator_cannot_block_admins_or_self(client: AsyncClient, db, app):
    moderator = await create_admin(db, app, superadmin=False)
    other_email = unique_email("admin")
    async with db.sessionmaker() as session:
        other = await AuthService(session, app.state.tokens, app.state.cipher).create_admin(
            other_email, PASSWORD, False
        )
    me = (await client.get("/api/v1/auth/me", headers=bearer(moderator))).json()
    assert (
        await client.post(
            f"{ADMIN}/users/{other.id}/moderation",
            json={"action": "block"},
            headers=bearer(moderator),
        )
    ).status_code == 403
    assert (
        await client.post(
            f"{ADMIN}/users/{me['id']}/moderation",
            json={"action": "block"},
            headers=bearer(moderator),
        )
    ).status_code == 403


async def test_superadmin_can_block_moderator(client: AsyncClient, db, app):
    superadmin = await create_admin(db, app, superadmin=True)
    email = unique_email("admin")
    async with db.sessionmaker() as session:
        moderator = await AuthService(session, app.state.tokens, app.state.cipher).create_admin(
            email, PASSWORD, False
        )
    r = await client.post(
        f"{ADMIN}/users/{moderator.id}/moderation",
        json={"action": "block"},
        headers=bearer(superadmin),
    )
    assert r.status_code == 200 and r.json()["is_active"] is False


async def test_audit_log_lists_actions_with_actor(client: AsyncClient, db, app):
    admin = await create_admin(db, app)
    _, vacancy = await published_vacancy(client, admin)
    await client.post(
        f"{ADMIN}/vacancies/{vacancy['id']}/moderation",
        json={"action": "block", "reason": "x"},
        headers=bearer(admin),
    )
    entries = (
        await client.get(f"{ADMIN}/audit", params={"action": "admin."}, headers=bearer(admin))
    ).json()["items"]
    actions = [e["action"] for e in entries]
    assert "admin.vacancy_block" in actions and "admin.company_status" in actions
    blocked = next(e for e in entries if e["action"] == "admin.vacancy_block")
    assert blocked["actor_email"].startswith("admin-") and blocked["meta"]["reason"] == "x"


async def test_admin_login_helper_reuses_secret(client: AsyncClient, db, app):
    """Повторный вход администратора с уже настроенной 2FA."""
    email = unique_email("admin")
    async with db.sessionmaker() as session:
        await AuthService(session, app.state.tokens, app.state.cipher).create_admin(
            email, PASSWORD, False
        )
    token = await admin_login(client, email)
    assert (await client.get(f"{ADMIN}/companies", headers=bearer(token))).status_code == 200
