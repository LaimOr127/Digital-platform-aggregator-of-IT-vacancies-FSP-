"""Двухфакторный вход администраторов (TOTP): настройка и проверка кода.

После верного пароля администратор получает mfa-токен (5 минут), привязанный к состоянию 2FA:
после успешного входа или сброса 2FA он недействителен. Первый вход — настройка приложения
по коду подключения из CLI (секрет -> QR), дальше каждый вход подтверждается кодом. Код нельзя
использовать повторно; после 5 неверных кодов подряд вход блокируется на 15 минут.
"""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, user_field_context
from app.core.errors import (
    ConflictError,
    MfaExpiredError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from app.core.security import TokenService
from app.core.timeutil import as_aware
from app.core.totp import generate_secret, provisioning_uri, verify
from app.models import User
from app.models.enums import UserRole
from app.repositories.audit import AuditRepository
from app.repositories.users import RefreshTokenRepository, UserRepository
from app.services.auth import AuthService, TokenPair
from app.services.enrollment import (
    enrollment_valid,
    finish_enrollment,
    mfa_stamp,
    start_enrollment,
)

ISSUER = "IT Match"
MAX_FAILURES = 5
LOCK_PERIOD = timedelta(minutes=15)


class MfaService:
    def __init__(self, session: AsyncSession, tokens: TokenService, cipher: FieldCipher) -> None:
        self.session = session
        self.tokens = tokens
        self.cipher = cipher
        self.users = UserRepository(session)
        self.audit = AuditRepository(session)
        self.auth = AuthService(session, tokens, cipher)

    async def setup(self, mfa_token: str, enrollment_code: str) -> tuple[str, str]:
        """Новый секрет для приложения-аутентификатора — только с кодом подключения."""
        user = await self._user(mfa_token)
        if user.totp_enabled:
            raise ConflictError("2FA уже настроена — введите код из приложения")
        if not enrollment_valid(user, enrollment_code):
            await self._fail(user)
            raise UnauthorizedError("неверный или просроченный код подключения")
        secret = generate_secret()
        user.totp_secret_enc = self.cipher.encrypt(secret, user_field_context("totp", user.id))
        await self.audit.record("auth.mfa_setup", user.id)
        await self.session.commit()
        return secret, provisioning_uri(secret, user.email, ISSUER)

    async def verify(self, mfa_token: str, code: str) -> TokenPair:
        user = await self._user(mfa_token)
        secret = self.cipher.decrypt(user.totp_secret_enc, user_field_context("totp", user.id))
        if secret is None:
            raise ConflictError("сначала настройте приложение-аутентификатор")
        step = verify(secret, code, time.time(), user.totp_last_step)
        if step is None:
            await self._fail(user)
            raise UnauthorizedError("неверный или уже использованный код")
        user.totp_last_step = step
        user.totp_failures = 0
        if not user.totp_enabled:
            finish_enrollment(user)
            await self.audit.record("auth.mfa_enrolled", user.id)
        return await self.auth.complete_login(user)

    async def _user(self, mfa_token: str) -> User:
        """Администратор шага 2FA под блокировкой строки: попытки сериализуются."""
        claims = self.tokens.decode_mfa(mfa_token)
        user = await self.users.lock_or_404(claims.user_id)
        if not user.is_active or user.role != UserRole.ADMIN or mfa_stamp(user) != claims.stamp:
            raise MfaExpiredError
        locked_until = user.totp_locked_until
        if locked_until is not None and as_aware(locked_until) > datetime.now(UTC):
            raise RateLimitedError("слишком много неверных кодов — попробуйте через 15 минут")
        return user

    async def _fail(self, user: User) -> None:
        user.totp_failures += 1
        await self.audit.record("auth.mfa_failed", user.id)
        if user.totp_failures >= MAX_FAILURES:
            user.totp_failures = 0
            user.totp_locked_until = datetime.now(UTC) + LOCK_PERIOD
            await self.audit.record("auth.mfa_locked", user.id)
        await self.session.commit()


async def reset_mfa(session: AsyncSession, email: str) -> str:
    """Сброс 2FA (потерян телефон): только CLI. Сессии администратора отзываются,
    возвращается новый код подключения."""
    user = await UserRepository(session).by_email(email)
    if user is None or user.role != UserRole.ADMIN:
        raise NotFoundError("администратор не найден")
    code = start_enrollment(user)
    await RefreshTokenRepository(session).revoke_all_for_user(user.id)
    await AuditRepository(session).record("auth.mfa_reset", None, "user", user.id)
    await session.commit()
    return code
