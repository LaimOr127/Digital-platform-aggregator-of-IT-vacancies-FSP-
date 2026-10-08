"""Демо-данные для показа и нагрузочного теста: кандидаты разных специализаций и грейдов
с навыками, образованием и категориями; одобренные компании с описанием, вакансиями (часть —
к продлению) и короткими задачами для кандидатов.

Только для dev: в prod команда отказывается работать. Вход в массовые демо-аккаунты невозможен
(случайный пароль никому не известен); для показа создаются два аккаунта с входом — кандидат и
компания, их пароль печатается один раз (seed_logins).
Генерация детерминирована (seed), повторный запуск добавляет новые профили.
"""

import random
import secrets
import uuid
from datetime import UTC, datetime, timedelta

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
    EmployerTask,
    Skill,
    User,
    Vacancy,
    candidate_categories,
    profile_skills,
    vacancy_skills,
)
from app.models.enums import (
    CompanyStatus,
    Education,
    Grade,
    MemberRole,
    SearchStatus,
    Specialization,
    UserRole,
    VacancyStatus,
    VerificationTier,
    WorkFormat,
)
from app.services.specializations import INDUSTRIES

_TITLES = [
    (
        "Backend-разработчик",
        Specialization.BACKEND,
        ["python", "go", "postgresql", "kafka", "redis"],
    ),
    ("Frontend-разработчик", Specialization.FRONTEND, ["javascript", "typescript", "react", "vue"]),
    (
        "Специалист по информационной безопасности",
        Specialization.SECURITY,
        ["information-security", "pentest", "linux"],
    ),
    ("ML-инженер", Specialization.DATA, ["python", "machine-learning", "pytorch", "data-analysis"]),
    ("Инженер по тестированию", Specialization.QA, ["qa-automation", "python", "sql"]),
    ("Мобильный разработчик", Specialization.MOBILE, ["kotlin", "swift", "android", "ios"]),
    ("DevOps-инженер", Specialization.DEVOPS, ["docker", "kubernetes", "terraform", "ci-cd"]),
]
_GRADES = list(Grade)
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
_INDUSTRIES = ["fintech", "ecommerce", "telecom", "games", "logistics", "government"]
_SOFT_SKILLS = ["communication", "teamwork", "ownership", "learning", "problem_solving"]
# короткие задачи компаний: по одной на специализацию (заголовок, текст)
_TASKS = {
    Specialization.BACKEND: (
        "Медленный эндпоинт ленты",
        "Лента пользователя отвечает 3 секунды. Как найдёте причину и что поправите?",
    ),
    Specialization.FRONTEND: (
        "Тормозит список из 10 000 строк",
        "Список заказов подвисает при прокрутке. Предложите, как ускорить отрисовку.",
    ),
    Specialization.QA: (
        "Поле ввода возраста",
        "Возраст — целое число от 18 до 120. Составьте набор проверок и объясните выбор значений.",
    ),
    Specialization.DATA: (
        "Модель деградировала",
        "Качество модели оттока упало за месяц на 8 %. Опишите, как будете искать причину.",
    ),
    Specialization.DEVOPS: (
        "Падающий деплой",
        "Каждый третий выкат в Kubernetes откатывается по health-check. С чего начнёте?",
    ),
    Specialization.MOBILE: (
        "Холодный старт 4 секунды",
        "Приложение долго запускается на старых Android. Как измерите и что ускорите?",
    ),
    Specialization.SECURITY: (
        "Подозрительные входы",
        "В логах — сотни неудачных входов с разных IP за час. Ваши действия и выводы?",
    ),
}
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
        user = _user(
            f"demo-{uuid.uuid4().hex[:12]}@demo.itmatch.local", password_hash, UserRole.CANDIDATE
        )
        profile = _profile(rng, user.id, cipher)
        session.add(user)
        profiles.append(profile)
        title_skills = next(s for t, _, s in _TITLES if t == profile.title)
        picked = rng.sample(title_skills, k=min(len(title_skills), rng.randint(2, 4)))
        if profile.confirmed_grade:
            profile.confirmed_skills = picked[: rng.randint(1, len(picked))]
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
    """Как после опроса и теста: у ~75% грейд подтверждён (иногда на ступень ниже заявленного)."""
    title, specialization, _ = rng.choice(_TITLES)
    salary = rng.randrange(80_000, 450_000, 10_000)
    grade = rng.choice(_GRADES)
    now = datetime.now(UTC)
    tested = rng.random() < 0.75
    confirmed = _GRADES[max(0, _GRADES.index(grade) - rng.choice([0, 0, 1]))] if tested else None
    profile = CandidateProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        about=rng.choice(_ABOUT),
        specialization=specialization,
        experience_years=_GRADES.index(grade) * 2 + rng.randint(0, 2),
        survey_at=now - timedelta(days=rng.randint(1, 120)),
        confirmed_grade=confirmed,
        grade_confirmed_at=now - timedelta(days=rng.randint(1, 120)) if tested else None,
        assessment_score=rng.randint(0, 100) if tested else None,
        last_activity_at=now - timedelta(days=rng.randint(0, 200)) if tested else None,
        grade=grade,
        work_formats=rng.sample([f.value for f in WorkFormat], k=rng.randint(1, 2)),
        city=rng.choice(_CITIES),
        relocation=rng.random() < 0.3,
        education=rng.choice([None, *Education]),
        soft_skills=rng.sample(_SOFT_SKILLS, k=rng.randint(1, 3)),
        industries=rng.sample(_INDUSTRIES, k=rng.randint(1, 2)),
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
    for i in range(companies):
        owner = _user(f"demo-hr-{uuid.uuid4().hex[:10]}@demo.itmatch.local", password_hash)
        await _add_company(session, rng, skills, owner, i, vacancies_each)
    await session.commit()
    return companies * vacancies_each


DEMO_CANDIDATE = "demo-candidate@example.org"  # .local не проходит проверку адреса при входе
DEMO_EMPLOYER = "demo-hr@example.org"
# кандидаты без опроса и теста: жюри проходит путь кандидата само, если почта на стенде не работает
DEMO_NEW_CANDIDATES = tuple(f"demo-new-{i}@example.org" for i in range(1, 4))


async def seed_logins(
    session: AsyncSession, cipher: FieldCipher, password: str | None = None
) -> dict[str, str]:
    """Аккаунты для показа: кандидат с заполненным профилем и категорией, три новых кандидата без
    теста и компания с вакансиями и задачами. Пароль — заданный (DEMO_PASSWORD) или случайный,
    возвращается один раз; существующие аккаунты не меняются."""
    await set_rls_context(session, None, SYSTEM_ROLE)
    emails = (DEMO_CANDIDATE, DEMO_EMPLOYER, *DEMO_NEW_CANDIDATES)
    existing = set(
        (await session.execute(select(User.email).where(User.email.in_(emails)))).scalars()
    )
    password = password or secrets.token_urlsafe(12)
    password_hash = hash_password(password)
    rng = random.Random(7)  # noqa: S311 - демо-данные
    created: dict[str, str] = {}
    if DEMO_CANDIDATE not in existing:
        user = _user(DEMO_CANDIDATE, password_hash, UserRole.CANDIDATE)
        session.add(user)
        await session.flush()
        profile = _profile(rng, user.id, cipher)
        profile.full_name_enc = cipher.encrypt(
            "Анна Демо", profile_field_context("full_name", user.id)
        )
        session.add(profile)
        created[DEMO_CANDIDATE] = password
    for i, email in enumerate(DEMO_NEW_CANDIDATES, start=1):
        if email in existing:
            continue
        user = _user(email, password_hash, UserRole.CANDIDATE)
        session.add(user)
        await session.flush()
        profile = CandidateProfile(id=uuid.uuid4(), user_id=user.id)
        profile.full_name_enc = cipher.encrypt(
            f"Новый Кандидат {i}", profile_field_context("full_name", user.id)
        )
        session.add(profile)
        created[email] = password
    if DEMO_EMPLOYER not in existing:
        skills = {s.slug: s.id for s in (await session.execute(select(Skill))).scalars()}
        await _add_company(session, rng, skills, _user(DEMO_EMPLOYER, password_hash), 0, 4)
        created[DEMO_EMPLOYER] = password
    await session.commit()
    return created


def _user(email: str, password_hash: str, role: UserRole = UserRole.EMPLOYER) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash=password_hash,
        role=role,
        email_verified=True,
        consent_at=datetime.now(UTC),
    )


async def _add_company(
    session: AsyncSession,
    rng: random.Random,
    skills: dict[str, uuid.UUID],
    owner: User,
    index: int,
    vacancies: int,
) -> None:
    """Компания с описанием, двумя задачами для кандидатов и опубликованными вакансиями."""
    company = EmployerCompany(
        id=uuid.uuid4(),
        name=f"ООО «{_COMPANY_NAMES[index % len(_COMPANY_NAMES)]} {index + 1}»",
        status=CompanyStatus.APPROVED,
        industry=rng.choice(list(INDUSTRIES.values())),
        description="Продуктовая ИТ-команда: выпускаем релизы каждые две недели, "
        "ценим инженерную культуру и обучение внутри команды.",
        contact_email=f"hr{index + 1}@example.org",  # .local не проходит проверку email в форме
    )
    session.add_all([owner, company])
    await session.flush()
    session.add(CompanyMember(company_id=company.id, user_id=owner.id, role=MemberRole.OWNER))
    for specialization in rng.sample(list(_TASKS), k=2):
        title, body = _TASKS[specialization]
        session.add(
            EmployerTask(
                company_id=company.id,
                created_by=owner.id,
                title=title,
                body=body,
                specialization=specialization,
                is_active=True,
            )
        )
    skill_links: list[dict] = []
    for _ in range(vacancies):
        vacancy, picked = _vacancy(rng, company.id)
        session.add(vacancy)
        skill_links += [
            {"vacancy_id": vacancy.id, "skill_id": skills[s]} for s in picked if s in skills
        ]
    await session.flush()
    if skill_links:
        await session.execute(insert(vacancy_skills), skill_links)


def _vacancy(rng: random.Random, company_id: uuid.UUID) -> tuple[Vacancy, list[str]]:
    title, specialization, title_skills = rng.choice(_TITLES)
    grade = rng.choice(_GRADES)
    low_from, low_to = _GRADE_SALARY[grade]
    salary_min = rng.randrange(low_from, low_to, 10_000)
    vacancy = Vacancy(
        id=uuid.uuid4(),
        company_id=company_id,
        title=title,
        description=rng.choice(_ABOUT),
        grade=grade,
        specialization=specialization,
        work_format=rng.choice(list(WorkFormat)),
        city=rng.choice(_CITIES),
        salary_min=salary_min,
        salary_max=salary_min + rng.randrange(salary_min // 5, salary_min // 5 * 2, 5_000),
        status=VacancyStatus.ACTIVE,
        # часть вакансий истекает в ближайшие дни — видно, как работает продление
        expires_at=datetime.now(UTC) + timedelta(days=rng.randint(1, 14)),
    )
    return vacancy, rng.sample(title_skills, k=min(len(title_skills), rng.randint(2, 4)))
