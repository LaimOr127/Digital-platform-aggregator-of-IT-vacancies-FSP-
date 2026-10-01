"""Паспорт навыков: снимок профиля с подтверждёнными ФСП достижениями, подписанный Ed25519.

Кандидат выпускает паспорт осознанно (публичная ссылка). Имя — только по его выбору и из ФСП
(подтверждённое), иначе помечается как заявленное. В анонимном паспорте достижения обобщены.
Новый паспорт, отвязка ФСП и изменение данных ФСП отзывают действующий. Срок действия — год.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import FieldCipher, profile_field_context
from app.core.errors import ConflictError, NotFoundError
from app.core.signing import PassportSigner
from app.db.session import SYSTEM_ROLE, set_rls_context
from app.models import CandidateProfile, FspLink, Passport
from app.repositories.audit import AuditRepository
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.fsp import CategoryRepository, FspAchievementRepository, FspLinkRepository
from app.repositories.passports import PassportRepository
from app.schemas.fsp import PassportCheck, PassportOut, PassportVerifyOut
from app.services.access import Action, Principal, policy
from app.services.categorization import DISCIPLINES, describe, describe_anonymous
from app.services.fsp_sync import to_evidence

PAYLOAD_VERSION = 2
ISSUER = "IT Match · ФСП"
VALIDITY = timedelta(days=365)


def to_out(passport: Passport) -> PassportOut:
    return PassportOut(
        id=passport.id,
        issued_at=passport.created_at,
        revoked_at=passport.revoked_at,
        payload=passport.payload,
        signature=passport.signature,
        key_id=passport.key_id,
    )


class PassportService:
    def __init__(
        self,
        session: AsyncSession,
        principal: Principal,
        signer: PassportSigner,
        cipher: FieldCipher,
        settings: Settings,
    ) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.signer = signer
        self.cipher = cipher
        self.demo = settings.fsp_demo_codes
        self.profiles = CandidateProfileRepository(session, principal.user_id)
        self.passports = PassportRepository(session)

    async def active(self) -> PassportOut | None:
        profile = await self.profiles.own_or_404()
        passport = await self.passports.active_for(profile.id)
        return to_out(passport) if passport else None

    async def issue(self, show_name: bool) -> PassportOut:
        profile = await self.profiles.own_or_404(for_update=True)
        await self.passports.revoke_all(profile.id)
        passport_id = uuid.uuid4()
        payload = await self._payload(profile, passport_id, show_name)
        passport = Passport(
            id=passport_id,
            profile_id=profile.id,
            payload=payload,
            signature=self.signer.sign(payload),
            key_id=self.signer.key_id,
        )
        try:
            await self.passports.add(passport)
        except IntegrityError as exc:  # параллельный выпуск: действующий паспорт только один
            await self.session.rollback()
            raise ConflictError("паспорт уже выпускается — обновите страницу") from exc
        await AuditRepository(self.session).record(
            "passport.issued", self.principal.user_id, "passport", passport_id
        )
        await self.session.commit()
        return to_out(passport)

    async def revoke(self) -> None:
        profile = await self.profiles.own_or_404(for_update=True)
        await self.passports.revoke_all(profile.id)
        await self.session.commit()

    async def _payload(
        self, profile: CandidateProfile, passport_id: uuid.UUID, show_name: bool
    ) -> dict:
        link = await FspLinkRepository(self.session, profile.id).own()
        achievements = await FspAchievementRepository(self.session, profile.id).all()
        categories = await CategoryRepository(self.session).for_profile(profile.id)
        summarize = describe if show_name else describe_anonymous
        issued = datetime.now(UTC)
        return {
            "version": PAYLOAD_VERSION,
            "passport_id": str(passport_id),
            "issuer": f"{ISSUER} (демо-стенд)" if self.demo else ISSUER,
            "demo": self.demo,
            "issued_at": issued.isoformat(timespec="seconds"),
            "expires_at": (issued + VALIDITY).isoformat(timespec="seconds"),
            "holder": self._holder(profile, link) if show_name else {"name": None, "source": None},
            # заявлено кандидатом: подпись подтверждает неизменность, а не достоверность
            "title": profile.title,
            "grade": profile.grade.value if profile.grade else None,
            "skills": sorted(s.name for s in profile.skills),
            "verification_tier": profile.verification_tier.value,
            "fsp": {
                "athlete_id": link.athlete_id if link and show_name else None,
                "rank": link.rank if link else None,
                "achievements": [
                    {
                        "discipline": DISCIPLINES.get(a.discipline, a.discipline),
                        "summary": summarize(to_evidence(a)),
                    }
                    for a in achievements
                ],
            },
            "categories": [c.title for c, _ in categories],
        }

    def _holder(self, profile: CandidateProfile, link: FspLink | None) -> dict:
        """Имя из ФСП подтверждено федерацией; без привязки — имя из профиля (заявлено)."""
        if link and link.full_name:
            return {"name": link.full_name, "source": "fsp"}
        name = self.cipher.decrypt(
            profile.full_name_enc, profile_field_context("full_name", profile.user_id)
        )
        return {"name": name, "source": "self"}


def _check(passport: Passport, signer: PassportSigner) -> PassportCheck:
    if passport.revoked_at is not None:
        return "revoked"
    if passport.key_id != signer.key_id:
        return "unknown_key"
    if not signer.verify(passport.payload, passport.signature):
        return "bad_signature"
    expires = passport.payload.get("expires_at")
    if expires and datetime.fromisoformat(expires) <= datetime.now(UTC):
        return "expired"
    return "valid"


async def verify_passport(
    session: AsyncSession, signer: PassportSigner, passport_id: uuid.UUID
) -> PassportVerifyOut:
    """Публичная проверка по id. Читает в контексте system (RLS отдаёт паспорта только
    владельцам); по отозванному паспорту возвращается только факт отзыва, без данных."""
    await set_rls_context(session, None, SYSTEM_ROLE)
    passport = await PassportRepository(session).get(passport_id)
    if passport is None:
        raise NotFoundError("паспорт не найден")
    status = _check(passport, signer)
    hidden = status == "revoked"
    return PassportVerifyOut(
        id=passport.id,
        issued_at=passport.created_at,
        revoked_at=passport.revoked_at,
        status=status,
        valid=status == "valid",
        payload=None if hidden else passport.payload,
        signature=None if hidden else passport.signature,
        key_id=None if hidden else passport.key_id,
        public_key=signer.public_key_b64,
    )
