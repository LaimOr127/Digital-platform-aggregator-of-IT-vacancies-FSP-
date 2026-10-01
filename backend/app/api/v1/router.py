"""Корневой роутер v1: подключает порталы кандидата, работодателя и админа."""

from fastapi import APIRouter

from app.api.v1 import (
    account,
    admin,
    auth,
    candidate,
    candidate_offers,
    catalog,
    employer,
    fsp,
    health,
    profile_import,
    public,
)

api_router = APIRouter(prefix="/api/v1")
for module in (
    health,
    auth,
    account,
    candidate,
    profile_import,
    fsp,
    candidate_offers,
    employer,
    catalog,
    admin,
    public,
):
    api_router.include_router(module.router)
