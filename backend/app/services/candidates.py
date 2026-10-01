"""Профиль кандидата: чтение и изменение только своего; имя и контакты шифруются."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import FieldCipher, profile_field_context
from app.core.logging import get_logger
from app.models import CandidateProfile
from app.repositories.candidates import CandidateProfileRepository, SkillRepository
from app.schemas.candidate import Contacts, ProfileOut, ProfileUpdateIn
from app.schemas.common import SkillOut
from app.services.access import Action, Principal, policy
from app.services.common import apply_fields, apply_salary, resolve_skills

log = get_logger(__name__)
_PLAIN_FIELDS = ("title", "about", "grade", "work_format", "city", "is_hidden")


class CandidateService:
    def __init__(self, session: AsyncSession, principal: Principal, cipher: FieldCipher) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.cipher = cipher
        self.profiles = CandidateProfileRepository(session, owner_id=principal.user_id)
        self.skills = SkillRepository(session)

    async def get_profile(self) -> ProfileOut:
        return self._to_out(await self.profiles.own_or_404())

    async def update_profile(self, data: ProfileUpdateIn) -> ProfileOut:
        profile = await self.profiles.own_or_404()
        changes = data.model_dump(exclude_unset=True)
        apply_fields(profile, changes, _PLAIN_FIELDS)
        apply_salary(profile, changes)
        if "full_name" in changes:
            profile.full_name_enc = self._encrypt(profile, "full_name", data.full_name)
        if "contacts" in changes:
            contacts = data.contacts or Contacts()
            profile.contacts_enc = self._encrypt(profile, "contacts", contacts.model_dump_json())
        if data.skills is not None:
            profile.skills = await resolve_skills(self.skills, data.skills)
        await self.session.commit()
        return self._to_out(profile)

    def _encrypt(self, p: CandidateProfile, field: str, value: str | None) -> str | None:
        return self.cipher.encrypt(value, profile_field_context(field, p.user_id))

    def _decrypt(self, p: CandidateProfile, field: str, token: str | None) -> str | None:
        """Повреждённое значение (сменили ключ, подмена в БД) не ломает профиль навсегда:
        поле отдаётся пустым, кандидат может заполнить его заново; событие пишется в лог."""
        try:
            return self.cipher.decrypt(token, profile_field_context(field, p.user_id))
        except ValueError:
            log.warning("undecryptable field %s in profile %s", field, p.id)
            return None

    def _to_out(self, p: CandidateProfile) -> ProfileOut:
        contacts_raw = self._decrypt(p, "contacts", p.contacts_enc)
        return ProfileOut(
            anon_id=p.anon_id,
            full_name=self._decrypt(p, "full_name", p.full_name_enc),
            # сохранённые данные уже прошли валидацию при записи; правила могли ужесточиться
            contacts=Contacts.model_construct(**json.loads(contacts_raw))
            if contacts_raw
            else Contacts(),
            title=p.title,
            about=p.about,
            grade=p.grade,
            work_format=p.work_format,
            city=p.city,
            salary_min=p.salary_min,
            salary_max=p.salary_max,
            verification_tier=p.verification_tier,
            is_hidden=p.is_hidden,
            skills=[SkillOut.model_validate(s) for s in p.skills],
        )
