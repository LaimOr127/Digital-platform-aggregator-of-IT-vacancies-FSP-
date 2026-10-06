"""Кабинет работодателя: компания, вакансии, публикация после модерации, пагинация."""

from httpx import AsyncClient

from tests.helpers import (
    VACANCY,
    approve_company,
    bearer,
    company_id,
    create_admin,
    create_vacancy,
    register_employer,
)

VACANCIES = "/api/v1/employer/vacancies"


async def test_company_pending_after_registration(client: AsyncClient, premoderation):
    token = await register_employer(client, company="ООО Тест")
    r = await client.get("/api/v1/employer/company", headers=bearer(token))
    assert r.status_code == 200
    assert r.json()["name"] == "ООО Тест" and r.json()["status"] == "pending"


async def test_vacancy_crud(client: AsyncClient):
    token = await register_employer(client)
    vacancy = await create_vacancy(client, token)
    assert vacancy["status"] == "draft"
    assert {s["slug"] for s in vacancy["skills"]} == {"python", "postgresql"}

    url = f"{VACANCIES}/{vacancy['id']}"
    r = await client.patch(
        url, json={"title": "Senior Backend", "grade": "senior"}, headers=bearer(token)
    )
    assert r.status_code == 200 and r.json()["grade"] == "senior"
    assert (await client.get(url, headers=bearer(token))).json()["title"] == "Senior Backend"

    assert (await client.post(f"{url}/close", headers=bearer(token))).json()["status"] == "closed"
    assert (await client.delete(url, headers=bearer(token))).status_code == 204
    assert (await client.get(url, headers=bearer(token))).status_code == 404


async def test_vacancy_requires_salary_range(client: AsyncClient):
    token = await register_employer(client)
    body = {"title": "Без вилки", "grade": "junior", "work_format": "office"}
    r = await client.post(VACANCIES, json=body, headers=bearer(token))
    assert r.status_code == 422


async def test_partial_update_cannot_break_salary_range(client: AsyncClient):
    token = await register_employer(client)
    vacancy = await create_vacancy(client, token)
    r = await client.patch(
        f"{VACANCIES}/{vacancy['id']}", json={"salary_min": 500_000}, headers=bearer(token)
    )
    assert r.status_code == 400


async def test_publish_requires_approved_company(client: AsyncClient, db, app, premoderation):
    token = await register_employer(client)
    vacancy = await create_vacancy(client, token)
    publish = f"{VACANCIES}/{vacancy['id']}/publish"
    assert (await client.post(publish, headers=bearer(token))).status_code == 403

    admin = await create_admin(db, app)
    await approve_company(client, admin, await company_id(client, token))
    r = await client.post(publish, headers=bearer(token))
    assert r.status_code == 200
    assert r.json()["status"] == "active" and r.json()["expires_at"]


async def test_cursor_pagination(client: AsyncClient):
    token = await register_employer(client)
    created = [(await create_vacancy(client, token, title=f"Вакансия {i}"))["id"] for i in range(5)]
    seen, cursor = [], None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = (await client.get(VACANCIES, params=params, headers=bearer(token))).json()
        seen += [v["id"] for v in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(created))


async def test_invalid_cursor(client: AsyncClient):
    token = await register_employer(client)
    r = await client.get(VACANCIES, params={"cursor": "garbage"}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_cursor"


async def test_status_filter(client: AsyncClient):
    token = await register_employer(client)
    v = await create_vacancy(client, token)
    await create_vacancy(client, token)
    await client.post(f"{VACANCIES}/{v['id']}/close", headers=bearer(token))
    r = await client.get(VACANCIES, params={"status": "closed"}, headers=bearer(token))
    assert [i["id"] for i in r.json()["items"]] == [v["id"]]


async def test_vacancy_patch_null_semantics(client: AsyncClient):
    token = await register_employer(client)
    vacancy = await create_vacancy(client, token, city="Москва")
    url = f"{VACANCIES}/{vacancy['id']}"
    r = await client.patch(url, json={"city": None}, headers=bearer(token))
    assert r.status_code == 200 and r.json()["city"] is None
    for field in ("title", "salary_min", "grade"):
        r = await client.patch(url, json={field: None}, headers=bearer(token))
        assert r.status_code == 422, field


async def test_blocked_company_loses_vacancies(client: AsyncClient, db, app):
    token = await register_employer(client)
    admin = await create_admin(db, app)
    cid = await company_id(client, token)
    await approve_company(client, admin, cid)
    vacancy = await create_vacancy(client, token)
    await client.post(f"{VACANCIES}/{vacancy['id']}/publish", headers=bearer(token))

    r = await client.post(
        f"/api/v1/admin/companies/{cid}/status",
        json={"status": "blocked", "reason": "фишинг"},
        headers=bearer(admin),
    )
    assert r.status_code == 200
    url = f"{VACANCIES}/{vacancy['id']}"
    assert (await client.get(url, headers=bearer(token))).json()["status"] == "blocked"
    assert (
        await client.patch(url, json={"title": "Новое"}, headers=bearer(token))
    ).status_code == 403
    r = await client.post(VACANCIES, json=VACANCY, headers=bearer(token))
    assert r.status_code == 403


async def test_company_works_right_away_without_premoderation(client: AsyncClient):
    """По ТЗ модерация на MVP не требуется: компания сразу ищет кандидатов (постмодерация)."""
    token = await register_employer(client)
    company = (await client.get("/api/v1/employer/company", headers=bearer(token))).json()
    assert company["status"] == "approved"
    r = await client.get("/api/v1/employer/catalog/categories", headers=bearer(token))
    assert r.status_code == 200


async def test_owner_edits_company_profile(client: AsyncClient):
    token = await register_employer(client)
    r = await client.patch(
        "/api/v1/employer/company",
        json={
            "description": "Делаем платёжную платформу",
            "industry": "Финтех",
            "contact_email": "hr@example.org",
            "website": "https://example.org",
        },
        headers=bearer(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["industry"] == "Финтех" and body["contact_email"] == "hr@example.org"
    bad = await client.patch(
        "/api/v1/employer/company", json={"contact_email": "nope"}, headers=bearer(token)
    )
    assert bad.status_code == 422
