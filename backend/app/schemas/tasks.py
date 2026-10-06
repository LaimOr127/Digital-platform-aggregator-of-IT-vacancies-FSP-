import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Grade, Specialization
from app.schemas.catalog import CandidateCardOut


class TaskIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=10, max_length=4000, description="условие: задача или вопрос")
    specialization: Specialization
    grade: Grade | None = Field(default=None, description="для какого грейда; пусто — для всех")


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    specialization: Specialization
    grade: Grade | None
    is_active: bool
    created_at: datetime
    answers_count: int = 0


class OfferedTaskOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    specialization: Specialization
    grade: Grade | None
    company_name: str


class CurrentTaskOut(BaseModel):
    """Задача периода: task = None, если ответ уже дан (next_at) или задач нет (reason)."""

    task: OfferedTaskOut | None
    next_at: datetime | None = None
    reason: str | None = None


class AnswerIn(BaseModel):
    answer: str = Field(min_length=20, max_length=4000, description="решение или подход к нему")


class RatingIn(BaseModel):
    rating: int = Field(ge=1, le=5)


class TaskAnswerOut(BaseModel):
    """Ответ для компании: анонимная карточка кандидата, без имени и контактов."""

    id: uuid.UUID
    answer: str
    rating: int | None
    created_at: datetime
    candidate: CandidateCardOut | None


class MyTaskAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_title: str
    company_name: str
    answer: str
    rating: int | None
    created_at: datetime
