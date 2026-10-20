#!/usr/bin/env python3
"""Почта на сервере: make smtp MODE=prod.

Спрашивает ящик и пароль приложения (пароль не отображается), проверяет вход на SMTP-сервер
и только после успешной проверки записывает настройки в .env (права 600). Пароль не попадает
в аргументы команд, историю оболочки и репозиторий. Порт 587 и STARTTLS — как ждёт worker.
"""

import getpass
import pathlib
import smtplib
import ssl
import sys

HOSTS = {
    "yandex.ru": "smtp.yandex.ru",
    "ya.ru": "smtp.yandex.ru",
    "mail.ru": "smtp.mail.ru",
    "bk.ru": "smtp.mail.ru",
    "inbox.ru": "smtp.mail.ru",
    "list.ru": "smtp.mail.ru",
}
ENV = pathlib.Path(__file__).resolve().parent.parent / ".env"


def main() -> None:
    email = input("Адрес ящика, с которого уходят письма: ").strip()
    domain = email.rpartition("@")[2].lower()
    host = HOSTS.get(domain) or input(f"SMTP-сервер для {domain} (порт 587, STARTTLS): ").strip()
    password = getpass.getpass("Пароль приложения (не отображается): ").strip()
    if not (email and host and password):
        sys.exit("нужны адрес, сервер и пароль")

    print(f"Проверяю вход на {host}:587 ...")
    try:
        with smtplib.SMTP(host, 587, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())  # с проверкой сертификата
            smtp.login(email, password)
    except (OSError, smtplib.SMTPException) as exc:
        sys.exit(f"Не удалось войти: {exc}. Настройки не изменены.")

    values = {
        "SMTP_HOST": host,
        "SMTP_PORT": "587",
        "SMTP_STARTTLS": "true",
        "SMTP_USER": email,
        "SMTP_PASSWORD": password.replace("$", "$$"),  # docker compose подставляет $ в .env
        "SMTP_FROM": f"IT Match <{email}>",
    }
    lines = [line for line in ENV.read_text().splitlines() if line.split("=", 1)[0] not in values]
    ENV.write_text("\n".join([*lines, *(f"{k}={v}" for k, v in values.items())]) + "\n")
    ENV.chmod(0o600)
    print("Вход успешен, настройки записаны в .env.")


if __name__ == "__main__":
    main()
