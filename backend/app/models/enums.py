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


class AiProviderKind(StrEnum):
    OPENAI = "openai"  # OpenAI-совместимый Chat Completions API
    ANTHROPIC = "anthropic"


class Specialization(StrEnum):
    """Специализация — первая половина категории кандидата (вторая — подтверждённый грейд)."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    MOBILE = "mobile"
    DATA = "data"  # анализ данных и машинное обучение
    DEVOPS = "devops"
    QA = "qa"
    SECURITY = "security"


class AssessmentStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"  # время вышло, ответы не отправлены


class AssessmentResult(StrEnum):
    PASSED = "passed"  # заявленный грейд подтверждён
    FAILED = "failed"  # не подтверждён: можно пройти тест на грейд ниже


class ApplicationDirection(StrEnum):
    """Кто проявил инициативу: компания пригласила или кандидат откликнулся сам."""

    INVITATION = "invitation"
    RESPONSE = "response"


class ApplicationStatus(StrEnum):
    SENT = "sent"  # отправлено, адресат ещё не открывал
    VIEWED = "viewed"  # адресат увидел
    ACCEPTED = "accepted"  # контакт состоялся: кандидат принял приглашение / компания — отклик
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"  # отозвал тот, кто отправил
    EXPIRED = "expired"  # без ответа дольше срока
