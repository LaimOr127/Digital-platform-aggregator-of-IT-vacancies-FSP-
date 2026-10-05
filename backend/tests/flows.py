"""Сквозные шаги найма для тестов: компания, кандидат с ФСП, собеседование, оффер."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.db.session import Database, get_database, set_rls_context
from app.models import Interview
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
INTERVIEWS = "/api/v1/employer/interviews"
MY_INTERVIEWS = "/api/v1/candidate/interviews"
APPLICATIONS = "/api/v1/employer/applications"
MY_APPLICATIONS = "/api/v1/candidate/applications"


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


def slot(hours: float) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def invitation_body(candidate: dict, employer: dict, **overrides) -> dict:
    """Приглашение на контакт: предложение, вилка, способ связи (вакансия — по желанию)."""
    return {
        "anon_id": candidate["anon_id"],
        "vacancy_id": employer["vacancy"]["id"],
        "title": "Backend-разработчик",
        "description": "Платформа платежей, команда из 6 человек",
        "grade": "middle",
        "work_format": "remote",
        "salary_min": 250_000,
        "salary_max": 320_000,
        "contact_method": "Telegram @hr_naim",
        **overrides,
    }


async def connect(client: AsyncClient, candidate: dict, employer: dict) -> str:
    """Контакт состоялся: компания пригласила, кандидат принял. Один на пару компания-кандидат."""
    cache = candidate.setdefault("applications", {})
    if employer["token"] not in cache:
        r = await client.post(
            APPLICATIONS,
            json=invitation_body(candidate, employer),
            headers=bearer(employer["token"]),
        )
        assert r.status_code == 201, r.text
        accepted = await client.post(
            f"{MY_APPLICATIONS}/{r.json()['id']}/accept", headers=bearer(candidate["token"])
        )
        assert accepted.status_code == 200, accepted.text
        cache[employer["token"]] = r.json()["id"]
    return cache[employer["token"]]


def invite_body(candidate: dict, employer: dict, **overrides) -> dict:
    """Собеседование по уже состоявшемуся контакту (сначала — connect)."""
    return {
        "application_id": candidate["applications"][employer["token"]],
        "slots": [slot(2), slot(26)],
        "format": "online",
        "location": "https://meet.example.org/backend",
        "interviewer": "Иван Петров, руководитель разработки",
        "message": "Обсудим задачи команды",
        **overrides,
    }


async def invite(client: AsyncClient, candidate: dict, employer: dict, **overrides) -> dict:
    await connect(client, candidate, employer)
    r = await client.post(
        INTERVIEWS,
        json=invite_body(candidate, employer, **overrides),
        headers=bearer(employer["token"]),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def accept_first_slot(client: AsyncClient, candidate: dict, interview: dict) -> dict:
    r = await client.post(
        f"{MY_INTERVIEWS}/{interview['id']}/accept",
        json={"slot": interview["slots"][0]},
        headers=bearer(candidate["token"]),
    )
    assert r.status_code == 200, r.text
    return r.json()


async def mark_held(client: AsyncClient, interview_id: str) -> None:
    """Время встречи прошло (вместо ожидания в реальном времени)."""
    app = client._transport.app  # type: ignore[attr-defined]
    db: Database = app.dependency_overrides[get_database]()
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(Interview)
            .where(Interview.id == uuid.UUID(interview_id))
            .values(scheduled_at=datetime.now(UTC) - timedelta(minutes=5))
        )
        await session.commit()


async def complete(
    client: AsyncClient, employer: dict, interview_id: str, result: str = "passed"
) -> dict:
    r = await client.post(
        f"{INTERVIEWS}/{interview_id}/complete",
        json={"result": result, "feedback": "Сильная команда задач"},
        headers=bearer(employer["token"]),
    )
    assert r.status_code == 200, r.text
    return r.json()


async def passed_interview(client: AsyncClient, candidate: dict, employer: dict) -> dict:
    interview = await invite(client, candidate, employer)
    await accept_first_slot(client, candidate, interview)
    await mark_held(client, interview["id"])
    return await complete(client, employer, interview["id"])


def offer_body(interview: dict, **overrides) -> dict:
    return {
        "interview_id": interview["id"],
        "salary_min": 250_000,
        "salary_max": 320_000,
        "message": "Нужен backend в команду платформы",
        **overrides,
    }


async def send(client: AsyncClient, candidate: dict, employer: dict, **overrides) -> dict:
    """Оффер по итогам успешного собеседования."""
    interview = await passed_interview(client, candidate, employer)
    r = await client.post(
        OFFERS, json=offer_body(interview, **overrides), headers=bearer(employer["token"])
    )
    assert r.status_code == 201, r.text
    return r.json()
