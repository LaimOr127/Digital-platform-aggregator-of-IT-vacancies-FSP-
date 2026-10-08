"""Разбор текста резюме по правилам: работает без внешних сервисов и для любого резюме.

Ищет контакты, имя, должность, грейд, стаж, город, формат, зарплату, навыки (по справочнику),
роли, софт-скиллы и раздел «О себе». Всё найденное — только предложение: кандидат
проверяет перед сохранением.
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import Education, Grade, WorkFormat

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
# все форматы, которые упоминает кандидат: «гибрид, удалённо, на месте работодателя» — три
_FORMATS = (
    (WorkFormat.OFFICE, r"\bофис|в\s+офисе|на\s+месте\s+работодател|office|on-?site"),
    (WorkFormat.HYBRID, r"гибрид|смешанн\w*\s+формат|hybrid"),
    (WorkFormat.REMOTE, r"удал[её]нн|удал[её]нк|удал[её]нно|из\s+дома|remote|work\s+from\s+home"),
)
_FORMAT_LINE = re.compile(r"(?:формат\s+работы|график\s+работы|work\s+format)[^\n]*", re.I)
_RELOCATION = re.compile(r"готов\w*\s+к\s+переезду|relocat", re.I)
_NO_RELOCATION = re.compile(r"не\s+готов\w*\s+к\s+переезду", re.I)
_EDUCATION = (
    (Education.PHD, r"кандидат\s+\w+\s+наук|доктор\s+\w+\s+наук|\bph\.?d"),
    (Education.MASTER, r"магист|master"),
    (Education.SPECIALIST, r"специалитет|\bспециалист\b"),
    (Education.BACHELOR, r"бакалав|bachelor"),
    (Education.INCOMPLETE_HIGHER, r"неоконченное\s+высшее"),
    (Education.VOCATIONAL, r"среднее\s+(?:специальное|профессиональное)|колледж|техникум"),
)
# строки с подписью в шапке резюме: «стек: …», «роли: …», «софт-скиллы: …»
_LABELED = {
    "stack": re.compile(r"^(?:стек|навыки|skills|технологии)\s*:\s*(.+)$", re.I | re.M),
    "roles": re.compile(r"^(?:роли|роль|roles?)\s*:\s*(.+)$", re.I | re.M),
    "soft": re.compile(
        r"^(?:софт-?\s?скиллы|soft\s?skills|личные\s+качества)\s*:\s*(.+)$", re.I | re.M
    ),
}
_DESIRED_TITLE = re.compile(r"^желаемая\s+должность[^\n]*\n([^\n]+)", re.I | re.M)
# роли и софт-скиллы — по ключевым словам; ключи совпадают со справочниками опроса
_ROLES = {
    "developer": r"разработчик|developer|программист|engineer|инженер",
    "team_lead": r"team\s?lead|тимлид|руковод\w*\s+(?:команд|групп|отдел)",
    "tech_lead": r"tech\s?lead|техлид|техническ\w*\s+лидер",
    "architect": r"архитектор|architect",
    "mentor": r"наставни|ментор|mentor",
}
_SOFT_SKILLS = {
    "communication": r"коммуникаб|коммуникац|communicat|переговор",
    "teamwork": r"командн\w*\s+(?:работ|игрок)|в\s+команде|team\s?player|teamwork",
    "leadership": r"лидерств|лидерск|капитан|leadership",
    "ownership": r"ответственн|ownership",
    "learning": r"обучаем|быстро\s+учусь|самообуч|fast\s+learner",
    "problem_solving": r"решени\w*\s+сложн|аналитическ\w*\s+мышлен|problem[\s-]solving",
    "time_management": r"самоорганиз|тайм-?менеджмент|time\s+management",
    "presenting": r"выступа|доклад|спикер|speaker|public\s+speaking",
}
# «опыт работы — 3 года 5 месяцев», «3,4 года», «8 месяцев», «5 years 2 months»
_EXPERIENCE = re.compile(
    r"(?:опыт(?:\s+работы)?|experience)[^\d\n]{0,20}"
    r"(?:(\d{1,2}(?:[.,]\d)?)\+?\s*(?:год|лет|year)\w*)?"
    r"(?:\s*(?:и\s*)?(\d{1,2})\s*(?:месяц|мес|month)\w*)?",
    re.I,
)
_SALARY = re.compile(
    r"(?:зарплат\w*|доход\w*|salary|ожидани\w*|зп)[^\d\n]{0,25}(?:от\s*)?"
    r"(\d[\d\s]{1,9})\s*(к|k|тыс\.?)?\s*(?:₽|руб|rub|р\.)?",
    re.I,
)
_CITY = re.compile(
    r"(?i:город|г\.|проживает|проживание|location|место\s+жительства)[:\s]+([А-ЯЁA-Z][\w-]+)"
)
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
    experience_years: float | None = None
    city: str | None = None
    work_formats: list[WorkFormat] = field(default_factory=list)
    relocation: bool | None = None
    education: Education | None = None
    stack: list[str] = field(default_factory=list)  # из строки «стек: …» — свои навыки
    extra_soft_skills: list[str] = field(default_factory=list)  # качества вне справочника
    salary_min: int | None = None
    about: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    roles: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def parse(text: str) -> ParsedResume:
    lines = [line for line in text.split("\n") if line.strip()]
    head = lines[:_HEAD_LINES]
    labeled = {key: _items(pattern, text) for key, pattern in _LABELED.items()}
    roles_text = ", ".join(labeled["roles"]) or text
    soft_text = ", ".join(labeled["soft"] + labeled["roles"]) or text
    desired = _first(_DESIRED_TITLE, text)
    result = ParsedResume(
        full_name=next((line for line in head if _NAME.match(line)), None),
        title=(desired or next((line for line in head if _is_role(line)), ""))[:120] or None,
        city=_first(_CITY, text),
        work_formats=_formats(text),
        relocation=None if _NO_RELOCATION.search(text) else bool(_RELOCATION.search(text)) or None,
        education=next((e for e, p in _EDUCATION if re.search(p, text, re.I)), None),
        salary_min=_salary(text),
        about=_about(lines),
        roles=_mentioned(_ROLES, roles_text),
        soft_skills=_mentioned(_SOFT_SKILLS, soft_text),
        stack=labeled["stack"],
        extra_soft_skills=[
            item.capitalize()
            for item in labeled["soft"]
            if not any(re.search(p, item, re.I) for p in _SOFT_SKILLS.values())
        ],
        **contacts(text),
    )
    result.experience_years = experience(text)
    title_area = " ".join(head)
    result.grade = next((g for g, p in _GRADES if re.search(p, title_area, re.I)), None)
    return result


def experience(text: str) -> float | None:
    """Стаж в годах с одной десятой: 3 года 5 месяцев -> 3.4 (в году 12 месяцев, не 10)."""
    for match in _EXPERIENCE.finditer(text):
        years, months = match.group(1), match.group(2)
        if years is None and months is None:
            continue
        total = float((years or "0").replace(",", ".")) + int(months or 0) / 12
        return float(Decimal(str(total)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    return None


def _formats(text: str) -> list[WorkFormat]:
    """Форматы из строки «Формат работы: …», а если её нет — из всего текста."""
    area = " ".join(_FORMAT_LINE.findall(text)) or text
    return [f for f, pattern in _FORMATS if re.search(pattern, area, re.I)]


def _items(pattern: re.Pattern[str], text: str) -> list[str]:
    match = pattern.search(text)
    if not match:
        return []
    return [item.strip(" .;") for item in re.split(r"[,;/]", match.group(1)) if item.strip(" .;")]


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


def _mentioned(patterns: dict[str, str], text: str) -> list[str]:
    return [key for key, pattern in patterns.items() if re.search(pattern, text, re.I)]


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
