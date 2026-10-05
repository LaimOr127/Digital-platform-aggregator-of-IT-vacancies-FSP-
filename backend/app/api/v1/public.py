import uuid

from fastapi import APIRouter, Response

from app.api.deps import SessionDep, SignerDep
from app.schemas.assessment import DictionariesOut, OptionOut, SpecializationOut
from app.schemas.common import SkillOut
from app.schemas.fsp import PassportVerifyOut
from app.services.directory import list_skills
from app.services.passport import verify_passport
from app.services.specializations import INDUSTRIES, ROLES, SOFT_SKILLS, SPECIALIZATIONS

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/skills", summary="Справочник навыков")
async def skills(session: SessionDep) -> list[SkillOut]:
    return await list_skills(session)


@router.get("/dictionaries", summary="Справочники: специализации, отрасли, роли")
async def dictionaries() -> DictionariesOut:
    return DictionariesOut(
        specializations=[
            SpecializationOut(slug=s.slug, title=s.title, group=s.group, skills=list(s.skills))
            for s in SPECIALIZATIONS.values()
        ],
        industries=[OptionOut(value=k, label=v) for k, v in INDUSTRIES.items()],
        roles=[OptionOut(value=k, label=v) for k, v in ROLES.items()],
        soft_skills=[OptionOut(value=k, label=v) for k, v in SOFT_SKILLS.items()],
    )


@router.get("/passport/{passport_id}", summary="Проверить паспорт навыков (публично)")
async def passport_verify(
    passport_id: uuid.UUID, session: SessionDep, signer: SignerDep, response: Response
) -> PassportVerifyOut:
    # отзыв должен действовать сразу: ответ не кэшируется и не индексируется поисковиками
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return await verify_passport(session, signer, passport_id)


@router.get("/passport-key", summary="Публичный ключ для проверки подписи паспортов")
async def passport_key(signer: SignerDep) -> dict[str, str]:
    return {"algorithm": "Ed25519", "key_id": signer.key_id, "public_key": signer.public_key_b64}
