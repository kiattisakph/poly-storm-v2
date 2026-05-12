import logging
from scheduler.models.domain import City, CitySource
from scheduler.strategies.base import CityStrategy
from scheduler.core.estimator import estimate_max_temp

logger = logging.getLogger(__name__)

SEOUL_TAF_OFFSET_C = 1.0


class SeoulStrategy(CityStrategy):
    city_code = "SEOUL"

    def estimate(self, city: City, sources: list[CitySource]) -> float | None:
        """
        Seoul: TAF TX เป็น primary source
        ถ้า sources config มีหลายตัว → weighted mean ผ่าน estimator
        บวก fixed offset เพื่อ map forecast ไปยัง WU/Polymarket bin
        """
        result = estimate_max_temp(city, sources)
        if result is None:
            logger.warning(f"[Seoul] estimator returned None")
            return None

        final = result.temp + SEOUL_TAF_OFFSET_C

        logger.info(
            f"[Seoul] estimate={result.temp}°C "
            f"offset={SEOUL_TAF_OFFSET_C:+.1f}°C "
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
