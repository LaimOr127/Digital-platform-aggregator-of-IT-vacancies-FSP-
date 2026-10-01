"""Профиль кандидата: чтение/изменение своего, шифрование ПДн, валидация."""

from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import set_rls_context
from app.models import CandidateProfile
from tests.helpers import bearer, register_candidate

PROFILE = "/api/v1/candidate/profile"


async def test_profile_created_on_registration(client: AsyncClient):
    token = await register_candidate(client, name="Мария Иванова")
    r = await client.get(PROFILE, headers=bearer(token))
    assert r.status_code == 200
    body = r.json()
    assert body["full_name"] == "Мария Иванова"
    assert body["verification_tier"] == "self_declared" and body["skills"] == []


async def test_update_profile(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.patch(
        PROFILE,
        json={
            "title": "Backend",
            "grade": "middle",
            "work_format": "remote",
            "salary_min": 150_000,
            "salary_max": 250_000,
            "skills": ["python", "postgresql", "python"],
            "contacts": {"telegram": "@ivan"},
        },
        headers=bearer(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grade"] == "middle" and body["contacts"]["telegram"] == "@ivan"
    assert sorted(s["slug"] for s in body["skills"]) == ["postgresql", "python"]

    r = await client.patch(PROFILE, json={"city": "Казань"}, headers=bearer(token))
    assert r.json()["grade"] == "middle" and r.json()["city"] == "Казань"


async def test_personal_data_encrypted_at_rest(client: AsyncClient, db):
    token = await register_candidate(client, name="Секретов Секрет")
    await client.patch(PROFILE, json={"contacts": {"phone": "+79990001122"}}, headers=bearer(token))
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        profile = (await session.execute(select(CandidateProfile))).scalar_one()
    assert "Секретов" not in (profile.full_name_enc or "")
    assert "+7999" not in (profile.contacts_enc or "")


async def test_unknown_skill_rejected(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.patch(PROFILE, json={"skills": ["cobol-2077"]}, headers=bearer(token))
    assert r.status_code == 422 and r.json()["error"]["code"] == "unknown_skills"


async def test_salary_range_validated_in_request(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.patch(
        PROFILE, json={"salary_min": 300_000, "salary_max": 100_000}, headers=bearer(token)
    )
    assert r.status_code == 422


async def test_salary_range_validated_against_stored_value(client: AsyncClient):
    token = await register_candidate(client)
    await client.patch(PROFILE, json={"salary_max": 100_000}, headers=bearer(token))
    r = await client.patch(PROFILE, json={"salary_min": 200_000}, headers=bearer(token))
    assert r.status_code == 400


async def test_null_for_required_field_is_422_not_500(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.patch(PROFILE, json={"is_hidden": None}, headers=bearer(token))
    assert r.status_code == 422 and r.json()["error"]["code"] == "null_not_allowed"


async def test_null_clears_optional_field(client: AsyncClient):
    token = await register_candidate(client)
    await client.patch(PROFILE, json={"city": "Казань"}, headers=bearer(token))
    r = await client.patch(PROFILE, json={"city": None}, headers=bearer(token))
    assert r.status_code == 200 and r.json()["city"] is None


async def test_contact_email_validated(client: AsyncClient):
    token = await register_candidate(client)
    r = await client.patch(
        PROFILE, json={"contacts": {"email": "not-an-email"}}, headers=bearer(token)
    )
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["loc"] == ["body", "contacts", "email"]
