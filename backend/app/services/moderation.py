"""Инструменты модератора: вакансии, пользователи, журнал аудита. Каждое действие — в аудит.

Модератор блокирует кандидатов и работодателей; администраторов — только суперадмин.
Себя заблокировать нельзя. Блокировка пользователя отзывает все его сессии.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, InvalidStateError
from app.models import AuditLog, User, Vacancy
from app.models.enums import UserRole, VacancyStatus
from app.repositories.admin import (
    AllUsersRepository,
    AllVacanciesRepository,
    AuditLogRepository,
    company_names,
    like_pattern,
)
from app.repositories.audit import AuditRepository
from app.repositories.base import Page
from app.repositories.users import RefreshTokenRepository
from app.schemas.admin import AdminUserOut, AdminVacancyOut, AuditEntryOut
from app.services.access import Action, Principal, policy

Paged = tuple[list, str | None]


class ModerationService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.ADMIN_MODERATE)
        self.session = session
        self.principal = principal
        self.vacancies = AllVacanciesRepository(session)
        self.users = AllUsersRepository(session)
        self.audit = AuditRepository(session)

    # --- вакансии -----------------------------------------------------------------------
    async def list_vacancies(
        self, status: VacancyStatus | None, cursor: str | None, limit: int
    ) -> Paged:
        conditions = [Vacancy.status == status] if status else []
        page = await self.vacancies.list_page(*conditions, cursor=cursor, limit=limit)
        return await self._vacancies_out(page.items), page.next_cursor

    async def moderate_vacancy(
        self, vacancy_id: uuid.UUID, action: str, reason: str
    ) -> AdminVacancyOut:
        vacancy = await self.vacancies.lock_or_404(vacancy_id)
        previous = vacancy.status
        if action == "block":
            vacancy.status = VacancyStatus.BLOCKED
        elif vacancy.status != VacancyStatus.BLOCKED:
            raise InvalidStateError("вакансия не заблокирована")
        else:
            vacancy.status = VacancyStatus.DRAFT  # компания проверит и опубликует заново
        await self.audit.record(
            f"admin.vacancy_{action}",
            self.principal.user_id,
            "vacancy",
            vacancy.id,
            {"from": previous, "to": vacancy.status, "reason": reason},
        )
        await self.session.commit()
        return (await self._vacancies_out([vacancy]))[0]

    async def _vacancies_out(self, items: list[Vacancy]) -> list[AdminVacancyOut]:
        names = await company_names(self.session, list({v.company_id for v in items}))
        return [
            AdminVacancyOut(
                **{f: getattr(v, f) for f in AdminVacancyOut.model_fields if f != "company_name"},
                company_name=names.get(v.company_id, "—"),
            )
            for v in items
        ]

    # --- пользователи -------------------------------------------------------------------
    async def list_users(
        self, role: UserRole | None, query: str | None, cursor: str | None, limit: int
    ) -> Paged:
        conditions = []
        if role:
            conditions.append(User.role == role)
        if query:
            conditions.append(User.email.ilike(like_pattern(query.strip().lower()), escape="\\"))
        page: Page[User] = await self.users.list_page(*conditions, cursor=cursor, limit=limit)
        return [_user_out(u) for u in page.items], page.next_cursor

    async def moderate_user(self, user_id: uuid.UUID, action: str, reason: str) -> AdminUserOut:
        if user_id == self.principal.user_id:
            raise ForbiddenError("нельзя заблокировать самого себя")
        target = await self.users.lock_or_404(user_id)
        if target.role == UserRole.ADMIN:
            policy.ensure(self.principal, Action.ADMIN_SUPER)
        target.is_active = action == "unblock"
        if action == "block":
            await RefreshTokenRepository(self.session).revoke_all_for_user(target.id)
        await self.audit.record(
            f"admin.user_{action}", self.principal.user_id, "user", target.id, {"reason": reason}
        )
        await self.session.commit()
        return _user_out(target)

    # --- аудит --------------------------------------------------------------------------
    async def list_audit(self, action: str | None, cursor: str | None, limit: int) -> Paged:
        conditions = [AuditLog.action.startswith(action)] if action else []
        page = await AuditLogRepository(self.session).list_page(
            *conditions, cursor=cursor, limit=limit
        )
        emails = await self.users.emails([e.actor_id for e in page.items if e.actor_id])
        return [
            AuditEntryOut(
                id=e.id,
                action=e.action,
                actor_email=emails.get(e.actor_id) if e.actor_id else None,
                target_type=e.target_type,
                target_id=e.target_id,
                meta=e.meta or {},
                created_at=e.created_at,
            )
            for e in page.items
        ], page.next_cursor


def _user_out(u: User) -> AdminUserOut:
    return AdminUserOut(
        id=u.id,
        email=u.email,
        role=u.role,
        is_active=u.is_active,
        is_superadmin=u.is_superadmin,
        totp_enabled=u.totp_enabled,
        created_at=u.created_at,
    )
