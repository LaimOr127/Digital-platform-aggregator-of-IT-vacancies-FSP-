"""Синхронизация профиля с ФСП: результаты -> достижения -> категории -> уровень подтверждения.
Используется кабинетом кандидата и фоновой задачей worker.

Паспорт навыков — подписанный снимок: если данные ФСП изменились, действующий паспорт
отзывается (иначе он продолжал бы подтверждать то, чего уже нет).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.fsp import FspClient, FspResult
from app.models import CandidateProfile, FspAchievement, FspLink
from app.models.enums import VerificationTier
from app.repositories.fsp import CategoryRepository, FspAchievementRepository, lock_link
from app.repositories.passports import PassportRepository
from app.services.categorization import Evidence, categorize

log = get_logger(__name__)
_MAX_BACKOFF = timedelta(hours=24)
_FIRST_BACKOFF = timedelta(minutes=15)


def to_evidence(item: FspAchievement | FspResult) -> Evidence:
    return Evidence(
        item.discipline, item.level, item.place, item.stage, item.competition_title, item.date
    )


def _fingerprint(items: list[FspAchievement] | list[FspResult]) -> list[tuple]:
    return sorted((i.external_id, i.place, i.stage, i.level) for i in items)


def backoff(failures: int) -> timedelta:
    """15 мин, 30 мин, 1 ч ... не больше суток."""
    exponent = min(max(0, failures - 1), 7)  # 15 мин * 2^7 > суток: дальше не растём
    return min(_MAX_BACKOFF, _FIRST_BACKOFF * 2**exponent)


class FspSyncer:
    def __init__(self, session: AsyncSession, client: FspClient, sync_every: timedelta) -> None:
        self.session = session
        self.client = client
        self.sync_every = sync_every
        self.categories = CategoryRepository(session)

    async def sync(self, profile: CandidateProfile, link: FspLink) -> None:
        link = await lock_link(self.session, link.id) or link
        athlete = await self.client.get_athlete(link.athlete_id)
        results = await self.client.get_results(link.athlete_id)
        achievements = FspAchievementRepository(self.session, profile.id)
        previous = _fingerprint(await achievements.all())
        await achievements.delete_own()
        self.session.add_all(_achievement(profile, r) for r in results)
        now = datetime.now(UTC)
        link.full_name, link.rank, link.region = athlete.full_name, athlete.rank, athlete.region
        link.last_synced_at, link.next_sync_at, link.sync_failures = now, now + self.sync_every, 0
        await self.recalculate(profile, [to_evidence(r) for r in results], athlete.rank)
        if previous != _fingerprint(results):
            await PassportRepository(self.session).revoke_all(profile.id)

    async def recalculate(
        self, profile: CandidateProfile, evidence: list[Evidence], rank: str | None
    ) -> None:
        matches = categorize(evidence, rank)
        known = await self.categories.by_slugs([m.slug for m in matches])
        assigned = []
        for match in matches:
            if match.slug not in known:
                log.warning("category %s is missing in the dictionary", match.slug)
                continue
            assigned.append((known[match.slug], list(match.reasons)))
        await self.categories.replace_for_profile(profile.id, assigned)
        profile.verification_tier = (
            VerificationTier.VERIFIED_FSP if evidence else VerificationTier.SELF_DECLARED
        )

    async def detach(self, profile: CandidateProfile, link: FspLink) -> None:
        """Отвязка (кандидатом или потому что аккаунт исчез в ФСП): данные ФСП удаляются,
        паспорт отзывается — без привязки он больше не подтверждён."""
        await self.session.delete(link)
        await FspAchievementRepository(self.session, profile.id).delete_own()
        await self.recalculate(profile, [], None)
        await PassportRepository(self.session).revoke_all(profile.id)


def _achievement(profile: CandidateProfile, r: FspResult) -> FspAchievement:
    return FspAchievement(
        profile_id=profile.id,
        external_id=r.external_id,
        discipline=r.discipline,
        competition_title=r.competition_title,
        level=r.level,
        date=r.date,
        place=r.place,
        stage=r.stage,
        role=r.role,
        team=r.team,
    )
