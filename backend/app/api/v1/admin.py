import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import PrincipalDep, SessionDep
from app.models.enums import CompanyStatus
from app.schemas.common import PageOut
from app.schemas.employer import CompanyOut, CompanyStatusIn
from app.services.admin import AdminService

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
