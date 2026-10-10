from typing import TYPE_CHECKING, Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from app.repositories.base import Page


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SkillOut(ORMModel):
    slug: str
    name: str


class PageOut[T](BaseModel):
    items: list[T]
    next_cursor: str | None

    @classmethod
    def build(cls, page: "Page[Any]", schema: type[T]) -> "PageOut[T]":
        """Page репозитория -> ответ API; schema — ORM-схема элемента."""
        return cls(
            items=[schema.model_validate(i) for i in page.items],  # type: ignore[attr-defined]
            next_cursor=page.next_cursor,
        )


# стаж в годах с одной десятой: 3 года 5 месяцев = 3.4
Years = Annotated[float, Field(ge=0, le=50), AfterValidator(lambda v: round(v, 1))]


def check_salary_range(salary_min: int | None, salary_max: int | None) -> None:
    """Единая проверка вилки: для схем и для частичных обновлений в сервисах."""
    if salary_min and salary_max and salary_max < salary_min:
        msg = "salary_max должен быть не меньше salary_min"
        raise ValueError(msg)


class SalaryRangeMixin(BaseModel):
    """Вилка: min <= max. Используется профилем кандидата и вакансией."""

    salary_min: int | None = Field(default=None, gt=0, le=10_000_000)
    salary_max: int | None = Field(default=None, gt=0, le=10_000_000)

    @model_validator(mode="after")
    def _range(self) -> "SalaryRangeMixin":
        check_salary_range(self.salary_min, self.salary_max)
        return self
