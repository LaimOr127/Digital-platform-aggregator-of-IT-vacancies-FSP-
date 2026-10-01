"""Шаблоны писем: тема и текст по виду письма. Только простой текст — без HTML и трекинга.

Темы статичные: данные пользователей (названия компаний, вакансий) попадают только в текст.
Ссылки с токенами используют фрагмент (#token=...): он не уходит на сервер и в логи прокси.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

Payload = dict[str, Any]
Renderer = Callable[[Payload, str], tuple[str, str]]

_SIGNATURE = "\n\n— IT Match, агрегатор ИТ-вакансий с данными ФСП"
_MSK = ZoneInfo("Europe/Moscow")


def _when(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(_MSK).strftime("%d.%m.%Y %H:%M МСК")


def _salary(payload: Payload) -> str:
    return f"{payload['salary_min']:,} – {payload['salary_max']:,} ₽".replace(",", " ")


def _verify_email(payload: Payload, url: str) -> tuple[str, str]:
    return "Подтвердите почту", (
        "Здравствуйте!\n\nЧтобы завершить регистрацию, откройте ссылку (действует 24 часа):\n"
        f"{url}/verify-email#token={payload['token']}\n\n"
        "Если вы не регистрировались, просто проигнорируйте письмо."
    )


def _account_exists(_: Payload, url: str) -> tuple[str, str]:
    return "Попытка регистрации", (
        "Здравствуйте!\n\nКто-то (возможно, вы) пытался зарегистрироваться с этим адресом, "
        "но аккаунт уже существует.\n\n"
        f"Войти: {url}/login\nЗабыли пароль? {url}/forgot-password\n\n"
        "Если это были не вы, ничего делать не нужно: доступ к аккаунту не изменился."
    )


def _password_reset(payload: Payload, url: str) -> tuple[str, str]:
    return "Сброс пароля", (
        "Здравствуйте!\n\nЧтобы задать новый пароль, откройте ссылку (действует 1 час):\n"
        f"{url}/reset-password#token={payload['token']}\n\n"
        "Если вы не запрашивали сброс, проигнорируйте письмо: пароль останется прежним."
    )


def _offer_received(payload: Payload, url: str) -> tuple[str, str]:
    return "Новый оффер", (
        f"Компания «{payload['company']}» предлагает вам вакансию «{payload['vacancy']}» "
        f"с зарплатой {_salary(payload)}.\n\n"
        "Имя и контакты компания увидит, только если вы примете оффер. Ответить можно 7 дней:\n"
        f"{url}/app/offers"
    )


def _offer_answered(payload: Payload, url: str) -> tuple[str, str]:
    if payload["accepted"]:
        return "Оффер принят", (
            f"Кандидат принял оффер по вакансии «{payload['vacancy']}». "
            f"Контакты доступны в разделе «Офферы»:\n{url}/company/offers"
        )
    return "Оффер отклонён", (
        f"Кандидат отклонил оффер по вакансии «{payload['vacancy']}».\n{url}/company/offers"
    )


def _company_status(payload: Payload, url: str) -> tuple[str, str]:
    if payload["status"] == "approved":
        return "Компания одобрена", (
            f"Компания «{payload['company']}» прошла модерацию: публикуйте вакансии и ищите "
            f"кандидатов в каталоге.\n{url}/company"
        )
    return "Компания заблокирована", (
        f"Компания «{payload['company']}» заблокирована модератором: вакансии скрыты, "
        "неотвеченные офферы отозваны."
    )


def _interview_invited(payload: Payload, url: str) -> tuple[str, str]:
    slots = "\n".join(f"• {_when(s)}" for s in payload["slots"])
    return "Приглашение на собеседование", (
        f"Компания «{payload['company']}» приглашает вас на собеседование по вакансии "
        f"«{payload['vacancy']}». Проводит: {payload['interviewer']}.\n\n"
        f"Варианты времени:\n{slots}\n\n"
        f"Выберите удобное время или откажитесь в кабинете:\n{url}/app/interviews\n\n"
        "Имя и контакты компания увидит только после того, как вы примете оффер."
    )


def _interview_scheduled(payload: Payload, url: str) -> tuple[str, str]:
    return "Собеседование назначено", (
        f"Кандидат выбрал время собеседования по вакансии «{payload['vacancy']}»: "
        f"{_when(payload['when'])}.\n{url}/company/interviews"
    )


def _interview_declined(payload: Payload, url: str) -> tuple[str, str]:
    return "Кандидат отказался от собеседования", (
        f"Кандидат отказался от собеседования по вакансии «{payload['vacancy']}».\n"
        f"{url}/company/interviews"
    )


def _interview_cancelled(payload: Payload, url: str) -> tuple[str, str]:
    return "Собеседование отменено", (
        f"Компания «{payload['company']}» отменила собеседование по вакансии "
        f"«{payload['vacancy']}».\n{url}/app/interviews"
    )


def _interview_result(payload: Payload, url: str) -> tuple[str, str]:
    if payload["passed"]:
        text = "Собеседование пройдено — компания может прислать вам оффер."
    else:
        text = "К сожалению, компания не готова продолжить. Отзыв — в кабинете."
    return "Итоги собеседования", (
        f"Итоги собеседования по вакансии «{payload['vacancy']}» в компании "
        f"«{payload['company']}»: {text}\n{url}/app/interviews"
    )


TEMPLATES: dict[str, Renderer] = {
    "verify_email": _verify_email,
    "account_exists": _account_exists,
    "password_reset": _password_reset,
    "offer_received": _offer_received,
    "offer_answered": _offer_answered,
    "company_status": _company_status,
    "interview_invited": _interview_invited,
    "interview_scheduled": _interview_scheduled,
    "interview_declined": _interview_declined,
    "interview_cancelled": _interview_cancelled,
    "interview_result": _interview_result,
}


def render(kind: str, payload: Payload, public_url: str) -> tuple[str, str]:
    subject, body = TEMPLATES[kind](payload, public_url.rstrip("/"))
    return subject, body + _SIGNATURE
