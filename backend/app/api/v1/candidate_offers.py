"""Кандидат: входящие офферы, принятие и отклонение."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CipherDep, PrincipalDep, SessionDep
from app.models.enums import OfferStatus
from app.schemas.catalog import OfferDeclineIn, OfferOut
from app.schemas.common import PageOut
from app.services.offers import CandidateOfferService

router = APIRouter(prefix="/candidate", tags=["candidate"])


def _service(
    session: SessionDep, principal: PrincipalDep, cipher: CipherDep
) -> CandidateOfferService:
    return CandidateOfferService(session, principal, cipher)


ServiceDep = Annotated[CandidateOfferService, Depends(_service)]


@router.get("/offers", summary="Входящие офферы")
async def list_offers(
    service: ServiceDep,
    status_filter: Annotated[OfferStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PageOut[OfferOut]:
    items, next_cursor = await service.list_offers(status_filter, cursor, limit)
    return PageOut(items=items, next_cursor=next_cursor)


@router.post("/offers/{offer_id}/accept", summary="Принять оффер (контакты передаются компании)")
async def accept_offer(offer_id: uuid.UUID, service: ServiceDep) -> OfferOut:
    return await service.accept(offer_id)


@router.post("/offers/{offer_id}/decline", summary="Отклонить оффер")
async def decline_offer(offer_id: uuid.UUID, data: OfferDeclineIn, service: ServiceDep) -> OfferOut:
    return await service.decline(offer_id, data.reason)
