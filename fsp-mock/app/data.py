"""Демо-данные мока ФСП. Дисциплины — реальные дисциплины спортивного программирования;
спортсмены, соревнования и результаты вымышлены. При появлении спецификации API ФСП
мок приводится к ней, а бэкенд меняет только реализацию FspClient."""

from dataclasses import asdict, dataclass

DISCIPLINES = {
    "product": "Продуктовое программирование",
    "algorithmic": "Алгоритмическое программирование",
    "security": "Программирование систем информационной безопасности",
    "drones": "Программирование беспилотных авиационных систем",
    "robotics": "Программирование робототехники",
}


@dataclass(frozen=True)
class Competition:
    id: str
    title: str
    discipline: str
    level: str  # regional | national | international
    date: str


@dataclass(frozen=True)
class Result:
    id: str
    competition_id: str
    place: int | None  # None — участие без итогового места
    stage: str  # qualification | final
    team: str | None
    role: str  # captain | member | individual


@dataclass(frozen=True)
class Athlete:
    id: str
    full_name: str
    region: str
    email: str
    rank: str | None  # МСМК | МС | КМС | 1 | 2 | 3
    results: tuple[Result, ...]

    def public(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "region": self.region,
            "rank": self.rank,
        }


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[0]}{'*' * max(1, len(name) - 2)}{name[-1]}@{domain}"


COMPETITIONS = {
    c.id: c
    for c in (
        Competition(
            "c-rus-prod-25",
            "Чемпионат России, продуктовое программирование",
            "product",
            "national",
            "2025-11-20",
        ),
        Competition(
            "c-rus-alg-25",
            "Чемпионат России, алгоритмическое программирование",
            "algorithmic",
            "national",
            "2025-10-05",
        ),
        Competition(
            "c-cup-sec-25",
            "Кубок России, информационная безопасность",
            "security",
            "national",
            "2025-06-14",
        ),
        Competition(
            "c-int-alg-25",
            "Международные соревнования по алгоритмическому программированию",
            "algorithmic",
            "international",
            "2025-09-12",
        ),
        Competition(
            "c-msk-prod-25",
            "Первенство Москвы, продуктовое программирование",
            "product",
            "regional",
            "2025-04-18",
        ),
        Competition(
            "c-spb-sec-25",
            "Чемпионат Санкт-Петербурга, информационная безопасность",
            "security",
            "regional",
            "2025-03-22",
        ),
        Competition(
            "c-kzn-bas-25",
            "Чемпионат Республики Татарстан, программирование БАС",
            "drones",
            "regional",
            "2025-05-30",
        ),
        Competition(
            "c-rus-rob-25",
            "Всероссийские соревнования, программирование робототехники",
            "robotics",
            "national",
            "2025-07-08",
        ),
        Competition(
            "c-nsk-alg-25",
            "Кубок Новосибирской области, алгоритмическое программирование",
            "algorithmic",
            "regional",
            "2025-02-15",
        ),
    )
}


def _r(
    rid: str,
    comp: str,
    place: int | None,
    stage: str = "final",
    team: str | None = None,
    role: str = "member",
) -> Result:
    return Result(rid, comp, place, stage, team, role)


ATHLETES = {
    a.id: a
    for a in (
        Athlete(
            "FSP-24001",
            "Анна Смирнова",
            "Республика Татарстан",
            "anna.smirnova@example.org",
            "КМС",
            (
                _r("r1", "c-rus-prod-25", 2, team="Byte Force", role="captain"),
                _r("r2", "c-msk-prod-25", 1, team="Byte Force", role="captain"),
            ),
        ),
        Athlete(
            "FSP-24002",
            "Илья Кузнецов",
            "Новосибирская область",
            "ilya.k@example.org",
            "МС",
            (
                _r("r3", "c-int-alg-25", 3, role="individual"),
                _r("r4", "c-rus-alg-25", 1, role="individual"),
                _r("r5", "c-nsk-alg-25", 1, role="individual"),
            ),
        ),
        Athlete(
            "FSP-24003",
            "Мария Орлова",
            "Санкт-Петербург",
            "m.orlova@example.org",
            "1",
            (
                _r("r6", "c-spb-sec-25", 2, team="RedShift", role="member"),
                _r("r7", "c-cup-sec-25", None, team="RedShift", role="member"),
            ),
        ),
        Athlete(
            "FSP-24004",
            "Тимур Галиев",
            "Республика Татарстан",
            "timur.g@example.org",
            "2",
            (_r("r8", "c-kzn-bas-25", 3, team="SkyCode", role="captain"),),
        ),
        Athlete(
            "FSP-24005",
            "Дарья Волкова",
            "Москва",
            "d.volkova@example.org",
            None,
            (
                _r(
                    "r9",
                    "c-msk-prod-25",
                    None,
                    stage="qualification",
                    team="Null Pointer",
                    role="member",
                ),
            ),
        ),
        Athlete(
            "FSP-24006",
            "Егор Белов",
            "Свердловская область",
            "egor.belov@example.org",
            "1",
            (
                _r("r10", "c-rus-rob-25", 5, team="Iron Logic", role="captain"),
                _r("r11", "c-rus-alg-25", None, role="individual"),
            ),
        ),
        Athlete("FSP-24007", "Алина Сафина", "Москва", "a.safina@example.org", None, ()),
    )
}


def result_payload(result: Result) -> dict:
    competition = COMPETITIONS[result.competition_id]
    return {
        **asdict(result),
        "competition": {
            **asdict(competition),
            "discipline_title": DISCIPLINES[competition.discipline],
        },
    }
