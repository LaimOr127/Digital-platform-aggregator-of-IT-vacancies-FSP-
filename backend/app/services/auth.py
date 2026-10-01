"""Регистрация, вход, ротация refresh-токенов, выход.

Неверный email и неверный пароль дают одинаковый ответ и одинаковое время (хеш-заглушка).
Повторное использование отозванного refresh-токена отзывает всю цепочку (признак кражи).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, profile_field_context
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    TokenService,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.core.timeutil import as_aware
from app.db.session import set_rls_context
from app.models import CandidateProfile, CompanyMember, EmployerCompany, RefreshToken, User
from app.models.enums import MemberRole, UserRole
from app.repositories.audit import AuditRepository
from app.repositories.users import RefreshTokenRepository, UserRepository
from app.schemas.auth import CandidateRegisterIn, EmployerRegisterIn
from app.services.enrollment import mfa_stamp, start_enrollment

_INVALID_CREDENTIALS = "неверный email или пароль"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_max_age: int


@dataclass(frozen=True)
class MfaChallenge:
    """Пароль верный, но для администратора нужен второй фактор (TOTP)."""

    mfa_token: str
    enrolled: bool


class AuthService:
    def __init__(self, session: AsyncSession, tokens: TokenService, cipher: FieldCipher) -> None:
        self.session = session
        self.tokens = tokens
        self.cipher = cipher
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.audit = AuditRepository(session)

    async def register_candidate(self, data: CandidateRegisterIn) -> TokenPair:
        user = await self._create_user(data.email, data.password, UserRole.CANDIDATE)
        await set_rls_context(self.session, user.id, user.role)
        name_enc = self.cipher.encrypt(data.full_name, profile_field_context("full_name", user.id))
        self.session.add(CandidateProfile(user_id=user.id, full_name_enc=name_enc))
        return await self._finish_registration(user)

    async def register_employer(self, data: EmployerRegisterIn) -> TokenPair:
        user = await self._create_user(data.email, data.password, UserRole.EMPLOYER)
        await set_rls_context(self.session, user.id, user.role)
        company = EmployerCompany(name=data.company_name, inn=data.inn)
        self.session.add(company)
        await self.session.flush()
        self.session.add(
            CompanyMember(company_id=company.id, user_id=user.id, role=MemberRole.OWNER)
        )
        return await self._finish_registration(user)

    async def create_admin(self, email: str, password: str, superadmin: bool) -> tuple[User, str]:
        """Только для CLI: через API администратора создать нельзя.
        Возвращает и код подключения 2FA — без него первый вход невозможен."""
        user = await self._create_user(email, password, UserRole.ADMIN, superadmin=superadmin)
        code = start_enrollment(user)
        await self.audit.record("admin.created", None, "user", user.id, {"superadmin": superadmin})
        await self.session.commit()
        return user, code

    async def login(self, email: str, password: str) -> TokenPair | MfaChallenge:
        user = await self.users.by_email(email)
        valid = verify_password(user.password_hash if user else None, password)
        if user is None or not valid or not user.is_active:
            raise UnauthorizedError(_INVALID_CREDENTIALS)
        if user.role == UserRole.ADMIN:
            await self.audit.record("auth.mfa_challenge", user.id)
            await self.session.commit()
            token = self.tokens.issue_mfa(user.id, mfa_stamp(user))
            return MfaChallenge(token, enrolled=user.totp_enabled)
        return await self.complete_login(user)

    async def complete_login(self, user: User) -> TokenPair:
        """Выдача сессии после всех проверок (пароль; для администратора — ещё и 2FA)."""
        pair = await self._issue(user, family_id=uuid.uuid4())
        await self.audit.record("auth.login", user.id)
        await self.session.commit()
        return pair

    async def refresh(self, raw_token: str) -> TokenPair:
        stored = await self.refresh_tokens.by_hash(hash_token(raw_token))
        if stored is None:
            raise UnauthorizedError("invalid refresh token")
        user = await self.users.get(stored.user_id)
        if as_aware(stored.expires_at) <= datetime.now(UTC) or user is None or not user.is_active:
            raise UnauthorizedError("invalid refresh token")
        if user.role == UserRole.ADMIN and not user.totp_enabled:
            raise UnauthorizedError("invalid refresh token")  # сессия без 2FA не продлевается
        # Атомарно «погасить» токен: из двух одновременных запросов с одним токеном
        # выиграет один, второй считается повторным использованием и отзывает всю цепочку
        if not await self.refresh_tokens.consume(stored.id):
            await self.refresh_tokens.revoke_family(stored.family_id)
            await self.audit.record("auth.refresh_reuse", stored.user_id)
            await self.session.commit()
            raise UnauthorizedError("invalid refresh token")
        # администратор: срок сессии абсолютный — ротация не продлевает её без повторной 2FA
        keep_expiry = as_aware(stored.expires_at) if user.role == UserRole.ADMIN else None
        pair = await self._issue(user, family_id=stored.family_id, expires_at=keep_expiry)
        await self.session.commit()
        return pair

    async def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        stored = await self.refresh_tokens.by_hash(hash_token(raw_token))
        if stored is not None:
            await self.refresh_tokens.revoke_family(stored.family_id)
            await self.session.commit()

    async def _create_user(
        self, email: str, password: str, role: UserRole, superadmin: bool = False
    ) -> User:
        # хеш считается до проверки email: время ответа не выдаёт, занят ли адрес
        password_hash = hash_password(password)
        if await self.users.by_email(email) is not None:
            raise ConflictError("email уже зарегистрирован")
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            is_superadmin=superadmin,
        )
        try:
            return await self.users.add(user)
        except IntegrityError as exc:  # гонка двух одновременных регистраций
            await self.session.rollback()
            raise ConflictError("email уже зарегистрирован") from exc

    async def _finish_registration(self, user: User) -> TokenPair:
        pair = await self._issue(user, family_id=uuid.uuid4())
        await self.audit.record("auth.register", user.id, "user", user.id, {"role": user.role})
        await self.session.commit()
        return pair

    async def _issue(
        self, user: User, family_id: uuid.UUID, expires_at: datetime | None = None
    ) -> TokenPair:
        raw = new_refresh_token()
        now = datetime.now(UTC)
        expires = expires_at or now + self.tokens.refresh_ttl_for(user.role)
        ttl = expires - now
        self.session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                family_id=family_id,
                expires_at=expires,
            )
        )
        return TokenPair(
            access_token=self.tokens.issue_access(user.id, user.role),
            refresh_token=raw,
            expires_in=self.tokens.access_ttl_seconds,
            refresh_max_age=int(ttl.total_seconds()),
        )
