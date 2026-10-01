"""Каталог и офферы: анонимность, оффер после собеседования, честная вилка, идемпотентность,
раскрытие контактов."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.db.session import set_rls_context
from app.models import ContactReveal, Offer
from app.worker.jobs import OfferExpiryJob
from tests.flows import (
    INBOX,
    OFFERS,
    accept_first_slot,
    approved_employer,
    invite,
    mark_held,
    offer_body,
    passed_interview,
    send,
    verified_candidate,
)
from tests.helpers import bearer, company_id, create_admin, register_candidate


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


async def test_idempotency_key_and_one_offer_per_interview(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    interview = await passed_interview(client, candidate, employer)
    headers = {**bearer(employer["token"]), "Idempotency-Key": "offer-1"}
    first = await client.post(OFFERS, json=offer_body(interview), headers=headers)
    retry = await client.post(OFFERS, json=offer_body(interview), headers=headers)
    assert (
        first.status_code == retry.status_code == 201 and first.json()["id"] == retry.json()["id"]
    )
    assert first.json()["interview_id"] == interview["id"]
    duplicate = await client.post(
        OFFERS, json=offer_body(interview), headers=bearer(employer["token"])
    )
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "salary", [{"salary_min": 300_000, "salary_max": 100_000}, {"salary_min": 0, "salary_max": 1}]
)
async def test_offer_requires_valid_salary_range(client: AsyncClient, db, app, salary):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    interview = await passed_interview(client, candidate, employer)
    r = await client.post(
        OFFERS, json=offer_body(interview, **salary), headers=bearer(employer["token"])
    )
    assert r.status_code == 422


async def test_offer_only_after_passed_interview(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    headers = bearer(employer["token"])
    interview = await invite(client, candidate, employer)
    assert (
        await client.post(OFFERS, json=offer_body(interview), headers=headers)
    ).status_code == 409
    await accept_first_slot(client, candidate, interview)
    assert (
        await client.post(OFFERS, json=offer_body(interview), headers=headers)
    ).status_code == 409
    await mark_held(client, interview["id"])
    failed = await client.post(
        f"/api/v1/employer/interviews/{interview['id']}/complete",
        json={"result": "failed"},
        headers=headers,
    )
    assert failed.json()["result"] == "failed"
    r = await client.post(OFFERS, json=offer_body(interview), headers=headers)
    assert r.status_code == 409 and "успешного собеседования" in r.json()["error"]["message"]


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


async def test_idempotency_key_cannot_be_reused_for_another_offer(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    first = await verified_candidate(client, "FSP-1")
    second = await verified_candidate(client, "FSP-2")
    headers = {**bearer(employer["token"]), "Idempotency-Key": "same-key"}
    first_interview = await passed_interview(client, first, employer)
    second_interview = await passed_interview(client, second, employer)
    assert (
        await client.post(OFFERS, json=offer_body(first_interview), headers=headers)
    ).status_code == 201
    reused = await client.post(OFFERS, json=offer_body(second_interview), headers=headers)
    assert reused.status_code == 409


async def test_no_repeat_offer_right_after_decline(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    await client.post(
        f"{INBOX}/{offer['id']}/decline", json={"reason": ""}, headers=bearer(candidate["token"])
    )
    interview = await passed_interview(client, candidate, employer)
    again = await client.post(OFFERS, json=offer_body(interview), headers=bearer(employer["token"]))
    assert again.status_code == 409 and "повторно" in again.json()["error"]["message"]


async def test_expired_offer_frees_the_pair_and_filters_match_display(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    await send(client, candidate, employer)
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(Offer).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    token = bearer(employer["token"])
    assert (await client.get(OFFERS, params={"status": "sent"}, headers=token)).json()[
        "items"
    ] == []
    assert (
        len((await client.get(OFFERS, params={"status": "expired"}, headers=token)).json()["items"])
        == 1
    )
    # просроченный оффер не мешает отправить новый, не дожидаясь worker
    await send(client, candidate, employer)


async def test_blocking_company_withdraws_pending_offers(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    admin = await create_admin(db, app)
    cid = await company_id(client, employer["token"])
    await client.post(
        f"/api/v1/admin/companies/{cid}/status",
        json={"status": "blocked", "reason": "спам"},
        headers=bearer(admin),
    )
    inbox = (await client.get(INBOX, headers=bearer(candidate["token"]))).json()["items"]
    assert inbox[0]["status"] == "withdrawn"
    assert (
        await client.post(f"{INBOX}/{offer['id']}/accept", headers=bearer(candidate["token"]))
    ).status_code == 409


async def test_offer_send_limited_per_company(client: AsyncClient, db, app):
    app.state.rate_limits["offer_send"] = (1, 86_400)
    employer = await approved_employer(client, db, app)
    first = await verified_candidate(client, "FSP-1")
    second = await verified_candidate(client, "FSP-2")
    await send(client, first, employer)
    interview = await passed_interview(client, second, employer)
    limited = await client.post(
        OFFERS, json=offer_body(interview), headers=bearer(employer["token"])
    )
    assert limited.status_code == 429


async def test_blocking_vacancy_withdraws_its_pending_offers(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    admin = await create_admin(db, app)
    blocked = await client.post(
        f"/api/v1/admin/vacancies/{employer['vacancy']['id']}/moderation",
        json={"action": "block", "reason": "сбор персональных данных"},
        headers=bearer(admin),
    )
    assert blocked.status_code == 200
    # контакты кандидата не должны уйти по вакансии, заблокированной модератором
    assert (
        await client.post(f"{INBOX}/{offer['id']}/accept", headers=bearer(candidate["token"]))
    ).status_code == 409
    inbox = (await client.get(INBOX, headers=bearer(candidate["token"]))).json()["items"]
    assert inbox[0]["status"] == "withdrawn"
