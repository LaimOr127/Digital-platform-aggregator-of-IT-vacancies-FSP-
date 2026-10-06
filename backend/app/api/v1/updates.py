"""Индикаторы нового: время последнего события по разделам кабинета."""

from fastapi import APIRouter

from app.api.deps import PrincipalDep, SessionDep
from app.schemas.updates import CandidateUpdatesOut, EmployerUpdatesOut
from app.services.updates import CandidateUpdatesService, EmployerUpdatesService

router = APIRouter()


@router.get("/candidate/updates", tags=["candidate"], summary="Когда что-то менялось в разделах")
async def candidate_updates(session: SessionDep, principal: PrincipalDep) -> CandidateUpdatesOut:
    return await CandidateUpdatesService(session, principal).get()


@router.get("/employer/updates", tags=["employer"], summary="Новое и вакансии к продлению")
async def employer_updates(session: SessionDep, principal: PrincipalDep) -> EmployerUpdatesOut:
    return await EmployerUpdatesService(session, principal).get()
