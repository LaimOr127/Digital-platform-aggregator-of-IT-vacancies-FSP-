"""Двухфакторный вход администраторов (TOTP): настройка и проверка кода.

После верного пароля администратор получает одноразовый mfa-токен (5 минут). При первом входе
он настраивает приложение-аутентификатор (секрет -> QR), затем каждый вход подтверждает кодом.
Код нельзя использовать повторно; сброс 2FA — только через CLI суперадмином.
"""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, user_field_context
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import TokenService
from app.core.totp import generate_secret, provisioning_uri, verify
from app.models import User
from app.models.enums import UserRole
from app.repositories.audit import AuditRepository
from app.repositories.users import RefreshTokenRepository, UserRepository
from app.services.auth import AuthService, TokenPair

ISSUER = "IT Match"
_EXPIRED = "сессия входа истекла — войдите заново"


class MfaService:
    def __init__(self, session: AsyncSession, tokens: TokenService, cipher: FieldCipher) -> None:
        self.session = session
        self.tokens = tokens
        self.cipher = cipher
        self.users = UserRepository(session)
        self.audit = AuditRepository(session)
        self.auth = AuthService(session, tokens, cipher)

    async def setup(self, mfa_token: str) -> tuple[str, str]:
        """Новый секрет для приложения-аутентификатора (только пока 2FA не включена)."""
        user = await self._user(mfa_token, lock=True)
        if user.totp_enabled:
            raise ConflictError("2FA уже настроена — введите код из приложения")
        secret = generate_secret()
        user.totp_secret_enc = self.cipher.encrypt(secret, user_field_context("totp", user.id))
        user.totp_last_step = None
        await self.session.commit()
        return secret, provisioning_uri(secret, user.email, ISSUER)

    async def verify(self, mfa_token: str, code: str) -> TokenPair:
        user = await self._user(mfa_token, lock=True)
        secret = self.cipher.decrypt(user.totp_secret_enc, user_field_context("totp", user.id))
        if secret is None:
            raise ConflictError("сначала настройте приложение-аутентификатор")
        step = verify(secret, code, time.time(), user.totp_last_step)
        if step is None:
            await self.audit.record("auth.mfa_failed", user.id)
            await self.session.commit()
            raise UnauthorizedError("неверный или уже использованный код")
        user.totp_last_step = step
        if not user.totp_enabled:
            user.totp_enabled = True
            await self.audit.record("auth.mfa_enrolled", user.id)
        return await self.auth.complete_login(user)

    async def _user(self, mfa_token: str, lock: bool = False) -> User:
        user_id = self.tokens.decode_mfa(mfa_token)
        user = await (self.users.lock_or_404 if lock else self.users.get_or_404)(user_id)
        if not user.is_active or user.role != UserRole.ADMIN:
            raise UnauthorizedError(_EXPIRED)
        return user


async def reset_mfa(session: AsyncSession, email: str) -> User:
    """Сброс 2FA (потерян телефон): только CLI. Все сессии администратора отзываются."""
    users = UserRepository(session)
    user = await users.by_email(email)
    if user is None or user.role != UserRole.ADMIN:
        raise UnauthorizedError("администратор не найден")
    user.totp_secret_enc, user.totp_enabled, user.totp_last_step = None, False, None
    await RefreshTokenRepository(session).revoke_all_for_user(user.id)
    await AuditRepository(session).record("auth.mfa_reset", None, "user", user.id)
    await session.commit()
    return user
