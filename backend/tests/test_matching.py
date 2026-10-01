"""Соответствие кандидата вакансии: факторы, итоговый процент, сортировка каталога."""

from types import SimpleNamespace

from httpx import AsyncClient

from app.models.enums import Grade, VerificationTier, WorkFormat
from app.services.matching.factors import (
    Candidate,
    DescriptionFactor,
    FormatFactor,
    GradeFactor,
    SalaryFactor,
    SkillsFactor,
)
from app.services.matching.scorer import VacancyContext, match
from app.services.matching.text import keywords, overlap
from tests.flows import CATALOG, approved_employer
from tests.helpers import bearer, register_candidate

PROFILE = "/api/v1/candidate/profile"


def skill(slug: str, name: str | None = None):
    return SimpleNamespace(slug=slug, name=name or slug.title())


def vacancy(**overrides):
    base = {
        "title": "Backend-разработчик",
        "description": "Высоконагруженный API на Python, PostgreSQL, очереди Kafka",
        "grade": Grade.MIDDLE,
        "work_format": WorkFormat.OFFICE,
        "city": "Казань",
        "salary_min": 200_000,
        "salary_max": 300_000,
        "skills": [skill("python"), skill("postgresql"), skill("kafka")],
    }
    return SimpleNamespace(**{**base, **overrides})


def ctx(v) -> VacancyContext:
    return VacancyContext.of(v)


def candidate(**overrides) -> Candidate:
    base = {
        "title": "Python-разработчик",
        "about": "Пишу высоконагруженные API, люблю PostgreSQL",
        "grade": Grade.MIDDLE,
        "work_format": WorkFormat.OFFICE,
        "city": "казань",
        "salary_min": 250_000,
        "verification_tier": VerificationTier.SELF_DECLARED,
        "skills": [skill("python"), skill("postgresql")],
    }
    return Candidate(SimpleNamespace(**{**base, **overrides}), [])  # type: ignore[arg-type]


def test_skills_share_and_explanation():
    result = SkillsFactor().score(ctx(vacancy()), candidate())
    assert result.share == round(2 / 3, 3)
    assert result.detail == "2 из 3: Python, Postgresql; нет: Kafka"


def test_grade_distance():
    assert GradeFactor().score(ctx(vacancy()), candidate()).share == 1.0
    assert GradeFactor().score(ctx(vacancy()), candidate(grade=Grade.SENIOR)).share == 0.5
    assert GradeFactor().score(ctx(vacancy()), candidate(grade=Grade.INTERN)).share == 0.0


def test_format_city_and_salary():
    assert FormatFactor().score(ctx(vacancy()), candidate()).detail == "тот же город: Казань"
    remote_wanted = candidate(city="Пермь", work_format=WorkFormat.REMOTE)
    assert FormatFactor().score(ctx(vacancy()), remote_wanted).share == 0.0
    assert SalaryFactor().score(ctx(vacancy()), candidate()).share == 1.0
    assert SalaryFactor().score(ctx(vacancy()), candidate(salary_min=360_000)).share == 0.6


def test_description_overlap_uses_word_stems():
    assert {"высоко", "разраб"} <= keywords("Высоконагруженный разработчик")
    share, common = overlap(
        "разработка высоконагруженных сервисов", "разработчик высоконагруженного API"
    )
    assert share == 1.0 and "разраб" in common
    assert (
        DescriptionFactor()
        .score(ctx(vacancy()), candidate(about=None, title=None, skills=[]))
        .share
        == 0
    )


def test_total_is_weighted_and_bounded():
    strong, weak = match(vacancy(), candidate()), match(vacancy(), candidate(skills=[], grade=None))
    assert 0 <= weak.score < strong.score <= 100
    assert sum(f.weight for f in strong.factors) == 100


async def set_profile(client: AsyncClient, token: str, **fields) -> None:
    r = await client.patch(PROFILE, json=fields, headers=bearer(token))
    assert r.status_code == 200, r.text


async def test_catalog_sorted_by_match_with_explanation(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    weak = await register_candidate(client)
    strong = await register_candidate(client)
    await set_profile(client, weak, title="Дизайнер", grade="intern", skills=["react"])
    await set_profile(
        client,
        strong,
        title="Backend",
        grade="middle",
        skills=["python", "postgresql"],
        about="Python API",
    )
    headers = bearer(employer["token"])
    params = {"vacancy_id": employer["vacancy"]["id"]}
    page = (await client.get(f"{CATALOG}/candidates", params=params, headers=headers)).json()
    scores = [c["match"]["score"] for c in page["items"]]
    assert len(scores) == 2 and scores[0] > scores[1]
    assert page["items"][0]["title"] == "Backend"
    assert {f["key"] for f in page["items"][0]["match"]["factors"]} == {
        "skills",
        "grade",
        "fsp",
        "description",
        "format",
        "salary",
    }
    # без вакансии — обычный порядок и без оценки
    plain = (await client.get(f"{CATALOG}/candidates", headers=headers)).json()
    assert all(c["match"] is None for c in plain["items"])


async def test_match_pages_and_foreign_vacancy(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    other = await approved_employer(client, db, app, name="ООО Чужая")
    for _ in range(3):
        await register_candidate(client)
    headers = bearer(employer["token"])
    params = {"vacancy_id": employer["vacancy"]["id"], "limit": 2}
    first = (await client.get(f"{CATALOG}/candidates", params=params, headers=headers)).json()
    second = (
        await client.get(
            f"{CATALOG}/candidates",
            params={**params, "cursor": first["next_cursor"]},
            headers=headers,
        )
    ).json()
    ids = [c["anon_id"] for c in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 3 and second["next_cursor"] is None
    foreign = {"vacancy_id": other["vacancy"]["id"]}
    r = await client.get(f"{CATALOG}/candidates", params=foreign, headers=headers)
    assert r.status_code == 404
    bad = await client.get(
        f"{CATALOG}/candidates", params={**params, "cursor": "zzz"}, headers=headers
    )
    assert bad.status_code == 409
