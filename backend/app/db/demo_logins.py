"""Именные демо-аккаунты с входом — для жюри и проверки каждого состояния вручную. Адреса
example.org: .local не проходит проверку адреса при входе. Пароль — заданный (DEMO_PASSWORD)
или случайный, печатается один раз; существующие аккаунты не меняются."""

import random
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, profile_field_context
from app.core.security import hash_password
from app.db.demo import _add_company, _profile, _user
from app.db.session import SYSTEM_ROLE, set_rls_context
from app.models import CandidateProfile, Skill, User
from app.models.enums import CompanyStatus, UserRole

DEMO_CANDIDATE = "demo-candidate@example.org"
# кандидаты без опроса и теста: жюри проходит путь кандидата само, если почта на стенде не работает
DEMO_NEW_CANDIDATES = tuple(f"demo-new-{i}@example.org" for i in range(1, 4))
# заблокирован модератором: вход отклоняется — видно, как работает блокировка
DEMO_BLOCKED_CANDIDATE = "demo-blocked@example.org"
DEMO_EMPLOYER = "demo-hr@example.org"
# компания в каждом статусе модерации: одобрена, ждёт проверки, заблокирована
DEMO_EMPLOYERS = {
    DEMO_EMPLOYER: CompanyStatus.APPROVED,
    "demo-hr-pending@example.org": CompanyStatus.PENDING,
    "demo-hr-blocked@example.org": CompanyStatus.BLOCKED,
}


async def seed_logins(
    session: AsyncSession, cipher: FieldCipher, password: str | None = None
) -> dict[str, str]:
    """Кандидат с профилем и категорией, три новых без теста, заблокированный кандидат и по
    компании в каждом статусе модерации с вакансиями и задачами."""
    await set_rls_context(session, None, SYSTEM_ROLE)
    emails = (DEMO_CANDIDATE, DEMO_BLOCKED_CANDIDATE, *DEMO_NEW_CANDIDATES, *DEMO_EMPLOYERS)
    existing = set(
        (await session.execute(select(User.email).where(User.email.in_(emails)))).scalars()
    )
    password = password or secrets.token_urlsafe(12)
    password_hash = hash_password(password)
    rng = random.Random(7)  # noqa: S311 - демо-данные
    created: dict[str, str] = {}
    for email, name, active in (
        (DEMO_CANDIDATE, "Анна Демо", True),
        (DEMO_BLOCKED_CANDIDATE, "Заблокированный Кандидат", False),
    ):
        if email in existing:
            continue
        user = _user(email, password_hash, UserRole.CANDIDATE)
        user.is_active = active
        session.add(user)
        await session.flush()
        profile = _profile(rng, user.id, cipher)
        profile.full_name_enc = cipher.encrypt(name, profile_field_context("full_name", user.id))
        session.add(profile)
        created[email] = password
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
    skills = {s.slug: s.id for s in (await session.execute(select(Skill))).scalars()}
    for index, (email, status) in enumerate(DEMO_EMPLOYERS.items()):
        if email in existing:
            continue
        owner = _user(email, password_hash)
        await _add_company(session, rng, skills, owner, index, 4, status)
        created[email] = password
    await session.commit()
    return created
