"""Демо-данные: компании с вакансиями и задачами, аккаунты для показа с одноразовым паролем."""

from sqlalchemy import func, select

from app.core.crypto import FieldCipher
from app.db.demo import seed_candidates, seed_market
from app.db.demo_logins import (
    DEMO_BLOCKED_CANDIDATE,
    DEMO_CANDIDATE,
    DEMO_EMPLOYER,
    DEMO_EMPLOYERS,
    DEMO_NEW_CANDIDATES,
    seed_logins,
)
from app.db.session import set_rls_context
from app.models import (
    CandidateProfile,
    EmployerCompany,
    EmployerTask,
    User,
    Vacancy,
    VacancyComplaint,
)
from app.models.enums import CompanyStatus, VacancyStatus
from tests.helpers import bearer, login


async def test_demo_market_has_vacancies_tasks_and_varied_profiles(db):
    cipher = FieldCipher("11" * 32)
    async with db.sessionmaker() as session:
        assert await seed_market(session, companies=2, vacancies_each=3) == 6
        assert await seed_candidates(session, cipher, 20) == 20
        await set_rls_context(session, None, "system")
        vacancies = (await session.execute(select(Vacancy))).scalars().all()
        tasks = await session.scalar(select(func.count()).select_from(EmployerTask))
        profiles = (await session.execute(select(CandidateProfile))).scalars().all()
    assert len(vacancies) == 6 and all(v.expires_at for v in vacancies)  # видно продление
    assert tasks == 4  # по две задачи на компанию
    assert len({p.specialization for p in profiles}) > 2 and any(p.education for p in profiles)


async def test_demo_logins_are_created_once(client, db):
    cipher = FieldCipher("11" * 32)
    async with db.sessionmaker() as session:
        first = await seed_logins(session, cipher)
    async with db.sessionmaker() as session:
        assert await seed_logins(session, cipher) == {}  # повтор не меняет пароль
    assert set(first) == {
        DEMO_CANDIDATE,
        DEMO_BLOCKED_CANDIDATE,
        *DEMO_NEW_CANDIDATES,
        *DEMO_EMPLOYERS,
    }
    # вход работает: почта подтверждена, пароль — напечатанный один раз
    assert await login(client, DEMO_EMPLOYER, first[DEMO_EMPLOYER])
    assert await login(client, DEMO_CANDIDATE, first[DEMO_CANDIDATE])
    # новый демо-кандидат ещё не проходил опрос и тест — жюри пройдёт их само
    token = await login(client, DEMO_NEW_CANDIDATES[0], first[DEMO_NEW_CANDIDATES[0]])
    state = (await client.get("/api/v1/candidate/assessment", headers=bearer(token))).json()
    assert state["survey"] is None and state["category"] is None


async def test_demo_password_can_be_set_for_the_jury_memo(db):
    async with db.sessionmaker() as session:
        logins = await seed_logins(session, FieldCipher("11" * 32), password="Jury-2026-memo")
    assert set(logins.values()) == {"Jury-2026-memo"}


async def test_demo_has_every_moderation_state(db):
    """Стенд показывает модерацию: компании на проверке и заблокированные, вакансии во всех
    статусах и с жалобами, заблокированные кандидаты."""
    async with db.sessionmaker() as session:
        await seed_candidates(session, FieldCipher("11" * 32), 60)
        await seed_market(session, companies=8, vacancies_each=8)
        await set_rls_context(session, None, "system")
        companies = set((await session.execute(select(EmployerCompany.status))).scalars())
        vacancies = set((await session.execute(select(Vacancy.status))).scalars())
        complaints = await session.scalar(select(func.count()).select_from(VacancyComplaint))
        blocked = await session.scalar(select(func.count()).where(User.is_active.is_(False)))
    assert companies == set(CompanyStatus)
    assert vacancies == set(VacancyStatus)
    assert complaints and blocked


async def test_demo_logins_cover_every_moderation_state(client, db):
    """Вход в компанию на модерации и заблокированную; заблокированный кандидат не входит."""
    async with db.sessionmaker() as session:
        logins = await seed_logins(session, FieldCipher("11" * 32), password="Jury-2026-memo")
    async with db.sessionmaker() as session:
        await set_rls_context(session, None, "system")
        statuses = set((await session.execute(select(EmployerCompany.status))).scalars())
    assert statuses == set(CompanyStatus) == set(DEMO_EMPLOYERS.values())
    pending = next(e for e, s in DEMO_EMPLOYERS.items() if s == CompanyStatus.PENDING)
    assert await login(client, pending, logins[pending])
    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_BLOCKED_CANDIDATE, "password": logins[DEMO_BLOCKED_CANDIDATE]},
    )
    assert blocked.status_code == 401
