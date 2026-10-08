"""Привязка ФСП: код подтверждения, синхронизация, категории, уровень подтверждения."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.core.errors import ServiceUnavailableError
from app.db.session import set_rls_context
from app.models import FspVerification
from tests.fake_fsp import CODE, result
from tests.helpers import bearer, link_fsp, register_candidate, register_employer

FSP = "/api/v1/candidate/fsp"


link = link_fsp


async def test_status_before_linking(client: AsyncClient):
    token = await register_candidate(client)
    body = (await client.get(FSP, headers=bearer(token))).json()
    assert body["linked"] is False and body["verification_tier"] == "self_declared"
    assert body["demo_mode"] is False
    assert body["achievements"] == [] and body["categories"] == []


async def test_link_flow_creates_achievements_and_categories(client: AsyncClient):
    token = await register_candidate(client)
    start = await client.post(f"{FSP}/link", json={"athlete_id": "fsp-1"}, headers=bearer(token))
    assert start.json()["email_masked"] == "a***@example.org"
    pending = (await client.get(FSP, headers=bearer(token))).json()
    assert pending["pending_athlete_id"] == "FSP-1"

    body = (await client.post(f"{FSP}/confirm", json={"code": CODE}, headers=bearer(token))).json()
    assert body["linked"] and body["athlete_id"] == "FSP-1" and body["rank"] == "КМС"
    assert body["verification_tier"] == "verified_fsp"
    assert [c["slug"] for c in body["categories"]] == ["product-advanced"]  # один приз + КМС
    assert body["achievements"][0]["discipline_title"] == "Продуктовое программирование"
    profile = (await client.get("/api/v1/candidate/profile", headers=bearer(token))).json()
    assert profile["verification_tier"] == "verified_fsp"


async def test_demo_code_hidden_unless_enabled(client: AsyncClient, app):
    token = await register_candidate(client)
    r = await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(token))
    assert r.json()["demo_code"] is None
    app.state.settings = app.state.settings.model_copy(update={"fsp_demo_codes": True})
    r = await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(token))
    assert r.json()["demo_code"] == CODE


async def test_wrong_code_rejected(client: AsyncClient):
    token = await register_candidate(client)
    await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(token))
    r = await client.post(f"{FSP}/confirm", json={"code": "000000"}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error"]["code"] == "fsp_verification_failed"
    assert (await client.get(FSP, headers=bearer(token))).json()["linked"] is False


async def test_confirm_without_request(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.post(f"{FSP}/confirm", json={"code": CODE}, headers=bearer(token))
    assert r.status_code == 400


async def test_unknown_athlete_404(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.post(f"{FSP}/link", json={"athlete_id": "FSP-404"}, headers=bearer(token))
    assert r.status_code == 404


async def test_athlete_cannot_be_linked_twice(client: AsyncClient):
    """Чужие достижения не присвоить: аккаунт ФСП принадлежит одному профилю."""
    await link(client, await register_candidate(client))
    thief = await register_candidate(client)
    await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(thief))
    r = await client.post(f"{FSP}/confirm", json={"code": CODE}, headers=bearer(thief))
    assert r.status_code == 409
    assert r.json()["error"]["message"] == "этот аккаунт ФСП уже привязан к другому профилю"
    assert (await client.get(FSP, headers=bearer(thief))).json()["linked"] is False


async def test_relink_requires_unlink(client: AsyncClient):
    token = await register_candidate(client)
    await link(client, token)
    r = await client.post(f"{FSP}/link", json={"athlete_id": "FSP-2"}, headers=bearer(token))
    assert r.status_code == 409


async def test_sync_picks_up_new_results(client: AsyncClient, fsp):
    token = await register_candidate(client)
    await link(client, token, "FSP-2")
    athlete, results = fsp.athletes["FSP-2"]
    fsp.athletes["FSP-2"] = (athlete, [*results, result("r9", "security", "international", 1)])
    body = (await client.post(f"{FSP}/sync", headers=bearer(token))).json()
    assert [c["slug"] for c in body["categories"]] == ["security-advanced"]  # один приз
    assert len(body["achievements"]) == 2


async def test_linked_without_results_stays_self_declared(client: AsyncClient):
    token = await register_candidate(client)
    body = await link(client, token, "FSP-3")
    assert body["linked"] and body["verification_tier"] == "self_declared"


async def test_unlink_clears_everything(client: AsyncClient):
    token = await register_candidate(client)
    await link(client, token)
    assert (await client.delete(FSP, headers=bearer(token))).status_code == 204
    body = (await client.get(FSP, headers=bearer(token))).json()
    assert not body["linked"] and body["categories"] == [] and body["achievements"] == []
    assert body["verification_tier"] == "self_declared"
    other = await register_candidate(client)  # аккаунт ФСП снова свободен
    assert (await link(client, other))["linked"]


@pytest.mark.parametrize("path", ["", "/sync"])
async def test_sync_and_unlink_require_link(client: AsyncClient, path: str):
    token = await register_candidate(client)
    method = "DELETE" if path == "" else "POST"
    r = await client.request(method, f"{FSP}{path}", headers=bearer(token))
    assert r.status_code == 404


async def test_employer_cannot_use_fsp(client: AsyncClient):
    token = await register_employer(client)
    assert (await client.get(FSP, headers=bearer(token))).status_code == 403


async def test_fsp_outage_during_confirm_keeps_link(client: AsyncClient, fsp):
    """Код одноразовый: если ФСП не отдала данные после подтверждения, привязка сохраняется."""
    token = await register_candidate(client)
    await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(token))

    async def down(_athlete_id: str):
        raise ServiceUnavailableError("down")

    fsp.get_results = down
    body = (await client.post(f"{FSP}/confirm", json={"code": CODE}, headers=bearer(token))).json()
    assert body["linked"] is True and body["achievements"] == [] and body["last_synced_at"] is None


async def test_expired_request_is_not_pending(client: AsyncClient, db):
    token = await register_candidate(client)
    await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(token))
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(FspVerification).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    body = (await client.get(FSP, headers=bearer(token))).json()
    assert body["pending_athlete_id"] is None
    r = await client.post(f"{FSP}/confirm", json={"code": CODE}, headers=bearer(token))
    assert r.status_code == 400


async def test_code_requests_limited_per_athlete(client: AsyncClient):
    """Письма владельцу аккаунта ФСП не чаще лимита, даже от разных пользователей."""
    codes = []
    for _ in range(6):
        token = await register_candidate(client)
        r = await client.post(f"{FSP}/link", json={"athlete_id": "FSP-2"}, headers=bearer(token))
        codes.append(r.status_code)
    assert codes == [200] * 5 + [429]


async def test_confirm_limited_per_user(client: AsyncClient, app):
    app.state.rate_limits["fsp_confirm"] = (2, 3600)
    token = await register_candidate(client)
    await client.post(f"{FSP}/link", json={"athlete_id": "FSP-1"}, headers=bearer(token))
    statuses = [
        (
            await client.post(f"{FSP}/confirm", json={"code": "000000"}, headers=bearer(token))
        ).status_code
        for _ in range(3)
    ]
    assert statuses == [400, 400, 429]
