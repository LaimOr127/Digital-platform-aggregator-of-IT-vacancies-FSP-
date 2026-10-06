"""Фоновая синхронизация ФСП: расписание, паузы после ошибок, отвязка удалённых аккаунтов."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.db.session import set_rls_context
from app.models import FspLink
from app.repositories.fsp import claim_due_links
from app.services.fsp_sync import backoff
from app.worker.jobs import FspSyncJob, HeartbeatJob, OfferExpiryJob, OutboxJob, build_jobs
from tests.fake_fsp import result
from tests.fake_notifier import MemoryNotifier
from tests.helpers import bearer, link_fsp, register_candidate

FSP = "/api/v1/candidate/fsp"
HOUR = timedelta(hours=1)


async def linked(client: AsyncClient, athlete_id: str) -> str:
    token = await register_candidate(client)
    await link_fsp(client, token, athlete_id)
    return token


async def make_due(db) -> None:
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        await session.execute(update(FspLink).values(next_sync_at=datetime.now(UTC) - HOUR))
        await session.commit()


async def links(db) -> dict[str, FspLink]:
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        return {
            link.athlete_id: link for link in (await session.execute(select(FspLink))).scalars()
        }


async def test_sync_job_follows_schedule(client: AsyncClient, db, fsp):
    token = await linked(client, "FSP-2")
    athlete, results = fsp.athletes["FSP-2"]
    fsp.athletes["FSP-2"] = (athlete, [*results, result("r7", "security", "national", 1)])
    job = FspSyncJob(db, fsp, sync_every=HOUR)
    assert await job.run() == 0  # только что синхронизирован — не по расписанию
    await make_due(db)
    assert await job.run() == 1
    body = (await client.get(FSP, headers=bearer(token))).json()
    assert [c["slug"] for c in body["categories"]] == ["security-elite"]


async def test_account_removed_in_fsp_is_detached(client: AsyncClient, db, fsp):
    token = await linked(client, "FSP-1")
    await linked(client, "FSP-2")
    await make_due(db)
    del fsp.athletes["FSP-1"]
    assert await FspSyncJob(db, fsp, sync_every=HOUR).run() == 1
    body = (await client.get(FSP, headers=bearer(token))).json()
    assert body["linked"] is False and body["verification_tier"] == "self_declared"


async def test_failing_link_is_postponed_and_does_not_block_queue(client: AsyncClient, db, fsp):
    await linked(client, "FSP-1")
    await linked(client, "FSP-2")
    await make_due(db)
    original = fsp.get_results

    async def broken_for_first(athlete_id: str):
        if athlete_id == "FSP-1":
            raise RuntimeError("boom")
        return await original(athlete_id)

    fsp.get_results = broken_for_first
    assert await FspSyncJob(db, fsp, sync_every=HOUR).run() == 1
    state = await links(db)
    assert state["FSP-1"].sync_failures == 1
    assert state["FSP-1"].next_sync_at.replace(tzinfo=UTC) > datetime.now(UTC)


async def test_fsp_outage_stops_the_batch(client: AsyncClient, db, fsp):
    await linked(client, "FSP-1")
    await linked(client, "FSP-2")
    await make_due(db)
    calls = []

    async def down(athlete_id: str):
        calls.append(athlete_id)
        raise ServiceUnavailableError("down")

    fsp.get_athlete = down
    assert await FspSyncJob(db, fsp, sync_every=HOUR).run() == 0
    assert len(calls) == 1  # после первой недоступности пакет прерван


def test_backoff_grows_and_is_capped():
    assert backoff(1) == timedelta(minutes=15)
    assert backoff(3) == timedelta(hours=1)
    assert backoff(50) == timedelta(hours=24)


async def test_build_jobs(db, fsp, app):
    jobs = build_jobs(
        Settings(fsp_sync_interval_minutes=5), db, fsp, app.state.cipher, MemoryNotifier()
    )
    assert [type(j) for j in jobs] == [HeartbeatJob, FspSyncJob, OfferExpiryJob, OutboxJob]
    await jobs[0].run()


async def test_due_links_are_claimed_once(client: AsyncClient, db):
    """Несколько экземпляров worker: пачку получает только один, второй — следующую."""
    await linked(client, "FSP-1")
    await linked(client, "FSP-2")
    await make_due(db)
    now = datetime.now(UTC)
    async with db.sessionmaker() as first, db.sessionmaker() as second:
        for session in (first, second):
            await set_rls_context(session, None, "system")
        batch = await claim_due_links(first, now, 1, timedelta(minutes=10))
        rest = await claim_due_links(second, now, 10, timedelta(minutes=10))
        again = await claim_due_links(first, now, 10, timedelta(minutes=10))
    assert len(batch) == 1 and len(rest) == 1 and batch != rest and again == []
