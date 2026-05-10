from uuid import UUID
from pydantic import BaseModel


class CityResponse(BaseModel):
    id: UUID
    name: str
    station: str
    latitude: float
    longitude: float
    timezone: str
    strategy_code: str
    active: bool

    class Config:
        from_attributes = True