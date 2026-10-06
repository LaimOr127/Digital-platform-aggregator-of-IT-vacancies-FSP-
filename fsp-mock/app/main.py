"""Мок API ФСП. Контракт: спортсмены, результаты соревнований, подтверждение аккаунта кодом.

Доступ к /api/v1 — только с сервисным ключом X-Api-Key (как у реальной интеграции).
"""

import os
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.data import ATHLETES, DISCIPLINES, mask_email, result_payload
from app.questionnaire import questionnaire_payload
from app.verification import VerificationError, VerificationStore

API_KEY = os.environ.get("FSP_API_KEY", "")
EXPOSE_CODES = os.environ.get("FSP_MOCK_EXPOSE_CODES", "false").lower() == "true"

app = FastAPI(title="FSP mock", version="0.2.0", docs_url="/docs", redoc_url=None)
app.state.verification = VerificationStore()


def require_api_key(x_api_key: Annotated[str, Header()] = "") -> None:
    if not API_KEY or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(401, "invalid api key")


Protected = [Depends(require_api_key)]


def _athlete(athlete_id: str):
    athlete = ATHLETES.get(athlete_id.strip().upper())
    if athlete is None:
        raise HTTPException(404, "athlete not found")
    return athlete


class StartIn(BaseModel):
    athlete_id: str = Field(min_length=3, max_length=32)


class ConfirmIn(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    code: str = Field(pattern=r"^\d{6}$")


@app.exception_handler(VerificationError)
async def _verification_error(_, exc: VerificationError) -> JSONResponse:
    return JSONResponse({"detail": exc.code}, status_code=exc.status)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/disciplines", dependencies=Protected)
async def disciplines() -> list[dict[str, str]]:
    return [{"id": k, "title": v} for k, v in DISCIPLINES.items()]


@app.get("/api/v1/athletes/{athlete_id}", dependencies=Protected)
async def athlete(athlete_id: str) -> dict:
    return _athlete(athlete_id).public()


@app.get("/api/v1/athletes/{athlete_id}/results", dependencies=Protected)
async def results(athlete_id: str) -> list[dict]:
    return [result_payload(r) for r in _athlete(athlete_id).results]


@app.get("/api/v1/athletes/{athlete_id}/questionnaire", dependencies=Protected)
async def questionnaire(athlete_id: str) -> dict:
    """Анкета из личного кабинета ФСП + подтверждённый федерацией email."""
    athlete = _athlete(athlete_id)
    return {**questionnaire_payload(athlete.id), "email": athlete.email}


@app.post("/api/v1/verification/start", dependencies=Protected)
async def start(data: StartIn) -> dict:
    target = _athlete(data.athlete_id)
    request_id, code = app.state.verification.start(target.id)
    body = {"request_id": request_id, "email_masked": mask_email(target.email), "expires_in": 600}
    if EXPOSE_CODES:
        body["demo_code"] = code
    return body


@app.post("/api/v1/verification/confirm", dependencies=Protected)
async def confirm(data: ConfirmIn) -> dict[str, str]:
    return {"athlete_id": app.state.verification.confirm(data.request_id, data.code)}
