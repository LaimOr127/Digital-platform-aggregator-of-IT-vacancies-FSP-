"""Выход на контакт: приглашения компании кандидатам и отклики кандидатов, лента вакансий."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep, require
from app.core.ratelimit import check_rate_limit
from app.models.enums import (
    ApplicationDirection,
    ApplicationStatus,
    Grade,
    Specialization,
    WorkFormat,
)
from app.repositories.vacancies import BoardFilters
from app.schemas.applications import (
    AcceptResponseIn,
    ApplicationOut,
    BoardVacancyOut,
    DeclineIn,
    EmployerApplicationOut,
    InvitationIn,
    ResponseIn,
)
from app.schemas.catalog import OfferContactsOut
from app.schemas.common import PageOut
from app.services.access import Action
from app.services.applications.candidate import CandidateApplicationService
from app.services.applications.employer import EmployerApplicationService
from app.services.vacancy_board import VacancyBoardService

router = APIRouter(tags=["applications"])
Limit = Annotated[int, Query(ge=1, le=50)]
Employer = [require(Action.COMPANY_READ_OWN)]
Candidate = [require(Action.PROFILE_MANAGE_OWN)]


def _employer(
    session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> EmployerApplicationService:
    return EmployerApplicationService(session, principal, cipher)


def _candidate(
    session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> CandidateApplicationService:
    return CandidateApplicationService(session, principal, cipher)


def _board(session: SessionDep, principal: PrincipalDep) -> VacancyBoardService:
    return VacancyBoardService(session, principal)


EmployerDep = Annotated[EmployerApplicationService, Depends(_employer)]
CandidateDep = Annotated[CandidateApplicationService, Depends(_candidate)]
BoardDep = Annotated[VacancyBoardService, Depends(_board)]


async def _invite_limit(request: Request, principal: PrincipalDep) -> None:
    key = str(principal.company_id or principal.user_id)
    await check_rate_limit(request, "application_invite", key=key)


async def _respond_limit(request: Request, principal: PrincipalDep) -> None:
    await check_rate_limit(request, "application_respond", key=str(principal.user_id))


# --- компания -----------------------------------------------------------------------------
@router.post(
    "/employer/applications",
    status_code=status.HTTP_201_CREATED,
    dependencies=[*Employer, Depends(_invite_limit)],
    summary="Пригласить кандидата: предложение, вилка, способ связи (вакансия — по желанию)",
)
async def invite(data: InvitationIn, service: EmployerDep) -> EmployerApplicationOut:
    return await service.invite(data)


@router.get(
    "/employer/applications",
    dependencies=Employer,
    summary="Приглашения компании и отклики кандидатов (новые отклики становятся просмотренными)",
)
async def employer_applications(
    service: EmployerDep,
    direction: ApplicationDirection | None = None,
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[EmployerApplicationOut]:
    items, next_cursor = await service.list_applications(direction, status_filter, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post(
    "/employer/applications/{application_id}/accept",
    dependencies=Employer,
    summary="Принять отклик: кандидат получит способ связи",
)
async def accept_response(
    application_id: uuid.UUID, data: AcceptResponseIn, service: EmployerDep
) -> EmployerApplicationOut:
    return await service.accept_response(application_id, data)


@router.post(
    "/employer/applications/{application_id}/decline",
    dependencies=Employer,
    summary="Отклонить отклик",
)
async def decline_response(
    application_id: uuid.UUID, data: DeclineIn, service: EmployerDep
) -> EmployerApplicationOut:
    return await service.decline_response(application_id, data.reason)


@router.post(
    "/employer/applications/{application_id}/withdraw",
    dependencies=Employer,
    summary="Отозвать приглашение",
)
async def withdraw_invitation(
    application_id: uuid.UUID, service: EmployerDep
) -> EmployerApplicationOut:
    return await service.withdraw(application_id)


@router.get(
    "/employer/applications/{application_id}/contacts",
    dependencies=Employer,
    summary="Контакты кандидата (после принятия приглашения или по отклику)",
)
async def application_contacts(application_id: uuid.UUID, service: EmployerDep) -> OfferContactsOut:
    return await service.contacts(application_id)


# --- кандидат -----------------------------------------------------------------------------
@router.get(
    "/candidate/applications",
    dependencies=Candidate,
    summary="Приглашения и мои отклики (новые приглашения становятся просмотренными)",
)
async def candidate_applications(
    service: CandidateDep,
    direction: ApplicationDirection | None = None,
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[ApplicationOut]:
    items, next_cursor = await service.list_applications(direction, status_filter, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post(
    "/candidate/applications/{application_id}/accept",
    dependencies=Candidate,
    summary="Принять приглашение: компания получит имя и контакты",
)
async def accept_invitation(application_id: uuid.UUID, service: CandidateDep) -> ApplicationOut:
    return await service.accept(application_id)


@router.post(
    "/candidate/applications/{application_id}/decline",
    dependencies=Candidate,
    summary="Отклонить приглашение",
)
async def decline_invitation(
    application_id: uuid.UUID, data: DeclineIn, service: CandidateDep
) -> ApplicationOut:
    return await service.decline(application_id, data.reason)


@router.post(
    "/candidate/applications/{application_id}/withdraw",
    dependencies=Candidate,
    summary="Отозвать свой отклик",
)
async def withdraw_response(application_id: uuid.UUID, service: CandidateDep) -> ApplicationOut:
    return await service.withdraw(application_id)


@router.get(
    "/candidate/vacancies",
    dependencies=Candidate,
    summary="Опубликованные вакансии по соответствию профилю",
)
async def board(
    service: BoardDep,
    specialization: Specialization | None = None,
    grade: Grade | None = None,
    work_format: WorkFormat | None = None,
    skill: Annotated[str | None, Query(max_length=64)] = None,
    q: Annotated[str | None, Query(max_length=100, description="поиск по названию")] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[BoardVacancyOut]:
    filters = BoardFilters(specialization, grade, work_format, skill, (q or "").strip() or None)
    items, next_cursor = await service.list_vacancies(filters, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.get("/candidate/vacancies/{vacancy_id}", dependencies=Candidate, summary="Вакансия")
async def board_vacancy(vacancy_id: uuid.UUID, service: BoardDep) -> BoardVacancyOut:
    return await service.vacancy(vacancy_id)


@router.post(
    "/candidate/vacancies/{vacancy_id}/respond",
    status_code=status.HTTP_201_CREATED,
    dependencies=[*Candidate, Depends(_respond_limit)],
    summary="Откликнуться: компания сразу получит имя и контакты",
)
async def respond(vacancy_id: uuid.UUID, data: ResponseIn, service: CandidateDep) -> ApplicationOut:
    return await service.respond(vacancy_id, data)
