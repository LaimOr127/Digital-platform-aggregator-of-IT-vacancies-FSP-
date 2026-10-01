"""Аутентификация. Access JWT — в теле ответа (фронт держит его в памяти);
refresh — в httpOnly+SameSite=Strict cookie, обновление/выход требуют CSRF-заголовок
(double submit: значение заголовка X-CSRF-Token должно совпасть с cookie csrf_token)."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep, TokensDep
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.ratelimit import check_rate_limit
from app.schemas.auth import (
    LoginIn,
    MeOut,
    MfaChallengeOut,
    MfaSetupIn,
    MfaSetupOut,
    MfaVerifyIn,
    TokenOut,
)
from app.services.auth import AuthService, MfaChallenge, TokenPair
from app.services.directory import current_user
from app.services.mfa import MfaService

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
_REFRESH_PATH = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])


async def _auth_limit(request: Request) -> None:
    await check_rate_limit(request, "auth")


async def _refresh_limit(request: Request) -> None:
    await check_rate_limit(request, "refresh")


AuthLimited = Depends(_auth_limit)  # используется и роутером account
RefreshLimited = Depends(_refresh_limit)


def _service(session: SessionDep, tokens: TokensDep, cipher: CipherDep) -> AuthService:
    return AuthService(session, tokens, cipher)


AuthServiceDep = Annotated[AuthService, Depends(_service)]


def _respond(request: Request, response: Response, pair: TokenPair) -> TokenOut:
    secure = request.app.state.settings.is_prod
    max_age = pair.refresh_max_age
    response.set_cookie(
        REFRESH_COOKIE,
        pair.refresh_token,
        max_age=max_age,
        path=_REFRESH_PATH,
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=max_age,
        path="/",
        httponly=False,
        secure=secure,
        samesite="strict",
    )
    return TokenOut(access_token=pair.access_token, expires_in=pair.expires_in)


def _check_csrf(csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise ForbiddenError("csrf check failed")


CsrfCookie = Annotated[str | None, Cookie(alias=CSRF_COOKIE)]
CsrfHeader = Annotated[str | None, Header(alias="X-CSRF-Token")]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post("/login", dependencies=[AuthLimited], summary="Вход (администратору — затем 2FA)")
async def login(
    data: LoginIn, request: Request, response: Response, service: AuthServiceDep
) -> TokenOut | MfaChallengeOut:
    # второй лимит — по аккаунту: перебор пароля с пула IP упирается в него
    await check_rate_limit(request, "login_email", key=data.email.lower())
    result = await service.login(data.email, data.password)
    if isinstance(result, MfaChallenge):
        return MfaChallengeOut(mfa_token=result.mfa_token, enrolled=result.enrolled)
    return _respond(request, response, result)


def _mfa(session: SessionDep, tokens: TokensDep, cipher: CipherDep) -> MfaService:
    return MfaService(session, tokens, cipher)


MfaServiceDep = Annotated[MfaService, Depends(_mfa)]


async def _mfa_limit(request: Request, mfa_token: str) -> None:
    """Попытки кода 2FA ограничены на администратора (по токену шага), не только по IP."""
    claims = request.app.state.tokens.decode_mfa(mfa_token)
    await check_rate_limit(request, "mfa", key=str(claims.user_id))


@router.post(
    "/2fa/setup", dependencies=[AuthLimited], summary="Настроить приложение-аутентификатор"
)
async def mfa_setup(data: MfaSetupIn, request: Request, service: MfaServiceDep) -> MfaSetupOut:
    await _mfa_limit(request, data.mfa_token)
    secret, uri = await service.setup(data.mfa_token, data.enrollment_code)
    return MfaSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/2fa/verify", dependencies=[AuthLimited], summary="Подтвердить вход кодом 2FA")
async def mfa_verify(
    data: MfaVerifyIn, request: Request, response: Response, service: MfaServiceDep
) -> TokenOut:
    await _mfa_limit(request, data.mfa_token)
    return _respond(request, response, await service.verify(data.mfa_token, data.code))


@router.post(
    "/refresh", dependencies=[RefreshLimited], summary="Новый access-токен (ротация refresh)"
)
async def refresh(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    refresh_token: RefreshCookie = None,
    csrf_cookie: CsrfCookie = None,
    csrf_header: CsrfHeader = None,
) -> TokenOut:
    _check_csrf(csrf_cookie, csrf_header)
    if not refresh_token:
        raise UnauthorizedError("refresh token missing")
    return _respond(request, response, await service.refresh(refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Выход")
async def logout(
    response: Response,
    service: AuthServiceDep,
    refresh_token: RefreshCookie = None,
    csrf_cookie: CsrfCookie = None,
    csrf_header: CsrfHeader = None,
) -> None:
    _check_csrf(csrf_cookie, csrf_header)
    await service.logout(refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path=_REFRESH_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.get("/me", summary="Текущий пользователь")
async def me(principal: PrincipalDep, session: SessionDep) -> MeOut:
    return await current_user(session, principal)
