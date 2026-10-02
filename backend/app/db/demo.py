"""Демо-данные для показа и нагрузочного теста: анонимные кандидаты с навыками и категориями,
одобренные компании с опубликованными вакансиями (для каталога, радара зарплат и пути роста).

Только для dev: в prod команда отказывается работать. Вход в демо-аккаунты невозможен
(случайный пароль никому не известен) — они нужны лишь для наполнения каталога.
Генерация детерминирована (seed), повторный запуск добавляет новые профили.
"""

import random
import secrets
import uuid

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, profile_field_context
from app.core.security import hash_password
from app.db.session import SYSTEM_ROLE, set_rls_context
from app.models import (
    CandidateProfile,
    Category,
    CompanyMember,
    EmployerCompany,
    Skill,
    User,
    Vacancy,
    candidate_categories,
    profile_skills,
    vacancy_skills,
)
from app.models.enums import (
    CompanyStatus,
    Grade,
    MemberRole,
    SearchStatus,
    UserRole,
    VacancyStatus,
    VerificationTier,
    WorkFormat,
)

_TITLES = [
    ("Backend-разработчик", ["python", "go", "postgresql", "docker", "kafka", "redis"]),
    ("Frontend-разработчик", ["javascript", "typescript", "react", "vue"]),
    ("Специалист по информационной безопасности", ["information-security", "pentest", "linux"]),
    ("ML-инженер", ["python", "machine-learning", "pytorch", "data-analysis"]),
    ("Разработчик робототехники", ["c++", "python", "robotics", "linux"]),
    ("Мобильный разработчик", ["kotlin", "swift", "android", "ios"]),
    ("DevOps-инженер", ["docker", "kubernetes", "terraform", "ci-cd", "linux"]),
]
_CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", None]
# вилки по грейдам (₽ в месяц): нижняя граница выбирается из диапазона, ширина — 20-40%
_GRADE_SALARY = {
    Grade.INTERN: (50_000, 100_000),
    Grade.JUNIOR: (100_000, 180_000),
    Grade.MIDDLE: (180_000, 300_000),
    Grade.SENIOR: (280_000, 450_000),
    Grade.LEAD: (400_000, 600_000),
}
_COMPANY_NAMES = [
    "Демо Софт",
    "Байт Лаб",
    "Северный Код",
    "Алгоритмика",
    "Облако Плюс",
    "Кибер Щит",
]
_ABOUT = [
    "Разрабатываю высоконагруженные сервисы и API, люблю чистую архитектуру.",
    "Участвую в соревнованиях ФСП с командой, отвечаю за алгоритмическую часть.",
    "Пишу автотесты и слежу за качеством, настраиваю CI/CD.",
    "Занимаюсь анализом данных и обучением моделей, довожу до продакшена.",
]


async def seed_candidates(session: AsyncSession, cipher: FieldCipher, count: int) -> int:
    await set_rls_context(session, None, SYSTEM_ROLE)
    rng = random.Random(count)  # noqa: S311 - демо-данные, не криптография
    skills = {s.slug: s.id for s in (await session.execute(select(Skill))).scalars()}
    categories = list((await session.execute(select(Category))).scalars())
    password_hash = hash_password(secrets.token_urlsafe(24))  # один хеш: вход невозможен
    skill_links: list[dict] = []
    category_links: list[dict] = []
    profiles: list[CandidateProfile] = []
    for _ in range(count):
        user = User(
            id=uuid.uuid4(),
            email=f"demo-{uuid.uuid4().hex[:12]}@demo.itmatch.local",
            password_hash=password_hash,
            role=UserRole.CANDIDATE,
            email_verified=True,
        )
        profile = _profile(rng, user.id, cipher)
        session.add(user)
        profiles.append(profile)
        title_skills = next(s for t, s in _TITLES if t == profile.title)
        picked = rng.sample(title_skills, k=min(len(title_skills), rng.randint(2, 4)))
        skill_links += [
            {"profile_id": profile.id, "skill_id": skills[slug]}
            for slug in picked
            if slug in skills
        ]
        if profile.verification_tier == VerificationTier.VERIFIED_FSP and categories:
            category = rng.choice(categories)
            category_links.append(
                {"profile_id": profile.id, "category_id": category.id, "reasons": []}
            )
    await session.flush()  # сначала пользователи: у моделей нет связи, порядок задаём сами
    session.add_all(profiles)
    await session.flush()
    for table, rows in ((profile_skills, skill_links), (candidate_categories, category_links)):
        if rows:
            await session.execute(insert(table), rows)
    await session.commit()
    return count


def _profile(rng: random.Random, user_id: uuid.UUID, cipher: FieldCipher) -> CandidateProfile:
    title, _ = rng.choice(_TITLES)
    salary = rng.randrange(80_000, 450_000, 10_000)
    profile = CandidateProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        about=rng.choice(_ABOUT),
        grade=rng.choice(list(Grade)),
        work_format=rng.choice(list(WorkFormat)),
        city=rng.choice(_CITIES),
        salary_min=salary,
        salary_max=salary + 50_000,
        verification_tier=rng.choice(
            [VerificationTier.SELF_DECLARED, VerificationTier.VERIFIED_FSP]
        ),
        search_status=rng.choice([SearchStatus.ACTIVE, SearchStatus.OPEN, SearchStatus.OPEN]),
    )
    profile.full_name_enc = cipher.encrypt(
        "Демо Кандидат", profile_field_context("full_name", user_id)
    )
    return profile


async def seed_market(session: AsyncSession, companies: int, vacancies_each: int) -> int:
    """Одобренные компании с опубликованными вакансиями по грейдам и направлениям."""
    await set_rls_context(session, None, SYSTEM_ROLE)
    rng = random.Random(companies * 1000 + vacancies_each)  # noqa: S311 - демо-данные
    skills = {s.slug: s.id for s in (await session.execute(select(Skill))).scalars()}
    password_hash = hash_password(secrets.token_urlsafe(24))
    skill_links: list[dict] = []
    created = 0
    for i in range(companies):
        owner = User(
            id=uuid.uuid4(),
            email=f"demo-hr-{uuid.uuid4().hex[:10]}@demo.itmatch.local",
            password_hash=password_hash,
            role=UserRole.EMPLOYER,
            email_verified=True,
        )
        name = f"ООО «{_COMPANY_NAMES[i % len(_COMPANY_NAMES)]} {i + 1}»"
        company = EmployerCompany(id=uuid.uuid4(), name=name, status=CompanyStatus.APPROVED)
        session.add_all([owner, company])
        await session.flush()
        session.add(CompanyMember(company_id=company.id, user_id=owner.id, role=MemberRole.OWNER))
        for _ in range(vacancies_each):
            vacancy, picked = _vacancy(rng, company.id)
            session.add(vacancy)
            skill_links += [
                {"vacancy_id": vacancy.id, "skill_id": skills[s]} for s in picked if s in skills
            ]
            created += 1
    await session.flush()
    if skill_links:
        await session.execute(insert(vacancy_skills), skill_links)
    await session.commit()
    return created


def _vacancy(rng: random.Random, company_id: uuid.UUID) -> tuple[Vacancy, list[str]]:
    title, title_skills = rng.choice(_TITLES)
    grade = rng.choice(list(Grade))
    low_from, low_to = _GRADE_SALARY[grade]
    salary_min = rng.randrange(low_from, low_to, 10_000)
    vacancy = Vacancy(
        id=uuid.uuid4(),
        company_id=company_id,
        title=title,
        description=rng.choice(_ABOUT),
        grade=grade,
        work_format=rng.choice(list(WorkFormat)),
        city=rng.choice(_CITIES),
        salary_min=salary_min,
        salary_max=salary_min + rng.randrange(salary_min // 5, salary_min // 5 * 2, 5_000),
        status=VacancyStatus.ACTIVE,
    )
    return vacancy, rng.sample(title_skills, k=min(len(title_skills), rng.randint(2, 4)))
