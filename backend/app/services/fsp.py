"""Привязка аккаунта ФСП кандидатом: запрос кода -> подтверждение -> синхронизация.

Код приходит на почту владельца аккаунта ФСП — так подтверждается, что кандидат привязывает
свой аккаунт, а не чужие достижения. Один аккаунт ФСП — один профиль (уникальный индекс).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.timeutil import as_aware
from app.integrations.fsp import FspClient, FspVerificationError
from app.models import CandidateProfile, FspLink, FspVerification
from app.repositories.audit import AuditRepository
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.fsp import (
    CategoryRepository,
    FspAchievementRepository,
    FspLinkRepository,
    FspVerificationRepository,
)
from app.schemas.fsp import AchievementOut, CategoryOut, FspLinkStartOut, FspStatusOut
from app.services.access import Action, Principal, policy
from app.services.categorization import DISCIPLINES
from app.services.fsp_sync import FspSyncer

log = get_logger(__name__)
_TAKEN = "этот аккаунт ФСП уже привязан к другому профилю"
_ALREADY_LINKED = "аккаунт ФСП уже привязан — сначала отвяжите его"


class FspService:
    def __init__(
        self, session: AsyncSession, principal: Principal, client: FspClient, settings: Settings
    ) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.client = client
        self.settings = settings
        self.profiles = CandidateProfileRepository(session, principal.user_id)
        self.syncer = FspSyncer(
            session, client, timedelta(minutes=settings.fsp_sync_interval_minutes)
        )
        self.audit = AuditRepository(session)

    async def status(self) -> FspStatusOut:
        profile = await self.profiles.own_or_404()
        link = await FspLinkRepository(self.session, profile.id).own()
        pending = await self._live_pending(profile)
        achievements = await FspAchievementRepository(self.session, profile.id).all()
        categories = await CategoryRepository(self.session).for_profile(profile.id)
        return FspStatusOut(
            linked=link is not None,
            athlete_id=link.athlete_id if link else None,
            rank=link.rank if link else None,
            region=link.region if link else None,
            last_synced_at=link.last_synced_at if link else None,
            pending_athlete_id=pending.athlete_id if pending and not link else None,
            verification_tier=profile.verification_tier,
            demo_mode=self.settings.fsp_demo_codes,
            achievements=[
                AchievementOut(
                    external_id=a.external_id,
                    discipline=a.discipline,
                    discipline_title=DISCIPLINES.get(a.discipline, a.discipline),
                    competition_title=a.competition_title,
                    level=a.level,
                    date=a.date,
                    place=a.place,
                    stage=a.stage,
                    role=a.role,
                    team=a.team,
                )
                for a in achievements
            ],
            categories=[
                CategoryOut(
                    slug=c.slug, discipline=c.discipline, tier=c.tier, title=c.title, reasons=r
                )
                for c, r in categories
            ],
        )

    async def start(self, athlete_id: str) -> FspLinkStartOut:
        profile = await self.profiles.own_or_404(for_update=True)
        if await FspLinkRepository(self.session, profile.id).own() is not None:
            raise ConflictError(_ALREADY_LINKED)
        # занятость аккаунта ФСП проверяет уникальный индекс при подтверждении: под RLS
        # кандидат не видит чужие привязки, поэтому предварительная проверка бесполезна
        started = await self.client.start_verification(athlete_id)
        await FspVerificationRepository(self.session, profile.id).delete_own()
        self.session.add(
            FspVerification(
                profile_id=profile.id,
                athlete_id=athlete_id,
                request_id=started.request_id,
                expires_at=datetime.now(UTC) + timedelta(seconds=started.expires_in),
            )
        )
        await self._commit_or_conflict("запрос кода уже выполняется — повторите через секунду")
        demo = started.demo_code if self.settings.fsp_demo_codes else None
        return FspLinkStartOut(
            email_masked=started.email_masked, expires_in=started.expires_in, demo_code=demo
        )

    async def confirm(self, code: str) -> FspStatusOut:
        profile = await self.profiles.own_or_404(for_update=True)
        if await FspLinkRepository(self.session, profile.id).own() is not None:
            raise ConflictError(_ALREADY_LINKED)
        pending = await self._live_pending(profile)
        if pending is None:
            raise FspVerificationError("код устарел — запросите новый")
        athlete_id = await self.client.confirm_verification(pending.request_id, code)
        if athlete_id != pending.athlete_id:
            raise FspVerificationError("код выдан для другого аккаунта ФСП")
        link = FspLink(profile_id=profile.id, athlete_id=athlete_id)
        self.session.add(link)
        await self._commit_or_conflict(_TAKEN, flush_only=True)
        await FspVerificationRepository(self.session, profile.id).delete_own()
        await self.audit.record("fsp.linked", self.principal.user_id, "fsp_link", link.id)
        # код одноразовый и уже использован в ФСП: привязку фиксируем до загрузки данных,
        # чтобы сбой ФСП на этом шаге не заставлял кандидата запрашивать новый код
        await self.session.commit()
        await self._sync_best_effort(profile, link)
        return await self.status()

    async def sync(self) -> FspStatusOut:
        profile = await self.profiles.own_or_404()
        link = await self._link(profile)
        await self.syncer.sync(profile, link)
        await self.session.commit()
        return await self.status()

    async def unlink(self) -> None:
        profile = await self.profiles.own_or_404(for_update=True)
        link = await self._link(profile)
        link_id = link.id
        await self.syncer.detach(profile, link)
        await self.audit.record("fsp.unlinked", self.principal.user_id, "fsp_link", link_id)
        await self.session.commit()

    async def _sync_best_effort(self, profile: CandidateProfile, link: FspLink) -> None:
        """Данные ФСП недоступны — привязка остаётся, worker догрузит их в ближайший прогон."""
        try:
            await self.syncer.sync(profile, link)
            await self.session.commit()
        except AppError:
            await self.session.rollback()
            log.warning("fsp data unavailable right after linking, deferred to worker")

    async def _live_pending(self, profile: CandidateProfile) -> FspVerification | None:
        pending = await FspVerificationRepository(self.session, profile.id).own()
        if pending is None or as_aware(pending.expires_at) <= datetime.now(UTC):
            return None
        return pending

    async def _link(self, profile: CandidateProfile) -> FspLink:
        link = await FspLinkRepository(self.session, profile.id).own()
        if link is None:
            raise NotFoundError("аккаунт ФСП не привязан")
        return link

    async def _commit_or_conflict(self, message: str, flush_only: bool = False) -> None:
        """Нарушение уникальности (гонка параллельных запросов) — 409 с понятным текстом."""
        try:
            await (self.session.flush() if flush_only else self.session.commit())
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(message) from exc
