import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, or_, update
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

    async def declined_since(self, profile_id: uuid.UUID, since: datetime) -> Offer | None:
        """Последний отказ кандидата этой компании после since (пауза перед повторным оффером)."""
        stmt = (
            self._select()
            .where(
                Offer.profile_id == profile_id,
                Offer.status == OfferStatus.DECLINED,
                Offer.responded_at >= since,
            )
            .order_by(Offer.responded_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

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


def status_condition(status: OfferStatus, now: datetime) -> ColumnElement[bool]:
    """Фильтр по статусу так, как его видит пользователь: просроченный «sent» — уже «истёк»,
    даже если worker ещё не отметил его в БД."""
    overdue = and_(Offer.status == OfferStatus.SENT, Offer.expires_at <= now)
    if status == OfferStatus.SENT:
        return and_(Offer.status == OfferStatus.SENT, Offer.expires_at > now)
    if status == OfferStatus.EXPIRED:
        return or_(Offer.status == OfferStatus.EXPIRED, overdue)
    return Offer.status == status


async def expire_pair(
    session: AsyncSession, vacancy_id: uuid.UUID, profile_id: uuid.UUID, now: datetime
) -> None:
    """Просроченный оффер этой пары освобождает место для нового, не дожидаясь worker."""
    await session.execute(
        update(Offer)
        .where(
            Offer.vacancy_id == vacancy_id,
            Offer.profile_id == profile_id,
            Offer.status == OfferStatus.SENT,
            Offer.expires_at <= now,
        )
        .values(status=OfferStatus.EXPIRED)
    )


async def withdraw_pending_for_company(session: AsyncSession, company_id: uuid.UUID) -> int:
    """Блокировка компании: её неотвеченные офферы отзываются — контакты ей больше не уйдут."""
    return await _withdraw_pending(session, Offer.company_id == company_id)


async def withdraw_pending_for_vacancy(session: AsyncSession, vacancy_id: uuid.UUID) -> int:
    """Блокировка вакансии: неотвеченные офферы по ней отзываются."""
    return await _withdraw_pending(session, Offer.vacancy_id == vacancy_id)


async def _withdraw_pending(session: AsyncSession, scope: ColumnElement[bool]) -> int:
    result = await session.execute(
        update(Offer)
        .where(scope, Offer.status == OfferStatus.SENT)
        .values(status=OfferStatus.WITHDRAWN)
    )
    return result.rowcount  # type: ignore[attr-defined]
