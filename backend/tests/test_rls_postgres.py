"""RLS — вторая линия защиты: даже если код приложения ошибётся с фильтром, PostgreSQL
не отдаст и не изменит чужие строки. Запросы идут напрямую в SQL под ролью приложения."""

import os

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.ratelimit_pg import PostgresRateLimiter, purge_expired
from app.db.session import Database, set_rls_context
from tests.flows import send
from tests.helpers import (
    approve_company,
    bearer,
    company_id,
    create_admin,
    create_vacancy,
    link_fsp,
    register_candidate,
    register_employer,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"), reason="нужен TEST_POSTGRES_URL (PostgreSQL)"
)


async def _user_ids(db: Database, role: str) -> list:
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        rows = await session.execute(
            text("SELECT id FROM users WHERE role = :r ORDER BY created_at"), {"r": role}
        )
        return list(rows.scalars())


async def _scalar(db: Database, user_id, role: str, sql: str) -> int:
    async with db.sessionmaker() as session:
        await set_rls_context(session, user_id, role)
        value = (await session.execute(text(sql))).scalar_one()
        await session.commit()
        return value


async def test_candidate_sees_and_updates_only_own_profile(client: AsyncClient, db: Database):
    await register_candidate(client, name="Алиса")
    await register_candidate(client, name="Боб")
    alice, _bob = await _user_ids(db, "candidate")

    visible = await _scalar(db, alice, "candidate", "SELECT count(*) FROM candidate_profiles")
    assert visible == 1
    updated = await _scalar(
        db,
        alice,
        "candidate",
        "WITH u AS (UPDATE candidate_profiles SET city = 'hack' RETURNING 1) "
        "SELECT count(*) FROM u",
    )
    assert updated == 1  # только своя строка


async def test_no_context_sees_nothing(client: AsyncClient, db: Database):
    await register_candidate(client)
    assert await _scalar(db, None, "", "SELECT count(*) FROM candidate_profiles") == 0


async def test_employer_reads_but_cannot_modify_profiles(
    client: AsyncClient, db: Database, app, premoderation
):
    visible_sql = "SELECT count(*) FROM candidate_profiles"
    await register_candidate(client)
    hidden = await register_candidate(client)
    await client.patch(
        "/api/v1/candidate/profile", json={"is_hidden": True}, headers=bearer(hidden)
    )
    token = await register_employer(client)
    (employer,) = await _user_ids(db, "employer")
    # компания на модерации — каталог кандидатов закрыт даже на уровне БД
    assert await _scalar(db, employer, "employer", visible_sql) == 0
    await approve_company(client, await create_admin(db, app), await company_id(client, token))
    # одобренная компания видит только нескрытые профили
    assert await _scalar(db, employer, "employer", visible_sql) == 1
    updated = await _scalar(
        db,
        employer,
        "employer",
        "WITH u AS (UPDATE candidate_profiles SET city = 'hack' RETURNING 1) "
        "SELECT count(*) FROM u",
    )
    assert updated == 0


async def test_draft_vacancy_invisible_to_other_company(client: AsyncClient, db: Database):
    owner = await register_employer(client, company="Компания A")
    await register_employer(client, company="Компания B")
    await create_vacancy(client, owner)
    owner_id, intruder_id = await _user_ids(db, "employer")
    assert await _scalar(db, owner_id, "employer", "SELECT count(*) FROM vacancies") == 1
    assert await _scalar(db, intruder_id, "employer", "SELECT count(*) FROM vacancies") == 0
    deleted = await _scalar(
        db,
        intruder_id,
        "employer",
        "WITH d AS (DELETE FROM vacancies RETURNING 1) SELECT count(*) FROM d",
    )
    assert deleted == 0


async def test_unpublished_vacancies_invisible_to_others(client: AsyncClient, db: Database, app):
    owner = await register_employer(client, company="Компания A")
    await register_employer(client, company="Компания B")
    admin = await create_admin(db, app)
    await approve_company(client, admin, await company_id(client, owner))
    active = await create_vacancy(client, owner)
    await client.post(f"/api/v1/employer/vacancies/{active['id']}/publish", headers=bearer(owner))
    _owner_id, other_id = await _user_ids(db, "employer")
    count_sql = "SELECT count(*) FROM vacancies"
    assert await _scalar(db, other_id, "employer", count_sql) == 1  # опубликованная видна
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(text("UPDATE vacancies SET expires_at = now() - interval '1 day'"))
        await session.commit()
    assert await _scalar(db, other_id, "employer", count_sql) == 0  # истёкшая скрыта


async def test_audit_log_is_append_only(client: AsyncClient, db: Database):
    await register_candidate(client)
    async with db.sessionmaker() as session:
        with pytest.raises(DBAPIError, match="permission denied"):
            await session.execute(text("DELETE FROM audit_log"))


async def test_app_role_cannot_rewrite_migration_state(db: Database):
    async with db.sessionmaker() as session:
        with pytest.raises(DBAPIError, match="permission denied"):
            await session.execute(text("DELETE FROM alembic_version"))


async def test_app_role_cannot_change_schema(db: Database):
    async with db.sessionmaker() as session:
        with pytest.raises(DBAPIError, match="permission denied"):
            await session.execute(text("CREATE TABLE _probe (id int)"))


async def test_fsp_link_hidden_from_employers_and_others(client: AsyncClient, db: Database, app):
    """athlete_id деанонимизирует кандидата: привязку видит только владелец."""
    owner = await register_candidate(client)
    await link_fsp(client, owner)
    await register_candidate(client)
    employer = await register_employer(client)
    await approve_company(client, await create_admin(db, app), await company_id(client, employer))
    owner_id, other_id = await _user_ids(db, "candidate")
    (employer_id,) = await _user_ids(db, "employer")
    sql = "SELECT count(*) FROM fsp_links"
    assert await _scalar(db, owner_id, "candidate", sql) == 1
    assert await _scalar(db, other_id, "candidate", sql) == 0
    assert await _scalar(db, employer_id, "employer", sql) == 0


async def test_passports_readable_only_by_owner(client: AsyncClient, db: Database):
    owner = await register_candidate(client)
    await client.post("/api/v1/candidate/passport", json={"show_name": True}, headers=bearer(owner))
    await register_candidate(client)
    owner_id, other_id = await _user_ids(db, "candidate")
    sql = "SELECT count(*) FROM passports"
    assert await _scalar(db, owner_id, "candidate", sql) == 1
    assert await _scalar(db, other_id, "candidate", sql) == 0
    assert await _scalar(db, None, "", sql) == 0  # публичная проверка идёт через контекст system


async def test_categories_dictionary_is_read_only_for_users(client: AsyncClient, db: Database):
    await register_candidate(client)
    (candidate_id,) = await _user_ids(db, "candidate")
    assert await _scalar(db, candidate_id, "candidate", "SELECT count(*) FROM categories") == 15
    changed = await _scalar(
        db,
        candidate_id,
        "candidate",
        "WITH u AS (UPDATE categories SET title = 'hack' RETURNING 1) SELECT count(*) FROM u",
    )
    assert changed == 0


async def test_offers_visible_only_to_parties(client: AsyncClient, db: Database, app):
    """Оффер и собеседование видят только кандидат и сотрудники компании-отправителя."""
    employer = await register_employer(client, company="Компания A")
    rival = await register_employer(client, company="Компания B")
    admin = await create_admin(db, app)
    for token in (employer, rival):
        await approve_company(client, admin, await company_id(client, token))
    vacancy = await create_vacancy(client, employer)
    await client.post(
        f"/api/v1/employer/vacancies/{vacancy['id']}/publish", headers=bearer(employer)
    )
    candidate = await register_candidate(client)
    await register_candidate(client)
    # принять приглашение можно, только указав контакт
    await client.patch(
        "/api/v1/candidate/profile",
        json={"contacts": {"telegram": "@anna"}},
        headers=bearer(candidate),
    )
    anon_id = (await client.get("/api/v1/candidate/profile", headers=bearer(candidate))).json()[
        "anon_id"
    ]
    await send(
        client,
        {"token": candidate, "anon_id": anon_id},
        {"token": employer, "vacancy": vacancy},
        salary_min=1,
        salary_max=2,
    )

    employer_id, rival_id = await _user_ids(db, "employer")
    candidate_id, other_id = await _user_ids(db, "candidate")
    for table in ("offers", "interviews"):
        sql = f"SELECT count(*) FROM {table}"  # noqa: S608 - имя таблицы из списка выше
        assert await _scalar(db, employer_id, "employer", sql) == 1, table
        assert await _scalar(db, candidate_id, "candidate", sql) == 1, table
        assert await _scalar(db, rival_id, "employer", sql) == 0, table
        assert await _scalar(db, other_id, "candidate", sql) == 0, table


async def test_postgres_rate_limiter_is_shared_and_sliding(db: Database):
    """Счётчики в PostgreSQL: два «процесса» (два лимитера) делят один лимит."""
    now = [3_600.0 * 1000]  # начало часового окна
    first = PostgresRateLimiter(db.engine, clock=lambda: now[0])
    second = PostgresRateLimiter(db.engine, clock=lambda: now[0])
    assert await first.hit("mfa:shared", 2, 3600)
    assert await second.hit("mfa:shared", 2, 3600)
    assert not await first.hit("mfa:shared", 2, 3600)
    # скользящее окно: в середине следующего часа учитывается половина прошлых попыток
    now[0] += 3600 + 1800
    assert not await second.hit("mfa:shared", 2, 3600)  # 1 + 3 * 0.5 = 2.5 > 2
    now[0] += 2160  # 10% третьего часа: 1 + 1 * 0.9 = 1.9 <= 2
    assert await first.hit("mfa:shared", 2, 3600)
    now[0] += 3600 * 3
    assert await purge_expired(db.engine) >= 1


async def test_applications_and_attempts_visible_only_to_parties(client: AsyncClient, db, app):
    """Приглашение видят только кандидат и компания; попытки теста — только сам кандидат."""
    from tests.assessment_flow import survey
    from tests.flows import APPLICATIONS, approved_employer, invitation_body, verified_candidate

    employer = await approved_employer(client, db, app, name="Компания A")
    await approved_employer(client, db, app, name="Компания B")
    candidate = await verified_candidate(client)
    await register_candidate(client)
    r = await client.post(
        APPLICATIONS, json=invitation_body(candidate, employer), headers=bearer(employer["token"])
    )
    assert r.status_code == 201
    await survey(client, candidate["token"])
    started = await client.post(
        "/api/v1/candidate/assessment/attempts",
        json={"grade": "middle"},
        headers=bearer(candidate["token"]),
    )
    assert started.status_code == 201

    employer_id, rival_id = await _user_ids(db, "employer")
    candidate_id, other_id = await _user_ids(db, "candidate")
    sql = "SELECT count(*) FROM applications"
    assert await _scalar(db, employer_id, "employer", sql) == 1
    assert await _scalar(db, candidate_id, "candidate", sql) == 1
    assert await _scalar(db, rival_id, "employer", sql) == 0
    assert await _scalar(db, other_id, "candidate", sql) == 0
    attempts = "SELECT count(*) FROM assessments"
    assert await _scalar(db, candidate_id, "candidate", attempts) == 1
    assert await _scalar(db, other_id, "candidate", attempts) == 0
    assert await _scalar(db, employer_id, "employer", attempts) == 0  # ответы не видит никто


async def test_tasks_and_answers_visible_only_to_parties(client: AsyncClient, db, app):
    """Активную задачу видят кандидаты, закрытую — только компания; ответ — автор и компания."""
    from tests.assessment_flow import survey
    from tests.flows import approved_employer

    owner = await approved_employer(client, db, app, name="Компания A")
    await approved_employer(client, db, app, name="Компания B")
    body = {"title": "Задача", "body": "Как ускорить ленту?", "specialization": "backend"}
    tasks = "/api/v1/employer/tasks"
    first = (await client.post(tasks, json=body, headers=bearer(owner["token"]))).json()
    closed = (await client.post(tasks, json=body, headers=bearer(owner["token"]))).json()
    await client.post(f"{tasks}/{closed['id']}/close", headers=bearer(owner["token"]))
    author = await register_candidate(client)
    await register_candidate(client)
    await survey(client, author)
    r = await client.post(
        f"/api/v1/candidate/tasks/{first['id']}/answers",
        json={"answer": "Индекс по user_id и курсорная пагинация вместо OFFSET."},
        headers=bearer(author),
    )
    assert r.status_code == 201, r.text

    owner_id, rival_id = await _user_ids(db, "employer")
    author_id, other_id = await _user_ids(db, "candidate")
    task_sql = "SELECT count(*) FROM employer_tasks"
    assert await _scalar(db, owner_id, "employer", task_sql) == 2
    assert await _scalar(db, other_id, "candidate", task_sql) == 1  # закрытая не видна
    assert await _scalar(db, rival_id, "employer", task_sql) == 0
    answers = "SELECT count(*) FROM task_answers"
    assert await _scalar(db, author_id, "candidate", answers) == 1
    assert await _scalar(db, owner_id, "employer", answers) == 1
    assert await _scalar(db, other_id, "candidate", answers) == 0
    assert await _scalar(db, rival_id, "employer", answers) == 0


async def test_vacancy_complaints_visible_only_to_author_and_moderator(
    client: AsyncClient, db, app
):
    """Жалобу видят автор и модератор; компания, на которую жалуются, и другие кандидаты — нет."""
    from tests.flows import approved_employer

    owner = await approved_employer(client, db, app, name="Компания A")
    author = await register_candidate(client)
    await register_candidate(client)
    r = await client.post(
        f"/api/v1/candidate/vacancies/{owner['vacancy']['id']}/complaint",
        json={"reason": "salary"},
        headers=bearer(author),
    )
    assert r.status_code == 204, r.text

    (owner_id,) = await _user_ids(db, "employer")
    author_id, other_id = await _user_ids(db, "candidate")
    (admin_id, *_) = await _user_ids(db, "admin")
    sql = "SELECT count(*) FROM vacancy_complaints"
    assert await _scalar(db, author_id, "candidate", sql) == 1
    assert await _scalar(db, admin_id, "admin", sql) == 1
    assert await _scalar(db, other_id, "candidate", sql) == 0
    assert await _scalar(db, owner_id, "employer", sql) == 0


async def test_section_views_visible_only_to_owner(client: AsyncClient, db: Database):
    """Отметки «раздел просмотрен» другого пользователя не видны и не меняются."""
    alice = await register_candidate(client, name="Алиса")
    await register_candidate(client, name="Боб")
    r = await client.post(
        "/api/v1/candidate/updates/seen", json={"section": "offers"}, headers=bearer(alice)
    )
    assert r.status_code == 204, r.text
    alice_id, bob_id = await _user_ids(db, "candidate")
    sql = "SELECT count(*) FROM section_views"
    assert await _scalar(db, alice_id, "candidate", sql) == 1
    assert await _scalar(db, bob_id, "candidate", sql) == 0
