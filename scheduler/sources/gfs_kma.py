import logging
import httpx
from scheduler.models.domain import City
from scheduler.sources.base import TempSource

logger = logging.getLogger(__name__)


class GFSSource(TempSource):
    source_type = "GFS"
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    TIMEOUT = 10

    def fetch(self, city: City) -> float | None:
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "daily": "temperature_2m_max",
            "timezone": city.timezone,
            "models": "gfs_seamless",
            "forecast_days": 1,
        }
        try:
            resp = httpx.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            vals = data.get("daily", {}).get("temperature_2m_max", [])
            if not vals or vals[0] is None:
                logger.warning(f"[GFS] no data for {city.name}")
                return None
            logger.info(f"[GFS] {city.name}: {vals[0]}°C")
            return float(vals[0])
        except Exception as e:
            logger.error(f"[GFS] fetch failed: {e}")
            return None


class KMASource(TempSource):
    source_type = "KMA"
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    TIMEOUT = 10

    def fetch(self, city: City) -> float | None:
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "daily": "temperature_2m_max",
            "timezone": city.timezone,
            "models": "kma_seamless",
            "forecast_days": 1,
        }
        try:
            resp = httpx.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            vals = data.get("daily", {}).get("temperature_2m_max", [])
            if not vals or vals[0] is None:
                logger.warning(f"[KMA] no data for {city.name}")
                return None
            logger.info(f"[KMA] {city.name}: {vals[0]}°C")
            return float(vals[0])
        except Exception as e:
            logger.error(f"[KMA] fetch failed: {e}")
            return None