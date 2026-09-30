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


def _fsp_limit(request: Request) -> None:
    check_rate_limit(request, "fsp")


def _fsp(
    session: SessionDep, principal: PrincipalDep, client: FspClientDep, settings: SettingsDep
) -> FspService:
    return FspService(session, principal, client, settings)


def _passport(
    session: SessionDep, principal: PrincipalDep, signer: SignerDep, cipher: CipherDep
) -> PassportService:
    return PassportService(session, principal, signer, cipher)


FspDep = Annotated[FspService, Depends(_fsp)]
PassportDep = Annotated[PassportService, Depends(_passport)]
Limited = [Depends(_fsp_limit)]


@router.get("/fsp", summary="Привязка ФСП, достижения и категории")
async def fsp_status(service: FspDep) -> FspStatusOut:
    return await service.status()


@router.post("/fsp/link", dependencies=Limited, summary="Запросить код подтверждения ФСП")
async def fsp_link(data: FspLinkIn, service: FspDep) -> FspLinkStartOut:
    return await service.start(data.athlete_id)


@router.post("/fsp/confirm", dependencies=Limited, summary="Подтвердить привязку кодом")
async def fsp_confirm(data: FspConfirmIn, service: FspDep) -> FspStatusOut:
    return await service.confirm(data.code)


@router.post("/fsp/sync", dependencies=Limited, summary="Обновить достижения из ФСП")
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
