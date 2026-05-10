"""
market.py — STORM v2
Fetch bins from Polymarket Gamma API and parse market data.
"""

import json
import logging
import re
from datetime import datetime, timezone

import httpx

from scheduler.models import MarketConfig, MarketBin

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com/events/slug"
TIMEOUT = 10


def build_slug(pattern: str, date: datetime) -> str:
    """
    'highest-temperature-in-seoul-on-{date}' + 2026-05-11
    → 'highest-temperature-in-seoul-on-may-11-2026'
    """
    date_str = date.strftime("%B-%-d-%Y").lower()
    return pattern.replace("{date}", date_str)


def get_market_bins(
    config: MarketConfig,
    date: datetime | None = None,
) -> list[MarketBin]:
    """Fetch bins for a market on the given date."""
    if date is None:
        date = datetime.now(tz=timezone.utc)

    slug = build_slug(config.slug_pattern, date)
    url = f"{GAMMA_API}/{slug}"
    logger.info(f"[market] slug={slug}")
    logger.info(f"[market] GET {url}")

    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return _parse_bins(data, config.market_type)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"[market] market not found: {slug}")
        else:
            logger.error(f"[market] HTTP error: {e}")
        return []
    except Exception as e:
        logger.error(f"[market] fetch failed: {e}")
        return []


def get_resolve_time(config: MarketConfig, date: datetime | None = None) -> datetime | None:
    """Fetch endDate from event as the real resolve time."""
    if date is None:
        date = datetime.now(tz=timezone.utc)

    slug = build_slug(config.slug_pattern, date)
    url = f"{GAMMA_API}/{slug}"

    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        end_date = data.get("endDate")
        if end_date:
            return datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except Exception as e:
        logger.warning(f"[market] get_resolve_time failed: {e}")

    return None


def find_target_bin(
    estimated_temp: float,
    bins: list[MarketBin],
    market_type: str,
) -> MarketBin | None:
    """Select the bin that covers estimated_temp."""
    for bin_ in bins:
        if _temp_matches_bin(estimated_temp, bin_.label):
            logger.info(
                f"[market] target={bin_.label} "
                f"yes_price={bin_.yes_price:.3f} "
                f"market_id={bin_.market_id}"
            )
            return bin_

    logger.warning(f"[market] no bin matches {estimated_temp}°C")
    return None


# ── internal ──────────────────────────────────────────────────────────────────

def _parse_bins(data: dict, market_type: str) -> list[MarketBin]:
    bins = []
    markets = data.get("markets", [])

    for m in markets:
        if not m.get("acceptingOrders", False):
            continue
        if m.get("closed") or m.get("archived"):
            continue

        label = m.get("groupItemTitle", "")
        if not label:
            continue

        yes_price = _parse_yes_price(m.get("outcomePrices", "[]"))
        if yes_price is None:
            continue

        clob_token_ids = _parse_clob_token_ids(m.get("clobTokenIds", "[]"))
        yes_token_id = clob_token_ids[0] if clob_token_ids else ""

        bins.append(MarketBin(
            label=label,
            yes_price=yes_price,
            probability=yes_price,
            market_id=m.get("id", ""),
            market_type=market_type,
            yes_token_id=yes_token_id,
            end_date=m.get("endDate", ""),
            order_min=float(m.get("orderMinSize", 5)),
            condition_id=m.get("conditionId", ""),
        ))

    bins.sort(key=lambda b: _parse_threshold(b.label))
    logger.info(f"[market] parsed {len(bins)} bins")
    return bins


def _parse_yes_price(outcome_prices_str: str) -> float | None:
    try:
        prices = json.loads(outcome_prices_str)
        if prices:
            return float(prices[0])
    except Exception:
        pass
    return None


def _parse_clob_token_ids(clob_str: str) -> list[str]:
    try:
        return json.loads(clob_str)
    except Exception:
        return []


def _parse_threshold(label: str) -> float:
    m = re.search(r'(\d+)', label)
    return float(m.group(1)) if m else 999.0


def _temp_matches_bin(temp: float, label: str) -> bool:
    m = re.match(r'(\d+)°C or higher', label, re.IGNORECASE)
    if m:
        return temp >= float(m.group(1))

    m = re.match(r'(\d+)°C or below', label, re.IGNORECASE)
    if m:
        return temp <= float(m.group(1))

    m = re.match(r'[Bb]elow (\d+)°C', label)
    if m:
        return temp < float(m.group(1))

    m = re.match(r'^(\d+)°C$', label)
    if m:
        return int(temp) == int(m.group(1))

    return False
