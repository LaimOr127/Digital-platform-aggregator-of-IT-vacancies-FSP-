"""Прохождение опроса и теста через API: правильные ответы берутся из БД (так тест знает их)."""

import uuid

from httpx import AsyncClient

from app.db.session import set_rls_context
from app.models import Assessment
from tests.helpers import bearer

ASSESSMENT = "/api/v1/candidate/assessment"


async def survey(
    client: AsyncClient,
    token: str,
    specialization: str = "backend",
    grade: str = "middle",
    skills: tuple[str, ...] = ("python", "postgresql"),
) -> dict:
    body = {
        "specialization": specialization,
        "grade": grade,
        "experience_years": 3,
        "industries": ["fintech"],
        "roles": ["developer"],
        "skills": list(skills),
    }
    r = await client.put(f"{ASSESSMENT}/survey", json=body, headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


async def responses(db, attempt_id: str, correct: int | None = None) -> list[str | None]:
    """Ответы на попытку: первые correct — верные, остальные — неверные (None — все верные)."""
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")  # на PostgreSQL попытки защищены RLS
        row = await session.get(Assessment, uuid.UUID(attempt_id))
        items = row.items
    answers: list[str | None] = []
    for i, item in enumerate(items):
        right = correct is None or i < correct
        if item["kind"] == "choice":
            index = item["options"].index(item["answer"])
            answers.append(str(index if right else (index + 1) % len(item["options"])))
        else:
            answers.append(item["answer"] if right else str(int(item["answer"]) + 1))
    return answers


async def take_test(
    client: AsyncClient, db, token: str, grade: str = "middle", correct: int | None = None
) -> dict:
    started = await client.post(
        f"{ASSESSMENT}/attempts", json={"grade": grade}, headers=bearer(token)
    )
    assert started.status_code == 201, started.text
    attempt = started.json()
    body = {"responses": await responses(db, attempt["id"], correct)}
    r = await client.post(
        f"{ASSESSMENT}/attempts/{attempt['id']}/submit", json=body, headers=bearer(token)
    )
    assert r.status_code == 200, r.text
    return r.json()


async def confirm(
    client: AsyncClient, db, token: str, specialization: str = "backend", grade: str = "middle"
) -> dict:
    """Опрос и успешный тест: кандидат получает категорию специализация x грейд."""
    await survey(client, token, specialization, grade)
    result = await take_test(client, db, token, grade)
    assert result["result"] == "passed", result
    return result
