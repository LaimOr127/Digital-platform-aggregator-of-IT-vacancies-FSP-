"""RLS — вторая линия защиты: даже если код приложения ошибётся с фильтром, PostgreSQL
не отдаст и не изменит чужие строки. Запросы идут напрямую в SQL под ролью приложения."""

import os

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import Database, set_rls_context
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


async def test_employer_reads_but_cannot_modify_profiles(client: AsyncClient, db: Database, app):
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
