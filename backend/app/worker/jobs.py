"""Фоновые задачи. Каждая задача — наследник Job (паттерн Strategy); набор собирает build_jobs."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.session import SYSTEM_ROLE, Database, set_rls_context
from app.integrations.fsp import FspClient
from app.models import CandidateProfile, FspLink
from app.repositories.fsp import links_due
from app.services.fsp_sync import FspSyncer

log = get_logger(__name__)


class Job(ABC):
    name: str
    interval_seconds: int

    @abstractmethod
    async def run(self) -> None: ...


class HeartbeatJob(Job):
    name, interval_seconds = "heartbeat", 60

    async def run(self) -> None:
        log.info("worker alive")


class FspSyncJob(Job):
    """Периодически обновляет достижения и категории привязанных профилей из ФСП.
    Ошибка одного профиля не останавливает остальные."""

    name, interval_seconds = "fsp-sync", 300
    batch_size = 50

    def __init__(self, db: Database, client: FspClient, sync_every: timedelta) -> None:
        self.db = db
        self.client = client
        self.sync_every = sync_every

    async def run(self) -> int:  # type: ignore[override]
        async with self.db.sessionmaker() as session:
            await set_rls_context(session, None, SYSTEM_ROLE)
            due = await links_due(session, datetime.now(UTC) - self.sync_every, self.batch_size)
            # id сохраняем заранее: после rollback объекты сессии устаревают
            targets = [(link.id, link.profile_id) for link in due]
            synced = 0
            for link_id, profile_id in targets:
                try:
                    link = await session.get(FspLink, link_id)
                    profile = await session.get(CandidateProfile, profile_id)
                    if link is not None and profile is not None:
                        await FspSyncer(session, self.client).sync(profile, link)
                        await session.commit()
                        synced += 1
                except Exception:
                    await session.rollback()
                    log.exception("fsp sync failed for link %s", link_id)
            if due:
                log.info("fsp sync: %d of %d profile(s) updated", synced, len(due))
            return synced


def build_jobs(settings: Settings, db: Database, client: FspClient) -> list[Job]:
    sync_every = timedelta(minutes=settings.fsp_sync_interval_minutes)
    return [HeartbeatJob(), FspSyncJob(db, client, sync_every)]
