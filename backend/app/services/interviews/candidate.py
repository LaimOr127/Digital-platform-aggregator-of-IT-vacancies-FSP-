"""Собеседования глазами кандидата: выбрать время или отказаться."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import InvalidStateError
from app.core.timeutil import as_aware
from app.models import Interview
from app.models.enums import InterviewStatus
from app.repositories.audit import AuditRepository
from app.repositories.base import Page
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.interviews import CandidateInterviewRepository, status_condition
from app.schemas.interviews import InterviewOut
from app.services.access import Action, Principal, policy
from app.services.interviews.common import (
    SlotError,
    effective_status,
    notify,
    offer_ids,
    parse_slots,
    to_out,
)


class CandidateInterviewService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.profiles = CandidateProfileRepository(session, principal.user_id)
        self.audit = AuditRepository(session)

    async def list_interviews(
        self, status: InterviewStatus | None, cursor: str | None, limit: int
    ) -> tuple[list[InterviewOut], str | None]:
        profile = await self.profiles.own_or_404()
        repo = CandidateInterviewRepository(self.session, profile.id)
        conditions = [status_condition(status, datetime.now(UTC))] if status else []
        page: Page[Interview] = await repo.list_page(*conditions, cursor=cursor, limit=limit)
        offers = await offer_ids(self.session, [i.id for i in page.items])
        return [to_out(i, offers.get(i.id)) for i in page.items], page.next_cursor

    async def accept(self, interview_id: uuid.UUID, slot: datetime) -> InterviewOut:
        interview = await self._own(interview_id)
        if effective_status(interview) != InterviewStatus.INVITED:
            raise InvalidStateError("на это приглашение уже нельзя ответить")
        chosen = as_aware(slot).astimezone(UTC).replace(microsecond=0)
        if chosen not in parse_slots(interview):
            raise SlotError("выберите один из предложенных вариантов времени")
        if chosen <= datetime.now(UTC):
            raise SlotError("это время уже прошло — выберите другое")
        interview.status = InterviewStatus.SCHEDULED
        interview.scheduled_at = chosen
        interview.responded_at = datetime.now(UTC)
        await self.audit.record(
            "interview.scheduled", self.principal.user_id, "interview", interview.id
        )
        notify(self.session, self.cipher, "interview_scheduled", interview, True,
               when=chosen.isoformat())  # fmt: skip
        await self.session.commit()
        return to_out(interview)

    async def decline(self, interview_id: uuid.UUID, reason: str) -> InterviewOut:
        """Отказ — и от приглашения, и от уже назначенной встречи."""
        interview = await self._own(interview_id)
        if effective_status(interview) not in (InterviewStatus.INVITED, InterviewStatus.SCHEDULED):
            raise InvalidStateError("на это приглашение уже нельзя ответить")
        interview.status = InterviewStatus.DECLINED
        interview.decline_reason = reason.strip() or None
        interview.responded_at = datetime.now(UTC)
        await self.audit.record(
            "interview.declined", self.principal.user_id, "interview", interview.id
        )
        notify(self.session, self.cipher, "interview_declined", interview, True)
        await self.session.commit()
        return to_out(interview)

    async def _own(self, interview_id: uuid.UUID) -> Interview:
        # блокировка профиля сериализует ответы кандидата (как у офферов)
        profile = await self.profiles.own_or_404(for_update=True)
        return await CandidateInterviewRepository(self.session, profile.id).lock_or_404(
            interview_id
        )
