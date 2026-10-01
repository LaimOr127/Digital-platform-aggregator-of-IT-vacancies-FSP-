"""Матрица прав AccessPolicy: роль x действие x владелец ресурса."""

import uuid
from types import SimpleNamespace

import pytest

from app.core.errors import ForbiddenError
from app.models.enums import CompanyStatus, MemberRole, UserRole
from app.services.access import Action, Principal, policy

COMPANY = uuid.uuid4()

candidate = Principal(user_id=uuid.uuid4(), role=UserRole.CANDIDATE)
employer_pending = Principal(
    user_id=uuid.uuid4(),
    role=UserRole.EMPLOYER,
    company_id=COMPANY,
    member_role=MemberRole.OWNER,
    company_status=CompanyStatus.PENDING,
)
employer_approved = Principal(
    user_id=uuid.uuid4(),
    role=UserRole.EMPLOYER,
    company_id=COMPANY,
    member_role=MemberRole.RECRUITER,
    company_status=CompanyStatus.APPROVED,
)
employer_without_company = Principal(user_id=uuid.uuid4(), role=UserRole.EMPLOYER)
moderator = Principal(user_id=uuid.uuid4(), role=UserRole.ADMIN)
superadmin = Principal(user_id=uuid.uuid4(), role=UserRole.ADMIN, is_superadmin=True)

own_vacancy = SimpleNamespace(company_id=COMPANY)
foreign_vacancy = SimpleNamespace(company_id=uuid.uuid4())


@pytest.mark.parametrize(
    ("principal", "action", "resource", "allowed"),
    [
        (candidate, Action.PROFILE_MANAGE_OWN, None, True),
        (employer_approved, Action.PROFILE_MANAGE_OWN, None, False),
        (moderator, Action.PROFILE_MANAGE_OWN, None, False),
        (employer_pending, Action.COMPANY_READ_OWN, None, True),
        (employer_without_company, Action.COMPANY_READ_OWN, None, False),
        (candidate, Action.COMPANY_READ_OWN, None, False),
        (employer_pending, Action.VACANCY_WRITE, own_vacancy, True),
        (employer_pending, Action.VACANCY_WRITE, foreign_vacancy, False),
        (employer_approved, Action.VACANCY_READ, foreign_vacancy, False),
        (candidate, Action.VACANCY_WRITE, None, False),
        (employer_pending, Action.VACANCY_PUBLISH, own_vacancy, False),
        (employer_approved, Action.VACANCY_PUBLISH, own_vacancy, True),
        (employer_approved, Action.VACANCY_PUBLISH, foreign_vacancy, False),
        (employer_pending, Action.CATALOG_READ, None, False),
        (employer_approved, Action.CATALOG_READ, None, True),
        (candidate, Action.CATALOG_READ, None, False),
        (employer_approved, Action.OFFER_SEND, None, True),
        (employer_approved, Action.OFFER_MANAGE, own_vacancy, True),
        (employer_approved, Action.OFFER_MANAGE, foreign_vacancy, False),
        (candidate, Action.OFFER_RESPOND, None, True),
        (employer_approved, Action.OFFER_RESPOND, None, False),
        (moderator, Action.ADMIN_MODERATE, None, True),
        (employer_approved, Action.ADMIN_MODERATE, None, False),
        (moderator, Action.ADMIN_SUPER, None, False),
        (superadmin, Action.ADMIN_SUPER, None, True),
    ],
)
def test_policy_matrix(principal, action, resource, allowed):
    assert policy.can(principal, action, resource) is allowed


def test_ensure_raises_forbidden():
    with pytest.raises(ForbiddenError):
        policy.ensure(candidate, Action.ADMIN_MODERATE)
