from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.errors import ServiceUnavailableError
from app.db.session import Database, get_database

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness: процесс жив")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness: есть связь с БД")
async def ready(db: Annotated[Database, Depends(get_database)]) -> dict[str, str]:
    if not await db.ping():
        raise ServiceUnavailableError("database unavailable")
    return {"status": "ready"}
