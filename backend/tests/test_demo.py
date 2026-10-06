"""Демо-данные: компании с вакансиями и задачами, аккаунты для показа с одноразовым паролем."""

from sqlalchemy import func, select

from app.core.crypto import FieldCipher
from app.db.demo import DEMO_CANDIDATE, DEMO_EMPLOYER, seed_candidates, seed_logins, seed_market
from app.db.session import set_rls_context
from app.models import CandidateProfile, EmployerTask, Vacancy
from tests.helpers import login


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
    assert set(first) == {DEMO_CANDIDATE, DEMO_EMPLOYER}
    # вход работает: почта подтверждена, пароль — напечатанный один раз
    assert await login(client, DEMO_EMPLOYER, first[DEMO_EMPLOYER])
    assert await login(client, DEMO_CANDIDATE, first[DEMO_CANDIDATE])
