"""Путь кандидата через API: опрос -> тест -> категория; ответы только на сервере; правила."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.db.session import set_rls_context
from app.models import Assessment
from tests.assessment_flow import ASSESSMENT, confirm, responses, survey, take_test
from tests.flows import approved_employer
from tests.helpers import bearer, register_candidate

PROFILE = "/api/v1/candidate/profile"


async def state(client: AsyncClient, token: str) -> dict:
    return (await client.get(ASSESSMENT, headers=bearer(token))).json()


def option(body: dict, grade: str) -> dict:
    return next(o for o in body["options"] if o["grade"] == grade)


async def test_survey_comes_first(client: AsyncClient):
    token = await register_candidate(client)
    empty = await state(client, token)
    assert empty["survey"] is None and empty["category"] is None and empty["options"] == []
    r = await client.post(f"{ASSESSMENT}/attempts", json={"grade": "middle"}, headers=bearer(token))
    assert r.status_code == 409
    after = await survey(client, token, "frontend", "junior")
    assert after["survey"]["specialization"] == "frontend" and after["survey"]["industries"]
    assert option(after, "junior")["allowed"]
    bad = await client.put(
        f"{ASSESSMENT}/survey",
        json={
            "specialization": "backend",
            "grade": "middle",
            "experience_years": 1,
            "industries": ["space"],
            "skills": ["python"],
        },
        headers=bearer(token),
    )
    assert bad.status_code == 422


async def test_attempt_hides_answers_and_confirms_category(client: AsyncClient, db):
    token = await register_candidate(client)
    await survey(client, token)
    started = await client.post(
        f"{ASSESSMENT}/attempts", json={"grade": "middle"}, headers=bearer(token)
    )
    attempt = started.json()
    assert len(attempt["questions"]) == 15
    assert "answer" not in str(attempt["questions"]) and "seed" not in attempt
    # пока тест идёт, второй не начать
    again = await client.post(
        f"{ASSESSMENT}/attempts", json={"grade": "junior"}, headers=bearer(token)
    )
    assert again.status_code == 409
    mismatch = await client.post(
        f"{ASSESSMENT}/attempts/{attempt['id']}/submit",
        json={"responses": ["0"]},
        headers=bearer(token),
    )
    assert mismatch.status_code == 422
    body = {"responses": await responses(db, attempt["id"])}
    result = (
        await client.post(
            f"{ASSESSMENT}/attempts/{attempt['id']}/submit", json=body, headers=bearer(token)
        )
    ).json()
    assert result["result"] == "passed" and result["confident"] and result["theta"] > 3
    assert sum(t["total"] for t in result["topics"]) == 15
    after = await state(client, token)
    assert after["category"]["slug"] == "backend:middle" and after["confirmed_skills"]
    assert after["category"]["title"] == "Бэкенд-разработчики · Middle"
    # уверенный результат — сразу можно на грейд выше, но не через ступень
    assert option(after, "senior")["allowed"] and not option(after, "lead")["allowed"]
    assert not option(after, "junior")["allowed"]  # смена грейда — раз в три месяца
    profile = (await client.get(PROFILE, headers=bearer(token))).json()
    assert profile["confirmed_grade"] == "middle" and profile["assessment_score"] > 0


async def test_failed_test_does_not_lower_grade(client: AsyncClient, db):
    token = await register_candidate(client)
    await survey(client, token, grade="senior")
    result = await take_test(client, db, token, "senior", correct=0)
    assert result["result"] == "failed" and result["score"] == 0
    after = await state(client, token)
    assert after["category"] is None and after["history"][0]["result"] == "failed"
    retry = option(after, "senior")
    assert not retry["allowed"] and retry["retry_at"]
    assert option(after, "middle")["allowed"]  # тест на грейд ниже — сразу
    profile = (await client.get(PROFILE, headers=bearer(token))).json()
    assert profile["grade"] == "senior" and profile["confirmed_grade"] is None


async def test_screenshot_fails_attempt_and_locks_grade(client: AsyncClient):
    token = await register_candidate(client)
    await survey(client, token, grade="middle")
    attempt = (
        await client.post(f"{ASSESSMENT}/attempts", json={"grade": "middle"}, headers=bearer(token))
    ).json()
    url = f"{ASSESSMENT}/attempts/{attempt['id']}"
    r = await client.post(f"{url}/violation", json={"reason": "screenshot"}, headers=bearer(token))
    assert r.status_code == 200, r.text
    assert (r.json()["result"], r.json()["violation"]) == ("failed", "screenshot")
    # ответы после нарушения не принимаются, грейд и выше закрыты, как после неудачи
    late = await client.post(f"{url}/submit", json={"responses": []}, headers=bearer(token))
    assert late.status_code == 409
    after = await state(client, token)
    assert not option(after, "middle")["allowed"] and not option(after, "senior")["allowed"]
    assert option(after, "junior")["allowed"]


async def test_time_limit_is_enforced(client: AsyncClient, db):
    token = await register_candidate(client)
    await survey(client, token)
    attempt = (
        await client.post(f"{ASSESSMENT}/attempts", json={"grade": "middle"}, headers=bearer(token))
    ).json()
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(
            update(Assessment).values(deadline_at=datetime.now(UTC) - timedelta(minutes=5))
        )
        await session.commit()
    body = {"responses": await responses(db, attempt["id"])}
    late = await client.post(
        f"{ASSESSMENT}/attempts/{attempt['id']}/submit", json=body, headers=bearer(token)
    )
    assert late.status_code == 409
    after = await state(client, token)
    assert after["active"] is None and after["history"][0]["status"] == "expired"
    # брошенный тест — как проваленный: этот грейд и выше закрыты, ниже — открыт
    assert after["history"][0]["result"] == "failed"
    assert not option(after, "middle")["allowed"] and option(after, "junior")["allowed"]


async def test_failure_locks_grade_in_every_specialization(client: AsyncClient, db):
    token = await register_candidate(client)
    await survey(client, token, grade="middle")
    await take_test(client, db, token, "middle", correct=0)
    # сменил специализацию — провал всё равно действует
    after = await survey(
        client, token, specialization="frontend", grade="middle", skills=("react",)
    )
    assert not option(after, "middle")["allowed"] and not option(after, "senior")["allowed"]
    assert option(after, "junior")["allowed"]


async def test_foreign_attempt_is_invisible(client: AsyncClient, db):
    owner = await register_candidate(client)
    await survey(client, owner)
    attempt = (
        await client.post(f"{ASSESSMENT}/attempts", json={"grade": "middle"}, headers=bearer(owner))
    ).json()
    intruder = await register_candidate(client)
    body = {"responses": await responses(db, attempt["id"])}
    r = await client.post(
        f"{ASSESSMENT}/attempts/{attempt['id']}/submit", json=body, headers=bearer(intruder)
    )
    assert r.status_code == 404
    missing = await client.post(
        f"{ASSESSMENT}/attempts/{uuid.uuid4()}/submit", json=body, headers=bearer(owner)
    )
    assert missing.status_code == 404


async def test_specialization_change_waits_like_grade_change(client: AsyncClient, db):
    token = await register_candidate(client)
    await confirm(client, db, token)
    change = await client.put(
        f"{ASSESSMENT}/survey",
        json={
            "specialization": "devops",
            "grade": "middle",
            "experience_years": 3,
            "skills": ["python"],
        },
        headers=bearer(token),
    )
    assert change.status_code == 409 and "специализацию" in change.json()["error"]["message"]


async def test_employer_sees_how_tasks_follow_the_vacancy(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    url = f"/api/v1/employer/vacancies/{employer['vacancy']['id']}/assessment-preview"
    preview = (await client.get(url, headers=bearer(employer["token"]))).json()
    assert len(preview) == 15 and all(q["answer"] for q in preview)
    assert {q["level"] for q in preview} == {2, 3, 4}  # вакансия middle
    candidate = await register_candidate(client)
    assert (await client.get(url, headers=bearer(candidate))).status_code == 403


async def test_dictionaries_are_public(client: AsyncClient):
    body = (await client.get("/api/v1/public/dictionaries")).json()
    assert len(body["specializations"]) == 7 and body["industries"] and body["roles"]


async def test_focus_losses_are_a_signal_not_a_failure(client: AsyncClient, db):
    token = await register_candidate(client)
    await survey(client, token)
    attempt = (
        await client.post(f"{ASSESSMENT}/attempts", json={"grade": "middle"}, headers=bearer(token))
    ).json()
    body = {"responses": await responses(db, attempt["id"]), "focus_losses": 3}
    r = await client.post(
        f"{ASSESSMENT}/attempts/{attempt['id']}/submit", json=body, headers=bearer(token)
    )
    assert r.json()["focus_losses"] == 3 and r.json()["result"] == "passed"
