from fastapi import APIRouter, Depends, Query
from api.core.deps import db_conn
from api.schemas import TradeResponse, StatsResponse
from api.services import trade_service

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=list[TradeResponse])
def list_trades(
    city_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, le=100),
    conn=Depends(db_conn),
):
    return trade_service.get_trades(conn, city_id, status, limit)


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    city_id: str | None = None,
    conn=Depends(db_conn),
):
    return trade_service.get_stats(conn, city_id)


@router.get("/positions")
def open_positions(conn=Depends(db_conn)):
    return trade_service.get_open_positions(conn)