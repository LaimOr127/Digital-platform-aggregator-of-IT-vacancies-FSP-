"""Корневой роутер v1. Порталы (candidate/employer/admin) подключаются здесь в следующих фазах."""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
