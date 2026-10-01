"""Аутентификация: вход, ротация refresh, CSRF, выход, rate limit.
Регистрация и операции по почте — в test_account.py."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_token
from app.models import AuditLog, User
from app.repositories.users import RefreshTokenRepository
from tests.helpers import PASSWORD, bearer, login, mailed_token, register_candidate, unique_email

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"


async def _signup(client: AsyncClient) -> tuple[str, str]:
    """Зарегистрированный и вошедший кандидат: (email, access-токен); cookie — у клиента."""
    email = unique_email("user")
    await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": email, "password": PASSWORD, "full_name": "Анна"},
    )
    token = await mailed_token(client, email, "verify_email")
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    return email, await login(client, email)


def _csrf(client: AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}


async def test_login_sets_secure_cookies(client: AsyncClient):
    email, _ = await _signup(client)
    r = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer" and r.json()["expires_in"] == 900
    refresh_cookie = next(h for h in r.headers.get_list("set-cookie") if "refresh_token=" in h)
    assert "HttpOnly" in refresh_cookie and "SameSite=strict" in refresh_cookie
    assert "Path=/api/v1/auth" in refresh_cookie


async def test_me_returns_current_user(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.get("/api/v1/auth/me", headers=bearer(token))
    assert r.status_code == 200
    assert r.json()["role"] == "candidate" and r.json()["company_id"] is None


@pytest.mark.parametrize("password", ["short1", "aaaaaaaaaaaa", "123456789012", "abababababab1"])
async def test_weak_password_rejected(client: AsyncClient, password: str):
    r = await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": unique_email("w"), "password": password, "full_name": "Анна"},
    )
    assert r.status_code == 422


async def test_password_is_not_stored_in_plaintext(client: AsyncClient, db):
    email, _ = await _signup(client)
    async with db.sessionmaker() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
    assert PASSWORD not in user.password_hash and user.password_hash.startswith("$argon2id$")


async def test_login_ok_and_audited(client: AsyncClient, db):
    email, _ = await _signup(client)
    r = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    assert r.status_code == 200 and r.json()["access_token"]
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "auth.login" in actions


async def test_wrong_password_and_unknown_email_look_identical(client: AsyncClient):
    email, _ = await _signup(client)
    wrong = await client.post(LOGIN, json={"email": email, "password": "Wrong-pass-42"})
    unknown = await client.post(
        LOGIN, json={"email": unique_email("nobody"), "password": "Wrong-pass-42"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_refresh_rotates_token(client: AsyncClient):
    await _signup(client)
    old_refresh = client.cookies.get("refresh_token")
    r = await client.post(REFRESH, headers=_csrf(client))
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.cookies.get("refresh_token") != old_refresh


async def test_refresh_requires_csrf_header(client: AsyncClient):
    await _signup(client)
    r = await client.post(REFRESH)
    assert r.status_code == 403
    r = await client.post(REFRESH, headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403


async def test_refresh_reuse_revokes_whole_family(client: AsyncClient):
    await _signup(client)
    stolen = client.cookies.get("refresh_token")
    assert (await client.post(REFRESH, headers=_csrf(client))).status_code == 200
    fresh = client.cookies.get("refresh_token")

    client.cookies.set("refresh_token", stolen, path="/api/v1/auth")
    assert (await client.post(REFRESH, headers=_csrf(client))).status_code == 401

    client.cookies.set("refresh_token", fresh, path="/api/v1/auth")
    assert (await client.post(REFRESH, headers=_csrf(client))).status_code == 401


async def test_logout_revokes_refresh(client: AsyncClient):
    await _signup(client)
    token = client.cookies.get("refresh_token")
    headers = _csrf(client)
    assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 204
    client.cookies.set("refresh_token", token, path="/api/v1/auth")
    client.cookies.set("csrf_token", headers["X-CSRF-Token"])
    assert (await client.post(REFRESH, headers=headers)).status_code == 401


async def test_inactive_user_cannot_login_or_use_token(client: AsyncClient, db):
    email, token = await _signup(client)
    async with db.sessionmaker() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.is_active = False
        await session.commit()
    assert (
        await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    ).status_code == 401
    me = await client.get("/api/v1/auth/me", headers=bearer(token))
    assert me.status_code == 401


@pytest.mark.parametrize("header", ["Bearer garbage", "Basic abc", ""])
async def test_bad_authorization_header(client: AsyncClient, header: str):
    r = await client.get("/api/v1/auth/me", headers={"Authorization": header})
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


async def test_login_rate_limited_per_ip(client: AsyncClient, app):
    app.state.rate_limits["auth"] = (10, 60)
    codes = [
        (
            await client.post(
                LOGIN, json={"email": unique_email("rl"), "password": "Wrong-pass-42"}
            )
        ).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


async def test_login_rate_limited_per_account(client: AsyncClient, app):
    """Перебор пароля одного аккаунта упирается в лимит даже с разных IP."""
    app.state.rate_limits["auth"] = (1000, 60)  # имитация пула IP: лимит по IP не мешает
    body = {"email": unique_email("victim"), "password": "Wrong-pass-42"}
    codes = [(await client.post(LOGIN, json=body)).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


async def test_refresh_has_own_rate_limit(client: AsyncClient, app):
    await _signup(client)
    app.state.rate_limits["auth"] = (0, 60)  # вход исчерпан, refresh работает
    assert (await client.post(REFRESH, headers=_csrf(client))).status_code == 200


async def test_concurrent_refresh_only_one_wins(client: AsyncClient, db):
    """Гонка: два запроса с одним токеном — «погасить» его может только один."""
    await _signup(client)
    token_hash = hash_token(client.cookies.get("refresh_token"))
    async with db.sessionmaker() as session:
        repo = RefreshTokenRepository(session)
        stored = await repo.by_hash(token_hash)
        first, second = await repo.consume(stored.id), await repo.consume(stored.id)
        await session.commit()
    assert (first, second) == (True, False)
