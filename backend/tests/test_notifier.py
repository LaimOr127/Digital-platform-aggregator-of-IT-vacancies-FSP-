"""SMTP-канал: письмо собирается корректно, STARTTLS и вход — только когда настроены."""

from typing import ClassVar

from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.notifier import Email, SmtpNotifier


class FakeSmtp:
    instances: ClassVar[list["FakeSmtp"]] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.address = (host, port, timeout)
        self.calls: list[str] = []
        self.messages: list = []
        FakeSmtp.instances.append(self)

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(self, *_: object) -> None:
        self.calls.append("quit")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login:{user}:{len(password)}")

    def send_message(self, message) -> None:
        self.messages.append(message)


async def test_dev_smtp_sends_plain_message(monkeypatch):
    monkeypatch.setattr("app.integrations.notifier.smtplib.SMTP", FakeSmtp)
    FakeSmtp.instances.clear()
    await SmtpNotifier(Settings()).send(Email("anna@example.org", "Тема", "Текст письма"))
    [smtp] = FakeSmtp.instances
    assert smtp.address[:2] == ("mailpit", 1025) and smtp.calls == ["quit"]
    [message] = smtp.messages
    assert message["To"] == "anna@example.org" and message["Subject"] == "Тема"
    assert message.get_content().strip() == "Текст письма"


async def test_prod_smtp_uses_tls_and_login(monkeypatch):
    monkeypatch.setattr("app.integrations.notifier.smtplib.SMTP", FakeSmtp)
    FakeSmtp.instances.clear()
    settings = Settings(
        smtp_host="smtp.example.org",
        smtp_port=587,
        smtp_user="mailer",
        smtp_password=SecretStr("p" * 20),
        smtp_starttls=True,
    )
    await SmtpNotifier(settings).send(Email("a@example.org", "s", "b"))
    assert FakeSmtp.instances[0].calls == ["starttls", "login:mailer:20", "quit"]
