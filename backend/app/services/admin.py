"""Модерация: компании. Каждое действие пишется в аудит, компания получает письмо."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher
from app.models import EmployerCompany
from app.models.enums import CompanyStatus, RecipientType
from app.repositories.applications import withdraw_open_invitations
from app.repositories.audit import AuditRepository
from app.repositories.base import Page
from app.repositories.companies import CompanyRepository
from app.repositories.offers import withdraw_pending_for_company
from app.repositories.vacancies import VacancyRepository
from app.services.access import Action, Principal, policy
from app.services.outbox import Outbox


class AdminService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.ADMIN_MODERATE)
        self.session = session
        self.outbox = Outbox(session, cipher)
        self.principal = principal
        self.companies = CompanyRepository(session)
        self.audit = AuditRepository(session)

    async def list_companies(
        self, status: CompanyStatus | None, cursor: str | None, limit: int
    ) -> Page[EmployerCompany]:
        conditions = [EmployerCompany.status == status] if status else []
        return await self.companies.list_page(*conditions, cursor=cursor, limit=limit)

    async def set_company_status(
        self, company_id: uuid.UUID, status: CompanyStatus, reason: str
    ) -> EmployerCompany:
        company = await self.companies.get_or_404(company_id)
        previous = company.status
        company.status = status
        blocked_vacancies = withdrawn_offers = withdrawn_invitations = 0
        if status == CompanyStatus.BLOCKED:
            blocked_vacancies = await VacancyRepository(self.session, company.id).block_open()
            withdrawn_offers = await withdraw_pending_for_company(self.session, company.id)
            withdrawn_invitations = await withdraw_open_invitations(self.session, company.id)
        await self.audit.record(
            "admin.company_status",
            self.principal.user_id,
            "company",
            company.id,
            {
                "from": previous,
                "to": status,
                "reason": reason,
                "vacancies": blocked_vacancies,
                "offers": withdrawn_offers,
                "invitations": withdrawn_invitations,
            },
        )
        if status != previous and status != CompanyStatus.PENDING:
            self.outbox.enqueue(
                "company_status",
                RecipientType.COMPANY,
                company.id,
                {"company": company.name, "status": status},
            )
        await self.session.commit()
        return company
