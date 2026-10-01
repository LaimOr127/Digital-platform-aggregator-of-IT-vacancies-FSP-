"""Единая конфигурация приложения. Все значения — только из окружения (.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

_WEAK_MARKERS = ("change", "example", "secret", "password")


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
    # Владелец схемы: задаётся только контейнеру migrate, api/worker его не получают
    db_owner_user: str = ""
    db_owner_password: SecretStr = SecretStr("")
    # Полный URL БД вместо сборки из частей (тесты: sqlite+aiosqlite)
    database_url_override: str = ""

    jwt_secret: SecretStr = SecretStr("")
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    # 32 байта в hex (64 символа): ключ AES-GCM для персональных данных
    field_encryption_key: SecretStr = SecretStr("")

    cors_origins: list[str] = Field(default_factory=list)
    fsp_base_url: str = "http://fsp-mock:8001"
    fsp_api_key: SecretStr = SecretStr("")
    fsp_timeout_seconds: float = 5.0
    # только для демо с моком: код подтверждения ФСП возвращается в ответе API
    fsp_demo_codes: bool = False
    fsp_sync_interval_minutes: int = 360
    # 32 байта в hex: seed ключа Ed25519 для подписи паспортов навыков
    passport_signing_key: SecretStr = SecretStr("")
    auth_rate_limit: str = "10/minute"  # вход/регистрация с одного IP
    login_email_rate_limit: str = "5/minute"  # попытки входа в один аккаунт с любых IP
    refresh_rate_limit: str = "60/minute"
    # ФСП: лимиты по пользователю и по аккаунту ФСП (перебор кода с пула IP не помогает)
    fsp_link_rate_limit: str = "10/hour"
    fsp_athlete_rate_limit: str = "5/hour"
    fsp_confirm_rate_limit: str = "20/hour"
    fsp_sync_rate_limit: str = "10/minute"
    offer_send_rate_limit: str = "50/day"  # офферы одной компании: защита кандидатов от спама

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return self._url(self.app_db_user, self.secret("app_db_password"))

    @property
    def migration_database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return self._url(self.db_owner_user, self.secret("db_owner_password"))

    def secret(self, name: str) -> str:
        """Значение секрета. В prod пустой или слабый секрет — ошибка при первом использовании:
        каждый сервис проверяет только те секреты, которые ему действительно выданы."""
        value = getattr(self, name).get_secret_value()
        weak = len(value) < 32 or any(m in value.lower() for m in _WEAK_MARKERS)
        if self.is_prod and weak:
            msg = f"{name.upper()} слишком слабый для prod (нужно >=32 случайных символов)"
            raise RuntimeError(msg)
        return value

    def _url(self, user: str, password: str) -> str:
        # URL.create экранирует спецсимволы пароля (@ : / %), в отличие от f-строки
        url = URL.create(
            "postgresql+asyncpg",
            username=user,
            password=password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )
        return url.render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
