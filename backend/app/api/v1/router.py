"""Корневой роутер v1: подключает порталы кандидата, работодателя и админа."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, candidate, employer, health, public

api_router = APIRouter(prefix="/api/v1")
for module in (health, auth, candidate, employer, admin, public):
    api_router.include_router(module.router)
