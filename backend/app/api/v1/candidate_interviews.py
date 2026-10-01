"""Кандидат: приглашения на собеседование — выбрать время или отказаться."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CipherDep, PrincipalDep, SessionDep
from app.models.enums import InterviewStatus
from app.schemas.common import PageOut
from app.schemas.interviews import InterviewAcceptIn, InterviewOut, InterviewReasonIn
from app.services.interviews.candidate import CandidateInterviewService

router = APIRouter(prefix="/candidate/interviews", tags=["candidate"])


def _service(
    session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> CandidateInterviewService:
    return CandidateInterviewService(session, principal, cipher)


ServiceDep = Annotated[CandidateInterviewService, Depends(_service)]


@router.get("", summary="Приглашения на собеседование")
async def list_interviews(
    service: ServiceDep,
    status_filter: Annotated[InterviewStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PageOut[InterviewOut]:
    items, next_cursor = await service.list_interviews(status_filter, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/{interview_id}/accept", summary="Выбрать время собеседования")
async def accept(
    interview_id: uuid.UUID, data: InterviewAcceptIn, service: ServiceDep
) -> InterviewOut:
    return await service.accept(interview_id, data.slot)


@router.post("/{interview_id}/decline", summary="Отказаться от собеседования")
async def decline(
    interview_id: uuid.UUID, data: InterviewReasonIn, service: ServiceDep
) -> InterviewOut:
    return await service.decline(interview_id, data.reason)
