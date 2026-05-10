"""
fetcher.py — STORM v2
TAF and METAR fetching from aviationweather.gov.
"""

import re
import logging
import httpx
from datetime import datetime, timezone

from scheduler.models import TAFResult, METARResult

logger = logging.getLogger(__name__)

BASE_TAF = "https://aviationweather.gov/api/data/taf"
BASE_METAR = "https://aviationweather.gov/api/data/metar"
TIMEOUT = 10


def fetch_taf(station: str) -> TAFResult | None:
    url = f"{BASE_TAF}?ids={station}&format=raw"
    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        raw = resp.text.strip()
        logger.info(f"[TAF] {station}: {raw[:80]}")

        match = re.search(r'TX(M?)(\d+)/(\d{2})(\d{2})Z', raw)
        if not match:
            logger.warning(f"[TAF] TX not found in {station}")
            return None

        temp = float(match.group(2))
        if match.group(1) == "M":
            temp = -temp

        tn_match = re.search(r'TN(M?)(\d+)/(\d{2})(\d{2})Z', raw)
        tn_temp = None
        if tn_match:
            tn_temp = float(tn_match.group(2))
            if tn_match.group(1) == "M":
                tn_temp = -tn_temp

        return TAFResult(
            raw=raw,
            tx_temp=temp,
            tn_temp=tn_temp,
            tx_day=int(match.group(3)),
            tx_hour_utc=int(match.group(4)),
            fetched_at=datetime.now(tz=timezone.utc),
        )
    except httpx.HTTPError as e:
        logger.error(f"[TAF] fetch failed: {e}")
        return None


def fetch_metar(station: str) -> METARResult | None:
    url = f"{BASE_METAR}?ids={station}&format=raw&hours=1"
    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        raw = resp.text.strip().splitlines()[0]
        logger.info(f"[METAR] {station}: {raw}")

        temp = _parse_temp(raw)
        wind_dir, wind_kt = _parse_wind(raw)

        if temp is None:
            return None

        return METARResult(
            raw=raw,
            current_temp=temp,
            wind_dir=wind_dir,
            wind_kt=wind_kt,
            fetched_at=datetime.now(tz=timezone.utc),
        )
    except httpx.HTTPError as e:
        logger.error(f"[METAR] fetch failed: {e}")
        return None


def get_wind_adjustment(wind_dir: int) -> float:
    if 157 <= wind_dir <= 247:
        return +1.0
    elif 67 <= wind_dir <= 157:
        return +0.5
    return 0.0


def _parse_temp(raw: str) -> float | None:
    match = re.search(r'\s(M?)(\d{2})/(M?)(\d{2})\s', raw)
    if not match:
        return None
    temp = float(match.group(2))
    return -temp if match.group(1) == "M" else temp


def _parse_wind(raw: str) -> tuple[int, int]:
    match = re.search(r'(\d{3})(\d{2})KT', raw)
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2))
