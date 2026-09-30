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
    assert shown["payload"]["holder"]["name"] == "Анна Смирнова"


async def test_new_passport_revokes_previous(client: AsyncClient):
    token = await linked_candidate(client)
    first = await issue(client, token)
    second = await issue(client, token)
    old = (await client.get(f"/api/v1/public/passport/{first['id']}")).json()
    assert old["valid"] is False and old["revoked_at"]
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
