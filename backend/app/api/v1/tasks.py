"""Регулярные короткие задания: компания публикует, кандидат решает задачу периода."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import PrincipalDep, SessionDep, require
from app.schemas.common import PageOut
from app.schemas.tasks import (
    AnswerIn,
    CurrentTaskOut,
    MyTaskAnswerOut,
    RatingIn,
    TaskAnswerOut,
    TaskIn,
    TaskOut,
)
from app.services.access import Action
from app.services.tasks import CandidateTaskService, EmployerTaskService

router = APIRouter(tags=["tasks"])
Limit = Annotated[int, Query(ge=1, le=50)]
Employer = [require(Action.COMPANY_READ_OWN)]
Candidate = [require(Action.PROFILE_MANAGE_OWN)]


def _employer(session: SessionDep, principal: PrincipalDep) -> EmployerTaskService:
    return EmployerTaskService(session, principal)


def _candidate(session: SessionDep, principal: PrincipalDep) -> CandidateTaskService:
    return CandidateTaskService(session, principal)


EmployerDep = Annotated[EmployerTaskService, Depends(_employer)]
CandidateDep = Annotated[CandidateTaskService, Depends(_candidate)]


@router.post(
    "/employer/tasks",
    status_code=status.HTTP_201_CREATED,
    dependencies=Employer,
    summary="Опубликовать короткую задачу для кандидатов специализации",
)
async def create_task(data: TaskIn, service: EmployerDep) -> TaskOut:
    return await service.create(data)


@router.get("/employer/tasks", dependencies=Employer, summary="Задачи компании с числом ответов")
async def list_tasks(
    service: EmployerDep, cursor: str | None = None, limit: Limit = 20
) -> PageOut[TaskOut]:
    items, next_cursor = await service.list_tasks(cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/employer/tasks/{task_id}/close", dependencies=Employer, summary="Снять задачу")
async def close_task(task_id: uuid.UUID, service: EmployerDep) -> TaskOut:
    return await service.close(task_id)


@router.get(
    "/employer/tasks/{task_id}/answers",
    dependencies=Employer,
    summary="Ответы кандидатов: анонимные карточки, без имени и контактов",
)
async def task_answers(
    task_id: uuid.UUID, service: EmployerDep, cursor: str | None = None, limit: Limit = 20
) -> PageOut[TaskAnswerOut]:
    items, next_cursor = await service.list_answers(task_id, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post(
    "/employer/tasks/{task_id}/answers/{answer_id}/rate",
    dependencies=Employer,
    summary="Оценить ответ (1–5): оценку видит кандидат",
)
async def rate_answer(
    task_id: uuid.UUID, answer_id: uuid.UUID, data: RatingIn, service: EmployerDep
) -> TaskAnswerOut:
    return await service.rate(task_id, answer_id, data.rating)


@router.get(
    "/candidate/tasks/current",
    dependencies=Candidate,
    summary="Задача периода (одна в неделю) или когда откроется следующая",
)
async def current_task(service: CandidateDep) -> CurrentTaskOut:
    return await service.current()


@router.post(
    "/candidate/tasks/{task_id}/answers",
    status_code=status.HTTP_201_CREATED,
    dependencies=Candidate,
    summary="Ответить: решение или подход к решению",
)
async def answer_task(task_id: uuid.UUID, data: AnswerIn, service: CandidateDep) -> MyTaskAnswerOut:
    return await service.answer(task_id, data)


@router.get("/candidate/tasks/answers", dependencies=Candidate, summary="Мои ответы и оценки")
async def my_answers(
    service: CandidateDep, cursor: str | None = None, limit: Limit = 20
) -> PageOut[MyTaskAnswerOut]:
    items, next_cursor = await service.my_answers(cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)
