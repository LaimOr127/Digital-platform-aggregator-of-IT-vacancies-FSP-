"""Статус поиска работы: виден в каталоге, «не ищу» убирает из каталога и закрывает офферы."""

from httpx import AsyncClient

from tests.flows import (
    APPLICATIONS,
    CATALOG,
    approved_employer,
    invitation_body,
    verified_candidate,
)
from tests.helpers import bearer

PROFILE = "/api/v1/candidate/profile"


async def set_status(client: AsyncClient, token: str, status: str) -> dict:
    r = await client.patch(PROFILE, json={"search_status": status}, headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


async def test_status_defaults_to_open_and_is_shown_in_catalog(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    own = (await client.get(PROFILE, headers=bearer(candidate["token"]))).json()
    assert own["search_status"] == "open"
    await set_status(client, candidate["token"], "active")
    cards = (await client.get(f"{CATALOG}/candidates", headers=bearer(employer["token"]))).json()
    assert [c["search_status"] for c in cards["items"]] == ["active"]


async def test_filter_by_active_search(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    active = await verified_candidate(client, athlete="FSP-1")
    await verified_candidate(client, athlete="FSP-2")
    await set_status(client, active["token"], "active")
    r = await client.get(
        f"{CATALOG}/candidates",
        params={"search_status": "active"},
        headers=bearer(employer["token"]),
    )
    assert [c["anon_id"] for c in r.json()["items"]] == [active["anon_id"]]


async def test_not_looking_leaves_catalog_and_blocks_offers(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    await set_status(client, candidate["token"], "closed")
    headers = bearer(employer["token"])
    assert (await client.get(f"{CATALOG}/candidates", headers=headers)).json()["items"] == []
    card = await client.get(f"{CATALOG}/candidates/{candidate['anon_id']}", headers=headers)
    assert card.status_code == 404
    # «не ищу» — новых приглашений на контакт не приходит
    invited = await client.post(
        APPLICATIONS, json=invitation_body(candidate, employer), headers=headers
    )
    assert invited.status_code == 404
    categories = (await client.get(f"{CATALOG}/categories", headers=headers)).json()
    assert all(c["candidates"] == 0 for c in categories)


async def test_unknown_status_rejected_in_russian(client: AsyncClient):
    from tests.helpers import register_candidate

    token = await register_candidate(client)
    r = await client.patch(PROFILE, json={"search_status": "maybe"}, headers=bearer(token))
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["msg"] == "Выберите значение из списка"
