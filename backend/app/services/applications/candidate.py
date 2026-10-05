"""Выход на контакт со стороны кандидата: ответ на приглашение и самостоятельный отклик.

Принимая приглашение или откликаясь, кандидат соглашается передать компании имя и контакты.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import ConflictError, InvalidStateError, NotFoundError
from app.core.timeutil import as_aware
from app.models import Application, EmployerCompany, Vacancy
from app.models.enums import (
    ApplicationDirection,
    ApplicationStatus,
    CompanyStatus,
    VacancyStatus,
)
from app.repositories.applications import (
    CandidateApplicationRepository,
    expire_pair,
    status_condition,
)
from app.repositories.audit import AuditRepository
from app.repositories.candidates import CandidateProfileRepository
from app.schemas.applications import ApplicationOut, ResponseIn
from app.services.access import Action, Principal, policy
from app.services.applications.common import (
    APPLICATION_TTL,
    candidate_out,
    companies,
    is_open,
    notify,
    snapshot_contacts,
)


class CandidateApplicationService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.profiles = CandidateProfileRepository(session, owner_id=principal.user_id)
        self.audit = AuditRepository(session)

    async def list_applications(
        self,
        direction: ApplicationDirection | None,
        status: ApplicationStatus | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[ApplicationOut], str | None]:
        profile = await self.profiles.own_or_404()
        repo = CandidateApplicationRepository(self.session, profile.id)
        now = datetime.now(UTC)
        conditions = [status_condition(status, now)] if status else []
        if direction:
            conditions.append(Application.direction == direction)
        page = await repo.list_page(*conditions, cursor=cursor, limit=limit)
        # кандидат открыл список — новые приглашения в нём становятся «просмотрено»
        await repo.mark_viewed(ApplicationDirection.INVITATION, [a.id for a in page.items], now)
        await self.session.commit()
        for application in page.items:
            await self.session.refresh(application)
        return await self._outs(page.items), page.next_cursor

    async def accept(self, application_id: uuid.UUID) -> ApplicationOut:
        profile = await self.profiles.own_or_404(for_update=True)
        application = await self._open(profile.id, application_id, ApplicationDirection.INVITATION)
        snapshot_contacts(self.cipher, profile, application)
        application.status = ApplicationStatus.ACCEPTED
        application.responded_at = datetime.now(UTC)
        profile.last_activity_at = application.responded_at
        await self.audit.record(
            "application.accepted", self.principal.user_id, "application", application.id
        )
        notify(self.session, self.cipher, "invitation_answered", application, True, accepted=True)
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def decline(self, application_id: uuid.UUID, reason: str) -> ApplicationOut:
        profile = await self.profiles.own_or_404()
        application = await self._open(profile.id, application_id, ApplicationDirection.INVITATION)
        application.status = ApplicationStatus.DECLINED
        application.decline_reason = reason.strip() or None
        application.responded_at = datetime.now(UTC)
        await self.audit.record(
            "application.declined", self.principal.user_id, "application", application.id
        )
        notify(self.session, self.cipher, "invitation_answered", application, True, accepted=False)
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def respond(self, vacancy_id: uuid.UUID, data: ResponseIn) -> ApplicationOut:
        """Самостоятельный отклик на опубликованную вакансию: контакты уходят компании сразу."""
        profile = await self.profiles.own_or_404(for_update=True)
        vacancy, company = await self._published(vacancy_id)
        now = datetime.now(UTC)
        await expire_pair(self.session, company.id, profile.id, now)
        application = Application(
            id=uuid.uuid4(),
            direction=ApplicationDirection.RESPONSE,
            company_id=company.id,
            profile_id=profile.id,
            vacancy_id=vacancy.id,
            created_by=self.principal.user_id,
            company_name=company.name,
            title=vacancy.title,
            description=vacancy.description,
            grade=vacancy.grade,
            work_format=vacancy.work_format,
            city=vacancy.city,
            salary_min=vacancy.salary_min,
            salary_max=vacancy.salary_max,
            message=data.message.strip(),
            expires_at=now + APPLICATION_TTL,
        )
        snapshot_contacts(self.cipher, profile, application)
        repo = CandidateApplicationRepository(self.session, profile.id)
        try:
            await repo.add(application)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "с этой компанией уже есть открытый отклик или приглашение — дождитесь ответа"
            ) from exc
        profile.last_activity_at = now
        await self.audit.record(
            "application.responded", self.principal.user_id, "application", application.id
        )
        notify(self.session, self.cipher, "response_received", application, True)
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def withdraw(self, application_id: uuid.UUID) -> ApplicationOut:
        profile = await self.profiles.own_or_404()
        application = await self._open(profile.id, application_id, ApplicationDirection.RESPONSE)
        application.status = ApplicationStatus.WITHDRAWN
        await self.audit.record(
            "application.withdrawn", self.principal.user_id, "application", application.id
        )
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def _open(
        self, profile_id: uuid.UUID, application_id: uuid.UUID, direction: ApplicationDirection
    ) -> Application:
        repo = CandidateApplicationRepository(self.session, profile_id)
        application = await repo.lock_or_404(application_id)
        if application.direction != direction or not is_open(application):
            raise InvalidStateError("ответить можно только на открытое обращение")
        return application

    async def _published(self, vacancy_id: uuid.UUID) -> tuple[Vacancy, EmployerCompany]:
        """Опубликованная, не истёкшая вакансия одобренной компании (в PostgreSQL то же — RLS)."""
        row = (
            await self.session.execute(
                select(Vacancy, EmployerCompany)
                .join(EmployerCompany, EmployerCompany.id == Vacancy.company_id)
                .where(Vacancy.id == vacancy_id)
            )
        ).first()
        if row is None:
            raise NotFoundError("вакансия не найдена")
        vacancy, company = row
        expired = vacancy.expires_at and as_aware(vacancy.expires_at) <= datetime.now(UTC)
        if (
            vacancy.status != VacancyStatus.ACTIVE
            or expired
            or company.status != CompanyStatus.APPROVED
        ):
            raise NotFoundError("вакансия не найдена или снята с публикации")
        return vacancy, company

    async def _outs(self, applications: list[Application]) -> list[ApplicationOut]:
        found = await companies(self.session, {a.company_id for a in applications})
        return [candidate_out(a, found.get(a.company_id)) for a in applications]
