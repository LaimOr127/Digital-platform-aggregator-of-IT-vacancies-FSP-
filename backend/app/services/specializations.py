"""Справочник специализаций и грейдов — основа категорий кандидатов.

Категория = специализация x подтверждённый тестом грейд («Бэкенд-разработчики · Middle»).
Справочник составлен по общепринятым направлениям ИТ; на этапе MVP — основные направления.
"""

from dataclasses import dataclass

from app.models.enums import Grade, Specialization


@dataclass(frozen=True)
class SpecializationInfo:
    slug: Specialization
    title: str  # «Бэкенд-разработка»
    group: str  # «Бэкенд-разработчики» — так называется категория
    skills: tuple[str, ...]  # типичный стек: подсказка в опросе


SPECIALIZATIONS: dict[Specialization, SpecializationInfo] = {
    s.slug: s
    for s in (
        SpecializationInfo(
            Specialization.BACKEND,
            "Бэкенд-разработка",
            "Бэкенд-разработчики",
            ("python", "go", "java", "postgresql", "redis", "kafka", "docker", "sql"),
        ),
        SpecializationInfo(
            Specialization.FRONTEND,
            "Фронтенд-разработка",
            "Фронтенд-разработчики",
            ("javascript", "typescript", "react", "vue", "angular"),
        ),
        SpecializationInfo(
            Specialization.MOBILE,
            "Мобильная разработка",
            "Мобильные разработчики",
            ("android", "ios", "kotlin", "swift"),
        ),
        SpecializationInfo(
            Specialization.DATA,
            "Данные и машинное обучение",
            "Специалисты по данным и ML",
            ("python", "machine-learning", "data-analysis", "sql", "pytorch"),
        ),
        SpecializationInfo(
            Specialization.DEVOPS,
            "DevOps и инфраструктура",
            "DevOps-инженеры",
            ("docker", "kubernetes", "linux", "ci-cd", "terraform"),
        ),
        SpecializationInfo(
            Specialization.QA,
            "Тестирование",
            "Инженеры по тестированию",
            ("qa-automation", "python", "java", "sql"),
        ),
        SpecializationInfo(
            Specialization.SECURITY,
            "Информационная безопасность",
            "Специалисты по ИБ",
            ("information-security", "pentest", "reverse-engineering", "linux"),
        ),
    )
}

GRADE_ORDER = [Grade.INTERN, Grade.JUNIOR, Grade.MIDDLE, Grade.SENIOR, Grade.LEAD]
GRADE_TITLES = {
    Grade.INTERN: "Стажёр",
    Grade.JUNIOR: "Junior",
    Grade.MIDDLE: "Middle",
    Grade.SENIOR: "Senior",
    Grade.LEAD: "Lead",
}

INDUSTRIES = {
    "fintech": "Финтех и банки",
    "ecommerce": "Электронная коммерция",
    "government": "Госсектор",
    "health": "Медицина",
    "education": "Образование",
    "games": "Игры",
    "telecom": "Телеком",
    "industry": "Промышленность",
    "media": "Медиа",
    "logistics": "Логистика и транспорт",
}

ROLES = {
    "developer": "Разработка",
    "team_lead": "Руководство командой",
    "tech_lead": "Техническое лидерство",
    "architect": "Архитектура",
    "mentor": "Наставничество",
}

SOFT_SKILLS = {
    "communication": "Коммуникация",
    "teamwork": "Работа в команде",
    "leadership": "Лидерство",
    "ownership": "Ответственность",
    "learning": "Обучаемость",
    "problem_solving": "Решение сложных задач",
    "time_management": "Самоорганизация",
    "presenting": "Публичные выступления",
}


EDUCATION = {
    "secondary": "Среднее общее",
    "vocational": "Среднее профессиональное",
    "incomplete_higher": "Неоконченное высшее",
    "bachelor": "Высшее — бакалавриат",
    "specialist": "Высшее — специалитет",
    "master": "Высшее — магистратура",
    "phd": "Учёная степень",
}


def specialization_for(stack: set[str]) -> tuple[Specialization | None, int]:
    """Специализация с наибольшим пересечением стека (slug навыков) с типичным стеком и число
    совпадений; без совпадений — None. Подсказка для опроса, категорию определяет тест."""
    overlap = {spec: len(stack & set(info.skills)) for spec, info in SPECIALIZATIONS.items()}
    best = max(overlap, key=lambda spec: overlap[spec])
    return (best, overlap[best]) if overlap[best] else (None, 0)


def known_keys(values: list[str], allowed: dict[str, str], label: str) -> list[str]:
    """Значения из справочника без повторов; неизвестное значение — ошибка валидации."""
    unknown = [v for v in values if v not in allowed]
    if unknown:
        raise ValueError(f"неизвестная {label}: {', '.join(unknown)}")
    return list(dict.fromkeys(values))


def level(grade: Grade) -> int:
    """Уровень сложности 1..5 (стажёр..lead) — общая шкала заданий и оценки кандидата."""
    return GRADE_ORDER.index(grade) + 1


def grade_at(value: int) -> Grade:
    return GRADE_ORDER[min(max(value, 1), len(GRADE_ORDER)) - 1]


def category_slug(specialization: Specialization, grade: Grade) -> str:
    return f"{specialization.value}:{grade.value}"


def category_title(specialization: Specialization, grade: Grade) -> str:
    return f"{SPECIALIZATIONS[specialization].group} · {GRADE_TITLES[grade]}"


def parse_category(slug: str) -> tuple[Specialization, Grade] | None:
    specialization, _, grade = slug.partition(":")
    try:
        return Specialization(specialization), Grade(grade)
    except ValueError:
        return None
