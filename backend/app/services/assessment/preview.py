"""Как система формирует задания под вакансию: пример теста по её специализации, грейду
и навыкам. Вариант генерируется заново при каждом запросе, поэтому показывается с ответами."""

import random
import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidStateError
from app.schemas.assessment import PreviewQuestionOut
from app.services.access import Principal
from app.services.assessment import views
from app.services.assessment.engine import assemble
from app.services.employer import EmployerService
from app.services.specializations import level


async def vacancy_preview(
    session: AsyncSession, principal: Principal, vacancy_id: uuid.UUID
) -> list[PreviewQuestionOut]:
    vacancy = await EmployerService(session, principal).get_vacancy(vacancy_id)
    if vacancy.specialization is None:
        raise InvalidStateError("укажите специализацию вакансии — по ней подбираются задания")
    focus = frozenset(s.slug for s in vacancy.skills)
    rng = random.Random(secrets.token_hex(8))
    items = assemble(vacancy.specialization.value, level(vacancy.grade), rng, focus)
    return [views.preview_question(i, item) for i, item in enumerate(items)]
