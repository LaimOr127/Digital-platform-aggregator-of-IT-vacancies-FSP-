"""Факторы соответствия (паттерн Strategy): новый фактор — новый класс, остальное не меняется.

Каждый фактор возвращает долю 0..1 и понятное работодателю объяснение. Основа выдачи —
категория, присвоенная по итогам опроса и теста, и результат теста; самоописание профиля
(заявленные навыки, текст «о себе») весит мало.

Подбор под вакансию: категория 30, тест 20 (близость уровня к грейду вакансии), навыки 20,
ФСП 10, описание 5, актуальность 5, формат и город 5, зарплата 5.
Сила профиля без вакансии: тест 60, ФСП 25, актуальность 15.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.timeutil import as_aware
from app.models import CandidateProfile, Category, Vacancy
from app.models.enums import VerificationTier, WorkFormat
from app.services.assessment.engine import level_from_score
from app.services.categorization import TIER_TITLES, TIERS
from app.services.matching.text import keywords, overlap_with
from app.services.specializations import GRADE_ORDER, GRADE_TITLES, grade_at

FRESH_DAYS, STALE_DAYS = 30, 180
FIT_TOLERANCE, FIT_RANGE = 0.5, 1.5  # уровни: «совпадает» и где соответствие падает до нуля


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

    def __init__(self, weight: int | None = None) -> None:
        if weight is not None:
            self.weight = weight

    def score(self, context: VacancyContext | None, candidate: Candidate) -> FactorScore:
        share, detail = self.evaluate(context, candidate)
        return FactorScore(self.key, self.label, self.weight, round(share, 3), detail)

    @abstractmethod
    def evaluate(
        self, context: VacancyContext | None, candidate: Candidate
    ) -> tuple[float, str]: ...


class VacancyFactor(Factor):
    """Фактор, которому нужна вакансия (подбор под потребность работодателя)."""

    def evaluate(self, context: VacancyContext | None, candidate: Candidate) -> tuple[float, str]:
        if context is None:
            raise ValueError(f"{self.key}: нужна вакансия")
        return self.compare(context, candidate)

    @abstractmethod
    def compare(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]: ...


class CategoryFactor(VacancyFactor):
    key, label, weight = "category", "Категория", 30

    def compare(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        profile, vacancy = candidate.profile, context.vacancy
        if vacancy.specialization and profile.specialization != vacancy.specialization:
            return 0.0, "другая специализация"
        if profile.confirmed_grade is None:
            claimed = GRADE_TITLES[profile.grade] if profile.grade else "не указан"
            return 0.2, f"грейд не подтверждён тестом (заявлен: {claimed})"
        gap = abs(GRADE_ORDER.index(profile.confirmed_grade) - GRADE_ORDER.index(vacancy.grade))
        title = GRADE_TITLES[profile.confirmed_grade]
        if gap == 0:
            return 1.0, f"подтверждённый грейд {title} совпадает"
        if gap == 1:
            return 0.5, f"подтверждённый грейд {title} — соседний"
        return 0.0, f"подтверждённый грейд {title} — далёкий"


class AssessmentFactor(Factor):
    """Без вакансии — сила профиля: больше баллов теста, выше в категории. Под вакансию —
    близость уровня по тесту к её грейду: кандидат сильно выше грейда подходит хуже точного
    (это показала процедура оценки: «чем сильнее, тем лучше» поднимало переквалифицированных)."""

    key, label, weight = "assessment", "Результат теста", 20

    def evaluate(self, context: VacancyContext | None, candidate: Candidate) -> tuple[float, str]:
        profile = candidate.profile
        if profile.confirmed_grade is None or profile.assessment_score is None:
            return 0.0, "тест не пройден"
        score = profile.assessment_score
        if context is None:
            return score / 100, f"{score} из 100 в своей категории"
        level = level_from_score(GRADE_ORDER.index(profile.confirmed_grade) + 1, score)
        target = GRADE_ORDER.index(context.vacancy.grade) + 1
        gap = level - target
        title = GRADE_TITLES[grade_at(round(level))]
        if abs(gap) < FIT_TOLERANCE:
            relation = "совпадает с грейдом вакансии"
        else:
            relation = "выше грейда вакансии" if gap > 0 else "ниже грейда вакансии"
        return max(0.0, 1 - abs(gap) / FIT_RANGE), f"уровень по тесту ≈ {title}: {relation}"


class FreshnessFactor(Factor):
    key, label, weight = "freshness", "Актуальность", 5

    def evaluate(self, context: VacancyContext | None, candidate: Candidate) -> tuple[float, str]:
        last = candidate.profile.last_activity_at
        if last is None:
            return 0.0, "нет недавних тестов и задач"
        days = (datetime.now(UTC) - as_aware(last)).days
        decay = (days - FRESH_DAYS) / (STALE_DAYS - FRESH_DAYS)
        share = 1.0 if days <= FRESH_DAYS else max(0.0, 1 - decay)
        detail = "активность сегодня" if days == 0 else f"последняя активность {days} дн. назад"
        return share, detail


class SkillsFactor(VacancyFactor):
    key, label, weight = "skills", "Навыки", 20

    def compare(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        """Навык, подтверждённый ответами теста, считается полностью, заявленный — наполовину."""
        wanted = context.skills
        if not wanted:
            return 0.5, "в вакансии навыки не указаны"
        confirmed = set(candidate.profile.confirmed_skills or [])
        declared = {s.slug for s in candidate.profile.skills}
        # свои навыки кандидата (вне справочника) сравниваются с вакансией по названию
        custom = {name.lower() for name in getattr(candidate.profile, "custom_skills", None) or []}
        tested = [name for slug, name in wanted.items() if slug in confirmed]
        claimed = [
            name
            for slug, name in wanted.items()
            if slug not in confirmed and (slug in declared or name.lower() in custom)
        ]
        missing = len(wanted) - len(tested) - len(claimed)
        parts = [f"подтверждены тестом: {', '.join(tested[:4])}" if tested else ""]
        parts.append(f"заявлены: {', '.join(claimed[:4])}" if claimed else "")
        parts.append(f"нет {missing} из {len(wanted)}" if missing else "")
        detail = "; ".join(p for p in parts if p) or "нет нужных навыков"
        return (len(tested) + 0.5 * len(claimed)) / len(wanted), detail


class FspFactor(Factor):
    key, label, weight = "fsp", "Достижения ФСП", 10

    def evaluate(self, context: VacancyContext | None, candidate: Candidate) -> tuple[float, str]:
        if candidate.profile.verification_tier != VerificationTier.VERIFIED_FSP:
            return 0.0, "навыки не подтверждены ФСП"
        if not candidate.categories:
            return 0.3, "аккаунт ФСП привязан, результатов пока нет"
        best = max(candidate.categories, key=lambda c: TIERS.index(c.tier))
        share = {"elite": 1.0, "advanced": 0.75, "base": 0.5}[best.tier]
        if not getattr(candidate.profile, "show_fsp", True):
            return share, "результаты ФСП подтверждены (детали скрыты кандидатом)"
        return share, TIER_TITLES.get(best.tier, best.tier)


class DescriptionFactor(VacancyFactor):
    key, label, weight = "description", "Описание и опыт", 5

    def compare(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        profile = candidate.profile
        about = profile.about if getattr(profile, "show_about", True) else None
        candidate_text = " ".join(
            filter(None, [profile.title, about, *(s.name for s in profile.skills)])
        )
        share, common = overlap_with(context.keywords, candidate_text)
        if not common:
            return share, "общих тем с описанием вакансии не найдено"
        return share, f"общие темы: {', '.join(common)}"


class FormatFactor(VacancyFactor):
    key, label, weight = "format", "Формат и город", 5

    def compare(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        profile, vacancy = candidate.profile, context.vacancy
        if vacancy.work_format == WorkFormat.REMOTE:
            return 1.0, "удалённая работа — город не важен"
        same_city = bool(
            profile.city and vacancy.city and profile.city.strip().lower() == vacancy.city.lower()
        )
        if same_city:
            return 1.0, f"тот же город: {vacancy.city}"
        if getattr(profile, "relocation", False):
            return 0.8, "готов к переезду"
        if (profile.work_formats or []) == [WorkFormat.REMOTE]:
            return 0.0, "кандидат хочет только удалённо"
        return 0.4, "город не совпадает или не указан"


class SalaryFactor(VacancyFactor):
    key, label, weight = "salary", "Зарплата", 5

    def compare(self, context: VacancyContext, candidate: Candidate) -> tuple[float, str]:
        expected, vacancy = candidate.profile.salary_min, context.vacancy
        if not getattr(candidate.profile, "show_salary", True):
            return 0.6, "кандидат скрыл ожидания"  # скрытое не влияет на выдачу и не раскрывается
        if not expected:
            return 0.6, "ожидания не указаны"
        if expected <= vacancy.salary_max:
            return 1.0, "ожидания в пределах вилки"
        over = (expected - vacancy.salary_max) / vacancy.salary_max
        return max(0.0, 1 - over * 2), f"ожидания выше вилки на {round(over * 100)}%"


FACTORS: tuple[Factor, ...] = (
    CategoryFactor(),
    AssessmentFactor(),
    SkillsFactor(),
    FspFactor(),
    DescriptionFactor(),
    FreshnessFactor(),
    FormatFactor(),
    SalaryFactor(),
)

# без вакансии: «сила подтверждённого профиля» внутри категории
STRENGTH_FACTORS: tuple[Factor, ...] = (
    AssessmentFactor(60),
    FspFactor(25),
    FreshnessFactor(15),
)
