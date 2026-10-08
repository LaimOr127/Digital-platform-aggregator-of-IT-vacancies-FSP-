"""Черновик профиля из файла резюме: текст -> правила (+ ИИ по согласию) -> справочник навыков.

Файл не сохраняется. В аудит пишется только факт разбора и использовался ли ИИ.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ServiceUnavailableError
from app.integrations.ai.base import AiUnavailableError
from app.repositories.audit import AuditRepository
from app.schemas.candidate import Contacts
from app.schemas.profile_import import ProfileDraftOut
from app.services.access import Action, Principal, policy
from app.services.profile_import import grade_for_experience, skills_out
from app.services.resume import rules
from app.services.resume.extract import extract_text
from app.services.resume.llm import AiProfile, AiResumeParser
from app.services.skill_matching import SkillDictionary
from app.services.specializations import ROLES, SOFT_SKILLS, specialization_for

_EXTRACT_TIMEOUT = 15  # секунд: «тяжёлый» PDF не держит запрос бесконечно


class ResumeImportService:
    def __init__(
        self, session: AsyncSession, principal: Principal, ai: AiResumeParser | None
    ) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.principal = principal
        self.ai = ai

    async def draft(self, data: bytes, use_ai: bool) -> ProfileDraftOut:
        try:
            text = await asyncio.wait_for(asyncio.to_thread(extract_text, data), _EXTRACT_TIMEOUT)
        except TimeoutError as exc:
            raise ServiceUnavailableError("файл обрабатывается слишком долго") from exc
        dictionary = await SkillDictionary.load(self.session)
        parsed = rules.parse(text)
        draft = build_resume_draft(parsed, dictionary.find_in_text(text), dictionary)
        ai_used = False
        if use_ai and self.ai is not None:
            try:
                ai_profile = await self.ai.parse(rules.mask_contacts(text))
                merge_ai(draft, ai_profile, dictionary, self.ai.label)
                ai_used = True
            except AiUnavailableError:
                draft.notes.append("ИИ сейчас недоступен — поля заполнены алгоритмом")
        await AuditRepository(self.session).record(
            "profile.resume_parsed", self.principal.user_id, meta={"ai": ai_used}
        )
        await self.session.commit()
        return draft


def build_resume_draft(
    parsed: rules.ParsedResume, slugs: list[str], dictionary: SkillDictionary
) -> ProfileDraftOut:
    grade = parsed.grade or grade_for_experience(parsed.experience_years)
    notes = ["Поля заполнены алгоритмом по тексту резюме — проверьте перед сохранением"]
    if parsed.grade is None and grade:
        notes.append(f"Грейд предложен по стажу ({parsed.experience_years} г.)")
    # строка «стек: …» — навыки из справочника, остальное станет своими навыками
    labeled = dictionary.match_names(parsed.stack)
    skills = list(dict.fromkeys([*labeled.slugs, *slugs]))
    return ProfileDraftOut(
        source="resume",
        full_name=parsed.full_name,
        title=parsed.title,
        about=parsed.about,
        grade=grade,
        specialization=specialization_for(set(skills))[0],
        work_formats=parsed.work_formats,
        relocation=parsed.relocation,
        education=parsed.education,
        city=parsed.city,
        salary_min=parsed.salary_min,
        experience_years=parsed.experience_years,
        roles=parsed.roles,
        soft_skills=[*parsed.soft_skills, *parsed.extra_soft_skills],
        contacts=Contacts(email=parsed.email, phone=parsed.phone, telegram=parsed.telegram),
        skills=skills_out(dictionary, skills),
        unknown_skills=labeled.unknown,
        notes=notes,
    )


def merge_ai(
    draft: ProfileDraftOut, ai: AiProfile, dictionary: SkillDictionary, label: str
) -> None:
    """ИИ уточняет смысловые поля; контакты — только локальные (в ИИ они не передавались)."""
    fields = (
        "full_name",
        "title",
        "about",
        "city",
        "work_formats",
        "education",
        "salary_min",
        "experience_years",
    )
    for name in fields:
        value = getattr(ai, name)
        if value:
            setattr(draft, name, value)
    draft.grade = ai.grade or grade_for_experience(ai.experience_years) or draft.grade
    # роли и софт-скиллы — объединение: ИИ мог увидеть то, что правила пропустили
    draft.roles = list(dict.fromkeys([*draft.roles, *(r for r in ai.roles if r in ROLES)]))
    draft.soft_skills = list(
        dict.fromkeys([*draft.soft_skills, *(s for s in ai.soft_skills if s in SOFT_SKILLS)])
    )
    matched = dictionary.match_names(ai.skills)
    known = [s.slug for s in draft.skills]
    draft.skills = skills_out(dictionary, known + [s for s in matched.slugs if s not in known])
    draft.unknown_skills = list(dict.fromkeys([*draft.unknown_skills, *matched.unknown]))
    draft.specialization = specialization_for({s.slug for s in draft.skills})[0]
    draft.notes = [
        f"Поля заполнены ИИ ({label}) — проверьте перед сохранением",
        "Контакты найдены на сервере и в ИИ-сервис не передавались",
    ]
