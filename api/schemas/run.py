from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class RunLogResponse(BaseModel):
    id: UUID
    city_name: str
    station: str
    taf_raw: str | None
    tx_temp: float | None
    tn_temp: float | None
    metar_temp: float | None
    wind_dir: int | None
    action: str | None
    note: str | None
    updated_date: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
