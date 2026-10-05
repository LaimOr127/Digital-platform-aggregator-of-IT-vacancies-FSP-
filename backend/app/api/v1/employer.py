import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import PrincipalDep, SessionDep
from app.models.enums import VacancyStatus
from app.schemas.common import PageOut
from app.schemas.employer import (
    CompanyOut,
    CompanyUpdateIn,
    VacancyCreateIn,
    VacancyOut,
    VacancyUpdateIn,
)
from app.services.employer import EmployerService

router = APIRouter(prefix="/employer", tags=["employer"])


def _service(session: SessionDep, principal: PrincipalDep) -> EmployerService:
    return EmployerService(session, principal)


ServiceDep = Annotated[EmployerService, Depends(_service)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/company", summary="Своя компания")
async def get_company(service: ServiceDep) -> CompanyOut:
    return CompanyOut.model_validate(await service.company())


@router.patch("/company", summary="Изменить профиль компании (владелец)")
async def update_company(data: CompanyUpdateIn, service: ServiceDep) -> CompanyOut:
    return CompanyOut.model_validate(await service.update_company(data))


@router.get("/vacancies", summary="Вакансии своей компании")
async def list_vacancies(
    service: ServiceDep,
    status_filter: Annotated[VacancyStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[VacancyOut]:
    page = await service.list_vacancies(status_filter, cursor, limit)
    return PageOut.build(page, VacancyOut)


@router.post("/vacancies", status_code=status.HTTP_201_CREATED, summary="Создать вакансию")
async def create_vacancy(data: VacancyCreateIn, service: ServiceDep) -> VacancyOut:
    return VacancyOut.model_validate(await service.create_vacancy(data))


@router.get("/vacancies/{vacancy_id}", summary="Вакансия своей компании")
async def get_vacancy(vacancy_id: uuid.UUID, service: ServiceDep) -> VacancyOut:
    return VacancyOut.model_validate(await service.get_vacancy(vacancy_id))


@router.patch("/vacancies/{vacancy_id}", summary="Изменить вакансию")
async def update_vacancy(
    vacancy_id: uuid.UUID, data: VacancyUpdateIn, service: ServiceDep
) -> VacancyOut:
    return VacancyOut.model_validate(await service.update_vacancy(vacancy_id, data))


@router.post("/vacancies/{vacancy_id}/publish", summary="Опубликовать/продлить на 14 дней")
async def publish_vacancy(vacancy_id: uuid.UUID, service: ServiceDep) -> VacancyOut:
    return VacancyOut.model_validate(await service.publish_vacancy(vacancy_id))


@router.post("/vacancies/{vacancy_id}/close", summary="Закрыть вакансию")
async def close_vacancy(vacancy_id: uuid.UUID, service: ServiceDep) -> VacancyOut:
    return VacancyOut.model_validate(await service.close_vacancy(vacancy_id))


@router.delete(
    "/vacancies/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить вакансию"
)
async def delete_vacancy(vacancy_id: uuid.UUID, service: ServiceDep) -> None:
    await service.delete_vacancy(vacancy_id)
