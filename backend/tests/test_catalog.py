"""Каталог кандидатов: доступ только одобренным компаниям, анонимность, фильтры, скрытые профили."""

from httpx import AsyncClient

from tests.flows import CATALOG, approved_employer, verified_candidate
from tests.helpers import bearer, register_employer


async def test_catalog_requires_approved_company(client: AsyncClient):
    pending = await register_employer(client)
    assert (await client.get(f"{CATALOG}/categories", headers=bearer(pending))).status_code == 403


async def test_catalog_shows_anonymous_cards(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    categories = (
        await client.get(f"{CATALOG}/categories", headers=bearer(employer["token"]))
    ).json()
    assert len(categories) == 15
    assert next(c for c in categories if c["slug"] == "product-elite")["candidates"] == 1

    page = (
        await client.get(
            f"{CATALOG}/candidates",
            params={"category": "product-elite"},
            headers=bearer(employer["token"]),
        )
    ).json()
    (card,) = page["items"]
    assert card["anon_id"] == candidate["anon_id"] and card["skills"] == ["Python"]
    text = str(card)
    for secret in ("Анна", "@anna", "FSP-1", "Соревнование"):
        assert secret not in text  # ни имени, ни контактов, ни ID ФСП, ни названий соревнований


async def test_catalog_filters_and_hidden_profiles(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    token = bearer(employer["token"])
    for params, expected in (
        ({"grade": "middle"}, 1),
        ({"grade": "senior"}, 0),
        ({"skill": "go"}, 0),
        ({"skill": "python"}, 1),
    ):
        page = (await client.get(f"{CATALOG}/candidates", params=params, headers=token)).json()
        assert len(page["items"]) == expected, params
    await client.patch(
        "/api/v1/candidate/profile", json={"is_hidden": True}, headers=bearer(candidate["token"])
    )
    assert (await client.get(f"{CATALOG}/candidates", headers=token)).json()["items"] == []
    assert (
        await client.get(f"{CATALOG}/candidates/{candidate['anon_id']}", headers=token)
    ).status_code == 404
