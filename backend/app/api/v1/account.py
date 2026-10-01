"""Регистрация и операции по почте: подтверждение адреса, повтор письма, сброс пароля.

Ответы не выдают, зарегистрирован ли адрес. Письма на один адрес ограничены отдельно
(почтовая бомба на чужой ящик), запросы с одного IP — общим лимитом auth.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CipherDep, SessionDep
from app.api.v1.auth import AuthLimited
from app.core.ratelimit import check_rate_limit
from app.schemas.auth import (
    AcceptedOut,
    CandidateRegisterIn,
    EmailIn,
    EmployerRegisterIn,
    LinkTokenIn,
    PasswordResetIn,
)
from app.services.account import AccountService

router = APIRouter(prefix="/auth", tags=["auth"])
ACCEPTED = status.HTTP_202_ACCEPTED
NO_CONTENT = status.HTTP_204_NO_CONTENT


def _service(session: SessionDep, cipher: CipherDep) -> AccountService:
    return AccountService(session, cipher)


AccountDep = Annotated[AccountService, Depends(_service)]


async def _email_limit(request: Request, email: str) -> None:
    await check_rate_limit(request, "email", key=email.lower())


@router.post(
    "/register/candidate",
    status_code=ACCEPTED,
    dependencies=[AuthLimited],
    summary="Регистрация кандидата (вход — после подтверждения почты)",
)
async def register_candidate(
    data: CandidateRegisterIn, request: Request, service: AccountDep
) -> AcceptedOut:
    await _email_limit(request, data.email)
    await service.register_candidate(data)
    return AcceptedOut()


@router.post(
    "/register/employer",
    status_code=ACCEPTED,
    dependencies=[AuthLimited],
    summary="Регистрация работодателя и компании (компания уходит на модерацию)",
)
async def register_employer(
    data: EmployerRegisterIn, request: Request, service: AccountDep
) -> AcceptedOut:
    await _email_limit(request, data.email)
    await service.register_employer(data)
    return AcceptedOut()


@router.post(
    "/verify-email", status_code=NO_CONTENT, dependencies=[AuthLimited], summary="Подтвердить почту"
)
async def verify_email(data: LinkTokenIn, service: AccountDep) -> None:
    await service.verify_email(data.token)


@router.post(
    "/verify-email/resend",
    status_code=ACCEPTED,
    dependencies=[AuthLimited],
    summary="Отправить письмо подтверждения ещё раз",
)
async def resend_verification(data: EmailIn, request: Request, service: AccountDep) -> AcceptedOut:
    await _email_limit(request, data.email)
    await service.resend_verification(data.email)
    return AcceptedOut()


@router.post(
    "/password/forgot",
    status_code=ACCEPTED,
    dependencies=[AuthLimited],
    summary="Письмо со ссылкой для сброса пароля",
)
async def forgot_password(data: EmailIn, request: Request, service: AccountDep) -> AcceptedOut:
    await _email_limit(request, data.email)
    await service.forgot_password(data.email)
    return AcceptedOut()


@router.post(
    "/password/reset",
    status_code=NO_CONTENT,
    dependencies=[AuthLimited],
    summary="Новый пароль по ссылке из письма (все сессии завершаются)",
)
async def reset_password(data: PasswordResetIn, service: AccountDep) -> None:
    await service.reset_password(data.token, data.password)
