import uuid

from app.models import CompanyMember, EmployerCompany
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[EmployerCompany]):
    model = EmployerCompany


class CompanyMemberRepository(BaseRepository[CompanyMember]):
    model = CompanyMember

    async def membership(self, user_id: uuid.UUID) -> CompanyMember | None:
        """Компания пользователя (в MVP — ровно одна: user_id уникален в company_members)."""
        return await self.first(CompanyMember.user_id == user_id)
