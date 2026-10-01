"""Автозаполнение профиля: черновик из анкеты ФСП (после подтверждения владения аккаунтом).

Данные ФСП запрашиваются только для привязанного и подтверждённого кодом аккаунта: по одному
ID чужую анкету не получить. Каждое чтение анкеты пишется в аудит.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.integrations.fsp import FspClient, FspQuestionnaire
from app.models import FspAchievement
from app.models.enums import Grade
from app.repositories.audit import AuditRepository
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.fsp import FspAchievementRepository, FspLinkRepository
from app.schemas.candidate import Contacts
from app.schemas.common import SkillOut
from app.schemas.profile_import import ProfileDraftOut
from app.services.access import Action, Principal, policy
from app.services.categorization import TIERS, describe_anonymous, result_tier
from app.services.fsp_sync import to_evidence
from app.services.skill_matching import SkillDictionary

# название должности по дисциплине — если в анкете специализация не указана
DISCIPLINE_TITLES = {
    "product": "Разработчик продуктовых решений",
    "algorithmic": "Разработчик (алгоритмы)",
    "security": "Специалист по информационной безопасности",
    "drones": "Разработчик беспилотных систем",
    "robotics": "Разработчик робототехники",
}
_TOP_ACHIEVEMENTS = 3


def grade_for_experience(years: int | None) -> Grade | None:
    """Ориентир по стажу; кандидат может поправить грейд перед сохранением."""
    if years is None:
        return None
    if years < 1:
        return Grade.INTERN
    if years < 3:
        return Grade.JUNIOR
    if years < 6:
        return Grade.MIDDLE
    return Grade.SENIOR


def skills_out(dictionary: SkillDictionary, slugs: list[str]) -> list[SkillOut]:
    names = {s.slug: s.name for s in dictionary.skills}
    return [SkillOut(slug=slug, name=names[slug]) for slug in slugs]


class FspImportService:
    def __init__(self, session: AsyncSession, principal: Principal, client: FspClient) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.client = client

    async def draft(self) -> ProfileDraftOut:
        profile = await CandidateProfileRepository(
            self.session, self.principal.user_id
        ).own_or_404()
        link = await FspLinkRepository(self.session, profile.id).own()
        if link is None:
            raise NotFoundError("сначала привяжите и подтвердите аккаунт ФСП")
        athlete = await self.client.get_athlete(link.athlete_id)
        questionnaire = await self.client.get_questionnaire(link.athlete_id)
        achievements = await FspAchievementRepository(self.session, profile.id).all()
        dictionary = await SkillDictionary.load(self.session)
        await AuditRepository(self.session).record(
            "fsp.questionnaire_read", self.principal.user_id, "fsp_link", link.id
        )
        await self.session.commit()
        return build_fsp_draft(
            athlete.full_name, athlete.region, questionnaire, achievements, dictionary
        )


def build_fsp_draft(
    full_name: str,
    region: str | None,
    q: FspQuestionnaire,
    achievements: list[FspAchievement],
    dictionary: SkillDictionary,
) -> ProfileDraftOut:
    matched = dictionary.match_names(list(q.stack))
    best = _best(achievements)
    notes = ["Имя, контакты и стек — из вашей анкеты в личном кабинете ФСП"]
    grade = grade_for_experience(q.experience_years)
    if grade:
        notes.append(f"Грейд предложен по стажу ({q.experience_years} г.) — проверьте")
    title = q.specialization or (DISCIPLINE_TITLES.get(best[0].discipline) if best else None)
    return ProfileDraftOut(
        source="fsp",
        full_name=full_name,
        title=title,
        about=_about(q, best),
        grade=grade,
        city=q.city or region,
        contacts=Contacts(email=q.email, phone=q.phone, telegram=q.telegram),
        skills=skills_out(dictionary, matched.slugs),
        unknown_skills=matched.unknown,
        notes=notes,
    )


def _best(achievements: list[FspAchievement]) -> list[FspAchievement]:
    """Сильнейшие результаты: по уровню результата, затем по дате (новые выше)."""
    ranked = sorted(
        achievements,
        key=lambda a: (TIERS.index(result_tier(to_evidence(a))), a.date),
        reverse=True,
    )
    return ranked[:_TOP_ACHIEVEMENTS]


def _about(q: FspQuestionnaire, best: list[FspAchievement]) -> str | None:
    parts = [q.about] if q.about else []
    if q.organization:
        parts.append(f"Учёба/клуб: {q.organization}.")
    if best:
        # «О себе» видно в анонимной карточке: без названий соревнований, как в каталоге
        lines = "\n".join(f"• {describe_anonymous(to_evidence(a))}" for a in best)
        parts.append(f"Достижения ФСП:\n{lines}")
    return "\n\n".join(parts) or None
