"""Общая часть выхода на контакт: сроки, статусы, снимок контактов кандидата, письма, ответы API.

Контакты кандидата раскрываются компании, только когда он принял приглашение или откликнулся
сам: в этот момент делается зашифрованный снимок имени и контактов, привязанный к записи.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, application_field_context, profile_field_context
from app.core.errors import AppError
from app.core.timeutil import as_aware
from app.models import Application, CandidateProfile, EmployerCompany
from app.models.enums import ApplicationDirection, ApplicationStatus, RecipientType
from app.repositories.applications import OPEN
from app.schemas.applications import ApplicationBase, ApplicationOut, CompanyBriefOut
from app.services.outbox import Outbox

APPLICATION_TTL = timedelta(days=14)
DECLINE_COOLDOWN = timedelta(days=30)


class ContactsRequiredError(AppError):
    status_code, code = 409, "contacts_required"

    def __init__(self) -> None:
        super().__init__("укажите в профиле хотя бы один контакт: телефон, Telegram или почту")


def effective_status(application: Application, now: datetime | None = None) -> ApplicationStatus:
    now = now or datetime.now(UTC)
    if application.status in OPEN and as_aware(application.expires_at) <= now:
        return ApplicationStatus.EXPIRED
    return application.status


def is_open(application: Application) -> bool:
    return effective_status(application) in OPEN


def contacts_available(application: Application) -> bool:
    """Компания видит контакты по принятому приглашению и по любому живому отклику."""
    if application.direction == ApplicationDirection.INVITATION:
        return application.status == ApplicationStatus.ACCEPTED
    return application.status != ApplicationStatus.WITHDRAWN


def snapshot_contacts(
    cipher: FieldCipher, profile: CandidateProfile, application: Application
) -> None:
    name = cipher.decrypt(
        profile.full_name_enc, profile_field_context("full_name", profile.user_id)
    )
    raw = cipher.decrypt(profile.contacts_enc, profile_field_context("contacts", profile.user_id))
    contacts = {k: v for k, v in (json.loads(raw) if raw else {}).items() if v}
    if not contacts:
        raise ContactsRequiredError()
    application.contact_name_enc = cipher.encrypt(
        name, application_field_context("name", application.id)
    )
    application.contacts_enc = cipher.encrypt(
        json.dumps(contacts), application_field_context("contacts", application.id)
    )


def read_contacts(cipher: FieldCipher, application: Application) -> tuple[str | None, dict]:
    name = cipher.decrypt(
        application.contact_name_enc, application_field_context("name", application.id)
    )
    raw = cipher.decrypt(
        application.contacts_enc, application_field_context("contacts", application.id)
    )
    return name, json.loads(raw) if raw else {}


def notify(
    session: AsyncSession,
    cipher: FieldCipher,
    kind: str,
    application: Application,
    to_company: bool,
    **extra: object,
) -> None:
    """Письмо другой стороне: только название компании и должность, без данных кандидата."""
    recipient = (
        (RecipientType.COMPANY, application.company_id)
        if to_company
        else (RecipientType.PROFILE, application.profile_id)
    )
    payload = {"company": application.company_name, "title": application.title, **extra}
    Outbox(session, cipher).enqueue(kind, recipient[0], recipient[1], payload)


def base_fields(application: Application) -> dict:
    return {
        field: getattr(application, field)
        for field in ApplicationBase.model_fields
        if field not in ("status", "expires_at", "viewed_at", "responded_at", "created_at")
    } | {
        "status": effective_status(application),
        "expires_at": as_aware(application.expires_at),
        "viewed_at": as_aware(application.viewed_at) if application.viewed_at else None,
        "responded_at": as_aware(application.responded_at) if application.responded_at else None,
        "created_at": as_aware(application.created_at),
    }


async def companies(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, EmployerCompany]:
    if not ids:
        return {}
    rows = await session.execute(select(EmployerCompany).where(EmployerCompany.id.in_(ids)))
    return {c.id: c for c in rows.scalars()}


def brief(company: EmployerCompany | None, fallback_name: str) -> CompanyBriefOut:
    if company is None:
        return CompanyBriefOut(name=fallback_name, industry=None, website=None, description="")
    return CompanyBriefOut(
        name=company.name,
        industry=company.industry,
        website=company.website,
        description=company.description or "",
    )


def candidate_out(application: Application, company: EmployerCompany | None) -> ApplicationOut:
    """Способ связи по отклику кандидат видит, когда компания приняла отклик."""
    visible = (
        application.direction == ApplicationDirection.INVITATION
        or application.status == ApplicationStatus.ACCEPTED
    )
    return ApplicationOut(
        **base_fields(application),
        company=brief(company, application.company_name),
        contact_method=application.contact_method if visible else None,
    )
