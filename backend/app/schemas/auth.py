import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole

_MIN_PASSWORD = 10


class PasswordMixin(BaseModel):
    password: str = Field(min_length=_MIN_PASSWORD, max_length=128)

    @field_validator("password")
    @classmethod
    def _strength(cls, value: str) -> str:
        if value.isdigit() or value.isalpha() or len(set(value)) < 5:
            msg = "пароль должен содержать буквы и цифры/символы и не быть однообразным"
            raise ValueError(msg)
        return value


class CandidateRegisterIn(PasswordMixin):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)


class EmployerRegisterIn(PasswordMixin):
    email: EmailStr
    company_name: str = Field(min_length=2, max_length=200)
    inn: str | None = Field(default=None, pattern=r"^\d{10}(\d{2})?$")


class EmailIn(BaseModel):
    email: EmailStr


class LinkTokenIn(BaseModel):
    """Токен из ссылки в письме."""

    token: str = Field(min_length=20, max_length=128)


class PasswordResetIn(PasswordMixin, LinkTokenIn):
    pass


class AccountDeleteIn(BaseModel):
    """Удаление аккаунта подтверждается паролем."""

    password: str = Field(min_length=1, max_length=128)


class AcceptedOut(BaseModel):
    """Ответ не зависит от того, зарегистрирован ли адрес."""

    detail: str = "Проверьте почту: если адрес зарегистрирован, письмо уже отправлено"


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - тип токена, не секрет
    expires_in: int


class MeOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_superadmin: bool
    company_id: uuid.UUID | None = None


class MfaChallengeOut(BaseModel):
    """Ответ на вход администратора: нужен код 2FA (mfa_token действует 5 минут)."""

    mfa_required: bool = True
    mfa_token: str
    enrolled: bool


class MfaTokenIn(BaseModel):
    mfa_token: str = Field(min_length=10, max_length=2048)


class MfaSetupIn(MfaTokenIn):
    """Код подключения выдаёт CLI (make create-admin / make reset-admin-2fa)."""

    enrollment_code: str = Field(min_length=8, max_length=64)


class MfaVerifyIn(MfaTokenIn):
    code: str = Field(pattern=r"^\d{6}$")


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
