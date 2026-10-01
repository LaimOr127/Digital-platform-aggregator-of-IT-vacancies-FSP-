"""Привязка аккаунта ФСП кандидатом: запрос кода -> подтверждение -> синхронизация.

Код приходит на почту владельца аккаунта ФСП — так подтверждается, что кандидат привязывает
свой аккаунт, а не чужие достижения. Один аккаунт ФСП — один профиль.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
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
from app.repositories.passports import PassportRepository
from app.schemas.fsp import AchievementOut, CategoryOut, FspLinkStartOut, FspStatusOut
from app.services.access import Action, Principal, policy
from app.services.categorization import DISCIPLINES
from app.services.fsp_sync import FspSyncer

_TAKEN = "этот аккаунт ФСП уже привязан к другому профилю"


class FspService:
    def __init__(
        self, session: AsyncSession, principal: Principal, client: FspClient, settings: Settings
    ) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.client = client
        self.settings = settings
        self.syncer = FspSyncer(session, client)
        self.audit = AuditRepository(session)

    async def status(self) -> FspStatusOut:
        profile = await self._profile()
        link = await FspLinkRepository(self.session, profile.id).own()
        pending = await FspVerificationRepository(self.session, profile.id).own()
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
        profile = await self._profile()
        athlete_id = athlete_id.strip().upper()
        if await FspLinkRepository(self.session, profile.id).own() is not None:
            raise ConflictError("аккаунт ФСП уже привязан — сначала отвяжите его")
        # занятость аккаунта ФСП проверяет уникальный индекс при подтверждении: под RLS
        # кандидат не видит чужие привязки, поэтому предварительная проверка бесполезна
        started = await self.client.start_verification(athlete_id)
        verifications = FspVerificationRepository(self.session, profile.id)
        await verifications.delete_own()
        self.session.add(
            FspVerification(
                profile_id=profile.id,
                athlete_id=athlete_id,
                request_id=started.request_id,
                expires_at=datetime.now(UTC) + timedelta(seconds=started.expires_in),
            )
        )
        await self.session.commit()
        demo = started.demo_code if self.settings.fsp_demo_codes else None
        return FspLinkStartOut(
            email_masked=started.email_masked, expires_in=started.expires_in, demo_code=demo
        )

    async def confirm(self, code: str) -> FspStatusOut:
        profile = await self._profile()
        verifications = FspVerificationRepository(self.session, profile.id)
        pending = await verifications.own()
        if pending is None or as_aware(pending.expires_at) <= datetime.now(UTC):
            raise FspVerificationError("код устарел — запросите новый")
        athlete_id = await self.client.confirm_verification(pending.request_id, code)
        if athlete_id != pending.athlete_id:
            raise FspVerificationError("код выдан для другого аккаунта ФСП")
        link = FspLink(profile_id=profile.id, athlete_id=athlete_id)
        self.session.add(link)
        await verifications.delete_own()
        try:
            await self.session.flush()
        except IntegrityError as exc:  # гонка: тот же аккаунт привязали параллельно
            await self.session.rollback()
            raise ConflictError(_TAKEN) from exc
        await self.syncer.sync(profile, link)
        await self.audit.record("fsp.linked", self.principal.user_id, "fsp_link", link.id)
        await self.session.commit()
        return await self.status()

    async def sync(self) -> FspStatusOut:
        profile = await self._profile()
        link = await self._link(profile)
        await self.syncer.sync(profile, link)
        await self.session.commit()
        return await self.status()

    async def unlink(self) -> None:
        profile = await self._profile()
        link = await self._link(profile)
        await self.session.delete(link)
        await self.syncer.clear(profile)
        # паспорт утверждал «подтверждено ФСП» — без привязки это уже неправда
        await PassportRepository(self.session).revoke_all(profile.id)
        await self.audit.record("fsp.unlinked", self.principal.user_id, "fsp_link", link.id)
        await self.session.commit()

    async def _profile(self) -> CandidateProfile:
        profile = await CandidateProfileRepository(self.session, self.principal.user_id).own()
        if profile is None:
            raise NotFoundError("profile not found")
        return profile

    async def _link(self, profile: CandidateProfile) -> FspLink:
        link = await FspLinkRepository(self.session, profile.id).own()
        if link is None:
            raise NotFoundError("аккаунт ФСП не привязан")
        return link
