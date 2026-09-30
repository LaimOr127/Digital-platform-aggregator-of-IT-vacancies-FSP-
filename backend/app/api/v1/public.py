from fastapi import APIRouter

from app.api.deps import SessionDep
from app.repositories.candidates import SkillRepository
from app.schemas.common import SkillOut

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/skills", summary="Справочник навыков")
async def list_skills(session: SessionDep) -> list[SkillOut]:
    return [SkillOut.model_validate(s) for s in await SkillRepository(session).all()]
