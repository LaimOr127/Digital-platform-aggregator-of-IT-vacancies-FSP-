"""Автозаполнение профиля: черновик из анкеты ФСП и из резюме (правила и ИИ по согласию)."""

import json
import uuid

import httpx
from httpx import AsyncClient
from sqlalchemy import select

from app.core.crypto import ai_key_context
from app.models import AiProvider, AuditLog
from app.models.enums import AiProviderKind
from tests.helpers import bearer, link_fsp, register_candidate
from tests.resume_files import docx

IMPORT = "/api/v1/candidate/import"
TOOL_INPUT = {
    "full_name": "Анна Смирнова",
    "title": "Backend-разработчик",
    "grade": "senior",
    "experience_years": 6,
    "city": "Казань",
    "work_format": "remote",
    "salary_min": 350000,
    "skills": ["Python", "Go", "Zig-2077"],
    "about": "Строю высоконагруженные сервисы.",
}


async def upload(client: AsyncClient, token: str, data: bytes, use_ai: bool = False):
    return await client.post(
        f"{IMPORT}/resume",
        files={"file": ("cv.docx", data, "application/octet-stream")},
        data={"use_ai": str(use_ai).lower()},
        headers=bearer(token),
    )


async def use_ai(app, db, handler, kind: AiProviderKind = AiProviderKind.ANTHROPIC) -> list[dict]:
    """Подключает модель как в админке и подменяет сеть: возвращает ушедшие к модели запросы."""
    sent: list[dict] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append({"url": str(request.url), "headers": dict(request.headers), "body": body})
        return handler(request)

    app.state.ai_transport = httpx.MockTransport(respond)
    async with db.sessionmaker() as session:
        provider = AiProvider(
            id=uuid.uuid4(),
            name="Тестовая модель",
            kind=kind,
            base_url="https://ai.test/v1",
            model="m",
            is_active=True,
        )
        provider.api_key_enc = app.state.cipher.encrypt("k" * 40, ai_key_context(provider.id))
        session.add(provider)
        await session.commit()
    return sent


def anthropic_reply(data: dict) -> httpx.Response:
    block = {"type": "tool_use", "name": "respond", "input": data}
    return httpx.Response(200, json={"content": [block]})


async def test_fsp_draft_after_confirmed_link(client: AsyncClient, db):
    token = await register_candidate(client)
    assert (await client.get(f"{IMPORT}/fsp", headers=bearer(token))).status_code == 404
    await link_fsp(client, token, "FSP-1")
    draft = (await client.get(f"{IMPORT}/fsp", headers=bearer(token))).json()
    assert draft["source"] == "fsp" and draft["full_name"] == "Анна"
    assert draft["city"] == "Казань" and draft["title"] == "Backend-разработчик"
    assert draft["grade"] == "middle"  # стаж 3 года
    # навыки — из справочника (на SQLite он короче, чем в боевом сиде PostgreSQL)
    assert [s["slug"] for s in draft["skills"]] == ["python", "postgresql"]
    assert draft["unknown_skills"] == ["COBOL-2077"]
    assert draft["contacts"] == {
        "email": "anna@fsp.example.org",
        "phone": "+7 900 000-00-01",
        "telegram": "@anna_dev",
    }
    assert "Достижения ФСП" in draft["about"] and "КФУ" in draft["about"]
    assert "Соревнование" not in draft["about"]  # без названий: текст виден в анонимной карточке
    # черновик ничего не меняет в профиле сам
    profile = (await client.get("/api/v1/candidate/profile", headers=bearer(token))).json()
    assert profile["city"] is None
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "fsp.questionnaire_read" in actions


async def test_resume_draft_by_rules(client: AsyncClient):
    token = await register_candidate(client)
    capabilities = (await client.get(f"{IMPORT}/capabilities", headers=bearer(token))).json()
    assert capabilities == {"ai_available": False, "ai_provider": None, "max_file_mb": 5}
    r = await upload(client, token, docx(), use_ai=True)  # ИИ не настроен: работают правила
    draft = r.json()
    assert r.status_code == 200 and draft["source"] == "resume"
    assert draft["title"] == "Senior Backend-разработчик" and draft["grade"] == "senior"
    assert draft["salary_min"] == 350_000 and draft["work_format"] == "remote"
    assert {"python", "go", "postgresql", "react"} <= {s["slug"] for s in draft["skills"]}
    assert draft["contacts"]["email"] == "anna.dev@example.org"


async def test_unsupported_and_oversized_files(client: AsyncClient):
    token = await register_candidate(client)
    png = await upload(client, token, b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    assert png.status_code == 422 and png.json()["error"]["code"] == "unsupported_file"
    big = await upload(client, token, b"%PDF-" + b"0" * (5 * 1024 * 1024))
    assert big.status_code == 422 and "5 МБ" in big.json()["error"]["message"]


async def test_ai_draft_without_contacts_sent(client: AsyncClient, app, db):
    sent = await use_ai(app, db, lambda _: anthropic_reply(TOOL_INPUT))
    token = await register_candidate(client)
    draft = (await upload(client, token, docx(), use_ai=True)).json()
    assert draft["title"] == "Backend-разработчик"
    assert draft["about"] == "Строю высоконагруженные сервисы."
    assert draft["unknown_skills"] == ["Zig-2077"]
    assert draft["contacts"]["telegram"] == "@anna_backend"  # найдено локально
    assert "Тестовая модель" in draft["notes"][0]
    [request] = sent
    prompt = request["body"]["messages"][0]["content"]
    assert "anna.dev@example.org" not in prompt and "123-45-67" not in prompt
    assert request["body"]["tool_choice"] == {"type": "tool", "name": "respond"}
    assert request["headers"]["x-api-key"] == "k" * 40


async def test_ai_requires_consent_and_falls_back(client: AsyncClient, app, db):
    sent = await use_ai(app, db, lambda _: httpx.Response(529, json={"error": "overloaded"}))
    token = await register_candidate(client)
    without_consent = (await upload(client, token, docx(), use_ai=False)).json()
    assert sent == [] and without_consent["title"] == "Senior Backend-разработчик"
    fallback = (await upload(client, token, docx(), use_ai=True)).json()
    assert len(sent) == 1 and any("недоступен" in n for n in fallback["notes"])
    assert fallback["skills"]


async def test_ai_answer_outside_schema_is_rejected(client: AsyncClient, app, db):
    await use_ai(app, db, lambda _: anthropic_reply({"grade": "god", "skills": []}))
    token = await register_candidate(client)
    draft = (await upload(client, token, docx(), use_ai=True)).json()
    assert draft["grade"] == "senior"  # из правил, ответ ИИ отброшен


async def test_openai_compatible_model(client: AsyncClient, app, db):
    """Любая модель с OpenAI-совместимым API; сервер без response_format — повтор без него."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "response_format" in json.loads(request.content):
            return httpx.Response(400, json={"error": "unsupported response_format"})
        content = '```json\n{"title": "Go-разработчик", "skills": ["Go"], "grade": "middle"}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    sent = await use_ai(app, db, handler, kind=AiProviderKind.OPENAI)
    token = await register_candidate(client)
    capabilities = (await client.get(f"{IMPORT}/capabilities", headers=bearer(token))).json()
    assert capabilities["ai_provider"] == "Тестовая модель"
    draft = (await upload(client, token, docx(), use_ai=True)).json()
    assert draft["title"] == "Go-разработчик" and draft["grade"] == "middle"
    assert len(sent) == 2 and sent[0]["url"] == "https://ai.test/v1/chat/completions"
    assert sent[0]["headers"]["authorization"] == "Bearer " + "k" * 40
