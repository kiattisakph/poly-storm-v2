import logging
from scheduler.models.domain import City, CitySource, EstimateResult
from scheduler.strategies.base import CityStrategy
from scheduler.core.fetcher import fetch_metar, get_wind_adjustment
from scheduler.core.estimator import estimate_max_temp

logger = logging.getLogger(__name__)


class SeoulStrategy(CityStrategy):
    city_code = "SEOUL"

    def estimate(self, city: City, sources: list[CitySource]) -> float | None:
        """
        Seoul: TAF TX เป็น primary source
        ถ้า sources config มีหลายตัว → weighted mean ผ่าน estimator
        บวก RKSI wind adjustment เสมอ
        """
        result = estimate_max_temp(city, sources)
        if result is None:
            logger.warning(f"[Seoul] estimator returned None")
            return None

        metar    = fetch_metar(city.station)
        wind_adj = get_wind_adjustment(metar.wind_dir) if metar else 0.0
        final    = result.temp + wind_adj

        logger.info(
            f"[Seoul] estimate={result.temp}°C "
            f"wind_adj={wind_adj:+.1f}°C "
            f"final={final}°C "
            f"sources={result.sources_used}"
        )
        return final

    def wu_to_bin_temp(self, raw_temp: float) -> int:
        """
        WU RKSI เก็บ °C โดยตรง → round ตรงๆ
        32.4 → 32, 32.5 → 33
        """
        return round(raw_temp)