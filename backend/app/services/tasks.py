"""Регулярные короткие задания (ТЗ: «система периодически предлагает задачу от работодателя»).

Компания публикует задачу для специализации (и, по желанию, грейда). Кандидату раз в период
предлагается одна задача его специализации: выбор детерминирован на неделю (хеш анонимного id
и номера недели), поэтому разные кандидаты получают разные задачи, а обновление страницы
задачу не меняет. Ответ (решение или подход) обновляет актуальность профиля — фактор
«Актуальность» в подборе; компания видит ответы анонимно и оценивает их.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, InvalidStateError, NotFoundError
from app.core.timeutil import as_aware
from app.models import CandidateProfile, EmployerTask, TaskAnswer
from app.models.enums import Grade
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.companies import CompanyRepository
from app.repositories.tasks import (
    CompanyAnswerRepository,
    CompanyTaskRepository,
    OpenTaskRepository,
    ProfileAnswerRepository,
)
from app.schemas.tasks import (
    AnswerIn,
    CurrentTaskOut,
    MyTaskAnswerOut,
    OfferedTaskOut,
    TaskAnswerOut,
    TaskIn,
    TaskOut,
)
from app.services.access import Action, Principal, policy
from app.services.catalog import cards_by_profile

TASK_PERIOD = timedelta(days=7)
NO_SURVEY = "Пройдите опрос в разделе «Тест»: задачи подбираются по специализации"
NO_TASKS = "Новых задач для вашей специализации пока нет — загляните позже"


class EmployerTaskService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.COMPANY_READ_OWN)
        if principal.company_id is None:
            raise ForbiddenError("no company")
        self.session = session
        self.principal = principal
        self.tasks = CompanyTaskRepository(session, principal.company_id)
        self.answers = CompanyAnswerRepository(session, principal.company_id)

    async def create(self, data: TaskIn) -> TaskOut:
        policy.ensure(self.principal, Action.TASK_PUBLISH)
        task = EmployerTask(
            company_id=self.tasks.owner_id,
            created_by=self.principal.user_id,
            title=data.title.strip(),
            body=data.body.strip(),
            specialization=data.specialization,
            grade=data.grade,
            is_active=True,
        )
        await self.tasks.add(task)
        await self.session.commit()
        return TaskOut.model_validate(task)

    async def list_tasks(self, cursor: str | None, limit: int) -> tuple[list[TaskOut], str | None]:
        page = await self.tasks.list_page(cursor=cursor, limit=limit)
        counts = await self.tasks.answer_counts([t.id for t in page.items])
        items = [
            TaskOut.model_validate(t).model_copy(update={"answers_count": counts.get(t.id, 0)})
            for t in page.items
        ]
        return items, page.next_cursor

    async def close(self, task_id: uuid.UUID) -> TaskOut:
        task = await self.tasks.get_or_404(task_id)
        task.is_active = False
        await self.session.commit()
        return TaskOut.model_validate(task)

    async def list_answers(
        self, task_id: uuid.UUID, cursor: str | None, limit: int
    ) -> tuple[list[TaskAnswerOut], str | None]:
        policy.ensure(self.principal, Action.APPLICATION_MANAGE)
        task = await self.tasks.get_or_404(task_id)
        page = await self.answers.list_page(
            TaskAnswer.task_id == task.id, cursor=cursor, limit=limit
        )
        return await self._outs(page.items), page.next_cursor

    async def rate(self, task_id: uuid.UUID, answer_id: uuid.UUID, rating: int) -> TaskAnswerOut:
        policy.ensure(self.principal, Action.APPLICATION_MANAGE)
        task = await self.tasks.get_or_404(task_id)
        answer = await self.answers.lock_or_404(answer_id)
        if answer.task_id != task.id:
            raise NotFoundError("task_answers not found")
        answer.rating = rating
        await self.session.commit()
        return (await self._outs([answer]))[0]

    async def _outs(self, answers: list[TaskAnswer]) -> list[TaskAnswerOut]:
        """Анонимные карточки авторов: компания может пригласить автора сильного ответа."""
        cards = await cards_by_profile(
            CatalogRepository(self.session), [a.profile_id for a in answers]
        )
        return [
            TaskAnswerOut(
                id=a.id,
                answer=a.answer,
                rating=a.rating,
                created_at=a.created_at,
                candidate=cards.get(a.profile_id),
            )
            for a in answers
        ]


class CandidateTaskService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.profiles = CandidateProfileRepository(session, owner_id=principal.user_id)
        self.open_tasks = OpenTaskRepository(session)

    async def current(self) -> CurrentTaskOut:
        profile = await self.profiles.own_or_404()
        if profile.specialization is None:
            return CurrentTaskOut(task=None, reason=NO_SURVEY)
        answers = ProfileAnswerRepository(self.session, profile.id)
        if next_at := await _next_at(answers):
            return CurrentTaskOut(task=None, next_at=next_at)
        offered = await self.open_tasks.offered_for(
            profile.specialization, _grade(profile), await answers.task_ids()
        )
        if not offered:
            return CurrentTaskOut(task=None, reason=NO_TASKS)
        task = _weekly_pick(profile.anon_id, offered)
        company = await CompanyRepository(self.session).get_or_404(task.company_id)
        return CurrentTaskOut(task=_offered(task, company.name))

    async def answer(self, task_id: uuid.UUID, data: AnswerIn) -> MyTaskAnswerOut:
        # блокировка профиля: два параллельных ответа не обойдут ограничение периода
        profile = await self.profiles.own_or_404(for_update=True)
        if profile.specialization is None:
            raise InvalidStateError(NO_SURVEY)
        answers = ProfileAnswerRepository(self.session, profile.id)
        if next_at := await _next_at(answers):
            raise ConflictError(f"следующую задачу можно решить с {next_at:%d.%m.%Y}")
        task = await self.open_tasks.get_or_404(task_id)
        if task.specialization != profile.specialization or task.grade not in (
            None,
            _grade(profile),
        ):
            raise InvalidStateError("задача предназначена для другой специализации или грейда")
        company = await CompanyRepository(self.session).get_or_404(task.company_id)
        answer = TaskAnswer(
            task_id=task.id,
            company_id=task.company_id,
            profile_id=profile.id,
            task_title=task.title,
            company_name=company.name,
            answer=data.answer.strip(),
        )
        try:
            await answers.add(answer)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("вы уже ответили на эту задачу") from exc
        profile.last_activity_at = datetime.now(UTC)  # свежий сигнал для подбора
        await self.session.commit()
        return MyTaskAnswerOut.model_validate(answer)

    async def my_answers(
        self, cursor: str | None, limit: int
    ) -> tuple[list[MyTaskAnswerOut], str | None]:
        profile = await self.profiles.own_or_404()
        page = await ProfileAnswerRepository(self.session, profile.id).list_page(
            cursor=cursor, limit=limit
        )
        return [MyTaskAnswerOut.model_validate(a) for a in page.items], page.next_cursor


async def _next_at(answers: ProfileAnswerRepository) -> datetime | None:
    """Когда откроется следующая задача; None — уже можно решать."""
    last = await answers.last_answered_at()
    if last is None:
        return None
    next_at = as_aware(last) + TASK_PERIOD
    return next_at if next_at > datetime.now(UTC) else None


def _grade(profile: CandidateProfile) -> Grade | None:
    return profile.confirmed_grade or profile.grade


def _weekly_pick(anon_id: uuid.UUID, offered: list[EmployerTask]) -> EmployerTask:
    """Задача недели: детерминированный выбор по анонимному id и номеру недели. Задачи,
    опубликованные в течение недели, участвуют со следующей — выбор не меняется посреди недели."""
    now = datetime.now(UTC)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    settled = [t for t in offered if as_aware(t.created_at) < week_start] or offered
    year, week, _ = now.isocalendar()
    digest = hashlib.sha256(f"{anon_id}:{year}-{week}".encode()).digest()
    return settled[int.from_bytes(digest[:4]) % len(settled)]


def _offered(task: EmployerTask, company_name: str) -> OfferedTaskOut:
    return OfferedTaskOut(
        id=task.id,
        title=task.title,
        body=task.body,
        specialization=task.specialization,
        grade=task.grade,
        company_name=company_name,
    )
