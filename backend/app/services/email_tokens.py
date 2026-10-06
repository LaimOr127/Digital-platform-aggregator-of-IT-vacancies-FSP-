"""Одноразовые токены из писем: подтверждение почты (сутки) и сброс пароля (час).

В БД — только sha256 токена. Новый токен гасит прежние того же назначения: действует
лишь последняя ссылка. Погашение атомарно: из двух одновременных запросов пройдёт один.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models import EmailToken
from app.models.enums import EmailTokenPurpose

TTL = {EmailTokenPurpose.VERIFY: timedelta(hours=24), EmailTokenPurpose.RESET: timedelta(hours=1)}


async def issue(session: AsyncSession, user_id: uuid.UUID, purpose: EmailTokenPurpose) -> str:
    now = datetime.now(UTC)
    await session.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw = secrets.token_urlsafe(32)
    session.add(
        EmailToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=now + TTL[purpose],
        )
    )
    return raw


async def consume(session: AsyncSession, raw: str, purpose: EmailTokenPurpose) -> uuid.UUID | None:
    """Погасить токен; None — если он неизвестен, истёк или уже использован."""
    now = datetime.now(UTC)
    result = await session.execute(
        update(EmailToken)
        .where(
            EmailToken.token_hash == hash_token(raw),
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(EmailToken.user_id)
    )
    return result.scalar_one_or_none()
