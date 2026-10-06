"""Тестирование кандидатов: опрос, тест на грейд, история; пример заданий под вакансию."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import PrincipalDep, SessionDep, require
from app.models.enums import Grade
from app.schemas.assessment import (
    AssessmentStateOut,
    AttemptOut,
    AttemptResultOut,
    PreviewQuestionOut,
    SubmitIn,
    SurveyIn,
    ViolationIn,
)
from app.services.access import Action
from app.services.assessment.preview import vacancy_preview
from app.services.assessment.service import AssessmentService

router = APIRouter(tags=["assessment"])


class StartIn(BaseModel):
    grade: Grade


def _service(session: SessionDep, principal: PrincipalDep) -> AssessmentService:
    return AssessmentService(session, principal)


ServiceDep = Annotated[AssessmentService, Depends(_service)]
Candidate = [require(Action.PROFILE_MANAGE_OWN)]


@router.get(
    "/candidate/assessment",
    dependencies=Candidate,
    summary="Категория, опрос, текущий тест, история и доступные грейды",
)
async def assessment_state(service: ServiceDep) -> AssessmentStateOut:
    return await service.state()


@router.put(
    "/candidate/assessment/survey",
    dependencies=Candidate,
    summary="Опрос: специализация, заявленный грейд, отрасли, роли, стаж, стек",
)
async def save_survey(data: SurveyIn, service: ServiceDep) -> AssessmentStateOut:
    return await service.save_survey(data)


@router.post(
    "/candidate/assessment/attempts",
    status_code=status.HTTP_201_CREATED,
    dependencies=Candidate,
    summary="Начать тест на грейд (задания генерируются для этой попытки)",
)
async def start_attempt(data: StartIn, service: ServiceDep) -> AttemptOut:
    return await service.start(data.grade)


@router.post(
    "/candidate/assessment/attempts/{attempt_id}/submit",
    dependencies=Candidate,
    summary="Отправить ответы и получить результат",
)
async def submit_attempt(
    attempt_id: uuid.UUID, data: SubmitIn, service: ServiceDep
) -> AttemptResultOut:
    return await service.submit(attempt_id, data)


@router.post(
    "/candidate/assessment/attempts/{attempt_id}/violation",
    dependencies=Candidate,
    summary="Снимок экрана во время теста: попытка не засчитана",
)
async def report_violation(
    attempt_id: uuid.UUID, data: ViolationIn, service: ServiceDep
) -> AttemptResultOut:
    return await service.forfeit(attempt_id, data.reason)


@router.get(
    "/employer/vacancies/{vacancy_id}/assessment-preview",
    dependencies=[require(Action.COMPANY_READ_OWN)],
    summary="Пример теста, который система соберёт под вакансию",
)
async def assessment_preview(
    vacancy_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[PreviewQuestionOut]:
    return await vacancy_preview(session, principal, vacancy_id)
