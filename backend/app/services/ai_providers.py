"""Языковые модели, подключённые в интерфейсе: управление (суперадмин) и выбор активной.

Адрес модели проверяется (защита от SSRF): только https (http — если явно разрешено для
локальной модели), без служебных адресов стенда, loopback и link-local (метаданные облака).
"""

import ipaddress
import time
import uuid
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import FieldCipher, ai_key_context
from app.core.errors import AppError, NotFoundError
from app.integrations.ai.anthropic import AnthropicClient
from app.integrations.ai.base import AiClient, AiUnavailableError
from app.integrations.ai.openai_compat import OpenAiCompatibleClient
from app.models import AiProvider
from app.models.enums import AiProviderKind
from app.repositories.audit import AuditRepository
from app.schemas.ai import AiProviderIn, AiProviderOut, AiProviderUpdate, AiTestOut
from app.services.access import Action, Principal, policy

# сервисы стенда (docker compose): модель не может указывать на них
_INTERNAL_HOSTS = {"db", "api", "worker", "web", "proxy", "migrate", "fsp-mock", "mailpit"}
_CLIENTS: dict[AiProviderKind, type[AiClient]] = {
    AiProviderKind.OPENAI: OpenAiCompatibleClient,
    AiProviderKind.ANTHROPIC: AnthropicClient,
}
_PING_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


class UnsafeUrlError(AppError):
    status_code, code = 422, "unsafe_url"


def check_url(url: str, allow_http: bool) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise UnsafeUrlError("адрес модели должен начинаться с https://")
    if parts.scheme == "http" and not allow_http:
        raise UnsafeUrlError("нужен https:// (http разрешается только для локальной модели)")
    host = parts.hostname.lower()
    if host in _INTERNAL_HOSTS or host == "localhost":
        raise UnsafeUrlError("адрес указывает на внутренний сервис")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url.strip().rstrip("/")
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
        raise UnsafeUrlError("адрес указывает на внутренний сервис")
    return url.strip().rstrip("/")


def build_client(
    provider: AiProvider, cipher: FieldCipher, transport: httpx.AsyncBaseTransport | None
) -> AiClient:
    key = cipher.decrypt(provider.api_key_enc, ai_key_context(provider.id)) or ""
    return _CLIENTS[provider.kind](provider.base_url, provider.model, key, transport)


async def active_client(
    session: AsyncSession,
    cipher: FieldCipher,
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[AiClient, str] | None:
    """Активная модель из интерфейса; если её нет — ключ Anthropic из окружения; иначе None."""
    provider = (
        await session.execute(select(AiProvider).where(AiProvider.is_active.is_(True)))
    ).scalar_one_or_none()
    if provider is not None:
        return build_client(provider, cipher, transport), provider.name
    key = settings.anthropic_api_key.get_secret_value()
    if key:
        client = AnthropicClient(settings.ai_base_url, settings.ai_model, key, transport)
        return client, f"Anthropic ({settings.ai_model})"
    return None


def to_out(p: AiProvider) -> AiProviderOut:
    return AiProviderOut(
        id=p.id,
        name=p.name,
        kind=p.kind,
        base_url=p.base_url,
        model=p.model,
        has_key=p.api_key_enc is not None,
        key_hint=p.key_hint,
        is_active=p.is_active,
        created_at=p.created_at,
    )


class AiProviderService:
    def __init__(
        self,
        session: AsyncSession,
        principal: Principal,
        cipher: FieldCipher,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        policy.ensure(principal, Action.ADMIN_SUPER)
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.settings = settings
        self.transport = transport
        self.audit = AuditRepository(session)

    async def list_providers(self) -> list[AiProviderOut]:
        rows = await self.session.execute(select(AiProvider).order_by(AiProvider.created_at))
        return [to_out(p) for p in rows.scalars()]

    async def create(self, data: AiProviderIn) -> AiProviderOut:
        provider = AiProvider(
            id=uuid.uuid4(),
            name=data.name.strip(),
            kind=data.kind,
            base_url=check_url(data.base_url, self.settings.ai_allow_http),
            model=data.model.strip(),
        )
        self._set_key(provider, data.api_key.get_secret_value() if data.api_key else "")
        self.session.add(provider)
        await self._audit("admin.ai_provider_created", provider)
        return to_out(provider)

    async def update(self, provider_id: uuid.UUID, data: AiProviderUpdate) -> AiProviderOut:
        provider = await self._get(provider_id)
        if data.base_url is not None:
            provider.base_url = check_url(data.base_url, self.settings.ai_allow_http)
        for field in ("name", "kind", "model"):
            value = getattr(data, field)
            if value is not None:
                setattr(provider, field, value.strip() if isinstance(value, str) else value)
        if data.clear_key:
            self._set_key(provider, "")
        elif data.api_key and data.api_key.get_secret_value():
            self._set_key(provider, data.api_key.get_secret_value())
        await self._audit("admin.ai_provider_updated", provider)
        return to_out(provider)

    async def delete(self, provider_id: uuid.UUID) -> None:
        provider = await self._get(provider_id)
        await self.session.delete(provider)
        await self._audit("admin.ai_provider_deleted", provider)

    async def activate(self, provider_id: uuid.UUID | None) -> list[AiProviderOut]:
        """Активна одна модель; None — выключить ИИ (останется ключ из окружения, если задан)."""
        await self.session.execute(update(AiProvider).values(is_active=False))
        await self.session.flush()
        if provider_id is not None:
            provider = await self._get(provider_id)
            provider.is_active = True
            await self._audit("admin.ai_provider_activated", provider)
        else:
            await self.audit.record("admin.ai_provider_deactivated", self.principal.user_id)
            await self.session.commit()
        return await self.list_providers()

    async def test(self, provider_id: uuid.UUID) -> AiTestOut:
        provider = await self._get(provider_id)
        client = build_client(provider, self.cipher, self.transport)
        started = time.monotonic()
        try:
            await client.complete_json("Проверка связи.", 'Верни {"ok": true}', _PING_SCHEMA)
        except AiUnavailableError as exc:
            elapsed = round((time.monotonic() - started) * 1000)
            return AiTestOut(ok=False, latency_ms=elapsed, message=_failure(exc))
        elapsed = round((time.monotonic() - started) * 1000)
        return AiTestOut(ok=True, latency_ms=elapsed, message=f"Модель ответила за {elapsed} мс")

    def _set_key(self, provider: AiProvider, key: str) -> None:
        key = key.strip()
        provider.api_key_enc = (
            self.cipher.encrypt(key, ai_key_context(provider.id)) if key else None
        )
        provider.key_hint = f"…{key[-4:]}" if len(key) >= 8 else None

    async def _get(self, provider_id: uuid.UUID) -> AiProvider:
        provider = await self.session.get(AiProvider, provider_id)
        if provider is None:
            raise NotFoundError("модель не найдена")
        return provider

    async def _audit(self, action: str, provider: AiProvider) -> None:
        meta = {"name": provider.name, "kind": provider.kind, "model": provider.model}
        await self.audit.record(action, self.principal.user_id, "ai_provider", provider.id, meta)
        await self.session.commit()


def _failure(exc: AiUnavailableError) -> str:
    """Понятная причина без деталей ответа сервера (в них может быть что угодно)."""
    cause = exc.__cause__
    if isinstance(cause, httpx.HTTPStatusError):
        code = cause.response.status_code
        hints = {401: "неверный ключ", 403: "нет доступа", 404: "неверный адрес или модель"}
        return f"Ошибка {code}: {hints.get(code, 'сервис отклонил запрос')}"
    if isinstance(cause, httpx.TimeoutException):
        return "Модель не ответила вовремя"
    if isinstance(cause, httpx.TransportError):
        return "Не удалось подключиться к адресу модели"
    return "Ответ модели не по формату — проверьте, что API совместим"
