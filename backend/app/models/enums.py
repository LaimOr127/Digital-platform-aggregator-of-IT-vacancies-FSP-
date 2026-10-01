"""Перечисления домена. Используются моделями, схемами API и AccessPolicy."""

from enum import StrEnum


class UserRole(StrEnum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"


class Grade(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"


class WorkFormat(StrEnum):
    OFFICE = "office"
    HYBRID = "hybrid"
    REMOTE = "remote"


class VerificationTier(StrEnum):
    SELF_DECLARED = "self_declared"
    RESUME_PARSED = "resume_parsed"
    VERIFIED_FSP = "verified_fsp"


class CompanyStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"


class MemberRole(StrEnum):
    OWNER = "owner"
    RECRUITER = "recruiter"


class OfferStatus(StrEnum):
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class VacancyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    BLOCKED = "blocked"


class RecipientType(StrEnum):
    """Кому письмо: пользователю, кандидату (по профилю) или владельцам компании."""

    USER = "user"
    PROFILE = "profile"
    COMPANY = "company"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"  # исчерпаны попытки
    DROPPED = "dropped"  # адресат недоступен (удалён, заблокирован)


class EmailTokenPurpose(StrEnum):
    VERIFY = "verify"
    RESET = "reset"


class SearchStatus(StrEnum):
    """Статус поиска работы кандидата: виден работодателям в каталоге."""

    ACTIVE = "active"  # активно ищу
    OPEN = "open"  # рассматриваю предложения
    CLOSED = "closed"  # не ищу: профиль не в каталоге, новые офферы не приходят


class InterviewStatus(StrEnum):
    INVITED = "invited"  # ждёт выбора слота кандидатом
    SCHEDULED = "scheduled"  # кандидат выбрал время
    DECLINED = "declined"  # кандидат отказался
    CANCELLED = "cancelled"  # компания отменила
    COMPLETED = "completed"  # прошло, результат отмечен
    EXPIRED = "expired"  # кандидат не ответил вовремя


class InterviewResult(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class InterviewFormat(StrEnum):
    ONLINE = "online"
    OFFICE = "office"
