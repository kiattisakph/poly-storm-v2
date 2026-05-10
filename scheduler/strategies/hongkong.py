"""
hongkong.py — STORM v2
Hong Kong strategy

Resolve source: Hong Kong Observatory (HKO)
  - "Absolute Daily Max (deg. C)" จาก Daily Extract
  - https://www.weather.gov.hk/en/cis/climat.htm
  - unit: °C ทศนิยม 1 ตำแหน่ง เช่น 29.2°C → bin 29°C

Bin matching: floor (ไม่ใช่ round)
  - 29.2°C → 29°C  ✅
  - 28.9°C → 28°C  ✅  (ถ้า round จะได้ 29°C ซึ่งผิด)

Data sources:
  - Primary: HKO Current Weather API (current temp real-time)
  - Forecast: HKO 9-day forecast API (max temp วันนี้)
  - Fallback: aviationweather.gov TAF VHHH (ICAO Chek Lap Kok)

ทุก API ของ HKO ฟรี ไม่ต้องใช้ API key
"""

import logging
import httpx
from scheduler.models.domain import City, CitySource
from scheduler.strategies.base import CityStrategy

logger = logging.getLogger(__name__)

# HKO Open Data API — ฟรี ไม่ต้อง key
HKO_CURRENT   = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en"
HKO_FORECAST   = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=fnd&lang=en"
HKO_WARNINGSUMMARY = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=en"
TAF_URL        = "https://aviationweather.gov/api/data/taf?ids=VHHH&format=raw"
TIMEOUT        = 10


class HongKongStrategy(CityStrategy):
    city_code = "HONG_KONG"

    def estimate(self, city: City, sources: list[CitySource]) -> float | None:
        """
        Hong Kong: ใช้ HKO API โดยตรง
        1. HKO forecast → max temp วันนี้ (ใช้ตอนเช้า)
        2. HKO current  → current temp ทุก station หา max (ใช้ระหว่างวัน)
        3. Fallback: TAF VHHH TX
        """
        import datetime, pytz
        hkt     = pytz.timezone("Asia/Hong_Kong")
        hour_hkt = datetime.datetime.now(tz=hkt).hour

        forecast_max = self._fetch_forecast_max()
        current_max  = self._fetch_current_max()

        logger.info(
            f"[HongKong] hour_hkt={hour_hkt} "
            f"forecast_max={forecast_max} "
            f"current_max={current_max}"
        )

        if forecast_max is None and current_max is None:
            # fallback: TAF VHHH
            return self._fetch_taf_tx()

        # ก่อนเที่ยง → เชื่อ forecast มากกว่า
        # หลังเที่ยง → เชื่อ current max มากกว่า
        if hour_hkt < 12:
            if forecast_max and current_max:
                return forecast_max * 0.7 + current_max * 0.3
            return forecast_max or current_max
        else:
            if forecast_max and current_max:
                # เอา max ของสองค่า เพราะ HKO resolve ค่าสูงสุด
                return max(forecast_max, current_max)
            return current_max or forecast_max

    def wu_to_bin_temp(self, raw_temp: float) -> int:
        """
        HKO ใช้ °C ทศนิยม 1 ตำแหน่ง และ Polymarket resolve ด้วย floor
        29.2°C → bin 29°C
        28.9°C → bin 28°C (ไม่ใช่ round!)

        หลักฐาน: May 3 peak=29.2°C → resolve เป็น 29°C
        """
        return int(raw_temp)  # floor

    # ── private ──────────────────────────────────────────────────────────────

    def _fetch_forecast_max(self) -> float | None:
        """
        HKO 9-day forecast → max temp วันแรก (วันนี้)
        Response: data.weatherForecast[0].forecastMaxtemp.value
        """
        try:
            resp = httpx.get(HKO_FORECAST, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            forecasts = data.get("weatherForecast", [])
            if not forecasts:
                return None

            today = forecasts[0]
            max_temp = today.get("forecastMaxtemp", {}).get("value")
            if max_temp is not None:
                logger.info(f"[HongKong] forecast max={max_temp}°C")
                return float(max_temp)

        except Exception as e:
            logger.warning(f"[HongKong] forecast fetch failed: {e}")

        return None

    def _fetch_current_max(self) -> float | None:
        """
        HKO current weather → temperature ทุก station หา max
        Response: data.temperature.data[].value
        """
        try:
            resp = httpx.get(HKO_CURRENT, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            stations = data.get("temperature", {}).get("data", [])
            if not stations:
                return None

            temps = [
                float(s["value"])
                for s in stations
                if s.get("value") is not None
            ]
            if not temps:
                return None

            result = max(temps)
            logger.info(f"[HongKong] current max={result}°C from {len(temps)} stations")
            return result

        except Exception as e:
            logger.warning(f"[HongKong] current fetch failed: {e}")

        return None

    def _fetch_taf_tx(self) -> float | None:
        """
        Fallback: TAF VHHH TX
        ใช้เฉพาะกรณี HKO API ล่ม
        """
        import re
        try:
            resp = httpx.get(TAF_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            raw = resp.text.strip()
            match = re.search(r'TX(M?)(\d+)/(\d{4})Z', raw)
            if match:
                temp = float(match.group(2))
                if match.group(1) == "M":
                    temp = -temp
                logger.info(f"[HongKong] TAF fallback TX={temp}°C")
                return temp
        except Exception as e:
            logger.warning(f"[HongKong] TAF fallback failed: {e}")

        return None