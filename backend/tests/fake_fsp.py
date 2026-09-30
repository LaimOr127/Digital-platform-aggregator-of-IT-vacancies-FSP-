"""Фейковый клиент ФСП для тестов: те же сигнатуры, что у HttpFspClient."""

from app.core.errors import NotFoundError
from app.integrations.fsp import FspAthlete, FspResult, FspVerificationError, FspVerificationStart

CODE = "424242"


def result(
    rid: str, discipline: str, level: str, place: int | None, stage: str = "final"
) -> FspResult:
    return FspResult(
        rid, discipline, f"Соревнование {rid}", level, "2025-10-01", place, stage, "member", None
    )


class FakeFspClient:
    def __init__(self) -> None:
        self.athletes = {
            "FSP-1": (
                FspAthlete("FSP-1", "Анна", "Москва", "КМС"),
                [result("r1", "product", "national", 2)],
            ),
            "FSP-2": (
                FspAthlete("FSP-2", "Илья", "Томск", None),
                [result("r2", "security", "regional", None, "qualification")],
            ),
            "FSP-3": (FspAthlete("FSP-3", "Олег", None, None), []),
        }
        self.requests: dict[str, str] = {}

    def _get(self, athlete_id: str):
        if athlete_id not in self.athletes:
            raise NotFoundError("спортсмен ФСП не найден")
        return self.athletes[athlete_id]

    async def get_athlete(self, athlete_id: str) -> FspAthlete:
        return self._get(athlete_id)[0]

    async def get_results(self, athlete_id: str) -> list[FspResult]:
        return list(self._get(athlete_id)[1])

    async def start_verification(self, athlete_id: str) -> FspVerificationStart:
        self._get(athlete_id)
        request_id = f"req-{athlete_id}-{len(self.requests)}"
        self.requests[request_id] = athlete_id
        return FspVerificationStart(request_id, "a***@example.org", 600, CODE)

    async def confirm_verification(self, request_id: str, code: str) -> str:
        if code != CODE or request_id not in self.requests:
            raise FspVerificationError("неверный или просроченный код")
        return self.requests.pop(request_id)

    async def aclose(self) -> None:
        return None
