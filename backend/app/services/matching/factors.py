"""Факторы соответствия (паттерн Strategy): новый фактор — новый класс, остальное не меняется.

Каждый фактор возвращает долю 0..1 и понятное работодателю объяснение. Веса — из плана:
навыки 40, грейд 20, ФСП 15, описание 15, формат и город 5, зарплата 5.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import CandidateProfile, Category, Vacancy
from app.models.enums import Grade, VerificationTier, WorkFormat
from app.services.categorization import TIER_TITLES, TIERS
from app.services.matching.text import keywords, overlap_with

GRADE_ORDER = [Grade.INTERN, Grade.JUNIOR, Grade.MIDDLE, Grade.SENIOR, Grade.LEAD]


@dataclass(frozen=True)
class Candidate:
    """Всё, что нужно для оценки: профиль и его категории ФСП."""

    profile: CandidateProfile
    categories: list[Category]


@dataclass(frozen=True)
class VacancyContext:
    """Вакансия с заранее подготовленными данными: считаются один раз на весь рейтинг."""

    vacancy: Vacancy
    skills: dict[str, str]  # slug -> название
    keywords: frozenset[str]

    @classmethod
    def of(cls, vacancy: Vacancy) -> "VacancyContext":
        return cls(
            vacancy,
            {s.slug: s.name for s in vacancy.skills},
            frozenset(keywords(f"{vacancy.title} {vacancy.description}")),
        )


@dataclass(frozen=True)
class FactorScore:
    key: str
    label: str
    weight: int
    share: float  # 0..1
    detail: str


class Factor(ABC):
    key: str
    label: str
    weight: int

    def score(self, context: VacancyContext, candidate: Candidate) -> FactorScore:
        share, detail = self.evaluate(context, candidate)
        return FactorScore(self.key, self.label, self.weight, round(share, 3), detail)

    @abstractmethod
    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]: ...


class SkillsFactor(Factor):
    key, label, weight = "skills", "Навыки", 40

    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        wanted = context.skills
        if not wanted:
            return 0.5, "в вакансии навыки не указаны"
        have = {s.slug for s in candidate.profile.skills}
        common = [name for slug, name in wanted.items() if slug in have]
        missing = [name for slug, name in wanted.items() if slug not in have]
        detail = f"{len(common)} из {len(wanted)}"
        if common:
            detail += f": {', '.join(common[:5])}"
        if missing:
            detail += f"; нет: {', '.join(missing[:3])}"
        return len(common) / len(wanted), detail


class GradeFactor(Factor):
    key, label, weight = "grade", "Грейд", 20

    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        grade = candidate.profile.grade
        if grade is None:
            return 0.3, "кандидат не указал грейд"
        gap = abs(GRADE_ORDER.index(grade) - GRADE_ORDER.index(context.vacancy.grade))
        return {0: (1.0, "совпадает"), 1: (0.5, "соседний")}.get(gap, (0.0, "далёкий"))


class FspFactor(Factor):
    key, label, weight = "fsp", "Подтверждение ФСП", 15

    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        if candidate.profile.verification_tier != VerificationTier.VERIFIED_FSP:
            return 0.0, "навыки не подтверждены ФСП"
        if not candidate.categories:
            return 0.3, "аккаунт ФСП привязан, результатов пока нет"
        best = max(candidate.categories, key=lambda c: TIERS.index(c.tier))
        share = {"elite": 1.0, "advanced": 0.75, "base": 0.5}[best.tier]
        return share, TIER_TITLES.get(best.tier, best.tier)


class DescriptionFactor(Factor):
    key, label, weight = "description", "Описание и опыт", 15

    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        profile = candidate.profile
        candidate_text = " ".join(
            filter(None, [profile.title, profile.about, *(s.name for s in profile.skills)])
        )
        share, common = overlap_with(context.keywords, candidate_text)
        if not common:
            return share, "общих тем с описанием вакансии не найдено"
        return share, f"общие темы: {', '.join(common)}"


class FormatFactor(Factor):
    key, label, weight = "format", "Формат и город", 5

    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        profile, vacancy = candidate.profile, context.vacancy
        if vacancy.work_format == WorkFormat.REMOTE:
            return 1.0, "удалённая работа — город не важен"
        same_city = bool(
            profile.city and vacancy.city and profile.city.strip().lower() == vacancy.city.lower()
        )
        if same_city:
            return 1.0, f"тот же город: {vacancy.city}"
        if profile.work_format == WorkFormat.REMOTE:
            return 0.0, "кандидат хочет удалённо"
        return 0.4, "город не совпадает или не указан"


class SalaryFactor(Factor):
    key, label, weight = "salary", "Зарплата", 5

    def evaluate(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        expected, vacancy = candidate.profile.salary_min, context.vacancy
        if not expected:
            return 0.6, "ожидания не указаны"
        if expected <= vacancy.salary_max:
            return 1.0, "ожидания в пределах вилки"
        over = (expected - vacancy.salary_max) / vacancy.salary_max
        return max(0.0, 1 - over * 2), f"ожидания выше вилки на {round(over * 100)}%"


FACTORS: tuple[Factor, ...] = (
    SkillsFactor(),
    GradeFactor(),
    FspFactor(),
    DescriptionFactor(),
    FormatFactor(),
    SalaryFactor(),
)
