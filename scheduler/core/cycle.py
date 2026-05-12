"""Trading cycle orchestration for the scheduler."""

import logging

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
    get_failed_trade_for_slug,
    close_stale_failed_trades,
    update_trade_snapshot,
    update_trade_status,
)
from scheduler.core.fetcher import fetch_taf
from scheduler.core.market import build_slug, get_market_bins, find_target_bin
from scheduler.core.risk import check_risk, check_entry_gate
from scheduler.core.executor import buy_yes
from scheduler.core.cycle_utils import (
    check_boundary_gate,
    check_taf_tx_gate,
    current_market_date,
    get_resolve_time,
    order_status,
    taf_value_change,
    target_market_date,
)
from scheduler.notifications import (
    notify_order_result,
    notify_rebalance,
    notify_taf_changed,
)
from scheduler.strategies.registry import STRATEGY_REGISTRY

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
        today_market_date = current_market_date()
        target_date = target_market_date()
        for mc in market_configs:
            closed_failed = close_stale_failed_trades(
                conn,
                city.id,
                mc.id,
                today_market_date.date(),
            )
            if closed_failed:
                logger.info(
                    f"  [{city.name}] closed {closed_failed} stale failed trade(s) "
                    f"before market_date={today_market_date.date().isoformat()}"
                )

            today_slug = build_slug(mc.slug_pattern, today_market_date)
            if today_market_date.date() != target_date.date():
                today_failed_trade = get_failed_trade_for_slug(
                    conn,
                    city.id,
                    mc.id,
                    today_slug,
                )
                if today_failed_trade:
                    logger.info(
                        f"  [{city.name}] failed trade exists for today's "
                        f"market_slug={today_slug} id={today_failed_trade['id']} "
                        "— will refresh/update"
                    )
                    pending_markets.append((
                        mc,
                        today_market_date,
                        today_slug,
                        today_failed_trade,
                        None,
                    ))

            market_date = target_date
            market_slug = build_slug(mc.slug_pattern, market_date)
            logger.info(
                f"  [{city.name}] config market_type={mc.market_type} "
                f"target_date={market_date.date().isoformat()} "
                f"slug={market_slug}"
            )

            existing_slug_trade = get_existing_trade_for_slug(
                conn,
                city.id,
                mc.id,
                market_slug,
            )
            if existing_slug_trade:
                if existing_slug_trade["status"] in ("won", "lost"):
                    logger.info(
                        f"  [{city.name}] already resolved slug={market_slug} "
                        f"status={existing_slug_trade['status']} "
                        f"bin={existing_slug_trade['bin_label']} — skip fetch"
                    )
                    continue
                logger.info(
                    f"  [{city.name}] active trade exists for slug={market_slug} "
                    f"status={existing_slug_trade['status']} "
                    f"bin={existing_slug_trade['bin_label']} — will refresh"
                )
                pending_markets.append(
                    (mc, market_date, market_slug, None, existing_slug_trade)
                )
                continue

            failed_slug_trade = get_failed_trade_for_slug(
                conn,
                city.id,
                mc.id,
                market_slug,
            )
            if failed_slug_trade:
                logger.info(
                    f"  [{city.name}] failed trade exists for slug={market_slug} "
                    f"id={failed_slug_trade['id']} — will refresh/update"
                )
            else:
                logger.info(
                    f"  [{city.name}] no trade for slug={market_slug} — will fetch data"
                )
            pending_markets.append((mc, market_date, market_slug, failed_slug_trade, None))

        if not pending_markets:
            logger.info(f"[{city.name}] all enabled market configs already traded")
            continue

        # ── TAF fetch + change detection ──────────────────────────────────
        taf = fetch_taf(city.station)
        last_taf_raw = get_last_taf(conn, city.id)
        taf_change = taf_value_change(taf, last_taf_raw)
        taf_changed = taf_change.changed

        if taf and taf_changed:
            logger.info(f"[{city.name}] TAF TX changed → saving new TAF")
            save_last_taf(conn, city.id, taf.raw)

        triggered_by_taf = force and taf_changed

        for mc, market_date, market_slug, failed_trade, active_trade in pending_markets:
            logger.info(f"  [{city.name}] market_type={mc.market_type}")
            logger.info(f"  [{city.name}] market_slug={market_slug}")

            gate_passed, gate_reason = check_entry_gate(
                taf=taf,
                taf_changed=taf_changed,
                triggered_by_taf=triggered_by_taf,
                city_timezone=city.timezone,
                require_taf=getattr(strategy, "requires_taf_entry", True),
                target_date=market_date,
            )
            if not gate_passed:
                logger.info(
                    f"[{city.name}] entry gate will block execution after market fetch: "
                    f"{gate_reason}"
                )

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
                    _update_failed_trade_status(
                        conn,
                        failed_trade,
                        "estimate failed",
                    )
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
                _update_failed_trade_status(
                    conn,
                    failed_trade,
                    "no market bins",
                )
                continue

            target_bin = find_target_bin(float(bin_temp), bins, mc.market_type)
            if not target_bin:
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} no bin matches {bin_temp}°C")
                _update_failed_trade_status(
                    conn,
                    failed_trade,
                    f"no bin matches {bin_temp}°C",
                )
                continue

            if taf_changed:
                previous_bin = _previous_bin_label(failed_trade, active_trade)
                notify_taf_changed(
                    market_slug,
                    taf_change.old_tx,
                    taf_change.new_tx,
                    taf_change.old_tn,
                    taf_change.new_tn,
                    previous_bin,
                    target_bin.label,
                )

            _refresh_failed_trade_snapshot(
                conn,
                failed_trade,
                target_bin,
                market_slug,
                raw_temp,
                market_date,
                "refreshed failed trade; pending execution gates",
            )

            taf_gate_passed, taf_gate_reason = check_taf_tx_gate(taf)
            if not taf_gate_passed:
                logger.warning(f"  [{city.name}] buy gate BLOCK: {taf_gate_reason}")
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} target={target_bin.label} "
                        f"buy gate: {taf_gate_reason}")
                _refresh_failed_trade_snapshot(
                    conn,
                    failed_trade,
                    target_bin,
                    market_slug,
                    raw_temp,
                    market_date,
                    f"buy gate: {taf_gate_reason}",
                )
                continue
            logger.info(f"  [{city.name}] buy gate TAF: {taf_gate_reason}")

            boundary_passed, boundary_reason = check_boundary_gate(
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
                _refresh_failed_trade_snapshot(
                    conn,
                    failed_trade,
                    target_bin,
                    market_slug,
                    raw_temp,
                    market_date,
                    f"buy gate: {boundary_reason}",
                )
                continue
            logger.info(f"  [{city.name}] buy gate boundary: {boundary_reason}")

            if not gate_passed:
                logger.warning(f"  [{city.name}] entry gate BLOCK: {gate_reason}")
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} target={target_bin.label} "
                        f"entry gate: {gate_reason}")
                _refresh_failed_trade_snapshot(
                    conn,
                    failed_trade,
                    target_bin,
                    market_slug,
                    raw_temp,
                    market_date,
                    f"entry gate: {gate_reason}",
                )
                continue

            if active_trade and active_trade["bin_label"] == target_bin.label:
                _handle_rebalance_if_needed(
                    conn,
                    city,
                    mc,
                    active_trade,
                    target_bin,
                    market_slug,
                    raw_temp,
                    market_date,
                    taf,
                )
                continue

            # ── guard: no duplicate position ──────────────────────────────
            existing = get_open_trade(conn, city.id, mc.id, target_bin.market_id)
            if existing:
                if existing["bin_label"] == target_bin.label:
                    logger.info(
                        f"  [{city.name}] already in position: {target_bin.label} — skip"
                    )
                    _refresh_failed_trade_snapshot(
                        conn,
                        failed_trade,
                        target_bin,
                        market_slug,
                        raw_temp,
                        market_date,
                        "open position already exists",
                    )
                    continue
                else:
                    logger.warning(
                        f"  [{city.name}] estimate changed bin: "
                        f"{existing['bin_label']} → {target_bin.label} "
                        f"— holding original position"
                    )
                    _refresh_failed_trade_snapshot(
                        conn,
                        failed_trade,
                        target_bin,
                        market_slug,
                        raw_temp,
                        market_date,
                        f"holding existing open bin {existing['bin_label']}",
                    )
                    continue

            # ── risk gate ─────────────────────────────────────────────────
            daily_loss = get_daily_loss(conn, city.id)
            resolve_at = get_resolve_time(city)
            passed, reason = check_risk(target_bin, resolve_at, daily_loss)

            if not passed:
                if failed_trade:
                    _refresh_failed_trade_snapshot(
                        conn,
                        failed_trade,
                        target_bin,
                        market_slug,
                        raw_temp,
                        market_date,
                        reason,
                    )
                else:
                    log_trade(conn, city.id, mc.id, target_bin.market_id,
                              market_slug, target_bin.label,
                              raw_temp, target_bin.yes_price,
                              "skipped", reason, target_bin.end_date,
                              market_date.date())
                log_run(conn, city.id, mc.id,
                        taf.raw if taf else None,
                        taf.tx_temp if taf else None,
                        taf.tn_temp if taf else None,
                        None, None, "skipped",
                        f"market_slug={market_slug} {reason}")
                continue

            rebalanced = _handle_rebalance_if_needed(
                conn,
                city,
                mc,
                active_trade,
                target_bin,
                market_slug,
                raw_temp,
                market_date,
                taf,
            )
            if rebalanced == "unchanged" or rebalanced == "blocked":
                continue

            # ── execute ───────────────────────────────────────────────────
            result = buy_yes(target_bin)
            status = order_status(result)
            skip_reason = None
            if status == "failed":
                skip_reason = "order failed on retry" if failed_trade else "order failed"
            if failed_trade:
                update_trade_snapshot(
                    conn,
                    failed_trade["id"],
                    target_bin.market_id,
                    market_slug,
                    target_bin.label,
                    raw_temp,
                    target_bin.yes_price,
                    status,
                    skip_reason,
                    target_bin.end_date,
                    market_date.date(),
                )
                logger.info(
                    f"  [{city.name}] updated failed trade "
                    f"id={failed_trade['id']} status={status}"
                )
            else:
                log_trade(conn, city.id, mc.id, target_bin.market_id,
                          market_slug, target_bin.label,
                          raw_temp, target_bin.yes_price, status, skip_reason,
                          target_bin.end_date, market_date.date())
            notify_order_result(
                market_slug,
                status,
                target_bin.label,
                raw_temp,
                target_bin.yes_price,
            )
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


def _previous_bin_label(*trades: dict | None) -> str | None:
    for trade in trades:
        if trade and trade.get("bin_label"):
            return trade["bin_label"]
    return None


def _handle_rebalance_if_needed(
    conn,
    city,
    mc,
    active_trade: dict | None,
    target_bin,
    market_slug: str,
    raw_temp: float,
    market_date,
    taf,
) -> str | None:
    if not active_trade:
        return None

    old_bin = active_trade["bin_label"]
    old_status = active_trade["status"]

    if old_bin == target_bin.label:
        update_trade_snapshot(
            conn,
            active_trade["id"],
            target_bin.market_id,
            market_slug,
            target_bin.label,
            raw_temp,
            target_bin.yes_price,
            old_status,
            None,
            target_bin.end_date,
            market_date.date(),
        )
        log_run(conn, city.id, mc.id,
                taf.raw if taf else None,
                taf.tx_temp if taf else None,
                taf.tn_temp if taf else None,
                None, None, "skipped",
                f"market_slug={market_slug} active trade unchanged "
                f"bin={target_bin.label} price={target_bin.yes_price}")
        logger.info(
            f"  [{city.name}] active trade unchanged: "
            f"id={active_trade['id']} bin={target_bin.label}"
        )
        return "unchanged"

    reason = (
        f"rebalanced to {target_bin.label}: "
        f"old_bin={old_bin} new_bin={target_bin.label} "
        f"temp={raw_temp:.2f} price={target_bin.yes_price}"
    )

    if old_status == "dry_run":
        update_trade_status(conn, active_trade["id"], "closed", reason)
        notify_rebalance(
            market_slug,
            old_bin,
            target_bin.label,
            "closed old row, created new row",
            "TAF update changed target bin",
        )
        logger.info(
            f"  [{city.name}] closed dry_run trade for rebalance: "
            f"id={active_trade['id']} {old_bin} → {target_bin.label}"
        )
        return "rebalanced"

    if old_status == "open":
        block_reason = (
            f"rebalance needed {old_bin} → {target_bin.label}, "
            "but live sell execution is not implemented"
        )
        notify_rebalance(
            market_slug,
            old_bin,
            target_bin.label,
            "blocked",
            "live sell execution is not implemented",
        )
        log_run(conn, city.id, mc.id,
                taf.raw if taf else None,
                taf.tx_temp if taf else None,
                taf.tn_temp if taf else None,
                None, None, "skipped",
                f"market_slug={market_slug} {block_reason}")
        logger.warning(f"  [{city.name}] {block_reason}")
        return "blocked"

    return None


def _update_failed_trade_status(conn, failed_trade: dict | None, reason: str) -> None:
    if not failed_trade:
        return
    update_trade_status(conn, failed_trade["id"], "failed", reason)
    logger.info(
        "updated failed trade id=%s reason=%s",
        failed_trade["id"],
        reason,
    )


def _refresh_failed_trade_snapshot(
    conn,
    failed_trade: dict | None,
    target_bin,
    market_slug: str,
    raw_temp: float,
    market_date,
    reason: str,
) -> None:
    if not failed_trade:
        return
    update_trade_snapshot(
        conn,
        failed_trade["id"],
        target_bin.market_id,
        market_slug,
        target_bin.label,
        raw_temp,
        target_bin.yes_price,
        "failed",
        reason,
        target_bin.end_date,
        market_date.date(),
    )
    logger.info(
        "refreshed failed trade id=%s bin=%s temp=%.2f price=%.3f reason=%s",
        failed_trade["id"],
        target_bin.label,
        raw_temp,
        target_bin.yes_price,
        reason,
    )
