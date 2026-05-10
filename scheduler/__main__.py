"""
__main__.py — STORM v2 scheduler entrypoint
Run with: python -m scheduler
"""

import argparse
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
    EVENT_SCHEDULER_STARTED,
)
from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.config import (
    DATABASE_URL,
    MIN_BOUNDARY_MARGIN,
    POLY_DRY_RUN,
    SCHEDULER_HEARTBEAT_SECONDS,
    SCHEDULER_RUN_ON_START,
)
from scheduler.db import (
    get_conn,
    ensure_runtime_schema,
    load_active_cities,
    load_city_sources,
    load_market_configs,
    log_trade,
    log_run,
    get_daily_loss,
    get_last_taf,
    save_last_taf,
    get_open_trade,
    get_existing_trade_for_slug,
)
from scheduler.core.fetcher import fetch_taf
from scheduler.core.market import build_slug, get_market_bins, find_target_bin
from scheduler.core.risk import check_risk, check_entry_gate
from scheduler.core.executor import buy_yes
from scheduler.core.resolver import run_resolver
from scheduler.strategies.registry import STRATEGY_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def run_cycle(force: bool = False):
    """
    force=True  → TAF-triggered cycle (enter immediately if TAF changed)
    force=False → normal 30-min cycle (pass entry gate normally)
    """
    logger.info(f"=== cycle start (force={force}) ===")
    conn = get_conn()
    ensure_runtime_schema(conn)

    cities = load_active_cities(conn)
    if not cities:
        logger.warning("no active cities")
        conn.close()
        return

    for city in cities:
        logger.info(f"--- {city.name} ({city.station}) strategy={city.strategy_code} ---")

        strategy = STRATEGY_REGISTRY.get(city.strategy_code)
        if not strategy:
            logger.error(f"[{city.name}] no strategy for '{city.strategy_code}'")
            continue

        sources_config = load_city_sources(conn, city.id)
        market_configs = load_market_configs(conn, city.id)

        if not market_configs:
            logger.warning(f"[{city.name}] no enabled market configs")
            continue

        pending_markets = []
        market_date = _city_now(city.timezone)
        for mc in market_configs:
            market_slug = build_slug(mc.slug_pattern, market_date)
            logger.info(
                f"  [{city.name}] config market_type={mc.market_type} "
                f"slug={market_slug}"
            )

            existing_slug_trade = get_existing_trade_for_slug(
                conn,
                city.id,
                mc.id,
                market_slug,
            )
            if existing_slug_trade:
                logger.info(
                    f"  [{city.name}] already traded slug={market_slug} "
                    f"status={existing_slug_trade['status']} "
                    f"bin={existing_slug_trade['bin_label']} — skip fetch"
                )
                continue

            logger.info(f"  [{city.name}] no trade for slug={market_slug} — will fetch data")
            pending_markets.append((mc, market_date, market_slug))

        if not pending_markets:
            logger.info(f"[{city.name}] all enabled market configs already traded")
            continue

        # ── TAF fetch + change detection ──────────────────────────────────
        taf = fetch_taf(city.station)
        last_taf_raw = get_last_taf(conn, city.id)
        taf_changed = _taf_values_changed(taf, last_taf_raw)

        if taf and taf_changed:
            logger.info(f"[{city.name}] TAF TX changed → saving new TAF")
            save_last_taf(conn, city.id, taf.raw)

        # ── entry gate ────────────────────────────────────────────────────
        triggered_by_taf = force and taf_changed
        gate_passed, gate_reason = check_entry_gate(
            taf=taf,
            taf_changed=taf_changed,
            triggered_by_taf=triggered_by_taf,
            city_timezone=city.timezone,
            require_taf=getattr(strategy, "requires_taf_entry", True),
        )

        if not gate_passed:
            logger.info(
                f"[{city.name}] entry gate will block execution after market fetch: "
                f"{gate_reason}"
            )

        for mc, market_date, market_slug in pending_markets:
            logger.info(f"  [{city.name}] market_type={mc.market_type}")
            logger.info(f"  [{city.name}] market_slug={market_slug}")

            raw_temp = strategy.estimate(city, sources_config)
            if raw_temp is None:
                if taf and taf.tx_temp is not None:
                    raw_temp = taf.tx_temp
                    logger.warning(
                        f"  [{city.name}] strategy estimate failed; "
                        f"fallback to fetched TAF TX={raw_temp:.2f}°C"
                    )
                else:
                    log_run(conn, city.id, mc.id,
                            taf.raw if taf else None,
                            taf.tx_temp if taf else None,
                            taf.tn_temp if taf else None,
                            None, None, "skipped",
                            f"market_slug={market_slug} estimate failed")
                    continue

            bin_temp = strategy.wu_to_bin_temp(raw_temp)
            logger.info(f"  [{city.name}] raw={raw_temp:.2f}°C → bin={bin_temp}°C")

            bins = get_market_bins(mc, date=market_date)
            if not bins:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} no market bins")
                continue

            target_bin = find_target_bin(float(bin_temp), bins, mc.market_type)
            if not target_bin:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} no bin matches {bin_temp}°C")
                continue

            taf_gate_passed, taf_gate_reason = _check_taf_tx_gate(taf)
            if not taf_gate_passed:
                logger.warning(f"  [{city.name}] buy gate BLOCK: {taf_gate_reason}")
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} target={target_bin.label} "
                        f"buy gate: {taf_gate_reason}")
                continue
            logger.info(f"  [{city.name}] buy gate TAF: {taf_gate_reason}")

            boundary_passed, boundary_reason = _check_boundary_gate(
                strategy,
                raw_temp,
                int(bin_temp),
            )
            if not boundary_passed:
                logger.warning(f"  [{city.name}] buy gate BLOCK: {boundary_reason}")
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} target={target_bin.label} "
                        f"buy gate: {boundary_reason}")
                continue
            logger.info(f"  [{city.name}] buy gate boundary: {boundary_reason}")

            if not gate_passed:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} target={target_bin.label} "
                        f"entry gate: {gate_reason}")
                continue

            # ── guard: no duplicate position ──────────────────────────────
            existing = get_open_trade(conn, city.id, mc.id, target_bin.market_id)
            if existing:
                if existing["bin_label"] == target_bin.label:
                    logger.info(
                        f"  [{city.name}] already in position: {target_bin.label} — skip"
                    )
                    continue
                else:
                    logger.warning(
                        f"  [{city.name}] estimate changed bin: "
                        f"{existing['bin_label']} → {target_bin.label} "
                        f"— holding original position"
                    )
                    continue

            # ── risk gate ─────────────────────────────────────────────────
            daily_loss = get_daily_loss(conn, city.id)
            resolve_at = _get_resolve_time(city)
            passed, reason = check_risk(target_bin, resolve_at, daily_loss)

            if not passed:
                log_trade(conn, city.id, mc.id, target_bin.market_id,
                          market_slug, target_bin.label,
                          raw_temp, target_bin.yes_price,
                          "skipped", reason)
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} {reason}")
                continue

            # ── execute ───────────────────────────────────────────────────
            result = buy_yes(target_bin)
            status = _order_status(result)
            log_trade(conn, city.id, mc.id, target_bin.market_id,
                      market_slug, target_bin.label,
                      raw_temp, target_bin.yes_price, status)
            log_run(conn, city.id, mc.id,
                    taf.raw if taf else None,
                    taf.tx_temp if taf else None,
                    taf.tn_temp if taf else None,
                    None, None, "executed",
                    f"market_slug={market_slug} "
                    f"bin={target_bin.label} price={target_bin.yes_price} "
                    f"taf_triggered={triggered_by_taf} status={status}")

    conn.close()
    logger.info("=== cycle end ===")


def _taf_values_changed(taf, last_taf_raw: str | None) -> bool:
    if taf is None:
        return False
    if last_taf_raw is None:
        return True

    def extract_temp(raw, token):
        m = re.search(rf'{token}(M?)(\d+)/\d+Z', raw)
        if m:
            t = float(m.group(2))
            return -t if m.group(1) == "M" else t
        return None

    new_values = (extract_temp(taf.raw, "TX"), extract_temp(taf.raw, "TN"))
    old_values = (extract_temp(last_taf_raw, "TX"), extract_temp(last_taf_raw, "TN"))
    changed = new_values != old_values
    if changed:
        logger.info(
            "TAF values changed: "
            f"TX {old_values[0]}°C → {new_values[0]}°C, "
            f"TN {old_values[1]}°C → {new_values[1]}°C"
        )
    return changed


def _get_resolve_time(city) -> datetime:
    now = datetime.now(tz=timezone.utc)
    resolve = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if resolve <= now:
        resolve += timedelta(days=1)
    return resolve


def _city_now(city_timezone: str) -> datetime:
    try:
        return datetime.now(tz=ZoneInfo(city_timezone))
    except Exception as e:
        logger.warning("timezone error for %s: %s; using UTC", city_timezone, e)
        return datetime.now(tz=timezone.utc)


def _check_taf_tx_gate(taf) -> tuple[bool, str]:
    if taf is None or taf.tx_temp is None:
        return False, "TAF TX required"
    return True, "ok"


def _check_boundary_gate(strategy, raw_temp: float, bin_temp: int) -> tuple[bool, str]:
    city_code = getattr(strategy, "city_code", "")
    if city_code == "HONG_KONG":
        fraction = abs(raw_temp - math.floor(raw_temp))
        distance = min(fraction, 1.0 - fraction)
        exact_boundary = math.isclose(distance, 0.0, abs_tol=1e-9)
    else:
        rounded = math.floor(raw_temp + 0.5)
        distance = 0.5 - abs(raw_temp - rounded)
        exact_boundary = math.isclose(distance, 0.0, abs_tol=1e-9)

    if exact_boundary:
        return True, (
            f"boundary exact: use rounded bin raw={raw_temp:.2f} bin={bin_temp}"
        )

    if distance + 1e-9 < MIN_BOUNDARY_MARGIN:
        return (
            False,
            f"estimate too close to bin boundary: raw={raw_temp:.2f} "
            f"bin={bin_temp} boundary_margin={distance:.2f} "
            f"< {MIN_BOUNDARY_MARGIN:.2f}",
        )

    return True, (
        f"boundary ok: raw={raw_temp:.2f} bin={bin_temp} "
        f"margin={distance:.2f}"
    )


def _order_status(result: dict | None) -> str:
    if not result:
        return "failed"
    if result.get("dry_run"):
        return "dry_run"
    return "open"


def _db_target() -> str:
    if not DATABASE_URL:
        return "not configured"
    if "@" in DATABASE_URL:
        return DATABASE_URL.rsplit("@", 1)[-1]
    return DATABASE_URL


def _format_next_run(dt) -> str:
    if dt is None:
        return "pending"
    return dt.astimezone(timezone.utc).isoformat()


def _job_overview(scheduler: BlockingScheduler) -> list[str]:
    jobs = sorted(
        scheduler.get_jobs(),
        key=lambda job: job.next_run_time or datetime.max.replace(tzinfo=timezone.utc),
    )
    return [f"{job.id}@{_format_next_run(job.next_run_time)}" for job in jobs]


def log_scheduler_ready(scheduler: BlockingScheduler) -> None:
    logger.info(
        "scheduler ready: dry_run=%s db=%s heartbeat=%ss",
        POLY_DRY_RUN,
        _db_target(),
        SCHEDULER_HEARTBEAT_SECONDS,
    )
    logger.info("startup run enabled: %s", SCHEDULER_RUN_ON_START)
    if SCHEDULER_RUN_ON_START and not POLY_DRY_RUN:
        logger.warning("startup cycle may place live orders because dry_run=False")
    for item in _job_overview(scheduler):
        logger.info("scheduled job: %s", item)


def run_heartbeat(scheduler: BlockingScheduler) -> None:
    overview = _job_overview(scheduler)
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

    # normal cycle every 30 min
    scheduler.add_job(run_normal, "interval", minutes=30, id="normal")

    if SCHEDULER_RUN_ON_START:
        scheduler.add_job(
            run_normal,
            "date",
            run_date=datetime.now(tz=timezone.utc),
            id="startup_normal",
        )

    # resolver every 30 min (offset by 15 min from normal cycle)
    scheduler.add_job(run_resolve, "interval", minutes=30, id="resolver",
                      start_date="2026-01-01 00:15:00")

    # TAF window cycles — every 5 min around TAF release times (UTC)
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

    return scheduler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STORM v2 scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run one normal scheduler cycle and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="with --once, treat the cycle as TAF-triggered",
    )
    parser.add_argument(
        "--resolve-once",
        action="store_true",
        help="run resolver once and exit",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="print configured job ids and exit",
    )
    args = parser.parse_args(argv)

    if args.once:
        run_cycle(force=args.force)
        return 0

    if args.resolve_once:
        run_resolve()
        return 0

    scheduler = build_scheduler()

    if args.list_jobs:
        for job in scheduler.get_jobs():
            print(f"{job.id}: {job.trigger}")
        return 0

    logger.info("STORM v2 starting...")
    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
