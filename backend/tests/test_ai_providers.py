"""Подключение языковых моделей в интерфейсе: только суперадмин, ключ не утекает, SSRF закрыт."""

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import AiProvider, AuditLog
from tests.helpers import bearer, create_admin, register_candidate

URL = "/api/v1/admin/ai-providers"
KEY = "sk-test-" + "x" * 32


def provider(**overrides) -> dict:
    return {
        "name": "OpenAI GPT",
        "kind": "openai",
        "base_url": "https://llm.example.test/v1",
        "model": "gpt-test",
        "api_key": KEY,
        **overrides,
    }


async def test_only_superadmin_manages_models(client: AsyncClient, db, app):
    moderator = await create_admin(db, app, superadmin=False)
    candidate = await register_candidate(client)
    for token in (moderator, candidate):
        assert (await client.get(URL, headers=bearer(token))).status_code == 403
        assert (await client.post(URL, json=provider(), headers=bearer(token))).status_code == 403


async def test_key_is_encrypted_and_never_returned(client: AsyncClient, db, app):
    admin = await create_admin(db, app, superadmin=True)
    created = await client.post(URL, json=provider(), headers=bearer(admin))
    assert created.status_code == 201
    body = created.json()
    assert body["has_key"] is True and body["key_hint"] == "…xxxx" and body["is_active"] is False
    listed = (await client.get(URL, headers=bearer(admin))).text
    assert KEY not in listed and KEY not in created.text
    async with db.sessionmaker() as session:
        stored = (await session.execute(select(AiProvider))).scalar_one()
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert stored.api_key_enc and KEY not in stored.api_key_enc
    assert "admin.ai_provider_created" in actions


@pytest.mark.parametrize(
    "base_url",
    [
        "http://llm.example.test/v1",  # http без явного разрешения
        "https://db:5432",
        "https://mailpit:8025",
        "https://localhost:11434",
        "https://127.0.0.1/v1",
        "https://169.254.169.254/latest",  # метаданные облака
        "https://10.0.0.5/v1",  # частная сеть — только с AI_ALLOW_PRIVATE_NETWORK
        "https://[::1]/v1",
        "https://[fd00::1]/v1",
        "ftp://example.org",
    ],
)
async def test_unsafe_addresses_rejected(client: AsyncClient, db, app, base_url: str):
    admin = await create_admin(db, app, superadmin=True)
    r = await client.post(URL, json=provider(base_url=base_url), headers=bearer(admin))
    assert r.status_code == 422 and r.json()["error"]["code"] == "unsafe_url"


async def test_local_model_over_http_when_allowed(client: AsyncClient, db, app):
    app.state.settings.ai_allow_http = True
    try:
        admin = await create_admin(db, app, superadmin=True)
        local = provider(base_url="http://host.docker.internal:11434/v1", api_key=None)
        r = await client.post(URL, json=local, headers=bearer(admin))
        assert r.status_code == 201 and r.json()["has_key"] is False
    finally:
        app.state.settings.ai_allow_http = False


async def test_single_active_model_and_key_update(client: AsyncClient, db, app):
    admin = await create_admin(db, app, superadmin=True)
    headers = bearer(admin)
    first = (await client.post(URL, json=provider(), headers=headers)).json()
    second = (
        await client.post(URL, json=provider(name="Claude", kind="anthropic"), headers=headers)
    ).json()
    await client.post(f"{URL}/{first['id']}/activate", headers=headers)
    listed = (await client.post(f"{URL}/{second['id']}/activate", headers=headers)).json()
    assert {p["name"]: p["is_active"] for p in listed} == {
        "OpenAI GPT": False,
        "Claude": True,
    }
    kept = await client.patch(f"{URL}/{second['id']}", json={"model": "claude-x"}, headers=headers)
    assert kept.json()["has_key"] is True and kept.json()["model"] == "claude-x"
    cleared = await client.patch(f"{URL}/{second['id']}", json={"clear_key": True}, headers=headers)
    assert cleared.json()["has_key"] is False
    off = (await client.post(f"{URL}/deactivate", headers=headers)).json()
    assert not any(p["is_active"] for p in off)
    assert (await client.delete(f"{URL}/{first['id']}", headers=headers)).status_code == 204


async def test_connection_check(client: AsyncClient, db, app):
    admin = await create_admin(db, app, superadmin=True)
    created = (await client.post(URL, json=provider(), headers=bearer(admin))).json()
    ok_reply = {"choices": [{"message": {"content": '{"ok": true}'}}]}
    app.state.ai_transport = httpx.MockTransport(lambda _: httpx.Response(200, json=ok_reply))
    ok = (await client.post(f"{URL}/{created['id']}/test", headers=bearer(admin))).json()
    assert ok["ok"] is True and "ответила" in ok["message"]
    app.state.ai_transport = httpx.MockTransport(
        lambda _: httpx.Response(401, json={"error": "bad"})
    )
    bad = (await client.post(f"{URL}/{created['id']}/test", headers=bearer(admin))).json()
    assert bad == {
        "ok": False,
        "latency_ms": bad["latency_ms"],
        "message": "Ошибка 401: неверный ключ",
    }
    app.state.ai_transport = httpx.MockTransport(lambda _: httpx.Response(403, json={}))
    blocked = (await client.post(f"{URL}/{created['id']}/test", headers=bearer(admin))).json()
    assert "закрыт для страны сервера" in blocked["message"]


async def test_template_placeholder_in_model_is_rejected(client: AsyncClient, db, app):
    admin = await create_admin(db, app, superadmin=True)
    model = "gpt://<folder_id>/yandexgpt/latest"
    r = await client.post(URL, json=provider(model=model), headers=bearer(admin))
    assert r.status_code == 422


async def test_address_resolving_to_loopback_is_blocked_before_request(
    client: AsyncClient, db, app
):
    """Десятичная запись IP проходит проверку текста, но ведёт на 127.0.0.1 — запрос не уходит."""
    admin = await create_admin(db, app, superadmin=True)
    created = await client.post(
        URL, json=provider(base_url="https://2130706433/v1"), headers=bearer(admin)
    )
    assert created.status_code == 201
    sent: list[httpx.Request] = []
    app.state.ai_transport = httpx.MockTransport(lambda r: sent.append(r) or httpx.Response(200))
    result = (await client.post(f"{URL}/{created.json()['id']}/test", headers=bearer(admin))).json()
    assert result["ok"] is False and "внутренний сервис" in result["message"]
    assert sent == []


async def test_private_network_only_when_allowed(client: AsyncClient, db, app):
    app.state.settings.ai_allow_private_network = True
    try:
        admin = await create_admin(db, app, superadmin=True)
        r = await client.post(
            URL, json=provider(base_url="https://10.0.0.5/v1"), headers=bearer(admin)
        )
        assert r.status_code == 201
        loopback = await client.post(
            URL, json=provider(base_url="https://127.0.0.1/v1"), headers=bearer(admin)
        )
        assert loopback.status_code == 422  # loopback закрыт всегда
    finally:
        app.state.settings.ai_allow_private_network = False
