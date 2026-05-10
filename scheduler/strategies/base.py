from abc import ABC, abstractmethod
from scheduler.models.domain import City, CitySource


class CityStrategy(ABC):
    city_code: str  # must match cities.strategy_code in DB
    requires_taf_entry: bool = True

    @abstractmethod
    def estimate(self, city: City, sources: list[CitySource]) -> float | None:
        """
        estimate max temp สำหรับเมืองนี้
        Returns float (°C) หรือ None ถ้าหาไม่ได้
        """
        ...

    @abstractmethod
    def wu_to_bin_temp(self, raw_temp: float) -> int:
        """
        แปลง raw temp → bin integer ตาม WU rounding ของเมืองนี้
        Seoul  : WU เก็บ °C → round ตรงๆ
        Singapore: WU เก็บ °F → แปลงกลับ → round
        """
        ...
