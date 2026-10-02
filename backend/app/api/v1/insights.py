"""Радар зарплат и путь роста (кандидат), рынок зарплат для вакансии (работодатель)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import PrincipalDep, SessionDep, require
from app.models.enums import Grade
from app.schemas.insights import GrowthOut, SalaryRadarOut
from app.services.access import Action
from app.services.insights import InsightsService

router = APIRouter(tags=["insights"])


def _service(session: SessionDep, principal: PrincipalDep) -> InsightsService:
    return InsightsService(session, principal)


ServiceDep = Annotated[InsightsService, Depends(_service)]


@router.get("/candidate/insights/salary", summary="Радар зарплат по моему грейду и стеку")
async def candidate_salary(service: ServiceDep) -> SalaryRadarOut:
    return await service.candidate_radar()


@router.get(
    "/candidate/insights/growth", summary="Путь роста: чего не хватает до следующего грейда"
)
async def candidate_growth(service: ServiceDep) -> GrowthOut:
    return await service.growth()


@router.get(
    "/employer/insights/salary",
    dependencies=[require(Action.COMPANY_READ_OWN)],
    summary="Рынок зарплат для вакансии (грейд и навыки)",
)
async def employer_salary(
    service: ServiceDep,
    grade: Grade,
    skills: Annotated[list[str], Query(max_length=20)] = [],  # noqa: B006 - FastAPI копирует
) -> SalaryRadarOut:
    return await service.market(grade, skills)
