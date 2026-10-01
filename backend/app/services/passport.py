"""Паспорт навыков: снимок профиля с подтверждёнными ФСП достижениями, подписанный Ed25519.

Кандидат выпускает паспорт осознанно (публичная ссылка), имя включается только по его выбору.
Новый паспорт отзывает предыдущий; проверка подлинности — публичная, по id.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, profile_field_context
from app.core.errors import NotFoundError
from app.core.signing import PassportSigner
from app.models import CandidateProfile, Passport
from app.repositories.audit import AuditRepository
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.fsp import CategoryRepository, FspAchievementRepository, FspLinkRepository
from app.repositories.passports import PassportRepository
from app.schemas.fsp import PassportOut, PassportVerifyOut
from app.services.access import Action, Principal, policy
from app.services.categorization import DISCIPLINES, describe
from app.services.fsp_sync import to_evidence

PAYLOAD_VERSION = 1
ISSUER = "IT Match · ФСП"


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
    ) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.signer = signer
        self.cipher = cipher
        self.passports = PassportRepository(session)

    async def active(self) -> PassportOut | None:
        profile = await self._profile()
        passport = await self.passports.active_for(profile.id)
        return to_out(passport) if passport else None

    async def issue(self, show_name: bool) -> PassportOut:
        profile = await self._profile()
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
        await self.passports.add(passport)
        await AuditRepository(self.session).record(
            "passport.issued", self.principal.user_id, "passport", passport_id
        )
        await self.session.commit()
        return to_out(passport)

    async def revoke(self) -> None:
        profile = await self._profile()
        await self.passports.revoke_all(profile.id)
        await self.session.commit()

    async def _payload(
        self, profile: CandidateProfile, passport_id: uuid.UUID, show_name: bool
    ) -> dict:
        link = await FspLinkRepository(self.session, profile.id).own()
        achievements = await FspAchievementRepository(self.session, profile.id).all()
        categories = await CategoryRepository(self.session).for_profile(profile.id)
        name = self.cipher.decrypt(
            profile.full_name_enc, profile_field_context("full_name", profile.user_id)
        )
        return {
            "version": PAYLOAD_VERSION,
            "passport_id": str(passport_id),
            "issuer": ISSUER,
            "issued_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "holder": {"name": name if show_name else None},
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
                        "summary": describe(to_evidence(a)),
                    }
                    for a in achievements
                ],
            },
            "categories": [c.title for c, _ in categories],
        }

    async def _profile(self) -> CandidateProfile:
        profile = await CandidateProfileRepository(self.session, self.principal.user_id).own()
        if profile is None:
            raise NotFoundError("profile not found")
        return profile


async def verify_passport(
    session: AsyncSession, signer: PassportSigner, passport_id: uuid.UUID
) -> PassportVerifyOut:
    """Публичная проверка: подпись валидна, ключ наш, паспорт не отозван."""
    passport = await PassportRepository(session).get(passport_id)
    if passport is None:
        raise NotFoundError("паспорт не найден")
    genuine = passport.key_id == signer.key_id and signer.verify(
        passport.payload, passport.signature
    )
    return PassportVerifyOut(
        **to_out(passport).model_dump(),
        valid=genuine and passport.revoked_at is None,
        public_key=signer.public_key_b64,
    )
