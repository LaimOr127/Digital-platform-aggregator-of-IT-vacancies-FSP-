"""Радар зарплат (k-анонимность), путь роста и удаление аккаунта кандидата."""

from httpx import AsyncClient
from sqlalchemy import select

from app.models import AuditLog, CandidateProfile, User
from tests.flows import approved_employer, send, verified_candidate
from tests.helpers import PASSWORD, bearer, create_vacancy, register_candidate

PROFILE = "/api/v1/candidate/profile"
SALARY = "/api/v1/candidate/insights/salary"
GROWTH = "/api/v1/candidate/insights/growth"


async def publish(client: AsyncClient, token: str, **fields) -> None:
    vacancy = await create_vacancy(client, token, **fields)
    r = await client.post(
        f"/api/v1/employer/vacancies/{vacancy['id']}/publish", headers=bearer(token)
    )
    assert r.status_code == 200, r.text


async def market(
    client: AsyncClient, db, app, companies: int, per_company: int, **fields
) -> list[dict]:
    employers = [
        await approved_employer(client, db, app, name=f"ООО Рынок {i}") for i in range(companies)
    ]
    for i, employer in enumerate(employers):
        for j in range(per_company):
            low = 200_000 + 10_000 * (i * per_company + j)
            await publish(
                client, employer["token"], salary_min=low, salary_max=low + 100_000, **fields
            )
    return employers


async def candidate(
    client: AsyncClient, salary: int, grade: str = "middle", skills=("python",)
) -> str:
    token = await register_candidate(client)
    r = await client.patch(
        PROFILE,
        json={"grade": grade, "skills": list(skills), "salary_min": salary},
        headers=bearer(token),
    )
    assert r.status_code == 200, r.text
    return token


async def test_radar_shows_market_only_for_large_enough_groups(client: AsyncClient, db, app):
    await market(client, db, app, companies=2, per_company=3)  # 6 вакансий, но 2 компании
    me = await candidate(client, 150_000)
    radar = (await client.get(SALARY, headers=bearer(me))).json()
    assert radar["vacancies"] is None and radar["min_group"] == 5  # компаний мало — скрыто
    assert radar["skills"] == ["Python"] and radar["grade"] == "middle"

    await market(client, db, app, companies=1, per_company=1)  # третья компания
    radar = (await client.get(SALARY, headers=bearer(me))).json()
    band = radar["vacancies"]
    # + по одной вакансии middle/Python, которую публикует approved_employer у каждой компании
    assert band["count"] == 10 and band["p25"] <= band["median"] <= band["p75"]
    assert radar["expectation"] == 150_000 and radar["position"] == "below"
    middle = next(step for step in radar["ladder"] if step["grade"] == "middle")
    assert middle["band"] == band


async def test_peers_need_five_other_candidates(client: AsyncClient):
    me = await candidate(client, 300_000)
    for salary in (210_000, 220_000, 230_000, 240_000):
        await candidate(client, salary)
    assert (await client.get(SALARY, headers=bearer(me))).json()["peers"] is None  # 4 коллеги
    await candidate(client, 250_000)
    peers = (await client.get(SALARY, headers=bearer(me))).json()["peers"]
    assert peers["count"] == 5 and peers["median"] == 230_000  # себя не учитываем


async def test_growth_path_lists_missing_skills_for_next_grade(client: AsyncClient, db, app):
    await market(
        client, db, app, companies=1, per_company=2, grade="senior", skills=["python", "go"]
    )
    me = await candidate(client, 250_000, grade="middle", skills=("python",))
    growth = (await client.get(GROWTH, headers=bearer(me))).json()
    assert growth["current_grade"] == "middle" and growth["target_grade"] == "senior"
    assert growth["vacancies_considered"] == 2
    assert growth["missing_skills"] == [{"slug": "go", "name": "Go", "share": 1.0}]
    assert [s["slug"] for s in growth["strengths"]] == ["python"]
    assert growth["salary_target"] is None  # одна компания — медиана скрыта
    assert "ФСП" in growth["fsp_next"]
    no_grade = await register_candidate(client)
    assert (await client.get(GROWTH, headers=bearer(no_grade))).status_code == 409


async def test_employer_market_hint(client: AsyncClient, db, app):
    employers = await market(client, db, app, companies=3, per_company=2)
    r = await client.get(
        "/api/v1/employer/insights/salary",
        params={"grade": "middle", "skills": ["python"]},
        headers=bearer(employers[0]["token"]),
    )
    assert r.status_code == 200 and r.json()["vacancies"]["count"] == 9  # 3 × 2 + 3 базовых
    me = await candidate(client, 100_000)
    assert (
        await client.get(
            "/api/v1/employer/insights/salary", params={"grade": "middle"}, headers=bearer(me)
        )
    ).status_code == 403


async def test_offers_feed_the_radar(client: AsyncClient, db, app):
    employers = [await approved_employer(client, db, app, name=f"ООО Оффер {i}") for i in range(3)]
    candidates = [await verified_candidate(client, f"FSP-{1 + i % 2}") for i in range(2)]
    for i, employer in enumerate(employers):
        for person in candidates:
            if (i, person["anon_id"]) != (2, candidates[1]["anon_id"]):
                await send(
                    client, person, employer, salary_min=300_000 + 10_000 * i, salary_max=350_000
                )
    me = await candidate(client, 320_000)
    offers = (await client.get(SALARY, headers=bearer(me))).json()["offers"]
    assert offers["count"] == 5


async def test_candidate_deletes_account_with_all_data(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    person = await verified_candidate(client)
    await send(client, person, employer)
    headers = bearer(person["token"])
    wrong = await client.post(
        "/api/v1/candidate/account/delete", json={"password": "wrong"}, headers=headers
    )
    assert wrong.status_code == 401
    r = await client.post(
        "/api/v1/candidate/account/delete", json={"password": PASSWORD}, headers=headers
    )
    assert r.status_code == 204
    assert (await client.get(PROFILE, headers=headers)).status_code == 401  # сессии больше нет
    async with db.sessionmaker() as session:
        from app.db.session import set_rls_context

        await set_rls_context(session, None, "system")
        profiles = (await session.execute(select(CandidateProfile.anon_id))).scalars().all()
        users = (await session.execute(select(User.role))).scalars().all()
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert person["anon_id"] not in [str(p) for p in profiles] and "candidate" not in users
    assert "account.deleted" in actions
    offers = (await client.get("/api/v1/employer/offers", headers=bearer(employer["token"]))).json()
    assert offers["items"] == []  # офферы удалены вместе с профилем


async def test_employer_cannot_delete_through_candidate_endpoint(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    r = await client.post(
        "/api/v1/candidate/account/delete",
        json={"password": PASSWORD},
        headers=bearer(employer["token"]),
    )
    assert r.status_code == 403
