"""Реестр моделей: импорт здесь регистрирует все таблицы в Base.metadata (нужно Alembic)."""

from app.models.ai_provider import AiProvider
from app.models.application import Application
from app.models.assessment import Assessment
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.candidate import CandidateProfile, Skill, profile_skills
from app.models.category import Category, candidate_categories
from app.models.company import CompanyMember, EmployerCompany
from app.models.fsp import FspAchievement, FspLink, FspVerification
from app.models.interview import Interview
from app.models.notify import EmailToken, OutboxMessage
from app.models.offer import ContactReveal, Offer
from app.models.passport import Passport
from app.models.task import EmployerTask, TaskAnswer
from app.models.user import RefreshToken, User
from app.models.vacancy import Vacancy, vacancy_skills

__all__ = [
    "AiProvider",
    "Application",
    "Assessment",
    "AuditLog",
    "Base",
    "CandidateProfile",
    "Category",
    "CompanyMember",
    "ContactReveal",
    "EmailToken",
    "EmployerCompany",
    "EmployerTask",
    "FspAchievement",
    "FspLink",
    "FspVerification",
    "Interview",
    "Offer",
    "OutboxMessage",
    "Passport",
    "RefreshToken",
    "Skill",
    "TaskAnswer",
    "User",
    "Vacancy",
    "candidate_categories",
    "profile_skills",
    "vacancy_skills",
]
