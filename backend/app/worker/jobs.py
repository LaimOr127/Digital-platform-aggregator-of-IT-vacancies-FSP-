"""Фоновые задачи. Каждая задача — наследник Job (паттерн Strategy); набор собирает build_jobs."""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import FieldCipher
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.core.logging import get_logger
from app.core.ratelimit_pg import purge_expired
from app.db.session import SYSTEM_ROLE, Database, set_rls_context
from app.integrations.fsp import FspClient
from app.integrations.notifier import Notifier
from app.models import CandidateProfile, FspLink
from app.repositories.audit import AuditRepository
from app.repositories.fsp import claim_due_links
from app.repositories.interviews import expire_overdue as expire_interviews
from app.repositories.offers import expire_overdue
from app.services.fsp_sync import FspSyncer, backoff
from app.services.outbox import OutboxDelivery

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
    """Обновляет достижения и категории привязанных профилей по расписанию next_sync_at.
    Ошибка профиля откладывает только его (пауза растёт), остальные не ждут; недоступность
    ФСП прерывает пакет; аккаунт, удалённый в ФСП, отвязывается (паспорт отзывается)."""

    name, interval_seconds = "fsp-sync", 300
    batch_size = 50
    lease = timedelta(minutes=10)  # столько пачка «занята» одним экземпляром worker

    def __init__(self, db: Database, client: FspClient, sync_every: timedelta) -> None:
        self.db = db
        self.client = client
        self.sync_every = sync_every

    async def run(self) -> int:  # type: ignore[override]
        async with self.db.sessionmaker() as session:
            await set_rls_context(session, None, SYSTEM_ROLE)
            # пачка захватывается атомарно: несколько экземпляров worker не дублируют работу
            targets = await claim_due_links(session, datetime.now(UTC), self.batch_size, self.lease)
            synced = 0
            for link_id, profile_id in targets:
                outcome = await self._sync_one(session, link_id, profile_id)
                synced += outcome == "synced"
                if outcome == "fsp_down":
                    break
            if targets:
                log.info("fsp sync: %d of %d profile(s) updated", synced, len(targets))
            return synced

    async def _sync_one(
        self, session: AsyncSession, link_id: uuid.UUID, profile_id: uuid.UUID
    ) -> str:
        syncer = FspSyncer(session, self.client, self.sync_every)
        try:
            link = await session.get(FspLink, link_id)
            profile = await session.get(CandidateProfile, profile_id)
            if link is None or profile is None:
                return "skipped"
            await syncer.sync(profile, link)
            await session.commit()
            return "synced"
        except NotFoundError:
            await session.rollback()
            await self._detach_missing(session, syncer, link_id, profile_id)
            return "detached"
        except Exception as exc:
            await session.rollback()
            await self._postpone(session, link_id)
            log.warning("fsp sync failed for link %s: %s", link_id, type(exc).__name__)
            return "fsp_down" if isinstance(exc, ServiceUnavailableError) else "failed"

    async def _postpone(self, session: AsyncSession, link_id: uuid.UUID) -> None:
        link = await session.get(FspLink, link_id)
        if link is not None:
            link.sync_failures += 1
            link.next_sync_at = datetime.now(UTC) + backoff(link.sync_failures)
            await session.commit()

    async def _detach_missing(
        self, session: AsyncSession, syncer: FspSyncer, link_id: uuid.UUID, profile_id: uuid.UUID
    ) -> None:
        link = await session.get(FspLink, link_id)
        profile = await session.get(CandidateProfile, profile_id)
        if link is None or profile is None:
            return
        await syncer.detach(profile, link)
        await AuditRepository(session).record("fsp.removed_in_fsp", None, "fsp_link", link_id)
        await session.commit()


class OfferExpiryJob(Job):
    """Офферы и приглашения на собеседование без ответа дольше срока — «истёк»."""

    name, interval_seconds = "offer-expiry", 600

    def __init__(self, db: Database) -> None:
        self.db = db

    async def run(self) -> int:  # type: ignore[override]
        async with self.db.sessionmaker() as session:
            await set_rls_context(session, None, SYSTEM_ROLE)
            now = datetime.now(UTC)
            expired = await expire_overdue(session, now) + await expire_interviews(session, now)
            await session.commit()
            if expired:
                log.info("offers expired: %d", expired)
            return expired


class RateLimitPurgeJob(Job):
    """Удаляет истёкшие счётчики лимитов (только при RATE_LIMIT_BACKEND=postgres)."""

    name, interval_seconds = "rate-limit-purge", 600

    def __init__(self, db: Database) -> None:
        self.db = db

    async def run(self) -> int:  # type: ignore[override]
        return await purge_expired(self.db.engine)


class OutboxJob(Job):
    """Отправка писем из очереди: часто, небольшими пачками, до опустошения очереди."""

    name, interval_seconds = "outbox", 5

    def __init__(self, db: Database, cipher: FieldCipher, notifier: Notifier, public_url: str):
        self.db = db
        self.cipher = cipher
        self.notifier = notifier
        self.public_url = public_url

    async def run(self) -> int:  # type: ignore[override]
        total = 0
        while True:
            async with self.db.sessionmaker() as session:
                await set_rls_context(session, None, SYSTEM_ROLE)
                delivery = OutboxDelivery(session, self.cipher, self.notifier, self.public_url)
                processed = await delivery.deliver_due()
            total += processed
            if processed == 0:
                return total


def build_jobs(
    settings: Settings, db: Database, client: FspClient, cipher: FieldCipher, notifier: Notifier
) -> list[Job]:
    sync_every = timedelta(minutes=settings.fsp_sync_interval_minutes)
    return [
        HeartbeatJob(),
        FspSyncJob(db, client, sync_every),
        OfferExpiryJob(db),
        OutboxJob(db, cipher, notifier, settings.public_url),
        *([RateLimitPurgeJob(db)] if settings.rate_limit_backend == "postgres" else []),
    ]
