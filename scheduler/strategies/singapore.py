import logging
import httpx
from scheduler.models.domain import City, CitySource
from scheduler.strategies.base import CityStrategy

logger = logging.getLogger(__name__)

AIR_TEMP_URL    = "https://api-open.data.gov.sg/v2/real-time/api/air-temperature"
FORECAST_24H    = "https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast"
FORECAST_4DAY   = "https://api-open.data.gov.sg/v2/real-time/api/four-day-weather-forecast"
TIMEOUT         = 10

# Changi Airport station ID ใน NEA network
CHANGI_STATION_IDS = {"S24", "S100", "S104"}  # fallback ถ้าไม่มี S24


class SingaporeStrategy(CityStrategy):
    city_code = "SINGAPORE"
    requires_taf_entry = False

    def estimate(self, city: City, sources: list[CitySource]) -> float | None:
        """
        Singapore: ไม่มี TAF TX → ใช้ 2 layers
        1. 24hr forecast → high temp range (ใช้ตอนเช้าก่อน peak)
        2. air-temperature stations → track current max (ใช้ระหว่างวัน)
        weighted ตาม time of day
        """
        import datetime, pytz
        sgt = pytz.timezone("Asia/Singapore")
        hour_sgt = datetime.datetime.now(tz=sgt).hour

        forecast_max = self._fetch_forecast_max()
        current_max  = self._fetch_air_temp_max()

        logger.info(
            f"[Singapore] hour={hour_sgt} "
            f"forecast_max={forecast_max} "
            f"current_max={current_max}"
        )

        if forecast_max is None and current_max is None:
            logger.error("[Singapore] all sources failed")
            return None

        # ก่อน peak (< 12:00 SGT) → เชื่อ forecast มากกว่า
        # ระหว่าง/หลัง peak (>= 12:00 SGT) → เชื่อ current_max มากกว่า
        if hour_sgt < 12:
            if forecast_max and current_max:
                return forecast_max * 0.7 + current_max * 0.3
            return forecast_max or current_max

        else:
            if forecast_max and current_max:
                return current_max * 0.8 + forecast_max * 0.2
            return current_max or forecast_max

    def wu_to_bin_temp(self, raw_temp: float) -> int:
        """
        WU WSSS เก็บ °F (whole number) แล้ว display เป็น °C
        32.777°C → 91°F → 32.78°C → round → 33°C

        ต้อง simulate WU rounding เพื่อให้ตรงกับที่ Polymarket resolve
        """
        fahrenheit  = round(raw_temp * 9 / 5 + 32)   # WU rounds to whole °F
        celsius     = (fahrenheit - 32) * 5 / 9
        return round(celsius)

    # ── private ──────────────────────────────────────────────────────────────

    def _fetch_forecast_max(self) -> float | None:
        """
        ดึง 24hr forecast แล้วเอา high temp
        fallback ไป 4-day ถ้า 24hr ไม่มีข้อมูล
        """
        for url in [FORECAST_24H, FORECAST_4DAY]:
            try:
                resp = httpx.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") == 17:  # DATA_NOT_FOUND
                    continue

                # 24hr forecast: data.data.records[0].general.temperature.high
                records = (
                    data.get("data", {})
                        .get("records", [])
                )
                if not records:
                    continue

                temp_high = (
                    records[0]
                    .get("general", {})
                    .get("temperature", {})
                    .get("high")
                )
                if temp_high is not None:
                    logger.info(f"[Singapore] forecast high={temp_high}°C from {url}")
                    return float(temp_high)

            except Exception as e:
                logger.warning(f"[Singapore] forecast fetch failed ({url}): {e}")

        return None

    def _fetch_air_temp_max(self) -> float | None:
        """
        ดึง air temperature readings ทุก station
        เอา max ของ Changi-area stations เป็นหลัก
        fallback เป็น max ของทุก station ถ้าไม่มี Changi
        """
        try:
            resp = httpx.get(AIR_TEMP_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 17:
                logger.warning("[Singapore] air-temp DATA_NOT_FOUND")
                return None

            readings = (
                data.get("data", {})
                    .get("readings", [{}])[0]
                    .get("data", [])
            )
            if not readings:
                return None

            # prefer Changi stations
            changi_temps = [
                r["value"] for r in readings
                if r.get("stationId") in CHANGI_STATION_IDS
                and r.get("value") is not None
            ]
            if changi_temps:
                result = max(changi_temps)
                logger.info(f"[Singapore] Changi air_temp max={result}°C")
                return float(result)

            # fallback: max ทุก station
            all_temps = [r["value"] for r in readings if r.get("value") is not None]
            if all_temps:
                result = max(all_temps)
                logger.info(f"[Singapore] all-station air_temp max={result}°C")
                return float(result)

        except Exception as e:
            logger.error(f"[Singapore] air-temp fetch failed: {e}")

        return None
