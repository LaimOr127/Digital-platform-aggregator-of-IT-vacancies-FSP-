"""Работодатель: каталог кандидатов по категориям и офферы."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.deps import CipherDep, PrincipalDep, SessionDep
from app.core.errors import AppError
from app.core.ratelimit import check_rate_limit
from app.models.enums import Grade, OfferStatus, SearchStatus, Specialization, WorkFormat
from app.repositories.catalog import CatalogFilters
from app.schemas.catalog import (
    CandidateCardOut,
    CatalogCategoryOut,
    EmployerOfferOut,
    FspCategoryOut,
    OfferContactsOut,
    OfferCreateIn,
)
from app.schemas.common import PageOut
from app.services.catalog import CatalogService
from app.services.offers import EmployerOfferService
from app.services.specializations import parse_category

router = APIRouter(prefix="/employer", tags=["employer"])
Limit = Annotated[int, Query(ge=1, le=50)]
Slug = Annotated[str | None, Query(max_length=64, pattern=r"^[a-z0-9][a-z0-9+#.\-]*$")]
Skills = Annotated[
    list[Annotated[str, Query(max_length=64, pattern=r"^[a-z0-9][a-z0-9+#.\-]*$")]],
    Query(max_length=10, description="все выбранные навыки"),
]


class UnknownCategoryError(AppError):
    status_code, code = 422, "unknown_category"


def _catalog(session: SessionDep, principal: PrincipalDep) -> CatalogService:
    return CatalogService(session, principal)


def _offers(
    session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> EmployerOfferService:
    return EmployerOfferService(session, principal, cipher)


CatalogDep = Annotated[CatalogService, Depends(_catalog)]
OffersDep = Annotated[EmployerOfferService, Depends(_offers)]


@router.get(
    "/catalog/categories", summary="Категории (специализация x грейд) со счётчиками кандидатов"
)
async def catalog_categories(service: CatalogDep) -> list[CatalogCategoryOut]:
    return await service.categories()


@router.get("/catalog/fsp-categories", summary="Категории достижений ФСП со счётчиками")
async def catalog_fsp_categories(service: CatalogDep) -> list[FspCategoryOut]:
    return await service.fsp_categories()


@router.get(
    "/catalog/candidates",
    summary="Анонимные карточки: по силе профиля или по соответствию вакансии",
)
async def catalog_candidates(
    service: CatalogDep,
    category: Annotated[
        str | None, Query(max_length=40, description="специализация:грейд, например backend:middle")
    ] = None,
    specialization: Specialization | None = None,
    grade: Grade | None = None,
    work_format: WorkFormat | None = None,
    city: Annotated[
        str | None, Query(max_length=100, description="живёт в городе или готов к переезду")
    ] = None,
    skill: Skills = [],  # noqa: B006 - FastAPI копирует значение по умолчанию
    search_status: SearchStatus | None = None,
    confirmed_only: bool = False,
    fsp_only: bool = False,
    fsp_category: Slug = None,
    vacancy_id: Annotated[
        uuid.UUID | None, Query(description="сортировать по соответствию этой вакансии")
    ] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[CandidateCardOut]:
    parsed = parse_category(category) if category else None
    if category and parsed is None:
        raise UnknownCategoryError("неизвестная категория")
    filters = CatalogFilters(
        category=parsed,
        specialization=specialization,
        grade=grade,
        work_format=work_format,
        city=city,
        skills=tuple(dict.fromkeys(skill)),
        search_status=search_status,
        confirmed_only=confirmed_only,
        fsp_only=fsp_only,
        fsp_category=fsp_category,
    )
    items, next_cursor = await service.candidates(filters, cursor, limit, vacancy_id)
    return PageOut(items=items, next_cursor=next_cursor)


@router.get("/catalog/candidates/{anon_id}", summary="Анонимная карточка кандидата")
async def catalog_candidate(anon_id: uuid.UUID, service: CatalogDep) -> CandidateCardOut:
    return await service.candidate(anon_id)


async def _offer_limit(request: Request, principal: PrincipalDep) -> None:
    """Офферы компании в сутки ограничены: кандидатов не заваливают предложениями."""
    await check_rate_limit(
        request, "offer_send", key=str(principal.company_id or principal.user_id)
    )


@router.post(
    "/offers",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_offer_limit)],
    summary="Отправить оффер",
)
async def send_offer(
    data: OfferCreateIn,
    service: OffersDep,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    ] = None,
) -> EmployerOfferOut:
    return await service.send(data, idempotency_key)


@router.get("/offers", summary="Офферы компании")
async def list_offers(
    service: OffersDep,
    status_filter: Annotated[OfferStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Limit = 20,
) -> PageOut[EmployerOfferOut]:
    items, next_cursor = await service.list_offers(status_filter, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/offers/{offer_id}/withdraw", summary="Отозвать оффер")
async def withdraw_offer(offer_id: uuid.UUID, service: OffersDep) -> EmployerOfferOut:
    return await service.withdraw(offer_id)


@router.get("/offers/{offer_id}/contacts", summary="Контакты кандидата (после принятия оффера)")
async def offer_contacts(offer_id: uuid.UUID, service: OffersDep) -> OfferContactsOut:
    return await service.contacts(offer_id)
