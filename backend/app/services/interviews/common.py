"""Общие правила собеседований: сроки, слоты, статус глазами пользователя, уведомления."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import AppError
from app.core.timeutil import as_aware
from app.models import Interview, Offer
from app.models.enums import InterviewStatus, RecipientType
from app.schemas.interviews import InterviewOut
from app.services.outbox import Outbox

INVITE_TTL = timedelta(days=7)  # столько кандидат может выбирать время
DECLINE_COOLDOWN = timedelta(days=30)  # после отказа — не приглашать снова сразу
MIN_LEAD = timedelta(hours=1)  # слот не раньше чем через час
MAX_AHEAD = timedelta(days=30)


class SlotError(AppError):
    status_code, code = 422, "invalid_slot"


def validate_slots(slots: list[datetime], now: datetime) -> list[datetime]:
    unique = sorted({as_aware(s).astimezone(UTC).replace(microsecond=0) for s in slots})
    for slot in unique:
        if slot < now + MIN_LEAD:
            raise SlotError("время собеседования — не раньше чем через час")
        if slot > now + MAX_AHEAD:
            raise SlotError("время собеседования — не позже чем через 30 дней")
    return unique


def parse_slots(interview: Interview) -> list[datetime]:
    return [datetime.fromisoformat(s) for s in interview.slots]


def effective_status(interview: Interview) -> InterviewStatus:
    """Приглашение без ответа после срока — «истекло», даже если worker ещё не отметил."""
    overdue = as_aware(interview.expires_at) <= datetime.now(UTC)
    if interview.status == InterviewStatus.INVITED and overdue:
        return InterviewStatus.EXPIRED
    return interview.status


def to_out(interview: Interview, offer_id: uuid.UUID | None = None) -> InterviewOut:
    data = {
        f: getattr(interview, f)
        for f in InterviewOut.model_fields
        if f not in ("status", "slots", "offer_id")
    }
    return InterviewOut(
        **data,
        status=effective_status(interview),
        slots=parse_slots(interview),
        offer_id=offer_id,
    )


async def offer_ids(
    session: AsyncSession, interview_ids: list[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """Офферы, отправленные по итогам этих собеседований."""
    if not interview_ids:
        return {}
    rows = await session.execute(
        select(Offer.interview_id, Offer.id).where(Offer.interview_id.in_(interview_ids))
    )
    return {interview_id: offer_id for interview_id, offer_id in rows.all() if interview_id}


def notify(
    session: AsyncSession,
    cipher: FieldCipher,
    kind: str,
    interview: Interview,
    to_company: bool,
    **extra: object,
) -> None:
    recipient = (
        (RecipientType.COMPANY, interview.company_id)
        if to_company
        else (RecipientType.PROFILE, interview.profile_id)
    )
    payload = {"company": interview.company_name, "vacancy": interview.vacancy_title, **extra}
    Outbox(session, cipher).enqueue(kind, *recipient, payload)
