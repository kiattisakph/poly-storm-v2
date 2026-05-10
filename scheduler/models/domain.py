from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class City:
    id: UUID
    name: str
    station: str
    latitude: float
    longitude: float
    timezone: str
    strategy_code: str


@dataclass
class CitySource:
    id: UUID
    city_id: UUID
    source_type: str
    priority: int
    weight: float
    enabled: bool


@dataclass
class MarketConfig:
    id: UUID
    city_id: UUID
    market_type: str      # 'HIGHEST_TEMP', 'LOWEST_TEMP'
    slug_pattern: str     # 'highest-temperature-in-seoul-on-{date}'
    temp_field: str       # 'TX' | 'TN'
    enabled: bool


@dataclass
class EstimateResult:
    temp: float
    sources_used: list[str]
    is_single_source: bool


@dataclass
class TAFResult:
    raw: str
    tx_temp: float
    tn_temp: float | None
    tx_day: int
    tx_hour_utc: int
    fetched_at: datetime


@dataclass
class METARResult:
    raw: str
    current_temp: float
    wind_dir: int
    wind_kt: int
    fetched_at: datetime


@dataclass
class MarketBin:
    label: str            # 'groupItemTitle' e.g. '19°C', '22°C or higher'
    yes_price: float      # outcomePrices[0] e.g. 0.335
    probability: float    # same as yes_price (market implied %)
    market_id: str        # markets[].id
    market_type: str      # 'HIGHEST_TEMP', 'LOWEST_TEMP'
    yes_token_id: str     # clobTokenIds[0]
    end_date: str         # ISO string e.g. '2026-05-11T12:00:00Z'
    order_min: float      # orderMinSize e.g. 5.0 shares
    condition_id: str     # conditionId
