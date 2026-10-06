"""Представление попыток и состояния тестирования для API (без правильных ответов)."""

from app.core.timeutil import as_aware
from app.models import Assessment, CandidateProfile
from app.schemas.assessment import (
    AssignedCategoryOut,
    AttemptOut,
    AttemptResultOut,
    GradeOptionOut,
    PreviewQuestionOut,
    QuestionOut,
    SurveyOut,
    TopicResultOut,
)
from app.schemas.common import SkillOut
from app.services.assessment.engine import GeneratedItem
from app.services.assessment.policy import CHANGE_COOLDOWN
from app.services.specializations import category_slug, category_title


def question(index: int, item: GeneratedItem) -> QuestionOut:
    return QuestionOut(
        index=index,
        topic=item.topic,
        level=item.level,
        kind=item.kind,
        prompt=item.prompt,
        code=item.code,
        options=list(item.options),
    )


def preview_question(index: int, item: GeneratedItem) -> PreviewQuestionOut:
    return PreviewQuestionOut(
        **question(index, item).model_dump(), skills=list(item.skills), answer=item.answer
    )


def attempt(row: Assessment) -> AttemptOut:
    items = [GeneratedItem.from_dict(d) for d in row.items]
    return AttemptOut(
        id=row.id,
        specialization=row.specialization,
        grade=row.grade,
        status=row.status,
        started_at=as_aware(row.started_at),
        deadline_at=as_aware(row.deadline_at),
        questions=[question(i, item) for i, item in enumerate(items)],
    )


def result(row: Assessment) -> AttemptResultOut:
    topics = row.topics or {}
    return AttemptResultOut(
        id=row.id,
        specialization=row.specialization,
        grade=row.grade,
        status=row.status,
        result=row.result,
        theta=row.theta,
        correct=row.correct,
        total=len(row.items),
        score=row.score,
        confident=row.confident,
        topics=[TopicResultOut(topic=t, correct=c, total=n) for t, (c, n) in topics.items()],
        started_at=as_aware(row.started_at),
        finished_at=as_aware(row.finished_at) if row.finished_at else None,
        violation=row.violation,
    )


def survey(profile: CandidateProfile) -> SurveyOut | None:
    if profile.specialization is None or profile.survey_at is None:
        return None
    return SurveyOut(
        specialization=profile.specialization,
        grade=profile.grade,
        experience_years=profile.experience_years,
        industries=profile.industries or [],
        roles=profile.roles or [],
        skills=[SkillOut.model_validate(s) for s in profile.skills],
        answered_at=as_aware(profile.survey_at),
    )


def category(profile: CandidateProfile) -> AssignedCategoryOut | None:
    if profile.specialization is None or profile.confirmed_grade is None:
        return None
    confirmed_at = as_aware(profile.grade_confirmed_at) if profile.grade_confirmed_at else None
    return AssignedCategoryOut(
        slug=category_slug(profile.specialization, profile.confirmed_grade),
        title=category_title(profile.specialization, profile.confirmed_grade),
        specialization=profile.specialization,
        grade=profile.confirmed_grade,
        score=profile.assessment_score,
        confirmed_at=confirmed_at,
        next_change_at=confirmed_at + CHANGE_COOLDOWN if confirmed_at else None,
    )


def blocked_options(options: list[GradeOptionOut], reason: str) -> list[GradeOptionOut]:
    return [
        GradeOptionOut(grade=o.grade, allowed=False, reason=reason, retry_at=None) for o in options
    ]
