"""Инструменты модератора: вакансии, пользователи, журнал аудита. Каждое действие — в аудит.

Модератор блокирует кандидатов и работодателей; администраторов — только суперадмин.
Себя заблокировать нельзя. Блокировка пользователя отзывает все его сессии, блокировка
вакансии — неотвеченные офферы по ней (контакты кандидатов по ней не уйдут).
Повторное действие (заблокировать заблокированное) — ошибка 409, без дублей в аудите.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, InvalidStateError
from app.models import AuditLog, User, Vacancy, VacancyComplaint
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
from app.repositories.offers import withdraw_pending_for_vacancy
from app.repositories.users import RefreshTokenRepository
from app.schemas.admin import AdminUserOut, AdminVacancyOut, AuditEntryOut
from app.services.access import Action, Principal, policy

Paged = tuple[list, str | None]


NOTES_SHOWN = 5
COMPLAINT_LABELS = {
    "fake": "Фиктивная вакансия или компания",
    "salary": "Вилка не соответствует",
    "discrimination": "Дискриминация",
    "spam": "Спам или сбор данных",
    "other": "Другое",
}


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
        self,
        status: VacancyStatus | None,
        cursor: str | None,
        limit: int,
        with_complaints: bool = False,
    ) -> Paged:
        conditions = [Vacancy.status == status] if status else []
        if with_complaints:
            conditions.append(Vacancy.id.in_(select(VacancyComplaint.vacancy_id)))
        page = await self.vacancies.list_page(*conditions, cursor=cursor, limit=limit)
        return await self._vacancies_out(page.items), page.next_cursor

    async def moderate_vacancy(
        self, vacancy_id: uuid.UUID, action: str, reason: str
    ) -> AdminVacancyOut:
        vacancy = await self.vacancies.lock_or_404(vacancy_id)
        previous = vacancy.status
        blocking = action == "block"
        if blocking == (previous == VacancyStatus.BLOCKED):
            raise InvalidStateError(
                "вакансия уже заблокирована" if blocking else "вакансия не заблокирована"
            )
        meta = {"from": previous, "reason": reason}
        if blocking:
            vacancy.status = VacancyStatus.BLOCKED
            meta["offers"] = await withdraw_pending_for_vacancy(self.session, vacancy.id)
        else:
            vacancy.status = VacancyStatus.DRAFT  # компания проверит и опубликует заново
        await self.audit.record(
            f"admin.vacancy_{action}",
            self.principal.user_id,
            "vacancy",
            vacancy.id,
            {**meta, "to": vacancy.status},
        )
        await self.session.commit()
        return (await self._vacancies_out([vacancy]))[0]

    async def _vacancies_out(self, items: list[Vacancy]) -> list[AdminVacancyOut]:
        names = await company_names(self.session, list({v.company_id for v in items}))
        notes = await self._complaints([v.id for v in items])
        own = set(AdminVacancyOut.model_fields) - {"company_name", "complaints", "complaint_notes"}
        return [
            AdminVacancyOut(
                **{f: getattr(v, f) for f in own},
                company_name=names.get(v.company_id, "—"),
                complaints=len(notes.get(v.id, [])),
                complaint_notes=notes.get(v.id, [])[:NOTES_SHOWN],
            )
            for v in items
        ]

    async def _complaints(self, vacancy_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
        """Жалобы по вакансиям, новые первыми: «причина: текст»."""
        rows = await self.session.execute(
            select(VacancyComplaint.vacancy_id, VacancyComplaint.reason, VacancyComplaint.comment)
            .where(VacancyComplaint.vacancy_id.in_(vacancy_ids))
            .order_by(VacancyComplaint.created_at.desc())
        )
        notes: dict[uuid.UUID, list[str]] = {}
        for vacancy_id, reason, comment in rows:
            label = COMPLAINT_LABELS.get(reason, reason)
            notes.setdefault(vacancy_id, []).append(f"{label}: {comment}" if comment else label)
        return notes

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
        blocking = action == "block"
        if blocking != target.is_active:
            raise InvalidStateError(
                "пользователь уже заблокирован" if blocking else "пользователь не заблокирован"
            )
        target.is_active = not blocking
        if blocking:
            await RefreshTokenRepository(self.session).revoke_all_for_user(target.id)
        await self.audit.record(
            f"admin.user_{action}", self.principal.user_id, "user", target.id, {"reason": reason}
        )
        await self.session.commit()
        return _user_out(target)

    # --- аудит --------------------------------------------------------------------------
    async def list_audit(self, action: str | None, cursor: str | None, limit: int) -> Paged:
        # autoescape: "_" в фильтре — буква, а не шаблон LIKE
        conditions = [AuditLog.action.startswith(action, autoescape=True)] if action else []
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
