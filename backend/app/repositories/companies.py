import uuid
from typing import Any

from sqlalchemy import Select, select

from app.models import CompanyMember, EmployerCompany
from app.models.enums import CompanyStatus
from app.repositories.base import BaseRepository


def approved_company_ids() -> Select[Any]:
    """Компании, которые видны кандидатам: заблокированные и непроверенные исключены."""
    return select(EmployerCompany.id).where(EmployerCompany.status == CompanyStatus.APPROVED)


class CompanyRepository(BaseRepository[EmployerCompany]):
    model = EmployerCompany


class CompanyMemberRepository(BaseRepository[CompanyMember]):
    model = CompanyMember

    async def membership(self, user_id: uuid.UUID) -> CompanyMember | None:
        """Компания пользователя (в MVP — ровно одна: user_id уникален в company_members)."""
        return await self.first(CompanyMember.user_id == user_id)
