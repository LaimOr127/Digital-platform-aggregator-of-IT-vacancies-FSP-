"""Канал доставки для тестов: письма складываются в список; можно имитировать сбой."""

from app.integrations.notifier import Email, Notifier


class MemoryNotifier(Notifier):
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[Email] = []
        self.fail = fail

    async def send(self, email: Email) -> None:
        if self.fail:
            raise ConnectionError("smtp down")
        self.sent.append(email)
