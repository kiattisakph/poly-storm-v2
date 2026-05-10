import re
import logging
import httpx
from scheduler.models.domain import City
from scheduler.sources.base import TempSource

logger = logging.getLogger(__name__)


class TAFTXSource(TempSource):
    source_type = "TAF_TX"
    BASE_URL = "https://aviationweather.gov/api/data/taf"
    TIMEOUT = 10

    def fetch(self, city: City) -> float | None:
        url = f"{self.BASE_URL}?ids={city.station}&format=raw"
        try:
            resp = httpx.get(url, timeout=self.TIMEOUT)
            resp.raise_for_status()
            raw = resp.text.strip()
            logger.info(f"[TAF_TX] {city.station}: {raw[:80]}")
            return self._parse_tx(raw)
        except httpx.HTTPError as e:
            logger.error(f"[TAF_TX] fetch failed: {e}")
            return None

    def _parse_tx(self, taf_raw: str) -> float | None:
        """
        TX22/1006Z  → 22.0
        TXM05/0506Z → -5.0
        """
        match = re.search(r'TX(M?)(\d+)/(\d{4})Z', taf_raw)
        if not match:
            logger.warning("[TAF_TX] TX pattern not found")
            return None
        temp = float(match.group(2))
        if match.group(1) == "M":
            temp = -temp
        return temp