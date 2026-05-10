"""
risk.py — STORM v2
Risk gate + Entry time gate.
"""

import logging
import pytz
from datetime import datetime, timezone

from scheduler.config import DAILY_LOSS_LIMIT_USD, MIN_HOURS_TO_RESOLVE
from scheduler.models import MarketBin

logger = logging.getLogger(__name__)


# ── Entry gate ────────────────────────────────────────────────────────────────

def check_entry_gate(
    taf,
    taf_changed: bool,
    triggered_by_taf: bool,
    city_timezone: str,
    require_taf: bool = True,
) -> tuple[bool, str]:
    """
    Entry gate rules:
    1. Must have real TAF TX (no model-only estimate)
    2. If TAF changed (triggered_by_taf) → immediate entry
    3. Otherwise → only allowed in time windows
    """
    if require_taf and (taf is None or taf.tx_temp is None):
        return False, "no TAF TX available — model-only, skip"

    if triggered_by_taf and taf_changed:
        return True, "TAF TX changed → immediate entry"

    return _check_time_window(city_timezone)


def _check_time_window(city_timezone: str) -> tuple[bool, str]:
    """
    Allowed entry windows (local time):
    - Window A: 07:00-09:00 (post morning TAF)
    - Window B: 13:00-15:00 (post midday TAF + near peak)
    """
    try:
        tz = pytz.timezone(city_timezone)
        now = datetime.now(tz=tz)
        hour = now.hour

        if 7 <= hour < 9:
            return True, f"window A (morning) hour={hour}"
        if 13 <= hour < 15:
            return True, f"window B (afternoon) hour={hour}"

        return False, f"outside entry windows (hour={hour} local)"

    except Exception as e:
        logger.warning(f"timezone error: {e}")
        return False, f"timezone error: {e}"


# ── Risk gate ─────────────────────────────────────────────────────────────────

def check_risk(
    market_bin: MarketBin,
    resolve_at: datetime,
    daily_loss_usd: float,
) -> tuple[bool, str]:
    """Risk checks after entry gate passed."""
    now = datetime.now(tz=timezone.utc)

    if daily_loss_usd >= DAILY_LOSS_LIMIT_USD:
        reason = f"daily loss limit: ${daily_loss_usd:.2f} >= ${DAILY_LOSS_LIMIT_USD}"
        logger.warning(f"[risk] BLOCK — {reason}")
        return False, reason

    hours_left = (resolve_at - now).total_seconds() / 3600
    if hours_left < MIN_HOURS_TO_RESOLVE:
        reason = f"too close to resolve: {hours_left:.1f}h left"
        logger.warning(f"[risk] BLOCK — {reason}")
        return False, reason

    if market_bin.yes_price > 0.90:
        reason = f"yes price too high: {market_bin.yes_price:.2f}"
        logger.warning(f"[risk] BLOCK — {reason}")
        return False, reason

    logger.info(f"[risk] PASS — hours_left={hours_left:.1f}h loss=${daily_loss_usd:.2f}")
    return True, "ok"
