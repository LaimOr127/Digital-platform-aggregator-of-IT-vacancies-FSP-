from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CipherDep, PrincipalDep, SessionDep
from app.schemas.candidate import ProfileOut, ProfileUpdateIn
from app.services.candidates import CandidateService

router = APIRouter(prefix="/candidate", tags=["candidate"])


def _service(session: SessionDep, principal: PrincipalDep, cipher: CipherDep) -> CandidateService:
    return CandidateService(session, principal, cipher)


ServiceDep = Annotated[CandidateService, Depends(_service)]


@router.get("/profile", summary="Свой профиль")
async def get_profile(service: ServiceDep) -> ProfileOut:
    return await service.get_profile()


@router.patch("/profile", summary="Изменить свой профиль")
async def update_profile(data: ProfileUpdateIn, service: ServiceDep) -> ProfileOut:
    return await service.update_profile(data)
