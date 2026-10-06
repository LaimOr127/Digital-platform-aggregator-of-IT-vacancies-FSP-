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
