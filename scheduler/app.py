"""STORM v2 scheduler application wiring."""

import logging
from datetime import datetime, timezone

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
    EVENT_SCHEDULER_STARTED,
)
from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.config import (
    POLY_DRY_RUN,
    SCHEDULER_HEARTBEAT_SECONDS,
    SCHEDULER_RUN_ON_START,
)
from scheduler.core.cycle import run_cycle
from scheduler.core.resolver import run_resolver
from scheduler.runtime_utils import db_target, job_overview

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def log_scheduler_ready(scheduler: BlockingScheduler) -> None:
    logger.info(
        "scheduler ready: dry_run=%s db=%s heartbeat=%ss",
        POLY_DRY_RUN,
        db_target(),
        SCHEDULER_HEARTBEAT_SECONDS,
    )
    logger.info("startup run enabled: %s", SCHEDULER_RUN_ON_START)
    if SCHEDULER_RUN_ON_START and not POLY_DRY_RUN:
        logger.warning("startup cycle may place live orders because dry_run=False")
    for item in job_overview(scheduler):
        logger.info("scheduled job: %s", item)


def run_heartbeat(scheduler: BlockingScheduler) -> None:
    overview = job_overview(scheduler)
    next_jobs = ", ".join(overview[:3]) if overview else "none"
    logger.info("heartbeat: alive dry_run=%s next=%s", POLY_DRY_RUN, next_jobs)


def make_scheduler_listener(scheduler: BlockingScheduler):
    def _listener(event) -> None:
        if event.code == EVENT_SCHEDULER_STARTED:
            log_scheduler_ready(scheduler)
            return

        job_id = getattr(event, "job_id", "unknown")
        if event.code == EVENT_JOB_SUBMITTED:
            logger.info("job submitted: %s", job_id)
        elif event.code == EVENT_JOB_EXECUTED:
            logger.info("job completed: %s", job_id)
        elif event.code == EVENT_JOB_MISSED:
            logger.warning("job missed: %s", job_id)
        elif event.code == EVENT_JOB_ERROR:
            exc = event.exception
            exc_info = (type(exc), exc, exc.__traceback__) if exc else None
            logger.error("job failed: %s", job_id, exc_info=exc_info)

    return _listener


# ── scheduler setup ───────────────────────────────────────────────────────────

def run_normal():
    run_cycle(force=False)


def run_taf_window():
    run_cycle(force=True)


def run_resolve():
    """Resolve open trades that are past their market end time."""
    run_resolver()


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_listener(
        make_scheduler_listener(scheduler),
        EVENT_SCHEDULER_STARTED
        | EVENT_JOB_SUBMITTED
        | EVENT_JOB_EXECUTED
        | EVENT_JOB_MISSED
        | EVENT_JOB_ERROR,
    )

    _add_cycle_jobs(scheduler)
    _add_resolver_job(scheduler)
    _add_taf_window_jobs(scheduler)
    _add_heartbeat_job(scheduler)

    return scheduler


def _add_cycle_jobs(scheduler: BlockingScheduler) -> None:
    scheduler.add_job(run_normal, "interval", minutes=30, id="normal")

    if SCHEDULER_RUN_ON_START:
        scheduler.add_job(
            run_normal,
            "date",
            run_date=datetime.now(tz=timezone.utc),
            id="startup_normal",
        )


def _add_resolver_job(scheduler: BlockingScheduler) -> None:
    """Run resolver often; DB filter waits until market endDate + 5m."""
    scheduler.add_job(run_resolve, "interval", minutes=5, id="resolver",
                      start_date="2026-01-01 00:05:00",
                      coalesce=True, max_instances=1)


def _add_taf_window_jobs(scheduler: BlockingScheduler) -> None:
    scheduler.add_job(run_taf_window, "cron",
                      hour=23, minute="50,55", id="taf_2300")
    scheduler.add_job(run_taf_window, "cron",
                      hour=0, minute="0,5,10,15", id="taf_0000")

    scheduler.add_job(run_taf_window, "cron",
                      hour=5, minute="50,55", id="taf_0550")
    scheduler.add_job(run_taf_window, "cron",
                      hour=6, minute="0,5,10,15", id="taf_0600")

    scheduler.add_job(run_taf_window, "cron",
                      hour=11, minute="50,55", id="taf_1150")
    scheduler.add_job(run_taf_window, "cron",
                      hour=12, minute="0,5,10,15", id="taf_1200")

    scheduler.add_job(run_taf_window, "cron",
                      hour=17, minute="50,55", id="taf_1750")
    scheduler.add_job(run_taf_window, "cron",
                      hour=18, minute="0,5,10,15", id="taf_1800")


def _add_heartbeat_job(scheduler: BlockingScheduler) -> None:
    if SCHEDULER_HEARTBEAT_SECONDS > 0:
        scheduler.add_job(
            run_heartbeat,
            "interval",
            seconds=SCHEDULER_HEARTBEAT_SECONDS,
            id="heartbeat",
            args=[scheduler],
            coalesce=True,
            max_instances=1,
        )
