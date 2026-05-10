"""
resolver.py — STORM v2
Resolves open trades after market settlement.

Checks Polymarket Gamma API for resolved markets,
updates trades with won/lost status and PnL.
"""

import logging
from datetime import datetime, timezone

import httpx

from scheduler.config import BET_AMOUNT
from scheduler.db import get_conn

logger = logging.getLogger(__name__)

GAMMA_MARKET_URL = "https://gamma-api.polymarket.com/markets"
TIMEOUT = 10


def run_resolver():
    """
    Main resolver loop:
    1. Fetch open trades past resolve time
    2. Check if market is resolved on Polymarket
    3. Update trade status + PnL
    """
    logger.info("=== resolver start ===")
    conn = get_conn()

    try:
        trades = _get_open_past_resolve(conn)

        if not trades:
            logger.info("[resolver] no open trades past resolve time — skip")
            conn.close()
            return

        logger.info(f"[resolver] found {len(trades)} trades to check")

        for trade in trades:
            _resolve_trade(conn, trade)

    except Exception as e:
        logger.error(f"[resolver] unexpected error: {e}")
    finally:
        conn.close()

    logger.info("=== resolver end ===")


def _resolve_trade(conn, trade: dict):
    """Resolve a single trade by checking Polymarket market status."""
    trade_id = trade["id"]
    market_id = trade["market_id"]
    bin_label = trade["bin_label"]

    try:
        # Double-check status hasn't changed (race condition guard)
        if trade["status"] != "open":
            logger.warning(f"[resolver] trade {trade_id} no longer open — skip")
            return

        # Fetch market resolution from Gamma API
        result = _fetch_market_result(market_id)

        if result is None:
            logger.info(f"[resolver] market {market_id} not yet resolved — skip")
            return

        resolved, outcome = result

        if not resolved:
            logger.info(f"[resolver] market {market_id} not resolved yet")
            return

        # Determine win/loss
        yes_price = trade["yes_price"]
        amount_usd = trade["amount_usd"]
        shares = amount_usd / yes_price

        if outcome == "Yes":
            status = "won"
            pnl = (shares * 1.0) - amount_usd
        else:
            status = "lost"
            pnl = -amount_usd

        # Update trade
        _update_trade_result(conn, trade_id, status, pnl)

        logger.info(
            f"[resolver] {bin_label} → {status} | "
            f"outcome={outcome} shares={shares:.2f} "
            f"pnl={pnl:+.2f} USD | market={market_id}"
        )

    except Exception as e:
        logger.error(f"[resolver] error resolving trade {trade_id}: {e}")


def _fetch_market_result(market_id: str) -> tuple[bool, str] | None:
    """
    Fetch market resolution from Polymarket Gamma API.

    Returns:
        (resolved, outcome) tuple if market data found, None on error.
        outcome is "Yes" or "No".
    """
    url = f"{GAMMA_MARKET_URL}/{market_id}"

    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        resolved = data.get("resolved", False)
        outcome = data.get("outcome", "")

        if not resolved:
            return (False, "")

        return (True, outcome)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"[resolver] market not found: {market_id}")
        else:
            logger.error(f"[resolver] HTTP error for {market_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"[resolver] fetch failed for {market_id}: {e}")
        return None


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_open_past_resolve(conn) -> list[dict]:
    """
    Get open trades where the market should have resolved by now.
    Uses created_at + 24h as a proxy for resolve time
    (markets resolve within 24h of creation).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT id, city_id, market_config_id, market_id,
               bin_label, yes_price, amount_usd, status, created_at
        FROM trades
        WHERE status = 'open'
          AND created_at < NOW() - INTERVAL '12 hours'
        ORDER BY created_at ASC
    """)
    return cur.fetchall()


def _update_trade_result(conn, trade_id, status: str, pnl: float):
    """Update trade with resolution result."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE trades
        SET status = %s,
            pnl = %s,
            resolved_at = NOW()
        WHERE id = %s
          AND status = 'open'
    """, (status, pnl, str(trade_id)))
    conn.commit()
