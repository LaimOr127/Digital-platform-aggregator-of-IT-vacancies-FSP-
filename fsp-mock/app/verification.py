"""Подтверждение владения аккаунтом ФСП одноразовым кодом (хранилище в памяти мока).

Реальный ФСП отправил бы код на почту спортсмена. Мок кладёт письмо в «исходящие»
и, только если явно включено FSP_MOCK_EXPOSE_CODES, возвращает код в ответе — для демо.
"""

import secrets
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

CODE_TTL_SECONDS = 600
MAX_ATTEMPTS = 5
OUTBOX_SIZE = 100


@dataclass
class Request:
    athlete_id: str
    code: str
    expires_at: float
    attempts: int = 0


class VerificationError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass
class VerificationStore:
    clock: Callable[[], float] = time.monotonic
    requests: dict[str, Request] = field(default_factory=dict)
    # «исходящие письма» (athlete_id, code): последние OUTBOX_SIZE, память мока не растёт
    outbox: deque[tuple[str, str]] = field(default_factory=lambda: deque(maxlen=OUTBOX_SIZE))

    def start(self, athlete_id: str) -> tuple[str, str]:
        request_id = uuid.uuid4().hex
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.requests[request_id] = Request(athlete_id, code, self.clock() + CODE_TTL_SECONDS)
        self.outbox.append((athlete_id, code))
        return request_id, code

    def confirm(self, request_id: str, code: str) -> str:
        request = self.requests.get(request_id)
        if request is None or request.expires_at < self.clock():
            self.requests.pop(request_id, None)
            raise VerificationError("expired")
        if request.attempts >= MAX_ATTEMPTS:
            raise VerificationError("too_many_attempts", 429)
        request.attempts += 1
        if not secrets.compare_digest(request.code, code):
            raise VerificationError("invalid_code")
        del self.requests[request_id]
        return request.athlete_id
