"""Разбор текста резюме по правилам: работает без внешних сервисов и для любого резюме.

Ищет контакты, имя, должность, грейд, стаж, город, формат, зарплату, навыки (по справочнику)
и раздел «О себе». Всё найденное — только предложение: кандидат проверяет перед сохранением.
"""

import re
from dataclasses import dataclass, field

from app.models.enums import Grade, WorkFormat

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
TELEGRAM = re.compile(r"(?:t\.me/|telegram[:\s]+@?|(?<![\w.])@)([A-Za-z][\w]{4,31})", re.I)

_ROLE_WORDS = (
    "разработчик", "developer", "engineer", "инженер", "программист", "аналитик", "analyst",
    "тестировщик", "qa", "devops", "data scientist", "архитектор", "architect", "team lead",
    "тимлид", "специалист", "backend", "frontend", "fullstack", "mobile",
)  # fmt: skip
_GRADES = (
    (Grade.LEAD, r"\b(?:team\s?lead|tech\s?lead|тимлид|lead)\b"),
    (Grade.SENIOR, r"\b(?:senior|сеньор|ведущий)\b"),
    (Grade.MIDDLE, r"\b(?:middle|мидл)\b"),
    (Grade.JUNIOR, r"\b(?:junior|джун(?:иор)?|младший)\b"),
    (Grade.INTERN, r"\b(?:intern|стаж[её]р|стажировк)"),
)
_FORMATS = (
    (WorkFormat.REMOTE, r"удал[её]нн|удал[её]нка|remote"),
    (WorkFormat.HYBRID, r"гибрид|hybrid"),
    (WorkFormat.OFFICE, r"\bофис|office"),
)
_EXPERIENCE = re.compile(
    r"(?:опыт(?:\s+работы)?|experience)[^\d\n]{0,20}(\d{1,2})\+?\s*(?:год|лет|year)", re.I
)
_SALARY = re.compile(
    r"(?:зарплат\w*|доход\w*|salary|ожидани\w*|зп)[^\d\n]{0,25}(?:от\s*)?"
    r"(\d[\d\s]{1,9})\s*(к|k|тыс\.?)?\s*(?:₽|руб|rub|р\.)?",
    re.I,
)
_CITY = re.compile(r"(?i:город|г\.|проживание|location|место\s+жительства)[:\s]+([А-ЯЁA-Z][\w-]+)")
_NAME = re.compile(r"^([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)(?:\s+[А-ЯЁA-Z][а-яёa-z-]+)?$")
_ABOUT = re.compile(r"^(?:о\s+себе|обо\s+мне|about(?:\s+me)?|summary)\s*:?\s*$", re.I)
_SECTION = re.compile(
    r"^(?:опыт\s+работы|образование|навыки|ключевые\s+навыки|experience|education|skills"
    r"|проекты|projects|контакты|языки|курсы)\s*:?\s*$",
    re.I,
)
_HEAD_LINES = 6
_ABOUT_LIMIT = 1500
_MIN_SALARY = 10_000


@dataclass
class ParsedResume:
    full_name: str | None = None
    title: str | None = None
    grade: Grade | None = None
    experience_years: int | None = None
    city: str | None = None
    work_format: WorkFormat | None = None
    salary_min: int | None = None
    about: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    notes: list[str] = field(default_factory=list)


def parse(text: str) -> ParsedResume:
    lines = [line for line in text.split("\n") if line.strip()]
    head = lines[:_HEAD_LINES]
    result = ParsedResume(
        full_name=next((line for line in head if _NAME.match(line)), None),
        title=next((line[:120] for line in head if _is_role(line)), None),
        city=_first(_CITY, text),
        work_format=next((f for f, p in _FORMATS if re.search(p, text, re.I)), None),
        salary_min=_salary(text),
        about=_about(lines),
        **contacts(text),
    )
    years = _first(_EXPERIENCE, text)
    result.experience_years = int(years) if years else None
    title_area = " ".join(head)
    result.grade = next((g for g, p in _GRADES if re.search(p, title_area, re.I)), None)
    return result


def contacts(text: str) -> dict[str, str | None]:
    """Контакты ищутся только локально: в ИИ-сервис текст уходит без них (см. mask_contacts)."""
    email = _first(EMAIL, text, group=0)
    phone = _first(PHONE, text, group=0)
    handle = _first(TELEGRAM, text)
    return {
        "email": email,
        "phone": re.sub(r"[^\d+]", "", phone) if phone else None,
        "telegram": f"@{handle}" if handle else None,
    }


def mask_contacts(text: str) -> str:
    text = EMAIL.sub("[email]", text)
    text = PHONE.sub("[телефон]", text)
    return TELEGRAM.sub("[telegram]", text)


def _is_role(line: str) -> bool:
    lowered = line.lower()
    return len(line) <= 120 and any(word in lowered for word in _ROLE_WORDS)


def _first(pattern: re.Pattern[str], text: str, group: int = 1) -> str | None:
    match = pattern.search(text)
    return match.group(group).strip() if match else None


def _salary(text: str) -> int | None:
    match = _SALARY.search(text)
    if not match:
        return None
    amount = int(re.sub(r"\s", "", match.group(1)))
    unit = (match.group(2) or "").lower()
    if unit:
        amount *= 1000
    return amount if amount >= _MIN_SALARY else None


def _about(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        if _ABOUT.match(line):
            body: list[str] = []
            for nxt in lines[index + 1 :]:
                if _SECTION.match(nxt):
                    break
                body.append(nxt)
            text = "\n".join(body).strip()
            return text[:_ABOUT_LIMIT] or None
    return None
