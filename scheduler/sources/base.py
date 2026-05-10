from abc import ABC, abstractmethod
from scheduler.models.domain import City


class TempSource(ABC):
    source_type: str

    @abstractmethod
    def fetch(self, city: City) -> float | None:
        """Fetch max temperature forecast for the given city. Returns °C or None."""
        ...
