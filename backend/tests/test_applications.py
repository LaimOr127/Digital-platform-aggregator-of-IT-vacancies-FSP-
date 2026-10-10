"""Выход на контакт: приглашение с вилкой без обязательной вакансии, статусы с «просмотрено»,
контакты — после согласия кандидата; отклик кандидата на вакансию."""

from httpx import AsyncClient
from sqlalchemy import select

from app.models import AuditLog, OutboxMessage
from tests.flows import (
    APPLICATIONS,
    MY_APPLICATIONS,
    approved_employer,
    invitation_body,
    verified_candidate,
)
from tests.helpers import bearer, company_id, create_admin, create_vacancy, register_candidate

BOARD = "/api/v1/candidate/vacancies"


async def invite(client: AsyncClient, candidate: dict, employer: dict, **overrides) -> dict:
    r = await client.post(
        APPLICATIONS,
        json=invitation_body(candidate, employer, **overrides),
        headers=bearer(employer["token"]),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def mine(client: AsyncClient, token: str, **params) -> list[dict]:
    return (await client.get(MY_APPLICATIONS, params=params, headers=bearer(token))).json()["items"]


async def theirs(client: AsyncClient, token: str, **params) -> list[dict]:
    return (await client.get(APPLICATIONS, params=params, headers=bearer(token))).json()["items"]


async def test_invitation_without_vacancy_reveals_contacts_after_accept(
    client: AsyncClient, db, app
):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    sent = await invite(client, candidate, employer, vacancy_id=None)
    assert sent["status"] == "sent" and sent["vacancy_id"] is None
    assert sent["candidate"]["anon_id"] == candidate["anon_id"] and not sent["contacts_available"]
    hidden = await client.get(
        f"{APPLICATIONS}/{sent['id']}/contacts", headers=bearer(employer["token"])
    )
    assert hidden.status_code == 403

    (seen,) = await mine(client, candidate["token"])
    # в приглашении — описание, вилка, название компании и способ связи
    assert seen["company"]["name"] == "ООО Найм" and seen["contact_method"] == "Telegram @hr_naim"
    assert (seen["salary_min"], seen["salary_max"]) == (250_000, 320_000)
    (tracked,) = await theirs(client, employer["token"])
    assert tracked["status"] == "viewed"  # кандидат открыл — компания видит «просмотрено»

    accepted = await client.post(
        f"{MY_APPLICATIONS}/{sent['id']}/accept", headers=bearer(candidate["token"])
    )
    assert accepted.json()["status"] == "accepted"
    contacts = (
        await client.get(f"{APPLICATIONS}/{sent['id']}/contacts", headers=bearer(employer["token"]))
    ).json()
    assert contacts == {
        "full_name": "Анна Смирнова",
        "phone": None,
        "telegram": "@anna",
        "email": None,
    }
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert {"application.invited", "application.accepted", "application.contacts_revealed"} <= set(
        actions
    )
    async with db.sessionmaker() as session:
        kinds = (await session.execute(select(OutboxMessage.kind))).scalars().all()
    # письма без данных кандидата: кандидату — о приглашении, компании — о принятии
    assert {"invitation_received", "invitation_answered"} <= set(kinds)


async def test_accepting_needs_contacts_in_profile(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    token = await register_candidate(client)
    anon_id = (await client.get("/api/v1/candidate/profile", headers=bearer(token))).json()[
        "anon_id"
    ]
    candidate = {"token": token, "anon_id": anon_id}
    sent = await invite(client, candidate, employer)
    r = await client.post(f"{MY_APPLICATIONS}/{sent['id']}/accept", headers=bearer(token))
    assert r.status_code == 409 and r.json()["error"]["code"] == "contacts_required"


async def test_decline_duplicate_and_withdraw(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    sent = await invite(client, candidate, employer)
    again = await client.post(
        APPLICATIONS, json=invitation_body(candidate, employer), headers=bearer(employer["token"])
    )
    assert again.status_code == 409  # одно открытое обращение на пару
    withdrawn = await client.post(
        f"{APPLICATIONS}/{sent['id']}/withdraw", headers=bearer(employer["token"])
    )
    assert withdrawn.json()["status"] == "withdrawn"
    second = await invite(client, candidate, employer)
    declined = await client.post(
        f"{MY_APPLICATIONS}/{second['id']}/decline",
        json={"reason": "Не мой стек"},
        headers=bearer(candidate["token"]),
    )
    assert declined.json()["status"] == "declined"
    cooldown = await client.post(
        APPLICATIONS, json=invitation_body(candidate, employer), headers=bearer(employer["token"])
    )
    assert cooldown.status_code == 409 and "пригласить снова" in cooldown.json()["error"]["message"]


async def test_candidate_responds_to_vacancy(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    board = (await client.get(BOARD, headers=bearer(candidate["token"]))).json()["items"]
    (vacancy,) = board
    assert vacancy["company"]["name"] == "ООО Найм" and vacancy["match"]["score"] > 0
    assert vacancy["application_status"] is None
    r = await client.post(
        f"{BOARD}/{vacancy['id']}/respond",
        json={"message": "Готова к собеседованию"},
        headers=bearer(candidate["token"]),
    )
    assert r.status_code == 201 and r.json()["direction"] == "response"
    assert r.json()["contact_method"] is None  # способ связи — после ответа компании
    (incoming,) = await theirs(client, employer["token"], direction="response")
    assert incoming["status"] == "viewed" and incoming["contacts_available"]
    accepted = await client.post(
        f"{APPLICATIONS}/{incoming['id']}/accept",
        json={"contact_method": "hr@naim.example"},
        headers=bearer(employer["token"]),
    )
    assert accepted.json()["status"] == "accepted"
    (answered,) = await mine(client, candidate["token"], direction="response")
    assert answered["contact_method"] == "hr@naim.example"
    after = (await client.get(BOARD, headers=bearer(candidate["token"]))).json()["items"]
    assert after[0]["application_status"] == "accepted"


async def test_response_rules(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    vacancy_id = employer["vacancy"]["id"]
    first = await client.post(
        f"{BOARD}/{vacancy_id}/respond", json={}, headers=bearer(candidate["token"])
    )
    twice = await client.post(
        f"{BOARD}/{vacancy_id}/respond", json={}, headers=bearer(candidate["token"])
    )
    assert twice.status_code == 409
    # вторая вакансия той же компании: кнопка неактивна и объясняет почему
    other = await create_vacancy(client, employer["token"], title="Python-разработчик")
    await client.post(
        f"/api/v1/employer/vacancies/{other['id']}/publish", headers=bearer(employer["token"])
    )
    board = (await client.get(BOARD, headers=bearer(candidate["token"]))).json()["items"]
    assert all(
        v["respond_blocked"] == "Вы уже откликнулись в эту компанию — дождитесь ответа"
        for v in board
    )
    withdrawn = await client.post(
        f"{MY_APPLICATIONS}/{first.json()['id']}/withdraw", headers=bearer(candidate["token"])
    )
    assert withdrawn.json()["status"] == "withdrawn"
    board = (await client.get(BOARD, headers=bearer(candidate["token"]))).json()["items"]
    assert all(v["respond_blocked"] is None for v in board)
    await client.post(
        f"/api/v1/employer/vacancies/{vacancy_id}/close", headers=bearer(employer["token"])
    )
    closed = await client.post(
        f"{BOARD}/{vacancy_id}/respond", json={}, headers=bearer(candidate["token"])
    )
    assert closed.status_code == 404


async def test_parties_only(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    rival = await approved_employer(client, db, app, name="ООО Конкурент")
    candidate = await verified_candidate(client)
    stranger = await register_candidate(client)
    sent = await invite(client, candidate, employer)
    for path in ("withdraw", "contacts"):
        method = client.get if path == "contacts" else client.post
        r = await method(f"{APPLICATIONS}/{sent['id']}/{path}", headers=bearer(rival["token"]))
        assert r.status_code == 404
    assert await theirs(client, rival["token"]) == []
    r = await client.post(f"{MY_APPLICATIONS}/{sent['id']}/accept", headers=bearer(stranger))
    assert r.status_code == 404
    assert await mine(client, stranger) == []


async def test_privacy_settings_hide_card_sections(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    await client.patch(
        "/api/v1/candidate/profile",
        json={
            "salary_min": 200_000,
            "about": "Пишу сервисы",
            "show_salary": False,
            "show_about": False,
            "show_fsp": False,
        },
        headers=bearer(candidate["token"]),
    )
    card = (
        await client.get(
            f"/api/v1/employer/catalog/candidates/{candidate['anon_id']}",
            headers=bearer(employer["token"]),
        )
    ).json()
    assert card["salary_min"] is None and card["about"] is None
    assert card["fsp_categories"] == [] and card["achievements"] == []


async def test_invitations_limited_per_company(client: AsyncClient, db, app):
    app.state.rate_limits["application_invite"] = (1, 86_400)
    employer = await approved_employer(client, db, app)
    first = await verified_candidate(client, "FSP-1")
    second = await verified_candidate(client, "FSP-2")
    await invite(client, first, employer)
    r = await client.post(
        APPLICATIONS, json=invitation_body(second, employer), headers=bearer(employer["token"])
    )
    assert r.status_code == 429


async def block(client: AsyncClient, db, app, employer: dict) -> None:
    cid = await company_id(client, employer["token"])
    r = await client.post(
        f"/api/v1/admin/companies/{cid}/status",
        json={"status": "blocked", "reason": "жалобы кандидатов"},
        headers=bearer(await create_admin(db, app)),
    )
    assert r.status_code == 200, r.text


async def test_blocked_company_loses_contact_channel(client: AsyncClient, db, app):
    """Заблокированная компания не получает контакты ни по новым, ни по прежним обращениям."""
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    sent = await invite(client, candidate, employer, vacancy_id=None)
    await block(client, db, app, employer)
    # открытое приглашение отозвано блокировкой — принять его нельзя
    accepted = await client.post(
        f"{MY_APPLICATIONS}/{sent['id']}/accept", headers=bearer(candidate["token"])
    )
    assert accepted.status_code == 409
    contacts = await client.get(
        f"{APPLICATIONS}/{sent['id']}/contacts", headers=bearer(employer["token"])
    )
    assert contacts.status_code == 403


async def test_board_shows_new_vacancy_despite_cache(client: AsyncClient, db, app):
    """Рейтинг ленты кэшируется, но публикация вакансии сразу сбрасывает кэш."""
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    first = (await client.get(BOARD, headers=bearer(candidate["token"]))).json()["items"]
    vacancy = await create_vacancy(client, employer["token"], title="Ещё одна вакансия")
    await client.post(
        f"/api/v1/employer/vacancies/{vacancy['id']}/publish", headers=bearer(employer["token"])
    )
    second = (await client.get(BOARD, headers=bearer(candidate["token"]))).json()["items"]
    assert len(second) == len(first) + 1
