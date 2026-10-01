"""Каталог и офферы: анонимность, честная вилка, идемпотентность, раскрытие контактов."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.db.session import set_rls_context
from app.models import ContactReveal, Offer
from app.worker.jobs import OfferExpiryJob
from tests.helpers import (
    approve_company,
    bearer,
    company_id,
    create_admin,
    create_vacancy,
    link_fsp,
    register_candidate,
    register_employer,
)

CATALOG = "/api/v1/employer/catalog"
OFFERS = "/api/v1/employer/offers"
INBOX = "/api/v1/candidate/offers"


async def approved_employer(client: AsyncClient, db, app, name: str = "ООО Найм") -> dict:
    token = await register_employer(client, company=name)
    await approve_company(client, await create_admin(db, app), await company_id(client, token))
    vacancy = await create_vacancy(client, token)
    await client.post(f"/api/v1/employer/vacancies/{vacancy['id']}/publish", headers=bearer(token))
    return {"token": token, "vacancy": vacancy}


async def verified_candidate(client: AsyncClient, athlete: str = "FSP-1") -> dict:
    token = await register_candidate(client, name="Анна Смирнова")
    await client.patch(
        "/api/v1/candidate/profile",
        json={
            "title": "Backend",
            "grade": "middle",
            "skills": ["python"],
            "contacts": {"telegram": "@anna"},
        },
        headers=bearer(token),
    )
    await link_fsp(client, token, athlete)
    anon_id = (await client.get("/api/v1/candidate/profile", headers=bearer(token))).json()[
        "anon_id"
    ]
    return {"token": token, "anon_id": anon_id}


def offer_body(candidate: dict, employer: dict, **overrides) -> dict:
    return {
        "anon_id": candidate["anon_id"],
        "vacancy_id": employer["vacancy"]["id"],
        "salary_min": 250_000,
        "salary_max": 320_000,
        "message": "Нужен backend в команду платформы",
        **overrides,
    }


async def send(client: AsyncClient, candidate: dict, employer: dict, **overrides) -> dict:
    r = await client.post(
        OFFERS, json=offer_body(candidate, employer, **overrides), headers=bearer(employer["token"])
    )
    assert r.status_code == 201, r.text
    return r.json()


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


async def test_offer_lifecycle_and_contacts(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    assert offer["status"] == "sent" and offer["company_name"] == "ООО Найм" and offer["candidate"]

    contacts_url = f"{OFFERS}/{offer['id']}/contacts"
    assert (await client.get(contacts_url, headers=bearer(employer["token"]))).status_code == 403

    inbox = (await client.get(INBOX, headers=bearer(candidate["token"]))).json()["items"]
    assert [o["id"] for o in inbox] == [offer["id"]] and inbox[0]["salary_min"] == 250_000
    accepted = await client.post(
        f"{INBOX}/{offer['id']}/accept", headers=bearer(candidate["token"])
    )
    assert accepted.json()["status"] == "accepted"

    contacts = (await client.get(contacts_url, headers=bearer(employer["token"]))).json()
    assert contacts == {
        "full_name": "Анна Смирнова",
        "phone": None,
        "telegram": "@anna",
        "email": None,
    }
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        reveals = (await session.execute(select(ContactReveal))).scalars().all()
        stored = (await session.execute(select(Offer))).scalar_one()
    assert len(reveals) == 1
    assert "Анна" not in (stored.contact_name_enc or "")  # снимок контактов зашифрован


async def test_decline_with_reason(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    r = await client.post(
        f"{INBOX}/{offer['id']}/decline",
        json={"reason": "Ищу удалёнку"},
        headers=bearer(candidate["token"]),
    )
    assert r.json()["status"] == "declined" and r.json()["decline_reason"] == "Ищу удалёнку"
    again = await client.post(f"{INBOX}/{offer['id']}/accept", headers=bearer(candidate["token"]))
    assert again.status_code == 409


async def test_idempotency_key_and_duplicate_pending_offer(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    headers = {**bearer(employer["token"]), "Idempotency-Key": "offer-1"}
    first = await client.post(OFFERS, json=offer_body(candidate, employer), headers=headers)
    retry = await client.post(OFFERS, json=offer_body(candidate, employer), headers=headers)
    assert (
        first.status_code == retry.status_code == 201 and first.json()["id"] == retry.json()["id"]
    )
    duplicate = await client.post(
        OFFERS, json=offer_body(candidate, employer), headers=bearer(employer["token"])
    )
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "salary", [{"salary_min": 300_000, "salary_max": 100_000}, {"salary_min": 0, "salary_max": 1}]
)
async def test_offer_requires_valid_salary_range(client: AsyncClient, db, app, salary):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    r = await client.post(
        OFFERS, json=offer_body(candidate, employer, **salary), headers=bearer(employer["token"])
    )
    assert r.status_code == 422


async def test_offer_only_for_published_vacancy(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    draft = await create_vacancy(client, employer["token"], title="Черновик")
    r = await client.post(
        OFFERS,
        json=offer_body(candidate, employer, vacancy_id=draft["id"]),
        headers=bearer(employer["token"]),
    )
    assert r.status_code == 409


async def test_withdraw_and_foreign_company_isolation(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    rival = await approved_employer(client, db, app, name="ООО Конкурент")
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    for method, path in (
        ("POST", f"{OFFERS}/{offer['id']}/withdraw"),
        ("GET", f"{OFFERS}/{offer['id']}/contacts"),
    ):
        assert (
            await client.request(method, path, headers=bearer(rival["token"]))
        ).status_code == 404
    assert (await client.get(OFFERS, headers=bearer(rival["token"]))).json()["items"] == []
    withdrawn = await client.post(
        f"{OFFERS}/{offer['id']}/withdraw", headers=bearer(employer["token"])
    )
    assert withdrawn.json()["status"] == "withdrawn"
    late = await client.post(f"{INBOX}/{offer['id']}/accept", headers=bearer(candidate["token"]))
    assert late.status_code == 409


async def test_candidate_cannot_answer_foreign_offer(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    other = await register_candidate(client)
    offer = await send(client, candidate, employer)
    assert (
        await client.post(f"{INBOX}/{offer['id']}/accept", headers=bearer(other))
    ).status_code == 404


async def test_offer_expiry(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(Offer).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    inbox = (await client.get(INBOX, headers=bearer(candidate["token"]))).json()["items"]
    assert inbox[0]["status"] == "expired"  # до прогона worker — по сроку
    assert (
        await client.post(f"{INBOX}/{offer['id']}/accept", headers=bearer(candidate["token"]))
    ).status_code == 409
    assert await OfferExpiryJob(db).run() == 1
