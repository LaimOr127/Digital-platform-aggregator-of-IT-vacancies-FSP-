"""Задания компаний и ответы кандидатов: тенант — компания или профиль кандидата."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select

from app.models import EmployerTask, TaskAnswer
from app.models.enums import Grade, Specialization
from app.repositories.base import BaseRepository, OwnedRepository
from app.repositories.companies import approved_company_ids


class CompanyTaskRepository(OwnedRepository[EmployerTask]):
    model = EmployerTask
    column = EmployerTask.company_id

    async def answer_counts(self, task_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        stmt = (
            select(TaskAnswer.task_id, func.count())
            .where(
                TaskAnswer.task_id.in_(task_ids),
                TaskAnswer.company_id == self.owner_id,
                TaskAnswer.blocked.is_(False),
            )
            .group_by(TaskAnswer.task_id)
        )
        return {task_id: count for task_id, count in await self.session.execute(stmt)}


class OpenTaskRepository(BaseRepository[EmployerTask]):
    """Активные задачи одобренных компаний — для кандидатов (активность дублирует RLS)."""

    model = EmployerTask

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(
            EmployerTask.is_active.is_(True),
            EmployerTask.company_id.in_(approved_company_ids()),
        )

    async def offered_for(
        self, specialization: Specialization, grade: Grade | None, answered: list[uuid.UUID]
    ) -> list[EmployerTask]:
        """Задачи специализации для грейда кандидата (или для всех), ещё без его ответа."""
        stmt = self._select().where(
            EmployerTask.specialization == specialization,
            EmployerTask.grade.is_(None) | (EmployerTask.grade == grade),
            EmployerTask.id.not_in(answered),
        )
        return list((await self.session.execute(stmt.order_by(EmployerTask.created_at))).scalars())


class CompanyAnswerRepository(OwnedRepository[TaskAnswer]):
    model = TaskAnswer
    column = TaskAnswer.company_id


class ProfileAnswerRepository(OwnedRepository[TaskAnswer]):
    model = TaskAnswer
    column = TaskAnswer.profile_id

    async def task_ids(self) -> list[uuid.UUID]:
        stmt = select(TaskAnswer.task_id).where(TaskAnswer.profile_id == self.owner_id)
        return list((await self.session.execute(stmt)).scalars())

    async def last_answered_at(self) -> datetime | None:
        """Закрытая из-за снимка экрана задача не считается ответом: период не сдвигается."""
        stmt = select(func.max(TaskAnswer.created_at)).where(
            TaskAnswer.profile_id == self.owner_id, TaskAnswer.blocked.is_(False)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
