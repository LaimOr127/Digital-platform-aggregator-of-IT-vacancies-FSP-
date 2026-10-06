"""Собеседования глазами компании: пригласить, отменить, отметить результат.

Собеседование назначается после состоявшегося контакта (приглашение принято или отклик
принят): компания уже знает контакты кандидата, кандидат — условия и способ связи.
Каждое действие — в аудит, кандидат получает письмо.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import ConflictError, ForbiddenError, InvalidStateError
from app.core.timeutil import as_aware
from app.models import Interview
from app.models.enums import ApplicationStatus, InterviewResult, InterviewStatus
from app.repositories.applications import CompanyApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.base import Page
from app.repositories.catalog import CatalogRepository
from app.repositories.interviews import (
    CompanyInterviewRepository,
    expire_for_application,
    status_condition,
)
from app.schemas.interviews import EmployerInterviewOut, InterviewCompleteIn, InterviewInviteIn
from app.services.access import Action, Principal, policy
from app.services.catalog import build_cards
from app.services.interviews.common import (
    DECLINE_COOLDOWN,
    INVITE_TTL,
    effective_status,
    notify,
    offer_ids,
    to_out,
    validate_slots,
)

_ACTIVE = (InterviewStatus.INVITED, InterviewStatus.SCHEDULED)


class EmployerInterviewService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.COMPANY_READ_OWN)
        if principal.company_id is None:
            raise ForbiddenError("no company")
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.company_id = principal.company_id
        self.interviews = CompanyInterviewRepository(session, self.company_id)
        self.catalog = CatalogRepository(session)
        self.audit = AuditRepository(session)

    async def invite(self, data: InterviewInviteIn) -> EmployerInterviewOut:
        """Собеседование — продолжение состоявшегося контакта (кандидат принял приглашение
        или компания приняла его отклик): условия и контакты стороны уже знают."""
        policy.ensure(self.principal, Action.OFFER_SEND)
        now = datetime.now(UTC)
        application = await CompanyApplicationRepository(self.session, self.company_id).get_or_404(
            data.application_id
        )
        if application.status != ApplicationStatus.ACCEPTED:
            raise InvalidStateError(
                "собеседование назначается после принятого приглашения или отклика"
            )
        profile_id = application.profile_id
        if declined := await self.interviews.declined_since(profile_id, now - DECLINE_COOLDOWN):
            retry = as_aware(declined.responded_at or now) + DECLINE_COOLDOWN
            raise ConflictError(f"кандидат отказался — пригласить снова можно с {retry:%d.%m.%Y}")
        slots = validate_slots(data.slots, now)
        await expire_for_application(self.session, application.id, now)
        if await self.interviews.active_for(application.id):
            raise ConflictError("по этому контакту уже есть собеседование — дождитесь ответа")
        interview = Interview(
            company_id=self.company_id,
            vacancy_id=application.vacancy_id,
            profile_id=profile_id,
            application_id=application.id,
            created_by=self.principal.user_id,
            company_name=application.company_name,
            vacancy_title=application.title,
            slots=[s.isoformat() for s in slots],
            duration_minutes=data.duration_minutes,
            format=data.format,
            location=data.location.strip(),
            interviewer=data.interviewer.strip(),
            message=data.message.strip(),
            expires_at=min(now + INVITE_TTL, slots[-1]),
        )
        try:
            await self.interviews.add(interview)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "кандидат уже приглашён на эту вакансию — дождитесь ответа"
            ) from exc
        await self.audit.record(
            "interview.invited", self.principal.user_id, "interview", interview.id
        )
        notify(self.session, self.cipher, "interview_invited", interview, False,
               interviewer=interview.interviewer, slots=interview.slots)  # fmt: skip
        await self.session.commit()
        return (await self._with_cards([interview]))[0]

    async def list_interviews(
        self, status: InterviewStatus | None, cursor: str | None, limit: int
    ) -> tuple[list[EmployerInterviewOut], str | None]:
        conditions = [status_condition(status, datetime.now(UTC))] if status else []
        page: Page[Interview] = await self.interviews.list_page(
            *conditions, cursor=cursor, limit=limit
        )
        return await self._with_cards(page.items), page.next_cursor

    async def cancel(self, interview_id: uuid.UUID, reason: str) -> EmployerInterviewOut:
        interview = await self.interviews.lock_or_404(interview_id)
        if effective_status(interview) not in _ACTIVE:
            raise InvalidStateError("отменить можно только предстоящее собеседование")
        interview.status = InterviewStatus.CANCELLED
        interview.decline_reason = reason.strip() or None
        await self.audit.record(
            "interview.cancelled", self.principal.user_id, "interview", interview.id
        )
        notify(self.session, self.cipher, "interview_cancelled", interview, False)
        await self.session.commit()
        return (await self._with_cards([interview]))[0]

    async def complete(
        self, interview_id: uuid.UUID, data: InterviewCompleteIn
    ) -> EmployerInterviewOut:
        """Результат — только после назначенного времени: оффер не обходит встречу."""
        interview = await self.interviews.lock_or_404(interview_id)
        now = datetime.now(UTC)
        if interview.status != InterviewStatus.SCHEDULED or interview.scheduled_at is None:
            raise InvalidStateError("результат отмечается для назначенного собеседования")
        if as_aware(interview.scheduled_at) > now:
            raise InvalidStateError("собеседование ещё не прошло")
        interview.status = InterviewStatus.COMPLETED
        interview.result = data.result
        interview.feedback = data.feedback.strip() or None
        interview.completed_at = now
        await self.audit.record(
            "interview.completed",
            self.principal.user_id,
            "interview",
            interview.id,
            {"result": data.result},
        )
        notify(self.session, self.cipher, "interview_result", interview, False,
               passed=data.result == InterviewResult.PASSED)  # fmt: skip
        await self.session.commit()
        return (await self._with_cards([interview]))[0]

    async def _with_cards(self, interviews: list[Interview]) -> list[EmployerInterviewOut]:
        profiles = await self.catalog.by_ids(list({i.profile_id for i in interviews}))
        cards = dict(
            zip([p.id for p in profiles], await build_cards(self.catalog, profiles), strict=True)
        )
        offers = await offer_ids(self.session, [i.id for i in interviews])
        return [
            EmployerInterviewOut(
                **to_out(i, offers.get(i.id)).model_dump(), candidate=cards.get(i.profile_id)
            )
            for i in interviews
        ]
