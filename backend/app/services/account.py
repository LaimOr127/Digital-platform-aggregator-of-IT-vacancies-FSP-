"""Регистрация и операции с аккаунтом по почте: подтверждение, повтор письма, сброс пароля.

Ответ никогда не выдаёт, зарегистрирован ли адрес: регистрация, повтор письма и сброс
пароля всегда отвечают «проверьте почту», а письмо получает только владелец адреса.
Занятый адрес получает письмо «аккаунт уже есть» (или повторную ссылку, если почта ещё
не подтверждена); хеш пароля считается в обоих случаях — время ответа одинаковое.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import FieldCipher, profile_field_context
from app.core.errors import ForbiddenError, InvalidLinkError, NotFoundError, WrongPasswordError
from app.core.security import hash_password_async, verify_password_async
from app.db.session import set_rls_context
from app.models import CandidateProfile, CompanyMember, EmployerCompany, User
from app.models.enums import (
    CompanyStatus,
    EmailTokenPurpose,
    MemberRole,
    RecipientType,
    UserRole,
)
from app.repositories.audit import AuditRepository
from app.repositories.users import RefreshTokenRepository, UserRepository
from app.schemas.auth import CandidateRegisterIn, EmployerRegisterIn
from app.services import email_tokens
from app.services.outbox import Outbox


class AccountService:
    def __init__(self, session: AsyncSession, cipher: FieldCipher) -> None:
        self.session = session
        self.cipher = cipher
        self.users = UserRepository(session)
        self.audit = AuditRepository(session)
        self.outbox = Outbox(session, cipher)

    # --- регистрация ---------------------------------------------------------------------
    async def register_candidate(self, data: CandidateRegisterIn) -> None:
        user = await self._register(data.email, data.password, UserRole.CANDIDATE)
        if user is not None:
            name_enc = self.cipher.encrypt(
                data.full_name, profile_field_context("full_name", user.id)
            )
            self.session.add(CandidateProfile(user_id=user.id, full_name_enc=name_enc))
        await self._commit_registration(user)

    async def register_employer(self, data: EmployerRegisterIn) -> None:
        user = await self._register(data.email, data.password, UserRole.EMPLOYER)
        if user is not None:
            # постмодерация: компания работает сразу, модератор может заблокировать её позже
            status = (
                CompanyStatus.PENDING
                if get_settings().company_premoderation
                else CompanyStatus.APPROVED
            )
            company = EmployerCompany(name=data.company_name, inn=data.inn, status=status)
            self.session.add(company)
            await self.session.flush()
            self.session.add(
                CompanyMember(company_id=company.id, user_id=user.id, role=MemberRole.OWNER)
            )
        await self._commit_registration(user)

    async def _register(self, email: str, password: str, role: UserRole) -> User | None:
        """Новый пользователь или None, если адрес занят (владельцу уйдёт письмо)."""
        password_hash = await hash_password_async(password)  # и для занятого: одинаковое время
        existing = await self.users.by_email(email)
        if existing is not None:
            await self._notify_existing(existing)
            return None
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            consent_at=datetime.now(UTC),  # без согласия запрос не проходит валидацию
        )
        try:
            user = await self.users.add(user)
        except IntegrityError:  # гонка двух регистраций одного адреса: письмо уйдёт победителю
            await self.session.rollback()
            return None
        await set_rls_context(self.session, user.id, user.role)
        return user

    async def _commit_registration(self, user: User | None) -> None:
        if user is not None:
            await self._send_link(user.id, EmailTokenPurpose.VERIFY)
            await self.audit.record("auth.register", user.id, "user", user.id, {"role": user.role})
        await self.session.commit()

    async def _notify_existing(self, user: User) -> None:
        if not user.is_active:
            return
        if user.email_verified:
            self.outbox.enqueue("account_exists", RecipientType.USER, user.id)
        else:
            await self._send_link(user.id, EmailTokenPurpose.VERIFY)

    # --- подтверждение почты ---------------------------------------------------------------
    async def resend_verification(self, email: str) -> None:
        user = await self.users.by_email(email)
        if user is not None and user.is_active and not user.email_verified:
            await self._send_link(user.id, EmailTokenPurpose.VERIFY)
            await self.session.commit()

    async def verify_email(self, token: str) -> None:
        user = await self._consume(token, EmailTokenPurpose.VERIFY)
        user.email_verified = True
        await self.audit.record("auth.email_verified", user.id)
        await self.session.commit()

    async def confirm_email_by_operator(self, email: str) -> None:
        """Только для CLI: оператор сервера подтверждает адрес, если письмо не дошло (стенд без
        SMTP, письмо в спаме). Пользователь регистрируется сам — пароль оператор не знает."""
        user = await self.users.by_email(email)
        if user is None:
            raise NotFoundError("пользователь с таким email не найден")
        user.email_verified = True
        await self.audit.record("auth.email_confirmed_by_operator", None, "user", user.id)
        await self.session.commit()

    # --- сброс пароля ------------------------------------------------------------------------
    async def forgot_password(self, email: str) -> None:
        user = await self.users.by_email(email)
        if user is not None and user.is_active:
            await self._send_link(user.id, EmailTokenPurpose.RESET)
            await self.session.commit()

    async def reset_password(self, token: str, password: str) -> None:
        """Новый пароль; все сессии завершаются. Ссылка из письма подтверждает и почту."""
        user = await self._consume(token, EmailTokenPurpose.RESET)
        user.password_hash = await hash_password_async(password)
        user.email_verified = True
        await RefreshTokenRepository(self.session).revoke_all_for_user(user.id)
        await self.audit.record("auth.password_reset", user.id)
        await self.session.commit()

    # --- удаление аккаунта (152-ФЗ) -------------------------------------------------------------
    async def delete_candidate(self, user_id: uuid.UUID, password: str) -> None:
        """Отзыв согласия: аккаунт кандидата удаляется со всеми данными (профиль, ФСП, паспорт,
        собеседования, офферы — каскадом в БД). В журнале остаётся только факт удаления."""
        user = await self.users.get(user_id)
        if user is None or user.role != UserRole.CANDIDATE:
            raise ForbiddenError("аккаунт компании удаляется через поддержку")
        if not await verify_password_async(user.password_hash, password):
            raise WrongPasswordError()
        await self.audit.record("account.deleted", None, "user", user.id, {"role": user.role})
        await self.session.delete(user)
        await self.session.commit()

    # --- общее ---------------------------------------------------------------------------------
    async def _send_link(self, user_id: uuid.UUID, purpose: EmailTokenPurpose) -> None:
        token = await email_tokens.issue(self.session, user_id, purpose)
        kind = "verify_email" if purpose == EmailTokenPurpose.VERIFY else "password_reset"
        self.outbox.enqueue(kind, RecipientType.USER, user_id, {"token": token})

    async def _consume(self, token: str, purpose: EmailTokenPurpose) -> User:
        user_id = await email_tokens.consume(self.session, token, purpose)
        user = await self.users.get(user_id) if user_id else None
        if user is None or not user.is_active:
            await self.session.rollback()
            raise InvalidLinkError("ссылка недействительна или устарела — запросите новую")
        return user
