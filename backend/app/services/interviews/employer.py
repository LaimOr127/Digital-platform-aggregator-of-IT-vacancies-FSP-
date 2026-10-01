"""Собеседования глазами компании: пригласить, отменить, отметить результат.

Кандидат до принятия оффера анонимен: компания видит его карточку из каталога.
Каждое действие — в аудит, кандидат получает письмо.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import ConflictError, ForbiddenError, InvalidStateError, NotFoundError
from app.core.timeutil import as_aware
from app.models import Interview
from app.models.enums import InterviewResult, InterviewStatus, VacancyStatus
from app.repositories.audit import AuditRepository
from app.repositories.base import Page
from app.repositories.catalog import CatalogRepository
from app.repositories.companies import CompanyRepository
from app.repositories.interviews import CompanyInterviewRepository, expire_pair, status_condition
from app.repositories.vacancies import VacancyRepository
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
        policy.ensure(self.principal, Action.OFFER_SEND)  # только одобренная компания
        now = datetime.now(UTC)
        vacancy = await VacancyRepository(self.session, self.company_id).get_or_404(data.vacancy_id)
        expired = vacancy.expires_at and as_aware(vacancy.expires_at) <= now
        if vacancy.status != VacancyStatus.ACTIVE or expired:
            raise InvalidStateError("приглашение — только по опубликованной вакансии")
        profile = await self.catalog.by_anon_id(data.anon_id)
        if profile is None:
            raise NotFoundError("кандидат не найден или скрыл профиль")
        if declined := await self.interviews.declined_since(profile.id, now - DECLINE_COOLDOWN):
            retry = as_aware(declined.responded_at or now) + DECLINE_COOLDOWN
            raise ConflictError(f"кандидат отказался — пригласить снова можно с {retry:%d.%m.%Y}")
        slots = validate_slots(data.slots, now)
        await expire_pair(self.session, vacancy.id, profile.id, now)
        company = await CompanyRepository(self.session).get_or_404(self.company_id)
        interview = Interview(
            company_id=self.company_id,
            vacancy_id=vacancy.id,
            profile_id=profile.id,
            created_by=self.principal.user_id,
            company_name=company.name,
            vacancy_title=vacancy.title,
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
