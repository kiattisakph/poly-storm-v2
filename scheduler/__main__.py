"""
__main__.py — STORM v2 scheduler entrypoint
Run with: python -m scheduler
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.db import (
    get_conn,
    load_active_cities,
    load_city_sources,
    load_market_configs,
    log_trade,
    log_run,
    get_daily_loss,
    get_last_taf,
    save_last_taf,
    get_open_trade,
)
from scheduler.core.fetcher import fetch_taf
from scheduler.core.market import get_market_bins, find_target_bin
from scheduler.core.risk import check_risk, check_entry_gate
from scheduler.core.executor import buy_yes
from scheduler.core.resolver import run_resolver
from scheduler.strategies.registry import STRATEGY_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_cycle(force: bool = False):
    """
    force=True  → TAF-triggered cycle (enter immediately if TAF changed)
    force=False → normal 30-min cycle (pass entry gate normally)
    """
    logger.info(f"=== cycle start (force={force}) ===")
    conn = get_conn()

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

        # ── TAF fetch + change detection ──────────────────────────────────
        taf = fetch_taf(city.station)
        last_taf_raw = get_last_taf(conn, city.id)
        taf_changed = _taf_tx_changed(taf, last_taf_raw)

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
        )

        if not gate_passed:
            logger.info(f"[{city.name}] entry gate: {gate_reason}")
            continue

        for mc in market_configs:
            logger.info(f"  [{city.name}] market_type={mc.market_type}")

            raw_temp = strategy.estimate(city, sources_config)
            if raw_temp is None:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped", "estimate failed")
                continue

            bin_temp = strategy.wu_to_bin_temp(raw_temp)
            logger.info(f"  [{city.name}] raw={raw_temp:.2f}°C → bin={bin_temp}°C")

            bins = get_market_bins(mc)
            if not bins:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped", "no market bins")
                continue

            target_bin = find_target_bin(float(bin_temp), bins, mc.market_type)
            if not target_bin:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped", f"no bin matches {bin_temp}°C")
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
                          target_bin.label, raw_temp, target_bin.yes_price,
                          "skipped", reason)
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped", reason)
                continue

            # ── execute ───────────────────────────────────────────────────
            result = buy_yes(target_bin)
            status = "open" if result else "failed"
            log_trade(conn, city.id, mc.id, target_bin.market_id,
                      target_bin.label, raw_temp, target_bin.yes_price, status)
            log_run(conn, city.id, mc.id,
                    taf.raw if taf else None,
                    taf.tx_temp if taf else None,
                    taf.tn_temp if taf else None,
                    None, None, "executed",
                    f"bin={target_bin.label} price={target_bin.yes_price} "
                    f"taf_triggered={triggered_by_taf}")

    conn.close()
    logger.info("=== cycle end ===")


def _taf_tx_changed(taf, last_taf_raw: str | None) -> bool:
    if taf is None:
        return False
    if last_taf_raw is None:
        return True

    def extract_tx(raw):
        m = re.search(r'TX(M?)(\d+)/\d+Z', raw)
        if m:
            t = float(m.group(2))
            return -t if m.group(1) == "M" else t
        return None

    new_tx = extract_tx(taf.raw)
    old_tx = extract_tx(last_taf_raw)
    changed = new_tx != old_tx
    if changed:
        logger.info(f"TAF TX changed: {old_tx}°C → {new_tx}°C")
    return changed


def _get_resolve_time(city) -> datetime:
    now = datetime.now(tz=timezone.utc)
    resolve = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if resolve <= now:
        resolve += timedelta(days=1)
    return resolve


# ── scheduler setup ───────────────────────────────────────────────────────────

def run_normal():
    run_cycle(force=False)


def run_taf_window():
    run_cycle(force=True)


def run_resolve():
    """Resolve open trades that are past their market end time."""
    run_resolver()


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")

    # normal cycle every 30 min
    scheduler.add_job(run_normal, "interval", minutes=30, id="normal")

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

    logger.info("STORM v2 starting...")
    scheduler.start()
