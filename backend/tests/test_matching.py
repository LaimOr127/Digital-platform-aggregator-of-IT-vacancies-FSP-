"""Соответствие кандидата вакансии: категория и тест важнее самоописания; сила профиля."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from httpx import AsyncClient

from app.models.enums import Grade, Specialization, VerificationTier, WorkFormat
from app.services.matching.factors import (
    AssessmentFactor,
    Candidate,
    CategoryFactor,
    DescriptionFactor,
    FormatFactor,
    FreshnessFactor,
    SalaryFactor,
    SkillsFactor,
)
from app.services.matching.scorer import VacancyContext, match, strength
from app.services.matching.text import keywords, overlap
from tests.assessment_flow import confirm
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
        "specialization": Specialization.BACKEND,
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
        "specialization": Specialization.BACKEND,
        "confirmed_grade": Grade.MIDDLE,
        "assessment_score": 80,
        "confirmed_skills": ["python"],
        "last_activity_at": datetime.now(UTC),
        "work_format": WorkFormat.OFFICE,
        "city": "казань",
        "salary_min": 250_000,
        "verification_tier": VerificationTier.SELF_DECLARED,
        "skills": [skill("python"), skill("postgresql")],
    }
    return Candidate(SimpleNamespace(**{**base, **overrides}), [])  # type: ignore[arg-type]


def test_category_is_specialization_and_confirmed_grade():
    score = CategoryFactor().score
    assert score(ctx(vacancy()), candidate()).share == 1.0
    assert score(ctx(vacancy()), candidate(confirmed_grade=Grade.SENIOR)).share == 0.5
    assert score(ctx(vacancy()), candidate(specialization=Specialization.FRONTEND)).share == 0.0
    # заявленный, но не подтверждённый грейд почти не помогает
    unconfirmed = score(ctx(vacancy()), candidate(confirmed_grade=None))
    assert unconfirmed.share == 0.2 and "не подтверждён" in unconfirmed.detail


def test_skills_confirmed_by_test_count_fully():
    result = SkillsFactor().score(ctx(vacancy()), candidate())
    assert result.share == round((1 + 0.5) / 3, 3)
    assert result.detail == "подтверждены тестом: Python; заявлены: Postgresql; нет 1 из 3"


def test_assessment_and_freshness():
    assert AssessmentFactor().score(None, candidate()).share == 0.8
    assert AssessmentFactor().score(None, candidate(confirmed_grade=None)).share == 0.0
    stale = datetime.now(UTC) - timedelta(days=200)
    assert FreshnessFactor().score(None, candidate(last_activity_at=stale)).share == 0.0
    assert FreshnessFactor().score(None, candidate(last_activity_at=None)).share == 0.0


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
    empty = candidate(about=None, title=None, skills=[])
    assert DescriptionFactor().score(ctx(vacancy()), empty).share == 0


def test_tested_candidate_beats_self_described():
    """Самоописание (навыки, текст) не перевешивает подтверждённую категорию и тест."""
    tested = candidate(skills=[], about=None, confirmed_skills=["python", "postgresql"])
    claims = candidate(
        confirmed_grade=None,
        assessment_score=None,
        confirmed_skills=[],
        skills=[skill("python"), skill("postgresql"), skill("kafka")],
    )
    assert match(vacancy(), tested).score > match(vacancy(), claims).score
    assert sum(f.weight for f in match(vacancy(), tested).factors) == 100


def test_strength_ranks_by_test_and_fsp():
    weak = strength(candidate(assessment_score=30))
    strong = strength(candidate(verification_tier=VerificationTier.VERIFIED_FSP))
    assert strong.score > weak.score
    assert [f.key for f in strong.factors] == ["assessment", "fsp", "freshness"]


async def test_catalog_ranks_categories_and_explains(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    claims = await register_candidate(client)
    await client.patch(
        PROFILE,
        json={"title": "Пишу на всём", "grade": "middle", "skills": ["python", "postgresql"]},
        headers=bearer(claims),
    )
    tested = await register_candidate(client)
    await confirm(client, db, tested, "backend", "middle")
    headers = bearer(employer["token"])

    by_vacancy = (
        await client.get(
            f"{CATALOG}/candidates",
            params={"vacancy_id": employer["vacancy"]["id"]},
            headers=headers,
        )
    ).json()["items"]
    assert by_vacancy[0]["category"]["slug"] == "backend:middle"
    assert by_vacancy[0]["match"]["score"] > by_vacancy[1]["match"]["score"]
    assert {f["key"] for f in by_vacancy[0]["match"]["factors"]} >= {"category", "assessment"}

    # без вакансии — по силе профиля, тоже с объяснением
    plain = (await client.get(f"{CATALOG}/candidates", headers=headers)).json()["items"]
    assert plain[0]["confirmed_grade"] == "middle" and plain[0]["strength"]["score"] > 0
    assert all(c["match"] is None for c in plain)

    # категория и «только подтверждённые»
    only = (
        await client.get(f"{CATALOG}/candidates", params={"confirmed_only": True}, headers=headers)
    ).json()["items"]
    assert len(only) == 1
    category = (
        await client.get(
            f"{CATALOG}/candidates", params={"category": "backend:middle"}, headers=headers
        )
    ).json()["items"]
    assert len(category) == 1
    counts = (await client.get(f"{CATALOG}/categories", headers=headers)).json()
    assert {c["slug"]: c["candidates"] for c in counts}["backend:middle"] == 1
    bad = await client.get(f"{CATALOG}/candidates", params={"category": "x:y"}, headers=headers)
    assert bad.status_code == 422


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
