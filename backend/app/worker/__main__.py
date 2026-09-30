"""Точка входа worker: python -m app.worker. Запускает все задачи из JOBS по расписанию."""

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.worker.jobs import JOBS, Job

log = get_logger("worker")


async def _loop(job: Job) -> None:
    while True:
        try:
            await job.run()
        except Exception:
            log.exception("job %s failed", job.name)
        await asyncio.sleep(job.interval_seconds)


async def main() -> None:
    setup_logging(get_settings().log_level)
    log.info("starting %d job(s)", len(JOBS))
    await asyncio.gather(*(_loop(j) for j in JOBS))


if __name__ == "__main__":
    asyncio.run(main())
