"""Регулярные короткие задания: компания публикует задачу для специализации, система раз в
период предлагает её кандидату, ответ обновляет актуальность профиля и виден компании анонимно."""

from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import set_rls_context
from app.models import CandidateProfile
from tests.assessment_flow import survey
from tests.flows import approved_employer
from tests.helpers import bearer, register_candidate

TASKS = "/api/v1/employer/tasks"
CURRENT = "/api/v1/candidate/tasks/current"
MY_ANSWERS = "/api/v1/candidate/tasks/answers"
ANSWER = "Разобью задачу на два шага: сначала индекс по user_id, затем пагинация курсором."


async def publish(client: AsyncClient, token: str, **overrides) -> dict:
    body = {
        "title": "Медленный запрос ленты",
        "body": "Лента пользователя грузится 3 секунды. Как найдёте причину и что поправите?",
        "specialization": "backend",
        "grade": None,
    } | overrides
    r = await client.post(TASKS, json=body, headers=bearer(token))
    assert r.status_code == 201, r.text
    return r.json()


async def candidate_with_survey(client: AsyncClient, specialization: str = "backend") -> str:
    token = await register_candidate(client)
    await survey(client, token, specialization)
    return token


async def answer(client: AsyncClient, token: str, task_id: str, text: str = ANSWER):
    return await client.post(
        f"/api/v1/candidate/tasks/{task_id}/answers", json={"answer": text}, headers=bearer(token)
    )


async def test_task_offered_answered_and_rated(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    task = await publish(client, employer["token"])
    token = await candidate_with_survey(client)

    current = (await client.get(CURRENT, headers=bearer(token))).json()
    assert current["task"]["id"] == task["id"] and current["task"]["company_name"] == "ООО Найм"
    assert (await answer(client, token, task["id"])).status_code == 201

    # задача решена — следующая будет через период, профиль стал «свежим»
    after = (await client.get(CURRENT, headers=bearer(token))).json()
    assert after["task"] is None and after["next_at"]
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")  # на PostgreSQL профили защищены RLS
        profile = (await session.execute(select(CandidateProfile))).scalar_one()
    assert profile.last_activity_at is not None

    listed = (await client.get(TASKS, headers=bearer(employer["token"]))).json()["items"]
    assert listed[0]["answers_count"] == 1
    url = f"{TASKS}/{task['id']}/answers"
    (received,) = (await client.get(url, headers=bearer(employer["token"]))).json()["items"]
    # компания видит ответ и анонимную карточку: без имени и контактов
    assert received["answer"] == ANSWER and received["candidate"]["anon_id"]
    assert "full_name" not in received["candidate"]
    rated = await client.post(
        f"{url}/{received['id']}/rate", json={"rating": 4}, headers=bearer(employer["token"])
    )
    assert rated.json()["rating"] == 4

    (mine,) = (await client.get(MY_ANSWERS, headers=bearer(token))).json()["items"]
    assert (mine["task_title"], mine["company_name"], mine["rating"]) == (
        "Медленный запрос ленты",
        "ООО Найм",
        4,
    )


async def test_task_matches_specialization_and_grade(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    await publish(client, employer["token"], specialization="frontend")
    await publish(client, employer["token"], grade="lead")
    token = await candidate_with_survey(client)
    assert (await client.get(CURRENT, headers=bearer(token))).json()["task"] is None


async def test_candidate_without_survey_gets_reason(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    task = await publish(client, employer["token"])
    token = await register_candidate(client)
    current = (await client.get(CURRENT, headers=bearer(token))).json()
    assert current["task"] is None and "опрос" in current["reason"]
    assert (await answer(client, token, task["id"])).status_code == 409


async def test_one_answer_per_period(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    first = await publish(client, employer["token"])
    second = await publish(client, employer["token"], title="Очередь писем")
    token = await candidate_with_survey(client)
    assert (await answer(client, token, first["id"])).status_code == 201
    again = await answer(client, token, second["id"])
    assert again.status_code == 409 and "следующ" in again.json()["error"]["message"]


async def test_closed_task_is_not_offered(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    task = await publish(client, employer["token"])
    closed = await client.post(f"{TASKS}/{task['id']}/close", headers=bearer(employer["token"]))
    assert closed.json()["is_active"] is False
    token = await candidate_with_survey(client)
    assert (await client.get(CURRENT, headers=bearer(token))).json()["task"] is None
    assert (await answer(client, token, task["id"])).status_code == 404


async def test_other_company_cannot_read_answers(client: AsyncClient, db, app):
    owner = await approved_employer(client, db, app)
    task = await publish(client, owner["token"])
    other = await approved_employer(client, db, app, name="ООО Другая")
    r = await client.get(f"{TASKS}/{task['id']}/answers", headers=bearer(other["token"]))
    assert r.status_code == 404
    closing = await client.post(f"{TASKS}/{task['id']}/close", headers=bearer(other["token"]))
    assert closing.status_code == 404


async def test_rating_is_validated(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    task = await publish(client, employer["token"])
    token = await candidate_with_survey(client)
    await answer(client, token, task["id"])
    url = f"{TASKS}/{task['id']}/answers"
    (received,) = (await client.get(url, headers=bearer(employer["token"]))).json()["items"]
    r = await client.post(
        f"{url}/{received['id']}/rate", json={"rating": 6}, headers=bearer(employer["token"])
    )
    assert r.status_code == 422


async def test_short_answer_rejected(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    task = await publish(client, employer["token"])
    token = await candidate_with_survey(client)
    assert (await answer(client, token, task["id"], text="да")).status_code == 422


async def test_tasks_of_blocked_company_are_not_offered(client: AsyncClient, db, app):
    from tests.test_applications import block

    employer = await approved_employer(client, db, app)
    await publish(client, employer["token"])
    await block(client, db, app, employer)
    token = await candidate_with_survey(client)
    assert (await client.get(CURRENT, headers=bearer(token))).json()["task"] is None


def test_weekly_pick_ignores_tasks_published_this_week():
    """Новая задача посреди недели не подменяет уже предложенную."""
    import uuid
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from app.services.tasks import _weekly_pick

    old = SimpleNamespace(created_at=datetime.now(UTC) - timedelta(days=30))
    fresh = SimpleNamespace(created_at=datetime.now(UTC))
    for _ in range(20):
        assert _weekly_pick(uuid.uuid4(), [old, fresh]) is old  # type: ignore[list-item]
    assert _weekly_pick(uuid.uuid4(), [fresh]) is fresh  # type: ignore[list-item]
