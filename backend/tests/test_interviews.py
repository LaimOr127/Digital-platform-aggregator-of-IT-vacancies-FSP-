"""Собеседования: приглашение со слотами -> выбор времени -> результат -> оффер."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update

from app.db.session import set_rls_context
from app.models import Interview, OutboxMessage
from app.worker.jobs import OfferExpiryJob
from tests.flows import (
    APPLICATIONS,
    INTERVIEWS,
    MY_INTERVIEWS,
    OFFERS,
    accept_first_slot,
    approved_employer,
    complete,
    connect,
    invitation_body,
    invite,
    invite_body,
    mark_held,
    offer_body,
    slot,
    verified_candidate,
)
from tests.helpers import bearer, register_candidate


async def test_full_hiring_flow(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    interview = await invite(client, candidate, employer)
    assert interview["status"] == "invited" and len(interview["slots"]) == 2
    assert "Анна" not in str(interview["candidate"])  # до оффера кандидат анонимен

    mine = (await client.get(MY_INTERVIEWS, headers=bearer(candidate["token"]))).json()["items"]
    assert mine[0]["company_name"] == "ООО Найм" and mine[0]["interviewer"].startswith("Иван")
    scheduled = await accept_first_slot(client, candidate, interview)
    assert scheduled["status"] == "scheduled" and scheduled["scheduled_at"]

    early = await client.post(
        f"{INTERVIEWS}/{interview['id']}/complete",
        json={"result": "passed"},
        headers=bearer(employer["token"]),
    )
    assert early.status_code == 409  # результат — только после встречи
    await mark_held(client, interview["id"])
    done = await complete(client, employer, interview["id"])
    assert done["status"] == "completed" and done["result"] == "passed"

    offer = await client.post(OFFERS, json=offer_body(interview), headers=bearer(employer["token"]))
    assert offer.status_code == 201
    mine = (await client.get(MY_INTERVIEWS, headers=bearer(candidate["token"]))).json()["items"]
    assert mine[0]["feedback"] == "Сильная команда задач"
    assert mine[0]["offer_id"] == offer.json()["id"]
    async with db.sessionmaker() as session:
        kinds = set((await session.execute(select(OutboxMessage.kind))).scalars())
    assert {"interview_invited", "interview_scheduled", "interview_result"} <= kinds


async def test_slots_and_location_validated(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    await connect(client, candidate, employer)
    headers = bearer(employer["token"])
    for overrides in (
        {"slots": [slot(-1)]},
        {"slots": [slot(0.5)]},
        {"slots": [slot(24 * 31)]},
        {"slots": []},
        {"location": "zoom.us/j/1"},
    ):
        r = await client.post(
            INTERVIEWS, json=invite_body(candidate, employer, **overrides), headers=headers
        )
        assert r.status_code == 422, overrides
    office = await invite(
        client, candidate, employer, format="office", location="Казань, ул. Баумана, 1"
    )
    assert office["format"] == "office"


async def test_candidate_must_pick_offered_slot(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    interview = await invite(client, candidate, employer)
    r = await client.post(
        f"{MY_INTERVIEWS}/{interview['id']}/accept",
        json={"slot": slot(5)},
        headers=bearer(candidate["token"]),
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_slot"


async def test_decline_and_cooldown(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    interview = await invite(client, candidate, employer)
    declined = await client.post(
        f"{MY_INTERVIEWS}/{interview['id']}/decline",
        json={"reason": "Уже нашла работу"},
        headers=bearer(candidate["token"]),
    )
    assert declined.json()["status"] == "declined"
    again = await client.post(
        INTERVIEWS, json=invite_body(candidate, employer), headers=bearer(employer["token"])
    )
    assert again.status_code == 409 and "пригласить снова" in again.json()["error"]["message"]


async def test_cancel_and_duplicate_invite(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    headers = bearer(employer["token"])
    interview = await invite(client, candidate, employer)
    duplicate = await client.post(
        INTERVIEWS, json=invite_body(candidate, employer), headers=headers
    )
    assert duplicate.status_code == 409
    cancelled = await client.post(
        f"{INTERVIEWS}/{interview['id']}/cancel",
        json={"reason": "вакансия закрыта"},
        headers=headers,
    )
    assert cancelled.json()["status"] == "cancelled"
    late = await client.post(
        f"{MY_INTERVIEWS}/{interview['id']}/accept",
        json={"slot": interview["slots"][0]},
        headers=bearer(candidate["token"]),
    )
    assert late.status_code == 409
    await invite(client, candidate, employer)  # после отмены можно пригласить снова


async def test_unanswered_invite_expires(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    interview = await invite(client, candidate, employer)
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(Interview).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    mine = await client.get(
        MY_INTERVIEWS, params={"status": "expired"}, headers=bearer(candidate["token"])
    )
    assert [i["id"] for i in mine.json()["items"]] == [interview["id"]]
    assert await OfferExpiryJob(db).run() == 1
    await invite(client, candidate, employer)  # просроченное не мешает новому приглашению


async def test_isolation_between_companies_and_candidates(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    rival = await approved_employer(client, db, app, name="ООО Конкурент")
    candidate = await verified_candidate(client)
    stranger = await register_candidate(client)
    interview = await invite(client, candidate, employer)
    for action, body in (("cancel", {"reason": ""}), ("complete", {"result": "passed"})):
        r = await client.post(
            f"{INTERVIEWS}/{interview['id']}/{action}", json=body, headers=bearer(rival["token"])
        )
        assert r.status_code == 404
    assert (await client.get(INTERVIEWS, headers=bearer(rival["token"]))).json()["items"] == []
    r = await client.post(
        f"{MY_INTERVIEWS}/{interview['id']}/accept",
        json={"slot": interview["slots"][0]},
        headers=bearer(stranger),
    )
    assert r.status_code == 404


async def test_interview_needs_established_contact(client: AsyncClient, db, app):
    """Собеседование — после принятого приглашения: не принятое не годится, чужое — тоже."""
    employer = await approved_employer(client, db, app)
    rival = await approved_employer(client, db, app, name="ООО Конкурент")
    candidate = await verified_candidate(client)
    sent = await client.post(
        APPLICATIONS,
        json=invitation_body(candidate, employer),
        headers=bearer(employer["token"]),
    )
    candidate["applications"] = {employer["token"]: sent.json()["id"]}
    r = await client.post(
        INTERVIEWS, json=invite_body(candidate, employer), headers=bearer(employer["token"])
    )
    assert r.status_code == 409 and "после принятого" in r.json()["error"]["message"]
    foreign = await client.post(
        INTERVIEWS, json=invite_body(candidate, employer), headers=bearer(rival["token"])
    )
    assert foreign.status_code == 404


async def test_invites_limited_per_company(client: AsyncClient, db, app):
    app.state.rate_limits["interview_invite"] = (1, 86_400)
    employer = await approved_employer(client, db, app)
    first = await verified_candidate(client, "FSP-1")
    second = await verified_candidate(client, "FSP-2")
    await connect(client, second, employer)
    await invite(client, first, employer)
    r = await client.post(
        INTERVIEWS, json=invite_body(second, employer), headers=bearer(employer["token"])
    )
    assert r.status_code == 429
