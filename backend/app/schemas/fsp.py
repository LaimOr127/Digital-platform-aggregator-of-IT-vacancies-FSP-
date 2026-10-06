import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import VerificationTier


class FspLinkIn(BaseModel):
    athlete_id: str = Field(pattern=r"^[A-Za-z0-9-]{3,32}$", description="ID спортсмена в ФСП")


class FspConfirmIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class FspLinkStartOut(BaseModel):
    email_masked: str
    expires_in: int
    demo_code: str | None = Field(default=None, description="только в демо-режиме с моком")


class AchievementOut(BaseModel):
    external_id: str
    discipline: str
    discipline_title: str
    competition_title: str
    level: str
    date: str
    place: int | None
    stage: str
    role: str
    team: str | None


class CategoryOut(BaseModel):
    slug: str
    discipline: str
    tier: str
    title: str
    reasons: list[str]


class FspStatusOut(BaseModel):
    linked: bool
    athlete_id: str | None = None
    rank: str | None = None
    region: str | None = None
    last_synced_at: datetime | None = None
    pending_athlete_id: str | None = None
    verification_tier: VerificationTier
    demo_mode: bool = Field(default=False, description="стенд с моком ФСП: коды видны в интерфейсе")
    achievements: list[AchievementOut]
    categories: list[CategoryOut]


class PassportIssueIn(BaseModel):
    show_name: bool = False


class PassportOut(BaseModel):
    id: uuid.UUID
    issued_at: datetime
    revoked_at: datetime | None
    payload: dict
    signature: str
    key_id: str


PassportCheck = Literal["valid", "revoked", "expired", "bad_signature", "unknown_key"]


class PassportVerifyOut(BaseModel):
    """Публичная проверка. По отозванному паспорту данные не отдаются (отзыв согласия)."""

    id: uuid.UUID
    issued_at: datetime
    revoked_at: datetime | None
    status: PassportCheck
    valid: bool
    payload: dict | None
    signature: str | None
    key_id: str | None
    public_key: str
