import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep, SignerDep
from app.repositories.candidates import SkillRepository
from app.schemas.common import SkillOut
from app.schemas.fsp import PassportVerifyOut
from app.services.passport import verify_passport

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/skills", summary="Справочник навыков")
async def list_skills(session: SessionDep) -> list[SkillOut]:
    return [SkillOut.model_validate(s) for s in await SkillRepository(session).all()]


@router.get("/passport/{passport_id}", summary="Проверить паспорт навыков (публично)")
async def passport_verify(
    passport_id: uuid.UUID, session: SessionDep, signer: SignerDep
) -> PassportVerifyOut:
    return await verify_passport(session, signer, passport_id)


@router.get("/passport-key", summary="Публичный ключ для проверки подписи паспортов")
async def passport_key(signer: SignerDep) -> dict[str, str]:
    return {"algorithm": "Ed25519", "key_id": signer.key_id, "public_key": signer.public_key_b64}
