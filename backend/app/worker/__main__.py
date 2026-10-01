"""Точка входа worker: python -m app.worker. Запускает все задачи из build_jobs по расписанию."""

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import get_database
from app.integrations.fsp import HttpFspClient
from app.worker.jobs import Job, build_jobs

log = get_logger("worker")


async def _loop(job: Job) -> None:
    while True:
        try:
            await job.run()
        except Exception:
            log.exception("job %s failed", job.name)
        await asyncio.sleep(job.interval_seconds)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    client = HttpFspClient(settings)
    jobs = build_jobs(settings, get_database(), client)
    log.info("starting %d job(s)", len(jobs))
    try:
        await asyncio.gather(*(_loop(j) for j in jobs))
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
