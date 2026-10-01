"""Работодатель: приглашения на собеседование, отмена, результат (дальше — оффер)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep
from app.core.ratelimit import check_rate_limit
from app.models.enums import InterviewStatus
from app.schemas.common import PageOut
from app.schemas.interviews import (
    EmployerInterviewOut,
    InterviewCompleteIn,
    InterviewInviteIn,
    InterviewReasonIn,
)
from app.services.interviews.employer import EmployerInterviewService

router = APIRouter(prefix="/employer/interviews", tags=["employer"])


def _service(
    session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> EmployerInterviewService:
    return EmployerInterviewService(session, principal, cipher)


ServiceDep = Annotated[EmployerInterviewService, Depends(_service)]


async def _invite_limit(request: Request, principal: PrincipalDep) -> None:
    """Приглашения компании в сутки ограничены: кандидатов не заваливают."""
    key = str(principal.company_id or principal.user_id)
    await check_rate_limit(request, "interview_invite", key=key)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_invite_limit)],
    summary="Пригласить кандидата на собеседование (1-3 варианта времени)",
)
async def invite(data: InterviewInviteIn, service: ServiceDep) -> EmployerInterviewOut:
    return await service.invite(data)


@router.get("", summary="Собеседования компании")
async def list_interviews(
    service: ServiceDep,
    status_filter: Annotated[InterviewStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PageOut[EmployerInterviewOut]:
    items, next_cursor = await service.list_interviews(status_filter, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/{interview_id}/cancel", summary="Отменить собеседование")
async def cancel(
    interview_id: uuid.UUID, data: InterviewReasonIn, service: ServiceDep
) -> EmployerInterviewOut:
    return await service.cancel(interview_id, data.reason)


@router.post("/{interview_id}/complete", summary="Отметить результат (после встречи)")
async def complete(
    interview_id: uuid.UUID, data: InterviewCompleteIn, service: ServiceDep
) -> EmployerInterviewOut:
    return await service.complete(interview_id, data)
