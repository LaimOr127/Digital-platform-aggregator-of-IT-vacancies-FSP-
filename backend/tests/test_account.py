"""Регистрация и операции по почте: подтверждение адреса, повтор письма, сброс пароля.
Главное свойство — ответы не выдают, зарегистрирован ли адрес."""

from httpx import AsyncClient
from sqlalchemy import select

from app.models import AuditLog, User
from tests.helpers import (
    PASSWORD,
    bearer,
    login,
    mailed_token,
    outbox_for,
    register_candidate,
    unique_email,
)

AUTH = "/api/v1/auth"
NEW_PASSWORD = f"New-{PASSWORD}"


async def register(client: AsyncClient, email: str, role: str = "candidate"):
    extra = {"full_name": "Анна"} if role == "candidate" else {"company_name": "ООО Тест"}
    return await client.post(
        f"{AUTH}/register/{role}", json={"email": email, "password": PASSWORD, **extra}
    )


async def verify(client: AsyncClient, email: str) -> None:
    token = await mailed_token(client, email, "verify_email")
    assert (await client.post(f"{AUTH}/verify-email", json={"token": token})).status_code == 204


async def kinds(client: AsyncClient, email: str) -> list[str]:
    return [kind for kind, _ in await outbox_for(client, email)]


async def test_registration_sends_link_and_login_waits_for_it(client: AsyncClient):
    email = unique_email("new")
    r = await register(client, email)
    assert r.status_code == 202 and "access_token" not in r.json()
    assert "refresh_token" not in r.headers.get("set-cookie", "")
    blocked = await client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "email_not_verified"
    await verify(client, email)
    assert await login(client, email)


async def test_taken_email_gets_identical_response(client: AsyncClient):
    """Повторная регистрация неотличима от новой; владельцу адреса уходит письмо."""
    email = unique_email("taken")
    first = await register(client, email)
    await verify(client, email)
    again = await register(client, email.upper(), role="employer")
    assert again.status_code == first.status_code == 202
    assert again.json() == first.json()
    assert await kinds(client, email) == ["account_exists", "verify_email"]


async def test_unverified_taken_email_gets_new_link(client: AsyncClient):
    email = unique_email("lost")
    await register(client, email)
    first_link = await mailed_token(client, email, "verify_email")
    await register(client, email)
    second_link = await mailed_token(client, email, "verify_email")
    assert first_link != second_link
    # прежняя ссылка погашена: действует только последняя
    old = await client.post(f"{AUTH}/verify-email", json={"token": first_link})
    assert old.status_code == 400 and old.json()["error"]["code"] == "invalid_link"
    assert (
        await client.post(f"{AUTH}/verify-email", json={"token": second_link})
    ).status_code == 204


async def test_employer_company_not_created_for_taken_email(client: AsyncClient, db):
    email = unique_email("emp")
    await register(client, email, role="employer")
    await register(client, email, role="employer")
    async with db.sessionmaker() as session:
        users = (await session.execute(select(User).where(User.email == email))).scalars().all()
    assert len(users) == 1


async def test_verification_link_is_single_use(client: AsyncClient):
    email = unique_email("once")
    await register(client, email)
    token = await mailed_token(client, email, "verify_email")
    assert (await client.post(f"{AUTH}/verify-email", json={"token": token})).status_code == 204
    again = await client.post(f"{AUTH}/verify-email", json={"token": token})
    assert again.status_code == 400


async def test_garbage_link_rejected(client: AsyncClient):
    r = await client.post(f"{AUTH}/verify-email", json={"token": "x" * 43})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_link"


async def test_resend_is_silent_for_unknown_and_verified(client: AsyncClient):
    email = unique_email("resend")
    await register(client, email)
    await verify(client, email)
    for address in (email, unique_email("ghost")):
        r = await client.post(f"{AUTH}/verify-email/resend", json={"email": address})
        assert r.status_code == 202
    assert await kinds(client, email) == ["verify_email"]  # подтверждённому — ничего


async def test_resend_sends_new_link_to_unverified(client: AsyncClient):
    email = unique_email("pending")
    await register(client, email)
    await client.post(f"{AUTH}/verify-email/resend", json={"email": email})
    assert await kinds(client, email) == ["verify_email", "verify_email"]
    await verify(client, email)


async def test_password_reset_flow(client: AsyncClient, db):
    token = await register_candidate(client)
    email = (await client.get(f"{AUTH}/me", headers=bearer(token))).json()["email"]
    unknown = await client.post(f"{AUTH}/password/forgot", json={"email": unique_email("x")})
    known = await client.post(f"{AUTH}/password/forgot", json={"email": email})
    assert unknown.status_code == known.status_code == 202 and unknown.json() == known.json()

    link = await mailed_token(client, email, "password_reset")
    reset = await client.post(
        f"{AUTH}/password/reset", json={"token": link, "password": NEW_PASSWORD}
    )
    assert reset.status_code == 204
    # прежние сессии завершены, старый пароль не подходит, новый — подходит
    refresh = await client.post(
        f"{AUTH}/refresh", headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""}
    )
    assert refresh.status_code == 401
    old = await client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    assert old.status_code == 401
    assert await login(client, email, NEW_PASSWORD)
    reused = await client.post(
        f"{AUTH}/password/reset", json={"token": link, "password": NEW_PASSWORD}
    )
    assert reused.status_code == 400
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "auth.password_reset" in actions


async def test_reset_link_also_confirms_email(client: AsyncClient):
    email = unique_email("unconfirmed")
    await register(client, email)
    await client.post(f"{AUTH}/password/forgot", json={"email": email})
    link = await mailed_token(client, email, "password_reset")
    await client.post(f"{AUTH}/password/reset", json={"token": link, "password": NEW_PASSWORD})
    assert await login(client, email, NEW_PASSWORD)


async def test_reset_rejects_weak_password(client: AsyncClient):
    r = await client.post(f"{AUTH}/password/reset", json={"token": "t" * 43, "password": "1234"})
    assert r.status_code == 422


async def test_blocked_user_gets_no_links(client: AsyncClient, db):
    email = unique_email("blocked")
    await register(client, email)
    async with db.sessionmaker() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.is_active = False
        await session.commit()
    await client.post(f"{AUTH}/password/forgot", json={"email": email})
    await client.post(f"{AUTH}/verify-email/resend", json={"email": email})
    assert await kinds(client, email) == ["verify_email"]


async def test_mail_to_one_address_is_limited(client: AsyncClient, app):
    app.state.rate_limits["email"] = (2, 3600)
    email = unique_email("bomb")
    codes = [
        (await client.post(f"{AUTH}/password/forgot", json={"email": email})).status_code
        for _ in range(3)
    ]
    assert codes == [202, 202, 429]
    # лимит по адресу: другой адрес не затронут
    other = await client.post(f"{AUTH}/password/forgot", json={"email": unique_email("ok")})
    assert other.status_code == 202
