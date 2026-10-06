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
# неудачи на аккаунт за сутки: новые запросы кода не дают новых попыток подбора
MAX_DAILY_FAILURES = 20
DAY_SECONDS = 86_400
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
    failures: dict[str, list[float]] = field(default_factory=dict)  # athlete_id -> моменты неудач
    # «исходящие письма» (athlete_id, code): последние OUTBOX_SIZE, память мока не растёт
    outbox: deque[tuple[str, str]] = field(default_factory=lambda: deque(maxlen=OUTBOX_SIZE))

    def start(self, athlete_id: str) -> tuple[str, str]:
        """Новый код аннулирует прежние запросы этого аккаунта; просроченные удаляются."""
        now = self.clock()
        if self._recent_failures(athlete_id, now) >= MAX_DAILY_FAILURES:
            raise VerificationError("too_many_attempts", 429)
        self.requests = {
            rid: r
            for rid, r in self.requests.items()
            if r.athlete_id != athlete_id and r.expires_at >= now
        }
        request_id = uuid.uuid4().hex
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.requests[request_id] = Request(athlete_id, code, now + CODE_TTL_SECONDS)
        self.outbox.append((athlete_id, code))
        return request_id, code

    def confirm(self, request_id: str, code: str) -> str:
        request = self.requests.get(request_id)
        if request is None or request.expires_at < self.clock():
            self.requests.pop(request_id, None)
            raise VerificationError("expired")
        now = self.clock()
        if (
            request.attempts >= MAX_ATTEMPTS
            or self._recent_failures(request.athlete_id, now) >= MAX_DAILY_FAILURES
        ):
            raise VerificationError("too_many_attempts", 429)
        request.attempts += 1
        if not secrets.compare_digest(request.code, code):
            self.failures.setdefault(request.athlete_id, []).append(now)
            raise VerificationError("invalid_code")
        del self.requests[request_id]
        return request.athlete_id

    def _recent_failures(self, athlete_id: str, now: float) -> int:
        recent = [t for t in self.failures.get(athlete_id, []) if t > now - DAY_SECONDS]
        if recent:
            self.failures[athlete_id] = recent
        else:
            self.failures.pop(athlete_id, None)
        return len(recent)
