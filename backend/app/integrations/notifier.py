"""Канал доставки уведомлений. Интерфейс Notifier: сейчас — почта (SMTP), Telegram и другие
каналы подключаются новой реализацией без изменений в сервисах."""

import asyncio
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import Settings

_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class Notifier(ABC):
    @abstractmethod
    async def send(self, email: Email) -> None:
        """Доставить письмо; любая ошибка — повод повторить попытку позже."""


class SmtpNotifier(Notifier):
    """Отправка через SMTP (в dev — Mailpit, в prod — почтовый сервис из .env)."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password.get_secret_value()
        self._sender = settings.smtp_from
        self._starttls = settings.smtp_starttls

    async def send(self, email: Email) -> None:
        # smtplib синхронный: отправка в отдельном потоке не блокирует остальные задачи worker
        await asyncio.to_thread(self._send_sync, self._message(email))

    def _message(self, email: Email) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)
        return message

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=_TIMEOUT_SECONDS) as smtp:
            if self._starttls:
                smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(message)
