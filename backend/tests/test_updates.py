"""Индикаторы нового: время последнего события по разделам и вакансии к продлению."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.db.session import set_rls_context
from app.models import Vacancy
from tests.flows import APPLICATIONS, approved_employer, invitation_body, verified_candidate
from tests.helpers import bearer

MINE = "/api/v1/candidate/updates"
THEIRS = "/api/v1/employer/updates"


async def test_candidate_sees_fresh_vacancy_and_new_invitation(client: AsyncClient, db, app):
    candidate = await verified_candidate(client)
    empty = (await client.get(MINE, headers=bearer(candidate["token"]))).json()
    assert empty["invitations"] is None and empty["offers"] is None

    before = datetime.now(UTC) - timedelta(seconds=5)
    employer = await approved_employer(client, db, app)
    r = await client.post(
        APPLICATIONS,
        json=invitation_body(candidate, employer),
        headers=bearer(employer["token"]),
    )
    assert r.status_code == 201, r.text

    news = (await client.get(MINE, headers=bearer(candidate["token"]))).json()
    # момент публикации вакансии, а не срок её снятия
    assert before < datetime.fromisoformat(news["vacancies"]) < datetime.now(UTC)
    assert datetime.fromisoformat(news["invitations"]) > before
    assert news["responses"] is None


async def test_employer_sees_vacancy_to_renew_and_application(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    fresh = (await client.get(THEIRS, headers=bearer(employer["token"]))).json()
    assert fresh["renew_due"] == 0 and fresh["applications"] is None

    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(Vacancy)
            .where(Vacancy.id == uuid.UUID(employer["vacancy"]["id"]))
            .values(expires_at=datetime.now(UTC) + timedelta(days=1))
        )
        await session.commit()
    candidate = await verified_candidate(client)
    await client.post(
        APPLICATIONS, json=invitation_body(candidate, employer), headers=bearer(employer["token"])
    )

    news = (await client.get(THEIRS, headers=bearer(employer["token"]))).json()
    assert news["renew_due"] == 1
    assert news["applications"] is not None


async def test_seen_mark_is_shared_by_all_devices(client: AsyncClient, db, app):
    """Отметка на сервере: открыл раздел на телефоне — точка гаснет и на ноутбуке."""
    candidate = await verified_candidate(client)
    phone = bearer(candidate["token"])
    r = await client.post(f"{MINE}/seen", json={"section": "offers"}, headers=phone)
    assert r.status_code == 204
    first = (await client.get(MINE, headers=phone)).json()["seen"]["offers"]
    # повторная отметка двигает время только вперёд; неизвестный раздел — ошибка
    await client.post(f"{MINE}/seen", json={"section": "offers"}, headers=phone)
    laptop = (await client.get(MINE, headers=phone)).json()["seen"]
    assert datetime.fromisoformat(laptop["offers"]) >= datetime.fromisoformat(first)
    bad = await client.post(f"{MINE}/seen", json={"section": "tasks"}, headers=phone)
    assert bad.status_code == 422

    employer = await approved_employer(client, db, app)
    hr = bearer(employer["token"])
    assert (
        await client.post(f"{THEIRS}/seen", json={"section": "tasks"}, headers=hr)
    ).status_code == 204
    assert "tasks" in (await client.get(THEIRS, headers=hr)).json()["seen"]
    # отметки кандидата и компании не смешиваются
    assert "tasks" not in (await client.get(MINE, headers=phone)).json()["seen"]
