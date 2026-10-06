"""Фабрика приложения: создаёт FastAPI, подключает middleware, ошибки и роутеры."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.crypto import FieldCipher
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.ratelimit import RateLimiter, build_limits
from app.core.ratelimit_pg import PostgresRateLimiter
from app.core.security import TokenService
from app.core.signing import PassportSigner
from app.db.session import get_database
from app.integrations.fsp import HttpFspClient


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.fsp_client.aclose()
        await get_database().dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        # Swagger UI отдаёт web по /api-docs/ (без CDN и inline-скриптов, совместим с CSP)
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        debug=False,  # иначе Starlette отдаёт клиенту traceback вместо единого формата ошибки
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Token"],
        )
    app.state.settings = settings
    app.state.tokens = TokenService(settings)
    app.state.cipher = FieldCipher(settings.secret("field_encryption_key"))
    app.state.signer = PassportSigner(settings.secret("passport_signing_key"))
    app.state.fsp_client = HttpFspClient(settings)
    app.state.ai_transport = None  # тесты подменяют сеть к языковым моделям
    app.state.rate_limiter = (
        PostgresRateLimiter(get_database().engine)
        if settings.rate_limit_backend == "postgres"
        else RateLimiter()
    )
    app.state.rate_limits = build_limits(
        {
            "auth": settings.auth_rate_limit,
            "email": settings.email_rate_limit,
            "resume": settings.resume_rate_limit,
            "ai": settings.ai_rate_limit,
            "interview_invite": settings.interview_invite_rate_limit,
            "application_invite": settings.application_invite_rate_limit,
            "application_respond": settings.application_respond_rate_limit,
            "login_email": settings.login_email_rate_limit,
            "refresh": settings.refresh_rate_limit,
            "fsp_link": settings.fsp_link_rate_limit,
            "fsp_athlete": settings.fsp_athlete_rate_limit,
            "fsp_confirm": settings.fsp_confirm_rate_limit,
            "fsp_sync": settings.fsp_sync_rate_limit,
            "offer_send": settings.offer_send_rate_limit,
            "mfa": settings.mfa_rate_limit,
        }
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
