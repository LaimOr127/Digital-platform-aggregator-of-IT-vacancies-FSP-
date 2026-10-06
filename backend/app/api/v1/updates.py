"""Индикаторы нового: время последнего события по разделам кабинета."""

from fastapi import APIRouter, status

from app.api.deps import PrincipalDep, SessionDep, require
from app.schemas.updates import (
    CandidateSeenIn,
    CandidateUpdatesOut,
    EmployerSeenIn,
    EmployerUpdatesOut,
)
from app.services.access import Action
from app.services.updates import CandidateUpdatesService, EmployerUpdatesService

router = APIRouter()


@router.get("/candidate/updates", tags=["candidate"], summary="Когда что-то менялось в разделах")
async def candidate_updates(session: SessionDep, principal: PrincipalDep) -> CandidateUpdatesOut:
    return await CandidateUpdatesService(session, principal).get()


@router.get("/employer/updates", tags=["employer"], summary="Новое и вакансии к продлению")
async def employer_updates(session: SessionDep, principal: PrincipalDep) -> EmployerUpdatesOut:
    return await EmployerUpdatesService(session, principal).get()


@router.post(
    "/candidate/updates/seen",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["candidate"],
    dependencies=[require(Action.PROFILE_MANAGE_OWN)],
    summary="Раздел открыт: точка гаснет на всех устройствах",
)
async def candidate_seen(
    data: CandidateSeenIn, session: SessionDep, principal: PrincipalDep
) -> None:
    await CandidateUpdatesService(session, principal).seen.mark(data.section)


@router.post(
    "/employer/updates/seen",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["employer"],
    dependencies=[require(Action.COMPANY_READ_OWN)],
    summary="Раздел открыт: точка гаснет на всех устройствах",
)
async def employer_seen(data: EmployerSeenIn, session: SessionDep, principal: PrincipalDep) -> None:
    await EmployerUpdatesService(session, principal).seen.mark(data.section)
