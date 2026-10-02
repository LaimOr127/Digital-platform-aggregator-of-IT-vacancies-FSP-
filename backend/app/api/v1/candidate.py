from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep, require
from app.api.v1.auth import AuthLimited, clear_session_cookies
from app.core.ratelimit import check_rate_limit
from app.schemas.auth import AccountDeleteIn
from app.schemas.candidate import ProfileOut, ProfileUpdateIn
from app.services.access import Action
from app.services.account import AccountService
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


@router.post(
    "/account/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[AuthLimited, require(Action.PROFILE_MANAGE_OWN)],
    summary="Удалить аккаунт и все данные (152-ФЗ; подтверждение паролем)",
)
async def delete_account(
    data: AccountDeleteIn,
    request: Request,
    response: Response,
    principal: PrincipalDep,
    session: SessionDep,
    cipher: CipherDep,
) -> None:
    # лимит подбора пароля по аккаунту, как у входа: украденный access-токен не даёт перебора
    await check_rate_limit(request, "login_email", key=f"account:{principal.user_id}")
    await AccountService(session, cipher).delete_candidate(principal.user_id, data.password)
    clear_session_cookies(response)
