"""Фоновая синхронизация ФСП: обновляет просроченные привязки, переживает ошибки."""

from datetime import timedelta

from httpx import AsyncClient

from app.core.config import Settings
from app.worker.jobs import FspSyncJob, HeartbeatJob, build_jobs
from tests.fake_fsp import CODE, result
from tests.helpers import bearer, register_candidate

FSP = "/api/v1/candidate/fsp"


async def linked(client: AsyncClient, athlete_id: str) -> str:
    token = await register_candidate(client)
    await client.post(f"{FSP}/link", json={"athlete_id": athlete_id}, headers=bearer(token))
    await client.post(f"{FSP}/confirm", json={"code": CODE}, headers=bearer(token))
    return token


async def test_sync_job_updates_due_profiles(client: AsyncClient, db, fsp):
    token = await linked(client, "FSP-2")
    athlete, results = fsp.athletes["FSP-2"]
    fsp.athletes["FSP-2"] = (athlete, [*results, result("r7", "security", "national", 1)])

    fresh_only = FspSyncJob(db, fsp, sync_every=timedelta(hours=6))
    assert await fresh_only.run() == 0  # только что синхронизирован — не трогаем

    job = FspSyncJob(db, fsp, sync_every=timedelta(seconds=0))
    assert await job.run() == 1
    body = (await client.get(FSP, headers=bearer(token))).json()
    assert [c["slug"] for c in body["categories"]] == ["security-elite"]


async def test_sync_job_survives_failing_profile(client: AsyncClient, db, fsp):
    await linked(client, "FSP-1")
    await linked(client, "FSP-2")
    del fsp.athletes["FSP-1"]  # аккаунт пропал в ФСП — ошибка только для этого профиля
    assert await FspSyncJob(db, fsp, sync_every=timedelta(seconds=0)).run() == 1


async def test_build_jobs(db, fsp):
    jobs = build_jobs(Settings(fsp_sync_interval_minutes=5), db, fsp)
    assert [type(j) for j in jobs] == [HeartbeatJob, FspSyncJob]
    await jobs[0].run()
