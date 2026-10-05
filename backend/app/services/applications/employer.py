"""Выход на контакт со стороны компании: приглашение кандидату из подборки, ответ на отклик.

Приглашение не требует опубликованной вакансии: достаточно описания предложения и вилки.
Контакты кандидата компания видит после его согласия (принял приглашение или откликнулся).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.core.errors import ConflictError, ForbiddenError, InvalidStateError, NotFoundError
from app.core.timeutil import as_aware
from app.models import Application
from app.models.enums import ApplicationDirection, ApplicationStatus, VacancyStatus
from app.repositories.applications import (
    CompanyApplicationRepository,
    expire_pair,
    status_condition,
)
from app.repositories.audit import AuditRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.companies import CompanyRepository
from app.repositories.vacancies import VacancyRepository
from app.schemas.applications import AcceptResponseIn, EmployerApplicationOut, InvitationIn
from app.schemas.catalog import OfferContactsOut
from app.services.access import Action, Principal, policy
from app.services.applications.common import (
    APPLICATION_TTL,
    DECLINE_COOLDOWN,
    base_fields,
    contacts_available,
    is_open,
    notify,
    read_contacts,
)
from app.services.catalog import cards_by_profile


class EmployerApplicationService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.COMPANY_READ_OWN)
        if principal.company_id is None:
            raise ForbiddenError("no company")
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.company_id: uuid.UUID = principal.company_id
        self.applications = CompanyApplicationRepository(session, self.company_id)
        self.catalog = CatalogRepository(session)
        self.audit = AuditRepository(session)

    async def invite(self, data: InvitationIn) -> EmployerApplicationOut:
        policy.ensure(self.principal, Action.OFFER_SEND)
        profile = await self.catalog.by_anon_id(data.anon_id)
        if profile is None:
            raise NotFoundError("кандидат не найден или скрыл профиль")
        now = datetime.now(UTC)
        if declined := await self.applications.declined_invitation_since(
            profile.id, now - DECLINE_COOLDOWN
        ):
            retry = as_aware(declined.responded_at or now) + DECLINE_COOLDOWN
            raise ConflictError(f"кандидат отказался — пригласить снова можно с {retry:%d.%m.%Y}")
        if data.vacancy_id:
            vacancy = await VacancyRepository(self.session, self.company_id).get_or_404(
                data.vacancy_id
            )
            if vacancy.status == VacancyStatus.BLOCKED:
                raise InvalidStateError("вакансия заблокирована модератором")
        await expire_pair(self.session, self.company_id, profile.id, now)
        company = await CompanyRepository(self.session).get_or_404(self.company_id)
        application = Application(
            id=uuid.uuid4(),
            direction=ApplicationDirection.INVITATION,
            company_id=self.company_id,
            profile_id=profile.id,
            vacancy_id=data.vacancy_id,
            created_by=self.principal.user_id,
            company_name=company.name,
            title=data.title.strip(),
            description=data.description.strip(),
            grade=data.grade,
            work_format=data.work_format,
            city=(data.city or "").strip() or None,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            contact_method=data.contact_method.strip(),
            expires_at=now + APPLICATION_TTL,
        )
        try:
            await self.applications.add(application)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "с этим кандидатом уже есть открытое приглашение или отклик — дождитесь ответа"
            ) from exc
        await self.audit.record(
            "application.invited", self.principal.user_id, "application", application.id
        )
        notify(self.session, self.cipher, "invitation_received", application, False,
               salary_min=application.salary_min, salary_max=application.salary_max)  # fmt: skip
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def list_applications(
        self,
        direction: ApplicationDirection | None,
        status: ApplicationStatus | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[EmployerApplicationOut], str | None]:
        now = datetime.now(UTC)
        conditions = [status_condition(status, now)] if status else []
        if direction:
            conditions.append(Application.direction == direction)
        page = await self.applications.list_page(*conditions, cursor=cursor, limit=limit)
        # компания открыла список — новые отклики в нём становятся «просмотрено»
        await self.applications.mark_viewed(
            ApplicationDirection.RESPONSE, [a.id for a in page.items], now
        )
        await self.session.commit()
        for application in page.items:
            await self.session.refresh(application)
        return await self._outs(page.items), page.next_cursor

    async def accept_response(
        self, application_id: uuid.UUID, data: AcceptResponseIn
    ) -> EmployerApplicationOut:
        application = await self._open(application_id, ApplicationDirection.RESPONSE)
        application.status = ApplicationStatus.ACCEPTED
        application.contact_method = data.contact_method.strip()
        application.responded_at = datetime.now(UTC)
        await self.audit.record(
            "application.accepted", self.principal.user_id, "application", application.id
        )
        notify(self.session, self.cipher, "response_answered", application, False,
               accepted=True, contact=application.contact_method)  # fmt: skip
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def decline_response(
        self, application_id: uuid.UUID, reason: str
    ) -> EmployerApplicationOut:
        application = await self._open(application_id, ApplicationDirection.RESPONSE)
        application.status = ApplicationStatus.DECLINED
        application.decline_reason = reason.strip() or None
        application.responded_at = datetime.now(UTC)
        await self.audit.record(
            "application.declined", self.principal.user_id, "application", application.id
        )
        notify(self.session, self.cipher, "response_answered", application, False, accepted=False)
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def withdraw(self, application_id: uuid.UUID) -> EmployerApplicationOut:
        application = await self._open(application_id, ApplicationDirection.INVITATION)
        application.status = ApplicationStatus.WITHDRAWN
        await self.audit.record(
            "application.withdrawn", self.principal.user_id, "application", application.id
        )
        await self.session.commit()
        return (await self._outs([application]))[0]

    async def contacts(self, application_id: uuid.UUID) -> OfferContactsOut:
        """Контакты — после согласия кандидата; каждое раскрытие пишется в аудит."""
        application = await self.applications.get_or_404(application_id)
        if not contacts_available(application):
            raise ForbiddenError("контакты откроются, когда кандидат примет приглашение")
        name, contacts = read_contacts(self.cipher, application)
        await self.audit.record(
            "application.contacts_revealed", self.principal.user_id, "application", application.id
        )
        await self.session.commit()
        return OfferContactsOut(
            full_name=name,
            phone=contacts.get("phone"),
            telegram=contacts.get("telegram"),
            email=contacts.get("email"),
        )

    async def _open(
        self, application_id: uuid.UUID, direction: ApplicationDirection
    ) -> Application:
        application = await self.applications.lock_or_404(application_id)
        if application.direction != direction or not is_open(application):
            raise InvalidStateError("ответить можно только на открытое обращение")
        return application

    async def _outs(self, applications: list[Application]) -> list[EmployerApplicationOut]:
        cards = await cards_by_profile(self.catalog, [a.profile_id for a in applications])
        return [
            EmployerApplicationOut(
                **base_fields(a),
                contact_method=a.contact_method,
                contacts_available=contacts_available(a),
                candidate=cards.get(a.profile_id),
            )
            for a in applications
        ]
