"""Зависимости FastAPI (DI): настройки, сессия, текущий пользователь (Principal).

Тесты подменяют их через app.dependency_overrides.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import FieldCipher
from app.core.errors import UnauthorizedError
from app.core.security import TokenService
from app.core.signing import PassportSigner
from app.db.session import get_session, set_rls_context
from app.integrations.fsp import FspClient
from app.models.enums import UserRole
from app.repositories.companies import CompanyMemberRepository, CompanyRepository
from app.repositories.users import UserRepository
from app.services.access import Principal

_bearer = HTTPBearer(auto_error=False)


def get_token_service(request: Request) -> TokenService:
    return request.app.state.tokens


def get_cipher(request: Request) -> FieldCipher:
    return request.app.state.cipher


def get_signer(request: Request) -> PassportSigner:
    return request.app.state.signer


def get_fsp_client(request: Request) -> FspClient:
    return request.app.state.fsp_client


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


SessionDep = Annotated[AsyncSession, Depends(get_session)]
TokensDep = Annotated[TokenService, Depends(get_token_service)]
CipherDep = Annotated[FieldCipher, Depends(get_cipher)]
SignerDep = Annotated[PassportSigner, Depends(get_signer)]
FspClientDep = Annotated[FspClient, Depends(get_fsp_client)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_principal(
    session: SessionDep,
    tokens: TokensDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """Проверяет access-токен, загружает пользователя и задаёт контекст RLS для сессии запроса."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("authentication required")
    claims = tokens.decode_access(credentials.credentials)
    user = await UserRepository(session).get(claims.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("authentication required")
    await set_rls_context(session, user.id, user.role)

    principal = Principal(user_id=user.id, role=user.role, is_superadmin=user.is_superadmin)
    if user.role != UserRole.EMPLOYER:
        return principal
    member = await CompanyMemberRepository(session).membership(user.id)
    company = await CompanyRepository(session).get(member.company_id) if member else None
    if member is None or company is None:
        return principal
    return Principal(
        user_id=user.id,
        role=user.role,
        company_id=company.id,
        member_role=member.role,
        company_status=company.status,
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]
