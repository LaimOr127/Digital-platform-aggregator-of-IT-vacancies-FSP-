"""Языковая модель в категоризации и подборе: подсказка с запасным путём по правилам,
оценка кандидатов только по анонимным карточкам."""

import json

import httpx
from httpx import AsyncClient

from tests.flows import approved_employer, verified_candidate
from tests.helpers import bearer, register_candidate
from tests.test_profile_import import anthropic_reply, use_ai

SUGGEST = "/api/v1/candidate/assessment/suggestion"
STATUS = "/api/v1/employer/catalog/ai-status"
REVIEW = "/api/v1/employer/catalog/ai-review"


async def backend_candidate(client: AsyncClient) -> str:
    token = await register_candidate(client)
    body = {"skills": ["python", "postgresql"], "experience_years": 4, "title": "Разработчик"}
    await client.patch("/api/v1/candidate/profile", json=body, headers=bearer(token))
    return token


async def test_suggestion_by_rules_without_model(client: AsyncClient):
    token = await backend_candidate(client)
    r = await client.post(SUGGEST, headers=bearer(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["specialization"], body["grade"], body["source"]) == ("backend", "middle", "rules")


async def test_suggestion_by_model_and_fallback_on_failure(client: AsyncClient, db, app):
    token = await backend_candidate(client)
    reply = {"specialization": "data", "grade": "junior", "reason": "Python и SQL — путь в данные"}
    sent = await use_ai(app, db, lambda _: anthropic_reply(reply))
    body = (await client.post(SUGGEST, headers=bearer(token))).json()
    assert (body["specialization"], body["source"], body["provider"]) == (
        "data",
        "ai",
        "Тестовая модель",
    )
    assert "Разработчик" in json.dumps(sent[0]["body"], ensure_ascii=False)

    app.state.ai_transport = httpx.MockTransport(lambda _: httpx.Response(500))
    fallback = (await client.post(SUGGEST, headers=bearer(token))).json()
    assert fallback["source"] == "rules" and fallback["reason"].startswith("Модель недоступна")


async def test_review_needs_model_and_sends_only_anonymous_cards(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    body = {"vacancy_id": employer["vacancy"]["id"], "anon_ids": [candidate["anon_id"]]}
    hr = bearer(employer["token"])
    assert (await client.get(STATUS, headers=hr)).json()["available"] is False
    assert (await client.post(REVIEW, json=body, headers=hr)).status_code == 409

    reply = {"reviews": [{"ref": 0, "fit": 81, "reason": "Python и PostgreSQL как в вакансии"}]}
    sent = await use_ai(app, db, lambda _: anthropic_reply(reply))
    assert (await client.get(STATUS, headers=hr)).json()["provider"] == "Тестовая модель"
    (review,) = (await client.post(REVIEW, json=body, headers=hr)).json()
    assert (review["anon_id"], review["fit"]) == (candidate["anon_id"], 81)
    prompt = json.dumps(sent[0]["body"], ensure_ascii=False)
    # модели уходит анонимная карточка: без имени и контактов
    assert "Анна" not in prompt and "@anna" not in prompt
    # повтор — из кэша, без нового запроса к модели
    await client.post(REVIEW, json=body, headers=hr)
    assert len(sent) == 1
