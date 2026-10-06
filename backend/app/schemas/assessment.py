import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AssessmentResult, AssessmentStatus, Grade, Specialization
from app.schemas.candidate import SkillSlug
from app.schemas.common import SkillOut
from app.services.specializations import INDUSTRIES, ROLES, known_keys


class SurveyIn(BaseModel):
    """Опрос по отрасли и специализации — первый шаг пути кандидата."""

    specialization: Specialization
    grade: Grade = Field(description="грейд, который кандидат заявляет и подтверждает тестом")
    experience_years: int = Field(ge=0, le=50)
    industries: list[str] = Field(default_factory=list, max_length=5)
    roles: list[str] = Field(default_factory=list, max_length=5)
    skills: list[SkillSlug] = Field(min_length=1, max_length=30)

    @field_validator("industries")
    @classmethod
    def _industries(cls, value: list[str]) -> list[str]:
        return known_keys(value, INDUSTRIES, "отрасль")

    @field_validator("roles")
    @classmethod
    def _roles(cls, value: list[str]) -> list[str]:
        return known_keys(value, ROLES, "роль")


class SurveyOut(BaseModel):
    specialization: Specialization
    grade: Grade | None
    experience_years: int | None
    industries: list[str]
    roles: list[str]
    skills: list[SkillOut]
    answered_at: datetime


class QuestionOut(BaseModel):
    """Задание без правильного ответа: ответ хранится только на сервере."""

    index: int
    topic: str
    level: int = Field(ge=1, le=5)
    kind: Literal["choice", "number"]
    prompt: str
    code: str | None
    options: list[str]


class PreviewQuestionOut(QuestionOut):
    """Пример задания для работодателя (вариант генерируется заново, поэтому с ответом)."""

    skills: list[str]
    answer: str


class AttemptOut(BaseModel):
    id: uuid.UUID
    specialization: Specialization
    grade: Grade
    status: AssessmentStatus
    started_at: datetime
    deadline_at: datetime
    questions: list[QuestionOut]


class TopicResultOut(BaseModel):
    topic: str
    correct: int
    total: int


class AttemptResultOut(BaseModel):
    id: uuid.UUID
    specialization: Specialization
    grade: Grade
    status: AssessmentStatus
    result: AssessmentResult | None
    theta: float | None = Field(description="оценка уровня по шкале грейдов 1–5")
    correct: int | None
    total: int
    score: int | None = Field(description="положение внутри категории, 0–100")
    confident: bool
    topics: list[TopicResultOut]
    started_at: datetime
    finished_at: datetime | None
    violation: str | None = Field(
        default=None, description="screenshot — снимок экрана во время теста, попытка не засчитана"
    )


class ViolationIn(BaseModel):
    """Нарушение, замеченное браузером во время теста или задачи."""

    reason: Literal["screenshot"] = "screenshot"


class SubmitIn(BaseModel):
    """Ответы по порядку заданий: номер варианта для выбора, число — для числового ответа."""

    responses: list[str | None] = Field(max_length=50)

    @field_validator("responses")
    @classmethod
    def _short(cls, value: list[str | None]) -> list[str | None]:
        if any(v is not None and len(v) > 32 for v in value):
            raise ValueError("слишком длинный ответ")
        return value


class GradeOptionOut(BaseModel):
    grade: Grade
    allowed: bool
    reason: str
    retry_at: datetime | None


class AssignedCategoryOut(BaseModel):
    slug: str
    title: str
    specialization: Specialization
    grade: Grade
    score: int | None
    confirmed_at: datetime | None
    next_change_at: datetime | None = Field(description="когда грейд можно сменить")


class AssessmentStateOut(BaseModel):
    survey: SurveyOut | None
    category: AssignedCategoryOut | None
    confirmed_skills: list[str]
    active: AttemptOut | None
    history: list[AttemptResultOut]
    options: list[GradeOptionOut]


class SpecializationOut(BaseModel):
    slug: Specialization
    title: str
    group: str
    skills: list[str]


class OptionOut(BaseModel):
    value: str
    label: str


class DictionariesOut(BaseModel):
    """Справочники для опроса и фильтров: специализации, отрасли, роли."""

    specializations: list[SpecializationOut]
    industries: list[OptionOut]
    roles: list[OptionOut]
    soft_skills: list[OptionOut]
    cities: list[str]
