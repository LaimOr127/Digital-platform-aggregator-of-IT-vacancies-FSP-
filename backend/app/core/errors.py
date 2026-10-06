"""Единый формат ошибок API: {"error": {"code", "message"}}. Внутренности не утекают клиенту."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.validation import humanize

log = get_logger(__name__)


class AppError(Exception):
    """Базовое доменное исключение; наследники задают code и status."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message or self.code


class NotFoundError(AppError):
    status_code, code = 404, "not_found"


class ForbiddenError(AppError):
    status_code, code = 403, "forbidden"


class UnauthorizedError(AppError):
    status_code, code = 401, "unauthorized"


class MfaExpiredError(UnauthorizedError):
    """Токен шага 2FA недействителен или истёк — вход нужно начать заново."""

    code = "mfa_expired"

    def __init__(self, message: str = "сессия входа истекла — войдите заново") -> None:
        super().__init__(message)


class WrongPasswordError(ForbiddenError):
    """Пароль для подтверждения действия неверен. Не 401: сессия действительна, и клиент
    не должен принимать ответ за истёкший токен (обновлять его и повторять запрос)."""

    code = "wrong_password"

    def __init__(self, message: str = "неверный пароль") -> None:
        super().__init__(message)


class EmailNotVerifiedError(AppError):
    """Пароль верный, но почта не подтверждена: клиент предлагает отправить письмо ещё раз."""

    status_code, code = 403, "email_not_verified"


class InvalidLinkError(AppError):
    """Ссылка из письма недействительна: устарела, уже использована или искажена."""

    status_code, code = 400, "invalid_link"


class ConflictError(AppError):
    status_code, code = 409, "conflict"


class InvalidStateError(AppError):
    status_code, code = 409, "invalid_state"


class RateLimitedError(AppError):
    status_code, code = 429, "rate_limited"


class ServiceUnavailableError(AppError):
    status_code, code = 503, "service_unavailable"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None


class ErrorOut(BaseModel):
    """Ответ с ошибкой: code — машинный код, message — текст для пользователя."""

    error: ErrorBody


_ERROR_CODES = {
    400: "Некорректный запрос (bad_request, invalid_link)",
    401: "Нет сессии или она истекла (unauthorized, mfa_expired)",
    403: "Нет прав на действие (forbidden, wrong_password, email_not_verified)",
    404: "Объект не найден или недоступен этой роли (not_found)",
    409: "Конфликт состояния (conflict, invalid_state)",
    422: "Ошибка валидации полей (validation_error, details — по полям)",
    429: "Превышен лимит запросов (rate_limited)",
}
# общий набор кодов ошибок для OpenAPI: подключается к корневому роутеру v1
ERROR_RESPONSES: dict[int | str, dict] = {
    status: {"model": ErrorOut, "description": text} for status, text in _ERROR_CODES.items()
}


def _body(code: str, message: str, details: object = None) -> dict:
    err: dict = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message), status_code=exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(_body("http_error", str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": e["loc"], "msg": humanize(e)} for e in exc.errors()]
        return JSONResponse(_body("validation_error", "Некорректные данные", details), 422)

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        # страховка: нарушение ограничения БД — конфликт данных, а не 500; детали SQL не отдаём
        log.warning("integrity error: %s", type(exc.orig).__name__)
        return JSONResponse(_body("conflict", "Конфликт данных"), status_code=409)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(_body("internal_error", "Внутренняя ошибка"), status_code=500)
