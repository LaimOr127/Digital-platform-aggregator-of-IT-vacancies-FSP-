"""Публичные справочники и данные текущего пользователя (без бизнес-правил, только чтение)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.repositories.candidates import SkillRepository
from app.repositories.users import UserRepository
from app.schemas.auth import MeOut
from app.schemas.common import SkillOut
from app.services.access import Principal


async def list_skills(session: AsyncSession) -> list[SkillOut]:
    return [SkillOut.model_validate(s) for s in await SkillRepository(session).all()]


async def current_user(session: AsyncSession, principal: Principal) -> MeOut:
    user = await UserRepository(session).get(principal.user_id)
    if user is None:
        raise UnauthorizedError("authentication required")
    return MeOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_superadmin=user.is_superadmin,
        company_id=principal.company_id,
        consent_at=user.consent_at,
    )
