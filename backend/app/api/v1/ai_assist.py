"""Языковая модель в категоризации (подсказка для опроса) и подборе (второе мнение о кандидатах)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import CipherDep, PrincipalDep, SessionDep, require
from app.core.ratelimit import check_rate_limit
from app.services.access import Action
from app.services.ai_assist import (
    MAX_REVIEW,
    AiResolved,
    AiReviewOut,
    CategorizationAssistant,
    MatchingAssistant,
    SuggestionOut,
)
from app.services.ai_providers import active_client

router = APIRouter()


async def get_ai(request: Request, session: SessionDep, cipher: CipherDep) -> AiResolved:
    """Модель, активная в настройках (или ключ из окружения); None — ИИ выключен."""
    state = request.app.state
    return await active_client(session, cipher, state.settings, state.ai_transport)


AiDep = Annotated[AiResolved, Depends(get_ai)]


async def _ai_limit(request: Request, principal: PrincipalDep) -> None:
    await check_rate_limit(request, "ai", key=str(principal.user_id))


class AiStatusOut(BaseModel):
    available: bool
    provider: str | None = Field(default=None, description="куда уйдут анонимные карточки")


class ReviewIn(BaseModel):
    vacancy_id: uuid.UUID
    anon_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_REVIEW)


@router.post(
    "/candidate/assessment/suggestion",
    tags=["candidate"],
    dependencies=[require(Action.PROFILE_MANAGE_OWN), Depends(_ai_limit)],
    summary="Подсказка специализации и грейда для опроса: модель или правила по стеку и стажу",
)
async def suggest(session: SessionDep, principal: PrincipalDep, ai: AiDep) -> SuggestionOut:
    return await CategorizationAssistant(session, principal, ai).suggest()


@router.get(
    "/employer/catalog/ai-status",
    tags=["employer"],
    dependencies=[require(Action.CATALOG_READ)],
    summary="Подключена ли языковая модель для оценки кандидатов",
)
async def ai_status(ai: AiDep) -> AiStatusOut:
    return AiStatusOut(available=ai is not None, provider=ai[1] if ai else None)


@router.post(
    "/employer/catalog/ai-review",
    tags=["employer"],
    dependencies=[require(Action.CATALOG_READ), Depends(_ai_limit)],
    summary="Оценка до 10 кандидатов под вакансию языковой моделью (по анонимным карточкам)",
)
async def ai_review(
    data: ReviewIn, session: SessionDep, principal: PrincipalDep, ai: AiDep
) -> list[AiReviewOut]:
    return await MatchingAssistant(session, principal, ai).review(data.vacancy_id, data.anon_ids)
