"""Единая конфигурация приложения. Все значения — только из окружения (.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_MARKERS = ("change", "example", "secret", "password", "12345")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None, extra="ignore", case_sensitive=False, hide_input_in_errors=True
    )

    app_env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "IT Match FSP"
    log_level: str = "INFO"

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "itmatch"
    app_db_user: str = "itmatch_app"
    app_db_password: SecretStr = SecretStr("")

    jwt_secret: SecretStr = SecretStr("")
    cors_origins: list[str] = Field(default_factory=list)
    fsp_base_url: str = "http://fsp-mock:8001"

    @property
    def database_url(self) -> str:
        pwd = self.app_db_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.app_db_user}:{pwd}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @model_validator(mode="after")
    def _check_secrets(self) -> "Settings":
        """В prod запрещаем пустые и слабые секреты — приложение просто не стартует."""
        if self.app_env != "prod":
            return self
        for name in ("app_db_password", "jwt_secret"):
            value = getattr(self, name).get_secret_value()
            if len(value) < 32 or any(m in value.lower() for m in _WEAK_MARKERS):
                msg = f"{name.upper()} слишком слабый для prod (нужно >=32 случайных символов)"
                raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
