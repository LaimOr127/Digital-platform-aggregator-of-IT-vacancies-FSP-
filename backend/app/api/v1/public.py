import uuid

from fastapi import APIRouter, Response

from app.api.deps import SessionDep, SignerDep
from app.schemas.common import SkillOut
from app.schemas.fsp import PassportVerifyOut
from app.services.directory import list_skills
from app.services.passport import verify_passport

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/skills", summary="Справочник навыков")
async def skills(session: SessionDep) -> list[SkillOut]:
    return await list_skills(session)


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
