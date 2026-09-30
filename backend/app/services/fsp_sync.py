"""Синхронизация одного профиля с ФСП: результаты -> достижения -> категории -> уровень
подтверждения. Используется и кабинетом кандидата, и фоновой задачей worker."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.fsp import FspClient, FspResult
from app.models import CandidateProfile, FspAchievement, FspLink
from app.models.enums import VerificationTier
from app.repositories.fsp import CategoryRepository, FspAchievementRepository
from app.services.categorization import Evidence, categorize


def to_evidence(item: FspAchievement | FspResult) -> Evidence:
    return Evidence(
        item.discipline, item.level, item.place, item.stage, item.competition_title, item.date
    )


class FspSyncer:
    def __init__(self, session: AsyncSession, client: FspClient) -> None:
        self.session = session
        self.client = client
        self.categories = CategoryRepository(session)

    async def sync(self, profile: CandidateProfile, link: FspLink) -> None:
        athlete = await self.client.get_athlete(link.athlete_id)
        results = await self.client.get_results(link.athlete_id)
        achievements = FspAchievementRepository(self.session, profile.id)
        await achievements.delete_own()
        self.session.add_all(_achievement(profile, r) for r in results)
        link.rank, link.region = athlete.rank, athlete.region
        link.last_synced_at = datetime.now(UTC)
        await self.recalculate(profile, [to_evidence(r) for r in results], athlete.rank)

    async def recalculate(
        self, profile: CandidateProfile, evidence: list[Evidence], rank: str | None
    ) -> None:
        assigned = []
        for match in categorize(evidence, rank):
            category = await self.categories.ensure(
                match.slug, match.discipline, match.tier, match.title
            )
            assigned.append((category, list(match.reasons)))
        await self.categories.replace_for_profile(profile.id, assigned)
        profile.verification_tier = (
            VerificationTier.VERIFIED_FSP if evidence else VerificationTier.SELF_DECLARED
        )

    async def clear(self, profile: CandidateProfile) -> None:
        await FspAchievementRepository(self.session, profile.id).delete_own()
        await self.recalculate(profile, [], None)


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
