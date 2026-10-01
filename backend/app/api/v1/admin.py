import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import PrincipalDep, SessionDep
from app.models.enums import CompanyStatus, UserRole, VacancyStatus
from app.schemas.admin import AdminUserOut, AdminVacancyOut, AuditEntryOut, ModerationIn
from app.schemas.common import PageOut
from app.schemas.employer import CompanyOut, CompanyStatusIn
from app.services.admin import AdminService
from app.services.moderation import ModerationService

router = APIRouter(prefix="/admin", tags=["admin"])


def _service(session: SessionDep, principal: PrincipalDep) -> AdminService:
    return AdminService(session, principal)


ServiceDep = Annotated[AdminService, Depends(_service)]


@router.get("/companies", summary="Компании (фильтр по статусу модерации)")
async def list_companies(
    service: ServiceDep,
    status: CompanyStatus | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageOut[CompanyOut]:
    page = await service.list_companies(status, cursor, limit)
    return PageOut.build(page, CompanyOut)


@router.post("/companies/{company_id}/status", summary="Одобрить/заблокировать компанию")
async def set_company_status(
    company_id: uuid.UUID, data: CompanyStatusIn, service: ServiceDep
) -> CompanyOut:
    company = await service.set_company_status(company_id, data.status, data.reason)
    return CompanyOut.model_validate(company)


def _moderation(session: SessionDep, principal: PrincipalDep) -> ModerationService:
    return ModerationService(session, principal)


ModerationDep = Annotated[ModerationService, Depends(_moderation)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/vacancies", summary="Все вакансии (модерация)")
async def list_vacancies(
    service: ModerationDep,
    status: VacancyStatus | None = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[AdminVacancyOut]:
    items, next_cursor = await service.list_vacancies(status, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/vacancies/{vacancy_id}/moderation", summary="Заблокировать/разблокировать вакансию")
async def moderate_vacancy(
    vacancy_id: uuid.UUID, data: ModerationIn, service: ModerationDep
) -> AdminVacancyOut:
    return await service.moderate_vacancy(vacancy_id, data.action, data.reason)


@router.get("/users", summary="Пользователи (поиск по email, фильтр по роли)")
async def list_users(
    service: ModerationDep,
    role: UserRole | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[AdminUserOut]:
    items, next_cursor = await service.list_users(role, q, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/users/{user_id}/moderation", summary="Заблокировать/разблокировать пользователя")
async def moderate_user(
    user_id: uuid.UUID, data: ModerationIn, service: ModerationDep
) -> AdminUserOut:
    return await service.moderate_user(user_id, data.action, data.reason)


@router.get("/audit", summary="Журнал аудита")
async def list_audit(
    service: ModerationDep,
    action: Annotated[str | None, Query(max_length=64, pattern=r"^[a-z_.]+$")] = None,
    cursor: str | None = None,
    limit: Limit = 50,
) -> PageOut[AuditEntryOut]:
    items, next_cursor = await service.list_audit(action, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)
