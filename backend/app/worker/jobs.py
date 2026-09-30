"""Фоновые задачи. Каждая задача — наследник Job (паттерн Strategy); регистрируются в JOBS."""

from abc import ABC, abstractmethod

from app.core.logging import get_logger


class Job(ABC):
    name: str
    interval_seconds: int

    @abstractmethod
    async def run(self) -> None: ...


class HeartbeatJob(Job):
    name, interval_seconds = "heartbeat", 60

    async def run(self) -> None:
        get_logger(__name__).info("worker alive")


# Фаза 2+: FspSyncJob, CategoryRecalcJob, VacancyExpiryJob, ResumeParseJob
JOBS: list[Job] = [HeartbeatJob()]
