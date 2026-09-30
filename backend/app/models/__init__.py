"""Реестр моделей: импорт здесь регистрирует все таблицы в Base.metadata (нужно Alembic)."""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.candidate import CandidateProfile, Skill, profile_skills
from app.models.company import CompanyMember, EmployerCompany
from app.models.user import RefreshToken, User
from app.models.vacancy import Vacancy, vacancy_skills

__all__ = [
    "AuditLog",
    "Base",
    "CandidateProfile",
    "CompanyMember",
    "EmployerCompany",
    "RefreshToken",
    "Skill",
    "User",
    "Vacancy",
    "profile_skills",
    "vacancy_skills",
]
