from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Grade


class SalaryBandOut(BaseModel):
    """Распределение зарплат группы: только если в ней не меньше min_group значений."""

    count: int
    p25: int
    median: int
    p75: int


class GradeSalaryOut(BaseModel):
    grade: Grade
    band: SalaryBandOut | None


class SalaryRadarOut(BaseModel):
    grade: Grade | None
    skills: list[str] = Field(description="навыки, по которым выбраны похожие вакансии")
    vacancies: SalaryBandOut | None = Field(description="вилки вакансий (середина)")
    offers: SalaryBandOut | None = Field(description="реальные офферы платформы")
    peers: SalaryBandOut | None = Field(description="ожидания кандидатов того же уровня")
    ladder: list[GradeSalaryOut] = Field(description="вакансии с тем же стеком по грейдам")
    expectation: int | None = None
    position: Literal["below", "within", "above"] | None = None
    min_group: int


class SkillShareOut(BaseModel):
    slug: str
    name: str
    share: float = Field(ge=0, le=1, description="доля вакансий, где навык требуется")


class GrowthOut(BaseModel):
    current_grade: Grade | None
    target_grade: Grade | None
    vacancies_considered: int
    missing_skills: list[SkillShareOut]
    strengths: list[SkillShareOut]
    salary_now: int | None
    salary_target: int | None
    fsp_next: str
    min_group: int
