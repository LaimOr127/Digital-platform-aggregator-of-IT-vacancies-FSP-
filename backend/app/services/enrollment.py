"""Код подключения 2FA: выдаёт только CLI (создание администратора, сброс 2FA).

Без кода пароль не позволяет привязать свой аутентификатор: настроить 2FA может лишь тот,
кому код передали по доверенному каналу. Код одноразовый, действует сутки, хранится хешем.
"""

import hmac
import secrets
from datetime import UTC, datetime, timedelta

from app.core.security import hash_token
from app.core.timeutil import as_aware
from app.models import User

ENROLL_TTL = timedelta(hours=24)


def start_enrollment(user: User) -> str:
    """Сбрасывает 2FA пользователя и возвращает новый код подключения (показать один раз)."""
    code = secrets.token_urlsafe(12)
    user.totp_secret_enc = None
    user.totp_enabled = False
    user.totp_last_step = None
    user.totp_failures = 0
    user.totp_locked_until = None
    user.totp_enroll_hash = hash_token(code)
    user.totp_enroll_expires_at = datetime.now(UTC) + ENROLL_TTL
    return code


def mfa_stamp(user: User) -> int:
    """Состояние 2FA для mfa-токена: меняется при каждом входе и при сбросе."""
    return user.totp_last_step or 0


def enrollment_valid(user: User, code: str) -> bool:
    if user.totp_enroll_hash is None or user.totp_enroll_expires_at is None:
        return False
    if as_aware(user.totp_enroll_expires_at) <= datetime.now(UTC):
        return False
    return hmac.compare_digest(user.totp_enroll_hash, hash_token(code))


def finish_enrollment(user: User) -> None:
    user.totp_enabled = True
    user.totp_enroll_hash = None
    user.totp_enroll_expires_at = None
