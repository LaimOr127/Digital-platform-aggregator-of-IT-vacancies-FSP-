"""Кабинет кандидата: привязка ФСП и паспорт навыков."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CipherDep, FspClientDep, PrincipalDep, SessionDep, SettingsDep, SignerDep
from app.core.ratelimit import check_rate_limit
from app.schemas.fsp import (
    FspConfirmIn,
    FspLinkIn,
    FspLinkStartOut,
    FspStatusOut,
    PassportIssueIn,
    PassportOut,
)
from app.services.fsp import FspService
from app.services.passport import PassportService

router = APIRouter(prefix="/candidate", tags=["candidate"])


def _per_user(scope: str):  # фабрика зависимостей FastAPI: лимит по пользователю
    async def dependency(request: Request, principal: PrincipalDep) -> None:
        await check_rate_limit(request, scope, key=str(principal.user_id))

    return Depends(dependency)


def _fsp(
    session: SessionDep, principal: PrincipalDep, client: FspClientDep, settings: SettingsDep
) -> FspService:
    return FspService(session, principal, client, settings)


def _passport(
    session: SessionDep,
    principal: PrincipalDep,
    signer: SignerDep,
    cipher: CipherDep,
    settings: SettingsDep,
) -> PassportService:
    return PassportService(session, principal, signer, cipher, settings)


FspDep = Annotated[FspService, Depends(_fsp)]
PassportDep = Annotated[PassportService, Depends(_passport)]


@router.get("/fsp", summary="Привязка ФСП, достижения и категории")
async def fsp_status(service: FspDep) -> FspStatusOut:
    return await service.status()


@router.post(
    "/fsp/link", dependencies=[_per_user("fsp_link")], summary="Запросить код подтверждения ФСП"
)
async def fsp_link(data: FspLinkIn, request: Request, service: FspDep) -> FspLinkStartOut:
    athlete_id = data.athlete_id.strip().upper()
    # письма владельцу аккаунта ФСП — не чаще лимита, кто бы их ни запрашивал
    await check_rate_limit(request, "fsp_athlete", key=athlete_id)
    return await service.start(athlete_id)


@router.post(
    "/fsp/confirm", dependencies=[_per_user("fsp_confirm")], summary="Подтвердить привязку кодом"
)
async def fsp_confirm(data: FspConfirmIn, service: FspDep) -> FspStatusOut:
    return await service.confirm(data.code)


@router.post(
    "/fsp/sync", dependencies=[_per_user("fsp_sync")], summary="Обновить достижения из ФСП"
)
async def fsp_sync(service: FspDep) -> FspStatusOut:
    return await service.sync()


@router.delete("/fsp", status_code=status.HTTP_204_NO_CONTENT, summary="Отвязать аккаунт ФСП")
async def fsp_unlink(service: FspDep) -> None:
    await service.unlink()


@router.get("/passport", summary="Действующий паспорт навыков")
async def passport_active(service: PassportDep) -> PassportOut | None:
    return await service.active()


@router.post("/passport", status_code=status.HTTP_201_CREATED, summary="Выпустить паспорт")
async def passport_issue(data: PassportIssueIn, service: PassportDep) -> PassportOut:
    return await service.issue(data.show_name)


@router.delete("/passport", status_code=status.HTTP_204_NO_CONTENT, summary="Отозвать паспорт")
async def passport_revoke(service: PassportDep) -> None:
    await service.revoke()
