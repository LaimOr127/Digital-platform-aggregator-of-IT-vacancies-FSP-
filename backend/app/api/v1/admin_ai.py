"""Суперадмин: подключение языковых моделей (OpenAI-совместимый API или Anthropic)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep
from app.schemas.ai import AiProviderIn, AiProviderOut, AiProviderUpdate, AiTestOut
from app.services.ai_providers import AiProviderService

router = APIRouter(prefix="/admin/ai-providers", tags=["admin"])


def _service(
    request: Request, session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> AiProviderService:
    state = request.app.state
    return AiProviderService(session, principal, cipher, state.settings, state.ai_transport)


ServiceDep = Annotated[AiProviderService, Depends(_service)]


@router.get("", summary="Подключённые модели")
async def list_providers(service: ServiceDep) -> list[AiProviderOut]:
    return await service.list_providers()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Подключить модель")
async def create_provider(data: AiProviderIn, service: ServiceDep) -> AiProviderOut:
    return await service.create(data)


@router.patch("/{provider_id}", summary="Изменить модель (пустой ключ — без изменений)")
async def update_provider(
    provider_id: uuid.UUID, data: AiProviderUpdate, service: ServiceDep
) -> AiProviderOut:
    return await service.update(provider_id, data)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить")
async def delete_provider(provider_id: uuid.UUID, service: ServiceDep) -> None:
    await service.delete(provider_id)


@router.post("/{provider_id}/activate", summary="Сделать активной (остальные выключаются)")
async def activate_provider(provider_id: uuid.UUID, service: ServiceDep) -> list[AiProviderOut]:
    return await service.activate(provider_id)


@router.post("/deactivate", summary="Выключить ИИ")
async def deactivate(service: ServiceDep) -> list[AiProviderOut]:
    return await service.activate(None)


@router.post("/{provider_id}/test", summary="Проверить подключение")
async def test_provider(provider_id: uuid.UUID, service: ServiceDep) -> AiTestOut:
    return await service.test(provider_id)
