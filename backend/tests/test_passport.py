"""Паспорт навыков: выпуск, подпись Ed25519, публичная проверка, отзыв, приватность имени."""

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from httpx import AsyncClient
from sqlalchemy import update

from app.core.signing import canonical_json
from app.db.session import set_rls_context
from app.models import Passport
from tests.fake_fsp import CODE
from tests.helpers import bearer, register_candidate

PASSPORT = "/api/v1/candidate/passport"


async def issue(client: AsyncClient, token: str, show_name: bool = False) -> dict:
    r = await client.post(PASSPORT, json={"show_name": show_name}, headers=bearer(token))
    assert r.status_code == 201, r.text
    return r.json()


async def linked_candidate(client: AsyncClient) -> str:
    token = await register_candidate(client, name="Анна Смирнова")
    await client.post(
        "/api/v1/candidate/fsp/link", json={"athlete_id": "FSP-1"}, headers=bearer(token)
    )
    await client.post("/api/v1/candidate/fsp/confirm", json={"code": CODE}, headers=bearer(token))
    return token


async def test_issue_and_verify_publicly(client: AsyncClient):
    token = await linked_candidate(client)
    passport = await issue(client, token)
    r = await client.get(f"/api/v1/public/passport/{passport['id']}")  # без токена
    body = r.json()
    assert r.status_code == 200 and body["valid"] is True
    assert body["payload"]["verification_tier"] == "verified_fsp"
    assert body["payload"]["categories"] and body["payload"]["fsp"]["achievements"]


async def test_signature_verifiable_with_public_key(client: AsyncClient):
    """Проверка без доверия серверу: подпись сверяется публичным ключом Ed25519."""
    passport = await issue(client, await linked_candidate(client))
    key = (await client.get("/api/v1/public/passport-key")).json()
    public = Ed25519PublicKey.from_public_bytes(base64.b64decode(key["public_key"]))
    public.verify(base64.b64decode(passport["signature"]), canonical_json(passport["payload"]))
    assert key["key_id"] == passport["key_id"]


async def test_name_hidden_by_default(client: AsyncClient):
    token = await linked_candidate(client)
    hidden = await issue(client, token)
    assert hidden["payload"]["holder"]["name"] is None
    assert hidden["payload"]["fsp"]["athlete_id"] is None
    shown = await issue(client, token, show_name=True)
    # имя подтверждено ФСП, а не взято из профиля
    assert shown["payload"]["holder"] == {"name": "Анна", "source": "fsp"}
    assert shown["payload"]["fsp"]["athlete_id"] == "FSP-1"


async def test_new_passport_revokes_previous(client: AsyncClient):
    token = await linked_candidate(client)
    first = await issue(client, token)
    second = await issue(client, token)
    old = (await client.get(f"/api/v1/public/passport/{first['id']}")).json()
    assert old["valid"] is False and old["revoked_at"] and old["status"] == "revoked"
    # по отозванному паспорту данные не раскрываются (отзыв согласия)
    assert old["payload"] is None and old["signature"] is None
    active = (await client.get(PASSPORT, headers=bearer(token))).json()
    assert active["id"] == second["id"]


async def test_revoke(client: AsyncClient):
    token = await linked_candidate(client)
    passport = await issue(client, token)
    assert (await client.delete(PASSPORT, headers=bearer(token))).status_code == 204
    assert (await client.get(PASSPORT, headers=bearer(token))).json() is None
    assert (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()["valid"] is False


async def test_tampered_payload_is_invalid(client: AsyncClient, db):
    passport = await issue(client, await linked_candidate(client))
    forged = {**passport["payload"], "grade": "lead"}
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(update(Passport).values(payload=forged))
        await session.commit()
    body = (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()
    assert body["valid"] is False


async def test_unknown_passport_404(client: AsyncClient):
    r = await client.get("/api/v1/public/passport/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_passport_without_fsp_is_self_declared(client: AsyncClient):
    passport = await issue(client, await register_candidate(client))
    assert passport["payload"]["verification_tier"] == "self_declared"
    assert passport["payload"]["fsp"]["achievements"] == []


async def test_unlinking_fsp_revokes_passport(client: AsyncClient):
    token = await linked_candidate(client)
    passport = await issue(client, token)
    assert (await client.delete("/api/v1/candidate/fsp", headers=bearer(token))).status_code == 204
    body = (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()
    assert body["valid"] is False and body["revoked_at"]


async def test_anonymous_passport_generalizes_achievements(client: AsyncClient):
    passport = await issue(client, await linked_candidate(client))
    (achievement,) = passport["payload"]["fsp"]["achievements"]
    assert "Соревнование" not in achievement["summary"]  # без названия соревнования
    assert achievement["summary"].startswith("призёр — всероссийский уровень")


async def test_self_declared_name_is_marked(client: AsyncClient):
    token = await register_candidate(client, name="Без ФСП")
    passport = await issue(client, token, show_name=True)
    assert passport["payload"]["holder"] == {"name": "Без ФСП", "source": "self"}


async def test_passport_has_expiry_and_expired_is_invalid(client: AsyncClient, db):
    passport = await issue(client, await linked_candidate(client))
    assert passport["payload"]["expires_at"] > passport["payload"]["issued_at"]
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        expired = {**passport["payload"], "expires_at": "2020-01-01T00:00:00+00:00"}
        await session.execute(update(Passport).values(payload=expired))
        await session.commit()
    body = (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()
    # подпись не совпадёт (payload изменён) — проверяем, что паспорт недействителен
    assert body["valid"] is False and body["status"] in {"expired", "bad_signature"}


async def test_unknown_key_reported(client: AsyncClient, db):
    passport = await issue(client, await linked_candidate(client))
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(update(Passport).values(key_id="old-key"))
        await session.commit()
    body = (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()
    assert body["status"] == "unknown_key" and body["valid"] is False


async def test_public_check_is_not_cached(client: AsyncClient):
    passport = await issue(client, await linked_candidate(client))
    r = await client.get(f"/api/v1/public/passport/{passport['id']}")
    assert r.headers["cache-control"] == "no-store" and "noindex" in r.headers["x-robots-tag"]


async def test_changed_fsp_results_revoke_passport(client: AsyncClient, fsp):
    token = await linked_candidate(client)
    passport = await issue(client, token)
    athlete, _ = fsp.athletes["FSP-1"]
    fsp.athletes["FSP-1"] = (athlete, [])  # результат аннулирован в ФСП
    await client.post("/api/v1/candidate/fsp/sync", headers=bearer(token))
    body = (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()
    assert body["status"] == "revoked"


async def test_unchanged_sync_keeps_passport(client: AsyncClient):
    token = await linked_candidate(client)
    passport = await issue(client, token)
    await client.post("/api/v1/candidate/fsp/sync", headers=bearer(token))
    assert (await client.get(f"/api/v1/public/passport/{passport['id']}")).json()["valid"] is True


async def test_demo_stand_is_marked_in_passport(client: AsyncClient, app):
    app.state.settings = app.state.settings.model_copy(update={"fsp_demo_codes": True})
    passport = await issue(client, await register_candidate(client))
    assert passport["payload"]["demo"] is True and "демо" in passport["payload"]["issuer"]
