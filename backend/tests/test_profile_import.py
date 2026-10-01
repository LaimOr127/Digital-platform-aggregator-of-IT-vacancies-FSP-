"""Автозаполнение профиля: черновик из анкеты ФСП и из резюме (правила и ИИ по согласию)."""

import json

import httpx
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import Settings
from app.models import AuditLog
from app.services.resume.llm import LlmResumeParser
from tests.helpers import bearer, link_fsp, register_candidate
from tests.resume_files import docx

IMPORT = "/api/v1/candidate/import"


async def upload(client: AsyncClient, token: str, data: bytes, use_ai: bool = False):
    return await client.post(
        f"{IMPORT}/resume",
        files={"file": ("cv.docx", data, "application/octet-stream")},
        data={"use_ai": str(use_ai).lower()},
        headers=bearer(token),
    )


def ai_parser(app, handler) -> list[dict]:
    """Подменяет ИИ-сервис: возвращает список запросов, которые к нему ушли."""
    sent: list[dict] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append({"headers": dict(request.headers), "body": json.loads(request.content)})
        return handler(request)

    parser = LlmResumeParser(Settings(anthropic_api_key=SecretStr("k" * 40)))
    parser.transport = httpx.MockTransport(respond)
    app.state.ai_parser = parser
    return sent


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
    # черновик ничего не меняет в профиле сам
    profile = (await client.get("/api/v1/candidate/profile", headers=bearer(token))).json()
    assert profile["city"] is None
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "fsp.questionnaire_read" in actions


async def test_resume_draft_by_rules(client: AsyncClient):
    token = await register_candidate(client)
    capabilities = (await client.get(f"{IMPORT}/capabilities", headers=bearer(token))).json()
    assert capabilities == {"ai_available": False, "max_file_mb": 5}
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


async def test_ai_draft_without_contacts_sent(client: AsyncClient, app):
    tool_input = {
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
    reply = {"content": [{"type": "tool_use", "name": "fill_profile", "input": tool_input}]}
    sent = ai_parser(app, lambda _: httpx.Response(200, json=reply))
    token = await register_candidate(client)
    draft = (await upload(client, token, docx(), use_ai=True)).json()
    assert (
        draft["title"] == "Backend-разработчик"
        and draft["about"] == "Строю высоконагруженные сервисы."
    )
    assert draft["unknown_skills"] == ["Zig-2077"]
    assert draft["contacts"]["telegram"] == "@anna_backend"  # найдено локально
    [request] = sent
    prompt = request["body"]["messages"][0]["content"]
    assert "anna.dev@example.org" not in prompt and "123-45-67" not in prompt
    assert request["body"]["tool_choice"] == {"type": "tool", "name": "fill_profile"}
    assert request["headers"]["x-api-key"] == "k" * 40


async def test_ai_requires_consent_and_falls_back(client: AsyncClient, app):
    sent = ai_parser(app, lambda _: httpx.Response(529, json={"error": "overloaded"}))
    token = await register_candidate(client)
    without_consent = (await upload(client, token, docx(), use_ai=False)).json()
    assert sent == [] and without_consent["title"] == "Senior Backend-разработчик"
    fallback = (await upload(client, token, docx(), use_ai=True)).json()
    assert len(sent) == 1 and any("недоступен" in n for n in fallback["notes"])
    assert fallback["skills"]


async def test_ai_answer_outside_schema_is_rejected(client: AsyncClient, app):
    bad = {
        "content": [
            {"type": "tool_use", "name": "fill_profile", "input": {"grade": "god", "skills": []}}
        ]
    }
    ai_parser(app, lambda _: httpx.Response(200, json=bad))
    token = await register_candidate(client)
    draft = (await upload(client, token, docx(), use_ai=True)).json()
    assert draft["grade"] == "senior"  # из правил, ответ ИИ отброшен
