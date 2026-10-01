"""Пароли (argon2id), access JWT и непрозрачные refresh-токены. Секреты — только из Settings."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import MfaExpiredError, UnauthorizedError

_JWT_ALG = "HS256"
_hasher = PasswordHasher()
# Хеш-заглушка: проверяется, когда пользователь не найден, чтобы время ответа не выдавало email
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Refresh-токены храним только как sha256: утечка БД не даёт рабочих токенов."""
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    role: str


@dataclass(frozen=True)
class MfaClaims:
    user_id: uuid.UUID
    stamp: int


MFA_TTL = timedelta(minutes=5)


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.secret("jwt_secret")
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        self.refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)
        # администратор: короткая сессия — украденный refresh живёт недолго
        self.admin_refresh_ttl = timedelta(hours=settings.admin_refresh_ttl_hours)
        if not self._secret:
            msg = "JWT_SECRET не задан"
            raise RuntimeError(msg)

    def refresh_ttl_for(self, role: str) -> timedelta:
        return self.admin_refresh_ttl if role == "admin" else self.refresh_ttl

    def issue_access(self, user_id: uuid.UUID, role: str) -> str:
        return self._encode({"sub": str(user_id), "role": role}, "access", self._access_ttl)

    def issue_mfa(self, user_id: uuid.UUID, stamp: int) -> str:
        """Пароль верный, нужен второй фактор: токен годен только для шага 2FA, 5 минут.
        stamp — состояние 2FA пользователя: после входа или сброса 2FA токен недействителен."""
        return self._encode({"sub": str(user_id), "stp": stamp}, "mfa", MFA_TTL)

    def decode_access(self, token: str) -> AccessClaims:
        data = self._decode(token, "access")
        try:
            return AccessClaims(user_id=uuid.UUID(data["sub"]), role=str(data["role"]))
        except (ValueError, KeyError) as exc:
            raise UnauthorizedError("invalid token") from exc

    def decode_mfa(self, token: str) -> MfaClaims:
        try:
            data = self._decode(token, "mfa")
            return MfaClaims(user_id=uuid.UUID(data["sub"]), stamp=int(data["stp"]))
        except (UnauthorizedError, ValueError, KeyError, TypeError) as exc:
            raise MfaExpiredError from exc

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._access_ttl.total_seconds())

    def _encode(self, claims: dict, typ: str, ttl: timedelta) -> str:
        now = datetime.now(UTC)
        payload = {**claims, "iat": now, "exp": now + ttl, "typ": typ}
        return jwt.encode(payload, self._secret, algorithm=_JWT_ALG)

    def _decode(self, token: str, typ: str) -> dict:
        """Подпись, срок и тип: токен одного назначения не подходит для другого."""
        try:
            data = jwt.decode(
                token, self._secret, algorithms=[_JWT_ALG], options={"require": ["exp", "sub"]}
            )
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("invalid token") from exc
        if data.get("typ") != typ:
            raise UnauthorizedError("invalid token")
        return data
