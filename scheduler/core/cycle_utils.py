"""Utility helpers for scheduler trade cycles."""

import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from scheduler.config import MARKET_TARGET_TIMEZONE, MIN_BOUNDARY_MARGIN

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TAFValueChange:
    changed: bool
    old_tx: float | None
    new_tx: float | None
    old_tn: float | None
    new_tn: float | None


def taf_values_changed(taf, last_taf_raw: str | None) -> bool:
    return taf_value_change(taf, last_taf_raw).changed


def taf_value_change(taf, last_taf_raw: str | None) -> TAFValueChange:
    if taf is None:
        return TAFValueChange(False, None, None, None, None)
    if last_taf_raw is None:
        new_values = (_extract_taf_temp(taf.raw, "TX"), _extract_taf_temp(taf.raw, "TN"))
        return TAFValueChange(True, None, new_values[0], None, new_values[1])

    new_values = (_extract_taf_temp(taf.raw, "TX"), _extract_taf_temp(taf.raw, "TN"))
    old_values = (
        _extract_taf_temp(last_taf_raw, "TX"),
        _extract_taf_temp(last_taf_raw, "TN"),
    )
    changed = new_values != old_values
    if changed:
        logger.info(
            "TAF values changed: "
            f"TX {old_values[0]}°C → {new_values[0]}°C, "
            f"TN {old_values[1]}°C → {new_values[1]}°C"
        )
    return TAFValueChange(
        changed,
        old_values[0],
        new_values[0],
        old_values[1],
        new_values[1],
    )


def _extract_taf_temp(raw: str | None, token: str) -> float | None:
    if not raw:
        return None
    m = re.search(rf'{token}(M?)(\d+)/\d+Z', raw)
    if m:
        t = float(m.group(2))
        return -t if m.group(1) == "M" else t
    return None


def get_resolve_time(city) -> datetime:
    now = datetime.now(tz=timezone.utc)
    resolve = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if resolve <= now:
        resolve += timedelta(days=1)
    return resolve


def city_now(city_timezone: str) -> datetime:
    try:
        return datetime.now(tz=ZoneInfo(city_timezone))
    except Exception as e:
        logger.warning("timezone error for %s: %s; using UTC", city_timezone, e)
        return datetime.now(tz=timezone.utc)


def target_market_date() -> datetime:
    """Return D+1 from the configured trading-day timezone."""
    return city_now(MARKET_TARGET_TIMEZONE) + timedelta(days=1)


def current_market_date() -> datetime:
    """Return the current trading-day date in the configured timezone."""
    return city_now(MARKET_TARGET_TIMEZONE)


def check_taf_tx_gate(taf) -> tuple[bool, str]:
    if taf is None or taf.tx_temp is None:
        return False, "TAF TX required"
    return True, "ok"


def check_boundary_gate(strategy, raw_temp: float, bin_temp: int) -> tuple[bool, str]:
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


def order_status(result: dict | None) -> str:
    if not result:
        return "failed"
    if result.get("dry_run"):
        return "dry_run"
    return "open"
