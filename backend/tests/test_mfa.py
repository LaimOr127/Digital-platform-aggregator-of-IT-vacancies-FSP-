"""2FA администраторов: обязательный второй шаг, настройка, повтор кода, сброс, короткая сессия."""

import time

from httpx import AsyncClient
from sqlalchemy import select

from app.core import totp
from app.models import AuditLog
from app.services.auth import AuthService
from app.services.mfa import reset_mfa
from tests.helpers import PASSWORD, admin_login, bearer, register_candidate, unique_email

LOGIN = "/api/v1/auth/login"


async def new_admin(db, app) -> str:
    email = unique_email("admin")
    async with db.sessionmaker() as session:
        await AuthService(session, app.state.tokens, app.state.cipher).create_admin(
            email, PASSWORD, True
        )
    return email


async def challenge(client: AsyncClient, email: str) -> dict:
    return (await client.post(LOGIN, json={"email": email, "password": PASSWORD})).json()


def current_code(secret: str, shift: int = 0) -> str:
    return totp.code_at(secret, int(time.time()) // totp.STEP_SECONDS + shift)


async def test_admin_password_alone_gives_no_session(client: AsyncClient, db, app):
    email = await new_admin(db, app)
    r = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    body = r.json()
    assert body == {"mfa_required": True, "mfa_token": body["mfa_token"], "enrolled": False}
    assert "refresh_token" not in r.headers.get("set-cookie", "")
    # токен шага 2FA не работает как access-токен
    assert (
        await client.get("/api/v1/admin/companies", headers=bearer(body["mfa_token"]))
    ).status_code == 401


async def test_enrollment_then_regular_login(client: AsyncClient, db, app):
    email = await new_admin(db, app)
    first = await challenge(client, email)
    setup = (
        await client.post("/api/v1/auth/2fa/setup", json={"mfa_token": first["mfa_token"]})
    ).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/IT%20Match:")
    verified = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"mfa_token": first["mfa_token"], "code": current_code(setup["secret"])},
    )
    assert verified.status_code == 200 and verified.json()["access_token"]
    assert (
        await client.get("/api/v1/admin/companies", headers=bearer(verified.json()["access_token"]))
    ).status_code == 200

    second = await challenge(client, email)
    assert second["enrolled"] is True
    again = await client.post("/api/v1/auth/2fa/setup", json={"mfa_token": second["mfa_token"]})
    assert again.status_code == 409  # секрет нельзя перевыпустить без сброса
    nxt = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"mfa_token": second["mfa_token"], "code": current_code(setup["secret"], 1)},
    )
    assert nxt.status_code == 200


async def test_wrong_and_replayed_codes_rejected(client: AsyncClient, db, app):
    email = await new_admin(db, app)
    first = await challenge(client, email)
    secret = (
        await client.post("/api/v1/auth/2fa/setup", json={"mfa_token": first["mfa_token"]})
    ).json()["secret"]
    wrong = "000000" if current_code(secret) != "000000" else "111111"
    bad = await client.post(
        "/api/v1/auth/2fa/verify", json={"mfa_token": first["mfa_token"], "code": wrong}
    )
    assert bad.status_code == 401
    code = current_code(secret)
    ok = await client.post(
        "/api/v1/auth/2fa/verify", json={"mfa_token": first["mfa_token"], "code": code}
    )
    assert ok.status_code == 200
    replay = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"mfa_token": (await challenge(client, email))["mfa_token"], "code": code},
    )
    assert replay.status_code == 401
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "auth.mfa_failed" in actions and "auth.mfa_enrolled" in actions


async def test_garbage_or_access_token_is_not_mfa_token(client: AsyncClient):
    candidate = await register_candidate(client)
    for token in ("garbage-token-value", candidate):
        r = await client.post("/api/v1/auth/2fa/setup", json={"mfa_token": token})
        assert r.status_code == 401


async def test_mfa_attempts_limited_per_admin(client: AsyncClient, db, app):
    app.state.rate_limits["mfa"] = (2, 3600)
    email = await new_admin(db, app)
    token = (await challenge(client, email))["mfa_token"]
    await client.post("/api/v1/auth/2fa/setup", json={"mfa_token": token})
    codes = [
        (
            await client.post(
                "/api/v1/auth/2fa/verify", json={"mfa_token": token, "code": "000001"}
            )
        ).status_code
        for _ in range(2)
    ]
    assert codes[-1] == 429


async def test_admin_session_is_short_and_not_extended(client: AsyncClient, db, app):
    email = await new_admin(db, app)
    first = await challenge(client, email)
    secret = (
        await client.post("/api/v1/auth/2fa/setup", json={"mfa_token": first["mfa_token"]})
    ).json()["secret"]
    r = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"mfa_token": first["mfa_token"], "code": current_code(secret)},
    )
    cookie = next(h for h in r.headers.get_list("set-cookie") if "refresh_token=" in h)
    assert "Max-Age=43200" in cookie or "Max-Age=4319" in cookie  # 12 часов
    refreshed = await client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("csrf_token")}
    )
    new_cookie = next(h for h in refreshed.headers.get_list("set-cookie") if "refresh_token=" in h)
    max_age = int(new_cookie.split("Max-Age=")[1].split(";")[0])
    assert max_age <= 43200  # ротация не продлевает сессию администратора


async def test_reset_mfa_requires_new_enrollment_and_revokes_sessions(client: AsyncClient, db, app):
    email = await new_admin(db, app)
    await admin_login(client, email)
    async with db.sessionmaker() as session:
        await reset_mfa(session, email)
    assert (await challenge(client, email))["enrolled"] is False
    r = await client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""}
    )
    assert r.status_code == 401


async def test_candidate_login_unchanged(client: AsyncClient):
    email = unique_email("cand")
    await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": email, "password": PASSWORD, "full_name": "Анна"},
    )
    body = (await client.post(LOGIN, json={"email": email, "password": PASSWORD})).json()
    assert body["access_token"] and "mfa_required" not in body
