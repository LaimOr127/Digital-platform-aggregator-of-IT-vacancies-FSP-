"""Каталог кандидатов: доступ только одобренным компаниям, анонимность, фильтры, скрытые профили."""

from httpx import AsyncClient

from tests.assessment_flow import confirm
from tests.flows import CATALOG, approved_employer, verified_candidate
from tests.helpers import bearer, create_admin, register_employer


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
    assert next(c for c in fsp if c["slug"] == "product-advanced")["candidates"] == 1

    for params in ({"category": "backend:middle"}, {"fsp_category": "product-advanced"}):
        page = (await client.get(f"{CATALOG}/candidates", params=params, headers=headers)).json()
        (card,) = page["items"]
        assert card["anon_id"] == candidate["anon_id"]
        assert card["category"]["title"] == "Бэкенд-разработчики · Middle"
        assert [c["slug"] for c in card["fsp_categories"]] == ["product-advanced"]
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


async def test_unconfirmed_candidates_rank_below_confirmed(client: AsyncClient, db, app):
    """Без подтверждённого тестом грейда кандидат виден, но ниже подтверждённых — даже с ФСП."""
    employer = await approved_employer(client, db, app)
    unconfirmed = await verified_candidate(client, "FSP-2")  # ФСП есть, теста нет
    confirmed = await verified_candidate(client, "FSP-3")
    await confirm(client, db, confirmed["token"])
    page = (await client.get(f"{CATALOG}/candidates", headers=bearer(employer["token"]))).json()
    order = [card["anon_id"] for card in page["items"]]
    assert order.index(confirmed["anon_id"]) < order.index(unconfirmed["anon_id"])
    card = next(c for c in page["items"] if c["anon_id"] == unconfirmed["anon_id"])
    assert card["category"] is None and card["confirmed_grade"] is None


async def test_blocked_candidate_leaves_the_catalog(client: AsyncClient, db, app):
    """Заблокированного модератором кандидата не видно и пригласить нельзя."""
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    admin = await create_admin(db, app)
    me = (await client.get("/api/v1/auth/me", headers=bearer(candidate["token"]))).json()
    await client.post(
        f"/api/v1/admin/users/{me['id']}/moderation",
        json={"action": "block", "reason": "фиктивный профиль"},
        headers=bearer(admin),
    )
    token = bearer(employer["token"])
    assert (await client.get(f"{CATALOG}/candidates", headers=token)).json()["items"] == []
    card = await client.get(f"{CATALOG}/candidates/{candidate['anon_id']}", headers=token)
    assert card.status_code == 404
