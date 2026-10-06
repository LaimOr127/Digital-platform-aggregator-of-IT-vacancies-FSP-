import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Grade, UserRole, VacancyStatus, WorkFormat


class AdminVacancyOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    title: str
    description: str
    grade: Grade
    work_format: WorkFormat
    salary_min: int
    salary_max: int
    status: VacancyStatus
    expires_at: datetime | None
    created_at: datetime
    complaints: int = Field(default=0, description="жалоб кандидатов")
    complaint_notes: list[str] = Field(default=[], description="последние жалобы: причина и текст")


class ModerationIn(BaseModel):
    action: Literal["block", "unblock"]
    reason: str = Field(default="", max_length=500)


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    is_superadmin: bool
    totp_enabled: bool
    created_at: datetime


class AuditEntryOut(BaseModel):
    id: uuid.UUID
    action: str
    actor_email: str | None
    target_type: str | None
    target_id: uuid.UUID | None
    meta: dict
    created_at: datetime
