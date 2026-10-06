"""Очередь писем: постановка в транзакции действия и доставка воркером.

Адресат хранится ссылкой (пользователь, профиль кандидата, компания) и разрешается в email
при отправке: заблокированным и удалённым письма не уходят. Параметры письма зашифрованы
и стираются после отправки или окончательной ошибки.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, outbox_payload_context
from app.core.logging import get_logger
from app.integrations.notifier import Email, Notifier
from app.models import CandidateProfile, CompanyMember, OutboxMessage, User
from app.models.enums import OutboxStatus, RecipientType
from app.services.emails import render

log = get_logger(__name__)
MAX_ATTEMPTS = 8
BATCH = 20


class Outbox:
    def __init__(self, session: AsyncSession, cipher: FieldCipher) -> None:
        self.session = session
        self.cipher = cipher

    def enqueue(
        self,
        kind: str,
        recipient_type: RecipientType,
        recipient_id: uuid.UUID,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Письмо уйдёт, только если транзакция действия зафиксируется."""
        message_id = uuid.uuid4()
        encrypted = self.cipher.encrypt(
            json.dumps(payload or {}, ensure_ascii=False), outbox_payload_context(message_id)
        )
        self.session.add(
            OutboxMessage(
                id=message_id,
                kind=kind,
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                payload_enc=encrypted,
            )
        )


class OutboxDelivery:
    """Доставка очереди (воркер, системная роль RLS). Ошибка письма откладывает только его."""

    def __init__(
        self, session: AsyncSession, cipher: FieldCipher, notifier: Notifier, public_url: str
    ) -> None:
        self.session = session
        self.cipher = cipher
        self.notifier = notifier
        self.public_url = public_url

    async def deliver_due(self) -> int:
        now = datetime.now(UTC)
        due = await self.session.execute(
            select(OutboxMessage)
            .where(
                OutboxMessage.status == OutboxStatus.PENDING, OutboxMessage.next_attempt_at <= now
            )
            .order_by(OutboxMessage.created_at)
            .limit(BATCH)
            .with_for_update(skip_locked=True)
        )
        messages = list(due.scalars())
        for message in messages:
            await self._deliver(message)
        await self.session.commit()
        return len(messages)

    async def _deliver(self, message: OutboxMessage) -> None:
        recipients = await self._recipients(message)
        if not recipients:
            self._finish(message, OutboxStatus.DROPPED)
            return
        try:
            raw = self.cipher.decrypt(message.payload_enc, outbox_payload_context(message.id))
            subject, body = render(message.kind, json.loads(raw or "{}"), self.public_url)
        except Exception:
            log.exception("outbox %s: cannot render %s", message.id, message.kind)
            self._finish(message, OutboxStatus.FAILED)
            return
        try:
            for address in recipients:
                await self.notifier.send(Email(address, subject, body))
        except Exception as exc:
            self._retry(message, exc)
            return
        self._finish(message, OutboxStatus.SENT)

    def _retry(self, message: OutboxMessage, exc: Exception) -> None:
        message.attempts += 1
        log.warning(
            "outbox %s attempt %d failed: %s", message.id, message.attempts, type(exc).__name__
        )
        if message.attempts >= MAX_ATTEMPTS:
            self._finish(message, OutboxStatus.FAILED)
        else:
            # 1, 2, 4 ... минут: временный сбой почты не теряет письма и не долбит сервер
            delay = timedelta(minutes=2 ** (message.attempts - 1))
            message.next_attempt_at = datetime.now(UTC) + delay

    @staticmethod
    def _finish(message: OutboxMessage, status: OutboxStatus) -> None:
        message.status = status
        message.payload_enc = None
        if status == OutboxStatus.SENT:
            message.sent_at = datetime.now(UTC)

    async def _recipients(self, message: OutboxMessage) -> list[str]:
        """Активные адресаты; кандидату и компании — только с подтверждённой почтой."""
        query = select(User.email).where(User.is_active.is_(True))
        if message.recipient_type == RecipientType.USER:
            query = query.where(User.id == message.recipient_id)
        elif message.recipient_type == RecipientType.PROFILE:
            query = query.join(CandidateProfile, CandidateProfile.user_id == User.id).where(
                CandidateProfile.id == message.recipient_id, User.email_verified.is_(True)
            )
        else:
            query = query.join(CompanyMember, CompanyMember.user_id == User.id).where(
                CompanyMember.company_id == message.recipient_id, User.email_verified.is_(True)
            )
        return list((await self.session.execute(query)).scalars())
