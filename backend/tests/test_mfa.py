"""2FA администраторов: обязательный второй шаг, код подключения, повтор кода, блокировка,
одноразовый шаг входа, сброс, короткая сессия."""

import time
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import totp
from app.core.errors import UnauthorizedError
from app.models import AuditLog
from app.repositories.users import UserRepository
from app.services.auth import AuthService
from app.services.mfa import reset_mfa
from tests.helpers import (
    PASSWORD,
    NewAdmin,
    admin_login,
    bearer,
    new_admin,
    register_candidate,
    unique_email,
)

LOGIN = "/api/v1/auth/login"
SETUP = "/api/v1/auth/2fa/setup"
VERIFY = "/api/v1/auth/2fa/verify"


async def challenge(client: AsyncClient, email: str) -> dict:
    return (await client.post(LOGIN, json={"email": email, "password": PASSWORD})).json()


async def setup(client: AsyncClient, admin: NewAdmin) -> tuple[str, str]:
    """Пароль -> настройка по коду подключения; возвращает (mfa_token, секрет)."""
    token = (await challenge(client, admin.email))["mfa_token"]
    r = await client.post(
        SETUP, json={"mfa_token": token, "enrollment_code": admin.enrollment_code}
    )
    assert r.status_code == 200, r.text
    assert r.json()["otpauth_uri"].startswith("otpauth://totp/IT%20Match:")
    return token, r.json()["secret"]


def current_code(secret: str, shift: int = 0) -> str:
    return totp.code_at(secret, int(time.time()) // totp.STEP_SECONDS + shift)


def wrong_code(secret: str) -> str:
    return "000000" if current_code(secret) != "000000" else "111111"


async def actions(db) -> list[str]:
    async with db.sessionmaker() as session:
        return list((await session.execute(select(AuditLog.action))).scalars().all())


async def test_admin_password_alone_gives_no_session(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    r = await client.post(LOGIN, json={"email": admin.email, "password": PASSWORD})
    body = r.json()
    assert body == {"mfa_required": True, "mfa_token": body["mfa_token"], "enrolled": False}
    assert "refresh_token" not in r.headers.get("set-cookie", "")
    # токен шага 2FA не работает как access-токен
    assert (
        await client.get("/api/v1/admin/companies", headers=bearer(body["mfa_token"]))
    ).status_code == 401


async def test_enrollment_requires_cli_code(client: AsyncClient, db, app):
    """Знать пароль недостаточно, чтобы привязать свой аутентификатор."""
    admin = await new_admin(db, app)
    token = (await challenge(client, admin.email))["mfa_token"]
    for code in ("wrong-enrollment-code", ""):
        r = await client.post(SETUP, json={"mfa_token": token, "enrollment_code": code})
        assert r.status_code in (401, 422)
    assert "auth.mfa_setup" not in await actions(db)


async def test_enrollment_then_regular_login(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    token, secret = await setup(client, admin)
    verified = await client.post(VERIFY, json={"mfa_token": token, "code": current_code(secret)})
    assert verified.status_code == 200
    access = verified.json()["access_token"]
    assert (await client.get("/api/v1/admin/companies", headers=bearer(access))).status_code == 200

    second = await challenge(client, admin.email)
    assert second["enrolled"] is True
    again = await client.post(
        SETUP, json={"mfa_token": second["mfa_token"], "enrollment_code": admin.enrollment_code}
    )
    assert again.status_code == 409  # код подключения одноразовый, секрет не перевыпустить
    nxt = await client.post(
        VERIFY, json={"mfa_token": second["mfa_token"], "code": current_code(secret, 1)}
    )
    assert nxt.status_code == 200
    assert {"auth.mfa_setup", "auth.mfa_enrolled"} <= set(await actions(db))


async def test_wrong_and_replayed_codes_rejected(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    token, secret = await setup(client, admin)
    bad = await client.post(VERIFY, json={"mfa_token": token, "code": wrong_code(secret)})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "unauthorized"
    code = current_code(secret)
    assert (await client.post(VERIFY, json={"mfa_token": token, "code": code})).status_code == 200
    fresh = (await challenge(client, admin.email))["mfa_token"]
    replay = await client.post(VERIFY, json={"mfa_token": fresh, "code": code})
    assert replay.status_code == 401
    assert "auth.mfa_failed" in await actions(db)


async def test_mfa_token_is_single_use(client: AsyncClient, db, app):
    """После входа тем же шагом новую сессию не получить даже со следующим кодом."""
    admin = await new_admin(db, app)
    token, secret = await setup(client, admin)
    ok = await client.post(VERIFY, json={"mfa_token": token, "code": current_code(secret)})
    assert ok.status_code == 200
    reuse = await client.post(VERIFY, json={"mfa_token": token, "code": current_code(secret, 1)})
    assert reuse.status_code == 401 and reuse.json()["error"]["code"] == "mfa_expired"


async def test_consecutive_failures_lock_the_step(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    token, secret = await setup(client, admin)
    for _ in range(5):
        r = await client.post(VERIFY, json={"mfa_token": token, "code": wrong_code(secret)})
        assert r.status_code == 401
    locked = await client.post(VERIFY, json={"mfa_token": token, "code": current_code(secret)})
    assert locked.status_code == 429  # даже верный код — только после паузы
    assert "auth.mfa_locked" in await actions(db)


async def test_garbage_or_access_token_is_not_mfa_token(client: AsyncClient):
    candidate = await register_candidate(client)
    for token in ("garbage-token-value", candidate):
        r = await client.post(VERIFY, json={"mfa_token": token, "code": "123456"})
        # отдельный код: клиент предлагает начать вход заново, а не ввести код ещё раз
        assert r.status_code == 401 and r.json()["error"]["code"] == "mfa_expired"


async def test_expired_mfa_token_reports_mfa_expired(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    claims = {"sub": str(admin.id), "stp": 0}
    expired = app.state.tokens._encode(claims, "mfa", timedelta(seconds=-1))
    r = await client.post(VERIFY, json={"mfa_token": expired, "code": "123456"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "mfa_expired"


async def test_mfa_attempts_limited_per_admin(client: AsyncClient, db, app):
    app.state.rate_limits["mfa"] = (2, 3600)
    admin = await new_admin(db, app)
    token, _ = await setup(client, admin)  # первая попытка из двух
    await client.post(VERIFY, json={"mfa_token": token, "code": "000001"})
    r = await client.post(VERIFY, json={"mfa_token": token, "code": "000001"})
    assert r.status_code == 429


async def test_admin_session_is_short_and_not_extended(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    token, secret = await setup(client, admin)
    r = await client.post(VERIFY, json={"mfa_token": token, "code": current_code(secret)})
    cookie = next(h for h in r.headers.get_list("set-cookie") if "refresh_token=" in h)
    assert "Max-Age=43200" in cookie or "Max-Age=4319" in cookie  # 12 часов
    refreshed = await client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("csrf_token")}
    )
    new_cookie = next(h for h in refreshed.headers.get_list("set-cookie") if "refresh_token=" in h)
    max_age = int(new_cookie.split("Max-Age=")[1].split(";")[0])
    assert max_age <= 43200  # ротация не продлевает сессию администратора


async def test_reset_mfa_requires_new_enrollment_and_revokes_sessions(client: AsyncClient, db, app):
    admin = await new_admin(db, app)
    await admin_login(client, admin.email, enrollment_code=admin.enrollment_code)
    stale_token = (await challenge(client, admin.email))["mfa_token"]
    async with db.sessionmaker() as session:
        code = await reset_mfa(session, admin.email)
    assert code != admin.enrollment_code
    assert (await challenge(client, admin.email))["enrolled"] is False
    r = await client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""}
    )
    assert r.status_code == 401
    # шаг входа, начатый до сброса, недействителен
    stale = await client.post(SETUP, json={"mfa_token": stale_token, "enrollment_code": code})
    assert stale.json()["error"]["code"] == "mfa_expired"
    assert await admin_login(client, admin.email, enrollment_code=code)


async def test_candidate_login_unchanged(client: AsyncClient):
    email = unique_email("cand")
    await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": email, "password": PASSWORD, "full_name": "Анна"},
    )
    body = (await client.post(LOGIN, json={"email": email, "password": PASSWORD})).json()
    assert body["access_token"] and "mfa_required" not in body


async def test_admin_session_without_2fa_cannot_be_refreshed(db, app):
    """Сессия, выданная администратору до включения 2FA, не продлевается."""
    admin = await new_admin(db, app)
    async with db.sessionmaker() as session:
        service = AuthService(session, app.state.tokens, app.state.cipher)
        user = await UserRepository(session).by_email(admin.email)
        pair = await service.complete_login(user)
        with pytest.raises(UnauthorizedError):
            await service.refresh(pair.refresh_token)
