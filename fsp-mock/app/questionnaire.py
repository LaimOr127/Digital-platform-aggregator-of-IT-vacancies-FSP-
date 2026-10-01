"""Анкета спортсмена в ФСП: то, что он сам заполнил в личном кабинете федерации.

Отдаётся только интеграции с сервисным ключом; платформа запрашивает её лишь для
спортсмена, подтвердившего владение аккаунтом ФСП кодом. Данные вымышлены.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Questionnaire:
    city: str
    organization: str | None  # вуз, клуб или компания
    specialization: str | None
    experience_years: int | None
    stack: tuple[str, ...]
    about: str | None
    phone: str | None
    telegram: str | None


QUESTIONNAIRES = {
    "FSP-24001": Questionnaire(
        city="Казань",
        organization="КФУ, Институт ВМиИТ",
        specialization="Backend-разработчик",
        experience_years=3,
        stack=("Python", "FastAPI", "PostgreSQL", "Docker", "React"),
        about="Капитан команды Byte Force: веду продуктовую разработку от идеи до релиза.",
        phone="+7 900 000-00-01",
        telegram="@anna_dev",
    ),
    "FSP-24002": Questionnaire(
        city="Новосибирск",
        organization="НГУ, механико-математический факультет",
        specialization="Алгоритмист, C++ разработчик",
        experience_years=2,
        stack=("C++", "Python", "Go", "Linux"),
        about="Олимпиадное программирование с 2018 года, люблю высоконагруженные системы.",
        phone=None,
        telegram="@ilya_algo",
    ),
    "FSP-24003": Questionnaire(
        city="Санкт-Петербург",
        organization="ИТМО",
        specialization="Специалист по информационной безопасности",
        experience_years=1,
        stack=("Python", "Linux", "Docker", "Wireshark"),
        about="CTF в команде RedShift: веб-уязвимости и форензика.",
        phone=None,
        telegram="@m_orlova",
    ),
    "FSP-24004": Questionnaire(
        city="Казань",
        organization="КНИТУ-КАИ",
        specialization="Разработчик БАС",
        experience_years=None,
        stack=("C++", "Python", "ROS"),
        about=None,
        phone="+7 900 000-00-04",
        telegram=None,
    ),
    "FSP-24006": Questionnaire(
        city="Екатеринбург",
        organization="УрФУ",
        specialization="Робототехник, embedded-разработчик",
        experience_years=2,
        stack=("C", "C++", "Python", "ROS", "Git"),
        about="Капитан Iron Logic: управление манипуляторами и компьютерное зрение.",
        phone=None,
        telegram="@egor_bot",
    ),
}


def questionnaire_payload(athlete_id: str) -> dict:
    """Пустая анкета, если спортсмен её не заполнял (такое бывает и в реальности)."""
    data = QUESTIONNAIRES.get(athlete_id)
    if data is None:
        return {
            "city": None,
            "organization": None,
            "specialization": None,
            "experience_years": None,
            "stack": [],
            "about": None,
            "phone": None,
            "telegram": None,
        }
    return {**asdict(data), "stack": list(data.stack)}
