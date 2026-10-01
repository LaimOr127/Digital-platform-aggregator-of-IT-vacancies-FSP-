import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContactReveal, Offer
from app.models.enums import OfferStatus
from app.repositories.base import BaseRepository


class CompanyOfferRepository(BaseRepository[Offer]):
    """Офферы одной компании (тенант)."""

    model = Offer

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        super().__init__(session)
        self.company_id = company_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(Offer.company_id == self.company_id)

    async def by_idempotency_key(self, key: str) -> Offer | None:
        return await self.first(Offer.idempotency_key == key)

    async def log_reveal(self, offer_id: uuid.UUID, viewer_id: uuid.UUID) -> None:
        self.session.add(
            ContactReveal(offer_id=offer_id, viewer_id=viewer_id, created_at=datetime.now(UTC))
        )


class CandidateOfferRepository(BaseRepository[Offer]):
    """Офферы, адресованные одному профилю кандидата."""

    model = Offer

    def __init__(self, session: AsyncSession, profile_id: uuid.UUID) -> None:
        super().__init__(session)
        self.profile_id = profile_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(Offer.profile_id == self.profile_id)


async def expire_overdue(session: AsyncSession, now: datetime) -> int:
    """Неотвеченные офферы с истёкшим сроком -> expired (worker, контекст system)."""
    result = await session.execute(
        update(Offer)
        .where(Offer.status == OfferStatus.SENT, Offer.expires_at < now)
        .values(status=OfferStatus.EXPIRED)
    )
    return result.rowcount  # type: ignore[attr-defined]
