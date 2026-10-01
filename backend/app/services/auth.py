"""Вход, ротация refresh-токенов, выход; создание администратора (CLI).
Регистрация и операции по почте — в services/account.py.

Неверный email и неверный пароль дают одинаковый ответ и одинаковое время (хеш-заглушка).
Повторное использование отозванного refresh-токена отзывает всю цепочку (признак кражи).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import ConflictError, EmailNotVerifiedError, UnauthorizedError
from app.core.security import (
    TokenService,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.core.timeutil import as_aware
from app.models import RefreshToken, User
from app.models.enums import UserRole
from app.repositories.audit import AuditRepository
from app.repositories.users import RefreshTokenRepository, UserRepository
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

    async def create_admin(self, email: str, password: str, superadmin: bool) -> tuple[User, str]:
        """Только для CLI: через API администратора создать нельзя.
        Возвращает и код подключения 2FA — без него первый вход невозможен."""
        if await self.users.by_email(email) is not None:
            raise ConflictError("email уже зарегистрирован")
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_superadmin=superadmin,
            email_verified=True,  # адрес задаёт оператор сервера
        )
        user = await self.users.add(user)
        code = start_enrollment(user)
        await self.audit.record("admin.created", None, "user", user.id, {"superadmin": superadmin})
        await self.session.commit()
        return user, code

    async def login(self, email: str, password: str) -> TokenPair | MfaChallenge:
        user = await self.users.by_email(email)
        valid = verify_password(user.password_hash if user else None, password)
        if user is None or not valid or not user.is_active:
            raise UnauthorizedError(_INVALID_CREDENTIALS)
        if not user.email_verified:
            raise EmailNotVerifiedError("подтвердите почту — ссылка в письме после регистрации")
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
