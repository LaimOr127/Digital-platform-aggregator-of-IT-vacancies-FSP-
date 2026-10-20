import uuid
from datetime import datetime

from pydantic import BaseModel, Field, SecretStr

from app.models.enums import AiProviderKind

# без «<» и «>»: незаменённая заглушка шаблона (gpt://<folder_id>/...) — сервис ответит 400
_MODEL_PATTERN = r"^[^<>]+$"


class AiProviderIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    kind: AiProviderKind
    base_url: str = Field(min_length=8, max_length=300)
    model: str = Field(min_length=1, max_length=120, pattern=_MODEL_PATTERN)
    api_key: SecretStr | None = Field(
        default=None, description="пусто — без ключа (локальная модель)"
    )


class AiProviderUpdate(BaseModel):
    """Пустой api_key — ключ не меняется; clear_key — удалить ключ."""

    name: str | None = Field(default=None, min_length=2, max_length=80)
    kind: AiProviderKind | None = None
    base_url: str | None = Field(default=None, min_length=8, max_length=300)
    model: str | None = Field(default=None, min_length=1, max_length=120, pattern=_MODEL_PATTERN)
    api_key: SecretStr | None = None
    clear_key: bool = False


class AiProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: AiProviderKind
    base_url: str
    model: str
    has_key: bool
    key_hint: str | None
    is_active: bool
    created_at: datetime


class AiTestOut(BaseModel):
    ok: bool
    latency_ms: int
    message: str
