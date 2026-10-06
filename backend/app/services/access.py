"""AccessPolicy — единственная точка решения «может ли X сделать Y с Z» (RBAC + владелец).

Роутеры и сервисы не проверяют роли сами: они вызывают policy.ensure(principal, action, resource).
Новое правило = новая запись в _RULES, остальной код не меняется.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.errors import ForbiddenError
from app.models.enums import CompanyStatus, MemberRole, UserRole


class Action(StrEnum):
    PROFILE_MANAGE_OWN = "profile.manage_own"
    COMPANY_READ_OWN = "company.read_own"
    VACANCY_READ = "vacancy.read"
    VACANCY_WRITE = "vacancy.write"
    VACANCY_PUBLISH = "vacancy.publish"
    CATALOG_READ = "catalog.read"
    OFFER_SEND = "offer.send"
    OFFER_MANAGE = "offer.manage"
    APPLICATION_MANAGE = "application.manage"
    OFFER_RESPOND = "offer.respond"
    TASK_PUBLISH = "task.publish"
    ADMIN_MODERATE = "admin.moderate"
    ADMIN_SUPER = "admin.super"


@dataclass(frozen=True)
class Principal:
    """Кто действует: собирается из access-токена и БД на каждый запрос."""

    user_id: uuid.UUID
    role: UserRole
    is_superadmin: bool = False
    company_id: uuid.UUID | None = None
    member_role: MemberRole | None = None
    company_status: CompanyStatus | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


def _is_candidate(p: Principal, _: Any) -> bool:
    return p.role == UserRole.CANDIDATE


def _is_employer_member(p: Principal, _: Any) -> bool:
    return p.role == UserRole.EMPLOYER and p.company_id is not None


def _owns_company_resource(p: Principal, resource: Any) -> bool:
    """Ресурс (вакансия) принадлежит компании пользователя. Без ресурса — просто член компании."""
    if not _is_employer_member(p, resource):
        return False
    return resource is None or getattr(resource, "company_id", None) == p.company_id


def _can_write_vacancy(p: Principal, resource: Any) -> bool:
    """Заблокированная модератором компания не создаёт и не меняет вакансии."""
    return _owns_company_resource(p, resource) and p.company_status != CompanyStatus.BLOCKED


def _can_publish(p: Principal, resource: Any) -> bool:
    return _owns_company_resource(p, resource) and p.company_status == CompanyStatus.APPROVED


def _approved_employer(p: Principal, _: Any) -> bool:
    """Каталог кандидатов и офферы — только для одобренной модератором компании."""
    return _is_employer_member(p, None) and p.company_status == CompanyStatus.APPROVED


def _manages_offer(p: Principal, resource: Any) -> bool:
    return _owns_company_resource(p, resource) and p.company_status != CompanyStatus.BLOCKED


def _is_admin(p: Principal, _: Any) -> bool:
    return p.is_admin


def _is_superadmin(p: Principal, _: Any) -> bool:
    return p.is_admin and p.is_superadmin


_RULES: dict[Action, Callable[[Principal, Any], bool]] = {
    Action.PROFILE_MANAGE_OWN: _is_candidate,
    Action.COMPANY_READ_OWN: _is_employer_member,
    Action.VACANCY_READ: _owns_company_resource,
    Action.VACANCY_WRITE: _can_write_vacancy,
    Action.VACANCY_PUBLISH: _can_publish,
    Action.CATALOG_READ: _approved_employer,
    Action.OFFER_SEND: _approved_employer,
    Action.OFFER_MANAGE: _manages_offer,
    Action.APPLICATION_MANAGE: _manages_offer,
    Action.OFFER_RESPOND: _is_candidate,
    Action.TASK_PUBLISH: _approved_employer,
    Action.ADMIN_MODERATE: _is_admin,
    Action.ADMIN_SUPER: _is_superadmin,
}


class AccessPolicy:
    def can(self, principal: Principal, action: Action, resource: Any = None) -> bool:
        rule = _RULES.get(action)
        return rule is not None and rule(principal, resource)

    def ensure(self, principal: Principal, action: Action, resource: Any = None) -> None:
        if not self.can(principal, action, resource):
            raise ForbiddenError("access denied")


policy = AccessPolicy()
