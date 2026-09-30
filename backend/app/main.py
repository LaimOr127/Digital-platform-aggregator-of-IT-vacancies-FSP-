"""Фабрика приложения: создаёт FastAPI, подключает middleware, ошибки и роутеры."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.db.session import get_database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await get_database().dispose()

    is_prod = settings.app_env == "prod"
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        # Swagger UI отдаёт web по /api-docs/ (без CDN и inline-скриптов, совместим с CSP)
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        debug=not is_prod,
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Token"],
        )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
