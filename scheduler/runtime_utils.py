"""Runtime helpers for the APScheduler entrypoint."""

from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.config import DATABASE_URL


def db_target() -> str:
    if not DATABASE_URL:
        return "not configured"
    if "@" in DATABASE_URL:
        return DATABASE_URL.rsplit("@", 1)[-1]
    return DATABASE_URL


def format_next_run(dt) -> str:
    if dt is None:
        return "pending"
    return dt.astimezone(timezone.utc).isoformat()


def job_overview(scheduler: BlockingScheduler) -> list[str]:
    jobs = sorted(
        scheduler.get_jobs(),
        key=lambda job: job.next_run_time or datetime.max.replace(tzinfo=timezone.utc),
    )
    return [f"{job.id}@{format_next_run(job.next_run_time)}" for job in jobs]
