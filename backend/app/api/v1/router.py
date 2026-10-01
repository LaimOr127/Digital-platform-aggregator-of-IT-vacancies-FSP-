"""Корневой роутер v1: подключает порталы кандидата, работодателя и админа."""

from fastapi import APIRouter

from app.api.v1 import (
    account,
    admin,
    admin_ai,
    auth,
    candidate,
    candidate_interviews,
    candidate_offers,
    catalog,
    employer,
    employer_interviews,
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
    candidate_interviews,
    candidate_offers,
    employer,
    employer_interviews,
    catalog,
    admin,
    admin_ai,
    public,
):
    api_router.include_router(module.router)
