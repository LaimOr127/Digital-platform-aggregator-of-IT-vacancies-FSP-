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
from app.core.errors import UnauthorizedError

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


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.secret("jwt_secret")
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        self.refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)
        if not self._secret:
            msg = "JWT_SECRET не задан"
            raise RuntimeError(msg)

    def issue_access(self, user_id: uuid.UUID, role: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "role": role,
            "iat": now,
            "exp": now + self._access_ttl,
            "typ": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=_JWT_ALG)

    def decode_access(self, token: str) -> AccessClaims:
        try:
            data = jwt.decode(
                token, self._secret, algorithms=[_JWT_ALG], options={"require": ["exp", "sub"]}
            )
            if data.get("typ") != "access":
                raise UnauthorizedError("invalid token")
            return AccessClaims(user_id=uuid.UUID(data["sub"]), role=str(data["role"]))
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise UnauthorizedError("invalid token") from exc

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._access_ttl.total_seconds())
