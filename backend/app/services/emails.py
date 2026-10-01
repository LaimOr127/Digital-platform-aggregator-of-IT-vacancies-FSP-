"""Шаблоны писем: тема и текст по виду письма. Только простой текст — без HTML и трекинга.

Темы статичные: данные пользователей (названия компаний, вакансий) попадают только в текст.
Ссылки с токенами используют фрагмент (#token=...): он не уходит на сервер и в логи прокси.
"""

from collections.abc import Callable
from typing import Any

Payload = dict[str, Any]
Renderer = Callable[[Payload, str], tuple[str, str]]

_SIGNATURE = "\n\n— IT Match, агрегатор ИТ-вакансий с данными ФСП"


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


TEMPLATES: dict[str, Renderer] = {
    "verify_email": _verify_email,
    "account_exists": _account_exists,
    "password_reset": _password_reset,
    "offer_received": _offer_received,
    "offer_answered": _offer_answered,
    "company_status": _company_status,
}


def render(kind: str, payload: Payload, public_url: str) -> tuple[str, str]:
    subject, body = TEMPLATES[kind](payload, public_url.rstrip("/"))
    return subject, body + _SIGNATURE
