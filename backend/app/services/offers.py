"""Офферы: работодатель предлагает -> кандидат принимает/отклоняет -> контакты раскрываются.

Оффер — снимок вакансии и вилки. При принятии кандидат передаёт снимок своих контактов,
зашифрованный с привязкой к офферу; работодатель видит только его, каждый просмотр в журнале.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, offer_field_context, profile_field_context
from app.core.errors import ConflictError, ForbiddenError, InvalidStateError, NotFoundError
from app.core.timeutil import as_aware
from app.models import Offer
from app.models.enums import OfferStatus, VacancyStatus
from app.repositories.audit import AuditRepository
from app.repositories.base import Page
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.companies import CompanyRepository
from app.repositories.offers import (
    CandidateOfferRepository,
    CompanyOfferRepository,
    expire_pair,
    status_condition,
)
from app.repositories.vacancies import VacancyRepository
from app.schemas.catalog import EmployerOfferOut, OfferContactsOut, OfferCreateIn, OfferOut
from app.services.access import Action, Principal, policy
from app.services.catalog import build_cards

OFFER_TTL = timedelta(days=7)
# после отказа кандидата компания не может сразу предложить снова (честный найм, без спама)
DECLINE_COOLDOWN = timedelta(days=30)


def effective_status(offer: Offer) -> OfferStatus:
    """Срок ответа истёк, а worker ещё не отметил — показываем как истёкший."""
    overdue = as_aware(offer.expires_at) <= datetime.now(UTC)
    return OfferStatus.EXPIRED if offer.status == OfferStatus.SENT and overdue else offer.status


def to_out(offer: Offer) -> OfferOut:
    data = {f: getattr(offer, f) for f in OfferOut.model_fields if f != "status"}
    return OfferOut(**data, status=effective_status(offer))


class EmployerOfferService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.COMPANY_READ_OWN)
        if principal.company_id is None:  # исключено правилом выше; явная проверка для типов
            raise ForbiddenError("no company")
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.company_id: uuid.UUID = principal.company_id
        self.offers = CompanyOfferRepository(session, self.company_id)
        self.catalog = CatalogRepository(session)
        self.audit = AuditRepository(session)

    async def send(self, data: OfferCreateIn, idempotency_key: str | None) -> EmployerOfferOut:
        policy.ensure(self.principal, Action.OFFER_SEND)
        if idempotency_key and (existing := await self.offers.by_idempotency_key(idempotency_key)):
            return await self._replay(existing, data)
        vacancy = await VacancyRepository(self.session, self.company_id).get_or_404(data.vacancy_id)
        if vacancy.status != VacancyStatus.ACTIVE or (
            vacancy.expires_at and as_aware(vacancy.expires_at) <= datetime.now(UTC)
        ):
            raise InvalidStateError("оффер отправляется только по опубликованной вакансии")
        profile = await self.catalog.by_anon_id(data.anon_id)
        if profile is None:
            raise NotFoundError("кандидат не найден или скрыл профиль")
        now = datetime.now(UTC)
        if declined := await self.offers.declined_since(profile.id, now - DECLINE_COOLDOWN):
            retry = as_aware(declined.responded_at or now) + DECLINE_COOLDOWN
            raise ConflictError(f"кандидат отклонил ваш оффер — повторно можно с {retry:%d.%m.%Y}")
        await expire_pair(self.session, vacancy.id, profile.id, now)
        company = await CompanyRepository(self.session).get_or_404(self.company_id)
        offer = Offer(
            company_id=self.company_id,
            vacancy_id=vacancy.id,
            profile_id=profile.id,
            created_by=self.principal.user_id,
            company_name=company.name,
            vacancy_title=vacancy.title,
            grade=vacancy.grade,
            work_format=vacancy.work_format,
            city=vacancy.city,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            message=data.message.strip(),
            idempotency_key=idempotency_key,
            expires_at=datetime.now(UTC) + OFFER_TTL,
        )
        try:
            await self.offers.add(offer)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "кандидату уже отправлен оффер на эту вакансию — дождитесь ответа"
            ) from exc
        await self.audit.record("offer.sent", self.principal.user_id, "offer", offer.id)
        await self.session.commit()
        return (await self._with_cards([offer]))[0]

    async def list_offers(
        self, status: OfferStatus | None, cursor: str | None, limit: int
    ) -> tuple[list[EmployerOfferOut], str | None]:
        conditions = [status_condition(status, datetime.now(UTC))] if status else []
        page: Page[Offer] = await self.offers.list_page(*conditions, cursor=cursor, limit=limit)
        return await self._with_cards(page.items), page.next_cursor

    async def withdraw(self, offer_id: uuid.UUID) -> EmployerOfferOut:
        offer = await self._own(offer_id, lock=True)
        if effective_status(offer) != OfferStatus.SENT:
            raise InvalidStateError("отозвать можно только оффер, ожидающий ответа")
        offer.status = OfferStatus.WITHDRAWN
        await self.audit.record("offer.withdrawn", self.principal.user_id, "offer", offer.id)
        await self.session.commit()
        return (await self._with_cards([offer]))[0]

    async def contacts(self, offer_id: uuid.UUID) -> OfferContactsOut:
        """Контакты — только по принятому офферу; каждое раскрытие пишется в журнал."""
        offer = await self._own(offer_id)
        if offer.status != OfferStatus.ACCEPTED:
            raise ForbiddenError("контакты доступны после того, как кандидат примет оффер")
        name = self.cipher.decrypt(offer.contact_name_enc, offer_field_context("name", offer.id))
        raw = self.cipher.decrypt(offer.contacts_enc, offer_field_context("contacts", offer.id))
        contacts = json.loads(raw) if raw else {}
        await self.offers.log_reveal(offer.id, self.principal.user_id)
        await self.audit.record(
            "offer.contacts_revealed", self.principal.user_id, "offer", offer.id
        )
        await self.session.commit()
        return OfferContactsOut(
            full_name=name,
            phone=contacts.get("phone"),
            telegram=contacts.get("telegram"),
            email=contacts.get("email"),
        )

    async def _own(self, offer_id: uuid.UUID, lock: bool = False) -> Offer:
        offer = await (self.offers.lock_or_404 if lock else self.offers.get_or_404)(offer_id)
        policy.ensure(self.principal, Action.OFFER_MANAGE, offer)
        return offer

    async def _replay(self, existing: Offer, data: OfferCreateIn) -> EmployerOfferOut:
        """Повтор с тем же ключом возвращает тот же оффер; ключ от другого оффера — ошибка."""
        profile = await self.catalog.by_anon_id(data.anon_id)
        same = (
            existing.vacancy_id == data.vacancy_id
            and profile is not None
            and existing.profile_id == profile.id
        )
        if not same:
            raise ConflictError("Idempotency-Key уже использован для другого оффера")
        return (await self._with_cards([existing]))[0]

    async def _with_cards(self, offers: list[Offer]) -> list[EmployerOfferOut]:
        profiles = await self.catalog.by_ids(list({o.profile_id for o in offers}))
        cards = dict(
            zip([p.id for p in profiles], await build_cards(self.catalog, profiles), strict=True)
        )
        return [
            EmployerOfferOut(**to_out(o).model_dump(), candidate=cards.get(o.profile_id))
            for o in offers
        ]


class CandidateOfferService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.OFFER_RESPOND)
        self.session = session
        self.principal = principal
        self.cipher = cipher
        self.profiles = CandidateProfileRepository(session, principal.user_id)
        self.audit = AuditRepository(session)

    async def list_offers(
        self, status: OfferStatus | None, cursor: str | None, limit: int
    ) -> tuple[list[OfferOut], str | None]:
        profile = await self.profiles.own_or_404()
        conditions = [status_condition(status, datetime.now(UTC))] if status else []
        page = await CandidateOfferRepository(self.session, profile.id).list_page(
            *conditions, cursor=cursor, limit=limit
        )
        return [to_out(o) for o in page.items], page.next_cursor

    async def accept(self, offer_id: uuid.UUID) -> OfferOut:
        profile = await self.profiles.own_or_404(for_update=True)
        offer = await self._pending(profile.id, offer_id)
        name = self.cipher.decrypt(
            profile.full_name_enc, profile_field_context("full_name", profile.user_id)
        )
        contacts = self.cipher.decrypt(
            profile.contacts_enc, profile_field_context("contacts", profile.user_id)
        )
        offer.contact_name_enc = self.cipher.encrypt(name, offer_field_context("name", offer.id))
        offer.contacts_enc = self.cipher.encrypt(
            contacts or "{}", offer_field_context("contacts", offer.id)
        )
        return await self._respond(offer, OfferStatus.ACCEPTED, "offer.accepted")

    async def decline(self, offer_id: uuid.UUID, reason: str) -> OfferOut:
        profile = await self.profiles.own_or_404(for_update=True)
        offer = await self._pending(profile.id, offer_id)
        offer.decline_reason = reason.strip() or None
        return await self._respond(offer, OfferStatus.DECLINED, "offer.declined")

    async def _pending(self, profile_id: uuid.UUID, offer_id: uuid.UUID) -> Offer:
        offer = await CandidateOfferRepository(self.session, profile_id).lock_or_404(offer_id)
        if effective_status(offer) != OfferStatus.SENT:
            raise InvalidStateError("на этот оффер уже нельзя ответить")
        return offer

    async def _respond(self, offer: Offer, status: OfferStatus, action: str) -> OfferOut:
        offer.status = status
        offer.responded_at = datetime.now(UTC)
        await self.audit.record(action, self.principal.user_id, "offer", offer.id)
        await self.session.commit()
        return to_out(offer)
