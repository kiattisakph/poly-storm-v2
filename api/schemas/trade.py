from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class TradeResponse(BaseModel):
    id: UUID
    city_name: str
    station: str
    bin_label: str
    temp_estimate: float
    yes_price: float
    amount_usd: float
    status: str
    skip_reason: str | None
    pnl: float | None
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    won: int
    lost: int
    open: int
    skipped: int
    total_pnl: float
    today_loss: float