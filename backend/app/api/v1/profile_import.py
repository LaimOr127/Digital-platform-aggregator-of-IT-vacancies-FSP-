"""Автозаполнение профиля кандидата: из анкеты ФСП и из файла резюме (PDF/DOCX).

Ответ — черновик: интерфейс показывает его кандидату, поля переносятся только по его выбору.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel

from app.api.deps import CipherDep, FspClientDep, PrincipalDep, SessionDep
from app.core.ratelimit import check_rate_limit
from app.schemas.profile_import import ProfileDraftOut
from app.services.access import Action, policy
from app.services.ai_providers import active_client
from app.services.profile_import import FspImportService
from app.services.resume.extract import MAX_BYTES, UnsupportedResumeError
from app.services.resume.llm import AiResumeParser
from app.services.resume.service import ResumeImportService


def _candidate_only(principal: PrincipalDep) -> None:
    """Проверка роли — до разбора тела: чужая роль получает 403, а не ошибку формы."""
    policy.ensure(principal, Action.PROFILE_MANAGE_OWN)


router = APIRouter(
    prefix="/candidate/import", tags=["candidate"], dependencies=[Depends(_candidate_only)]
)


async def get_ai_parser(
    request: Request, session: SessionDep, cipher: CipherDep
) -> AiResumeParser | None:
    """Модель, активная в настройках (или ключ из окружения); None — ИИ выключен."""
    state = request.app.state
    resolved = await active_client(session, cipher, state.settings, state.ai_transport)
    return AiResumeParser(*resolved) if resolved else None


AiParserDep = Annotated[AiResumeParser | None, Depends(get_ai_parser)]


class ImportCapabilitiesOut(BaseModel):
    ai_available: bool
    ai_provider: str | None = None  # для согласия: куда уйдёт текст резюме
    max_file_mb: int = MAX_BYTES // (1024 * 1024)


@router.get("/capabilities", summary="Доступен ли ИИ-разбор резюме")
async def capabilities(ai: AiParserDep) -> ImportCapabilitiesOut:
    return ImportCapabilitiesOut(ai_available=ai is not None, ai_provider=ai.label if ai else None)


@router.get("/fsp", summary="Черновик профиля из анкеты ФСП (после привязки аккаунта)")
async def from_fsp(
    request: Request, session: SessionDep, principal: PrincipalDep, client: FspClientDep
) -> ProfileDraftOut:
    check_rate_limit(request, "fsp_sync", key=str(principal.user_id))
    return await FspImportService(session, principal, client).draft()


@router.post("/resume", summary="Черновик профиля из резюме (PDF/DOCX до 5 МБ)")
async def from_resume(
    request: Request,
    session: SessionDep,
    principal: PrincipalDep,
    ai: AiParserDep,
    file: Annotated[UploadFile, File(description="PDF или DOCX")],
    use_ai: Annotated[bool, Form(description="согласие на разбор ИИ-сервисом")] = False,
) -> ProfileDraftOut:
    check_rate_limit(request, "resume", key=str(principal.user_id))
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise UnsupportedResumeError("файл больше 5 МБ")
    return await ResumeImportService(session, principal, ai).draft(data, use_ai)
