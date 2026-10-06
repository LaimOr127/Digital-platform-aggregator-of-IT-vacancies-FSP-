"""Каталог кандидатов: доступ только одобренным компаниям, анонимность, фильтры, скрытые профили."""

from httpx import AsyncClient

from tests.assessment_flow import confirm
from tests.flows import CATALOG, approved_employer, verified_candidate
from tests.helpers import bearer, register_employer


async def test_catalog_requires_approved_company(client: AsyncClient, premoderation):
    pending = await register_employer(client)
    assert (await client.get(f"{CATALOG}/categories", headers=bearer(pending))).status_code == 403


async def test_catalog_shows_anonymous_cards(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    await confirm(client, db, candidate["token"], "backend", "middle")
    headers = bearer(employer["token"])
    categories = (await client.get(f"{CATALOG}/categories", headers=headers)).json()
    assert len(categories) == 7 * 5  # каждая специализация x каждый грейд
    assert next(c for c in categories if c["slug"] == "backend:middle")["candidates"] == 1
    # достижения ФСП — отдельный справочник для фильтра
    fsp = (await client.get(f"{CATALOG}/fsp-categories", headers=headers)).json()
    assert len(fsp) == 15
    assert next(c for c in fsp if c["slug"] == "product-elite")["candidates"] == 1

    for params in ({"category": "backend:middle"}, {"fsp_category": "product-elite"}):
        page = (await client.get(f"{CATALOG}/candidates", params=params, headers=headers)).json()
        (card,) = page["items"]
        assert card["anon_id"] == candidate["anon_id"]
        assert card["category"]["title"] == "Бэкенд-разработчики · Middle"
        assert [c["slug"] for c in card["fsp_categories"]] == ["product-elite"]
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
        ({"skill": ["python", "go"]}, 0),  # все выбранные навыки
        ({"specialization": "frontend"}, 0),
        ({"fsp_only": True}, 1),
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
