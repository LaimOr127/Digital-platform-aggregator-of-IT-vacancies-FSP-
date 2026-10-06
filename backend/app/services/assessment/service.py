"""Путь кандидата: опрос по специализации -> тест на заявленный грейд -> категория.

Категория (специализация x подтверждённый грейд) и результат теста определяют, где кандидат
окажется в выдаче работодателя. Самоописание профиля на категорию не влияет.
"""

import random
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ConflictError, InvalidStateError
from app.core.timeutil import as_aware
from app.models import Assessment, CandidateProfile
from app.models.enums import AssessmentResult, AssessmentStatus, Grade
from app.repositories.assessments import AssessmentRepository
from app.repositories.audit import AuditRepository
from app.repositories.candidates import CandidateProfileRepository, SkillRepository
from app.schemas.assessment import (
    AssessmentStateOut,
    AttemptOut,
    AttemptResultOut,
    GradeOptionOut,
    SubmitIn,
    SurveyIn,
)
from app.services.access import Action, Principal, policy
from app.services.assessment import views
from app.services.assessment.engine import GeneratedItem, assemble, evaluate
from app.services.assessment.policy import CHANGE_COOLDOWN, AttemptRecord, decide
from app.services.common import resolve_skills
from app.services.specializations import GRADE_ORDER, level

TIME_LIMIT = timedelta(minutes=25)
GRACE = timedelta(minutes=1)  # задержка сети при отправке на последней секунде


class AnswersMismatchError(AppError):
    status_code, code = 422, "invalid_answers"


class AssessmentService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.profiles = CandidateProfileRepository(session, owner_id=principal.user_id)
        self.audit = AuditRepository(session)

    async def state(self) -> AssessmentStateOut:
        profile = await self.profiles.own_or_404()
        repo = AssessmentRepository(self.session, profile.id)
        active = await self._active(repo)
        options = await self._options(profile, repo)
        if active:
            options = views.blocked_options(options, "завершите начатый тест")
        return AssessmentStateOut(
            survey=views.survey(profile),
            category=views.category(profile),
            confirmed_skills=profile.confirmed_skills or [],
            active=views.attempt(active) if active else None,
            history=[views.result(a) for a in await repo.history()],
            options=options,
        )

    async def save_survey(self, data: SurveyIn) -> AssessmentStateOut:
        profile = await self.profiles.own_or_404(for_update=True)
        now = datetime.now(UTC)
        if profile.specialization and data.specialization != profile.specialization:
            self._ensure_can_change(profile, now)
            _reset_category(profile)
        profile.specialization = data.specialization
        profile.grade = data.grade
        profile.experience_years = data.experience_years
        profile.industries = data.industries
        profile.roles = data.roles
        profile.skills = await resolve_skills(SkillRepository(self.session), data.skills)
        profile.survey_at = now
        await self.audit.record("assessment.survey", self.principal.user_id, "profile", profile.id)
        await self.session.commit()
        return await self.state()

    async def start(self, grade: Grade) -> AttemptOut:
        profile = await self.profiles.own_or_404(for_update=True)
        if profile.specialization is None or profile.survey_at is None:
            raise InvalidStateError("сначала пройдите опрос: специализация и заявленный грейд")
        repo = AssessmentRepository(self.session, profile.id)
        if await self._active(repo):
            raise ConflictError("завершите начатый тест")
        now = datetime.now(UTC)
        decision = decide(grade, *_confirmed(profile), await _records(profile, repo), now)
        if not decision.allowed:
            when = f" (с {decision.retry_at:%d.%m.%Y})" if decision.retry_at else ""
            raise InvalidStateError(decision.reason + when)
        seed = secrets.token_hex(8)
        focus = frozenset(s.slug for s in profile.skills)
        items = assemble(profile.specialization.value, level(grade), random.Random(seed), focus)
        attempt = Assessment(
            profile_id=profile.id,
            specialization=profile.specialization,
            grade=grade,
            status=AssessmentStatus.IN_PROGRESS,
            seed=seed,
            items=[i.as_dict() for i in items],
            survey=_snapshot(profile),
            started_at=now,
            deadline_at=now + TIME_LIMIT,
        )
        await repo.add(attempt)
        await self.audit.record(
            "assessment.started", self.principal.user_id, "assessment", attempt.id, {"grade": grade}
        )
        await self.session.commit()
        return views.attempt(attempt)

    async def submit(self, attempt_id: uuid.UUID, data: SubmitIn) -> AttemptResultOut:
        profile = await self.profiles.own_or_404(for_update=True)
        attempt = await AssessmentRepository(self.session, profile.id).lock_or_404(attempt_id)
        if attempt.status != AssessmentStatus.IN_PROGRESS:
            raise InvalidStateError("тест уже завершён")
        now = datetime.now(UTC)
        if now > as_aware(attempt.deadline_at) + GRACE:
            _expire(attempt)
            await self.session.commit()
            raise InvalidStateError("время на тест вышло — ответы не засчитаны")
        items = [GeneratedItem.from_dict(d) for d in attempt.items]
        if len(data.responses) != len(items):
            raise AnswersMismatchError("число ответов не совпадает с числом заданий")
        outcome = evaluate(items, data.responses, level(attempt.grade))
        attempt.responses = data.responses
        attempt.status = AssessmentStatus.COMPLETED
        attempt.finished_at = now
        attempt.result = AssessmentResult.PASSED if outcome.passed else AssessmentResult.FAILED
        attempt.theta, attempt.theta_error = outcome.theta, outcome.error
        attempt.correct, attempt.score = outcome.correct, outcome.score
        attempt.confident, attempt.topics = outcome.confident, outcome.topics
        if outcome.passed:
            profile.grade = profile.confirmed_grade = attempt.grade
            profile.grade_confirmed_at = now
            profile.assessment_score = outcome.score
            profile.confirmed_skills = list(outcome.skills)
        profile.last_activity_at = now
        await self.audit.record(
            "assessment.completed",
            self.principal.user_id,
            "assessment",
            attempt.id,
            {"grade": attempt.grade, "result": attempt.result, "theta": outcome.theta},
        )
        await self.session.commit()
        return views.result(attempt)

    async def forfeit(self, attempt_id: uuid.UUID, reason: str) -> AttemptResultOut:
        """Снимок экрана во время теста: попытка не засчитана — как проваленная, с теми же
        правилами повтора (этот грейд и выше — через 14 дней)."""
        profile = await self.profiles.own_or_404(for_update=True)
        attempt = await AssessmentRepository(self.session, profile.id).lock_or_404(attempt_id)
        if attempt.status != AssessmentStatus.IN_PROGRESS:
            raise InvalidStateError("тест уже завершён")
        attempt.status = AssessmentStatus.COMPLETED
        attempt.finished_at = datetime.now(UTC)
        attempt.result = AssessmentResult.FAILED
        attempt.correct, attempt.score, attempt.confident = 0, 0, False
        attempt.violation = reason
        await self.audit.record(
            "assessment.violation",
            self.principal.user_id,
            "assessment",
            attempt.id,
            {"grade": attempt.grade, "reason": reason},
        )
        await self.session.commit()
        return views.result(attempt)

    async def _active(self, repo: AssessmentRepository) -> Assessment | None:
        """Открытая попытка; просроченные закрываются при обращении (ответы не засчитаны)."""
        active = None
        expired = False
        for row in await repo.in_progress():
            if datetime.now(UTC) > as_aware(row.deadline_at) + GRACE:
                _expire(row)
                expired = True
            else:
                active = row
        if expired:
            await self.session.commit()
        return active

    async def _options(
        self, profile: CandidateProfile, repo: AssessmentRepository
    ) -> list[GradeOptionOut]:
        if profile.specialization is None or profile.survey_at is None:
            return []
        records, now = await _records(profile, repo), datetime.now(UTC)
        options = []
        for grade in GRADE_ORDER:
            decision = decide(grade, *_confirmed(profile), records, now)
            options.append(
                GradeOptionOut(
                    grade=grade,
                    allowed=decision.allowed,
                    reason=decision.reason,
                    retry_at=decision.retry_at,
                )
            )
        return options

    @staticmethod
    def _ensure_can_change(profile: CandidateProfile, now: datetime) -> None:
        """Смена специализации сбрасывает категорию — с тем же ограничением, что смена грейда."""
        confirmed, confirmed_at = _confirmed(profile)
        if confirmed and confirmed_at and now < confirmed_at + CHANGE_COOLDOWN:
            retry = confirmed_at + CHANGE_COOLDOWN
            raise InvalidStateError(
                f"категория подтверждена недавно: сменить специализацию можно с {retry:%d.%m.%Y}"
            )


def _confirmed(profile: CandidateProfile) -> tuple[Grade | None, datetime | None]:
    at = as_aware(profile.grade_confirmed_at) if profile.grade_confirmed_at else None
    return profile.confirmed_grade, at


async def _records(profile: CandidateProfile, repo: AssessmentRepository) -> list[AttemptRecord]:
    if profile.specialization is None:
        return []
    return [
        AttemptRecord(
            grade=a.grade,
            result=a.result,
            confident=a.confident,
            finished_at=as_aware(a.finished_at) if a.finished_at else None,
        )
        for a in await repo.finished_for(profile.specialization)
    ]


def _reset_category(profile: CandidateProfile) -> None:
    profile.confirmed_grade = None
    profile.grade_confirmed_at = None
    profile.assessment_score = None
    profile.confirmed_skills = []


def _expire(attempt: Assessment) -> None:
    attempt.status = AssessmentStatus.EXPIRED
    attempt.finished_at = attempt.deadline_at


def _snapshot(profile: CandidateProfile) -> dict:
    return {
        "specialization": profile.specialization,
        "grade": profile.grade,
        "experience_years": profile.experience_years,
        "industries": profile.industries or [],
        "roles": profile.roles or [],
        "skills": [s.slug for s in profile.skills],
    }
