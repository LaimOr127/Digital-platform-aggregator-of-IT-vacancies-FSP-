"""Аутентификация. Access JWT — в теле ответа (фронт держит его в памяти);
refresh — в httpOnly+SameSite=Strict cookie, обновление/выход требуют CSRF-заголовок
(double submit: значение заголовка X-CSRF-Token должно совпасть с cookie csrf_token)."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep, TokensDep
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.ratelimit import check_rate_limit
from app.repositories.users import UserRepository
from app.schemas.auth import CandidateRegisterIn, EmployerRegisterIn, LoginIn, MeOut, TokenOut
from app.services.auth import AuthService, TokenPair

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
_REFRESH_PATH = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_limit(request: Request) -> None:
    check_rate_limit(request, "auth")


def _refresh_limit(request: Request) -> None:
    check_rate_limit(request, "refresh")


AuthLimited = Depends(_auth_limit)
RefreshLimited = Depends(_refresh_limit)


def _service(session: SessionDep, tokens: TokensDep, cipher: CipherDep) -> AuthService:
    return AuthService(session, tokens, cipher)


AuthServiceDep = Annotated[AuthService, Depends(_service)]


def _respond(request: Request, response: Response, pair: TokenPair) -> TokenOut:
    secure = request.app.state.settings.is_prod
    max_age = int(request.app.state.tokens.refresh_ttl.total_seconds())
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


@router.post(
    "/register/candidate",
    status_code=status.HTTP_201_CREATED,
    dependencies=[AuthLimited],
    summary="Регистрация кандидата",
)
async def register_candidate(
    data: CandidateRegisterIn, request: Request, response: Response, service: AuthServiceDep
) -> TokenOut:
    return _respond(request, response, await service.register_candidate(data))


@router.post(
    "/register/employer",
    status_code=status.HTTP_201_CREATED,
    dependencies=[AuthLimited],
    summary="Регистрация работодателя и компании (компания уходит на модерацию)",
)
async def register_employer(
    data: EmployerRegisterIn, request: Request, response: Response, service: AuthServiceDep
) -> TokenOut:
    return _respond(request, response, await service.register_employer(data))


@router.post("/login", dependencies=[AuthLimited], summary="Вход")
async def login(
    data: LoginIn, request: Request, response: Response, service: AuthServiceDep
) -> TokenOut:
    # второй лимит — по аккаунту: перебор пароля с пула IP упирается в него
    check_rate_limit(request, "login_email", key=data.email.lower())
    return _respond(request, response, await service.login(data.email, data.password))


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
    user = await UserRepository(session).get(principal.user_id)
    if user is None:
        raise UnauthorizedError("authentication required")
    return MeOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_superadmin=user.is_superadmin,
        company_id=principal.company_id,
    )
