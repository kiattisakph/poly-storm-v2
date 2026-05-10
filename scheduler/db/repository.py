"""
repository.py — STORM v2
All database queries in one place.
"""

import psycopg2
import psycopg2.extras
from uuid import UUID

from scheduler.config import DATABASE_URL
from scheduler.models import City, CitySource, MarketConfig


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def load_active_cities(conn) -> list[City]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, station, latitude, longitude, timezone, strategy_code
        FROM cities WHERE active = true
    """)
    return [City(**row) for row in cur.fetchall()]


def load_city_sources(conn, city_id: UUID) -> list[CitySource]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, city_id, source_type, priority, weight, enabled
        FROM city_sources WHERE city_id = %s ORDER BY priority ASC
    """, (str(city_id),))
    return [CitySource(**row) for row in cur.fetchall()]


def load_market_configs(conn, city_id: UUID) -> list[MarketConfig]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, city_id, market_type, slug_pattern, temp_field, enabled
        FROM market_configs WHERE city_id = %s AND enabled = true
    """, (str(city_id),))
    return [MarketConfig(**row) for row in cur.fetchall()]


def get_last_taf(conn, city_id: UUID) -> str | None:
    cur = conn.cursor()
    cur.execute("""
        SELECT taf_raw FROM run_logs
        WHERE city_id = %s AND taf_raw IS NOT NULL
        ORDER BY created_at DESC LIMIT 1
    """, (str(city_id),))
    row = cur.fetchone()
    return row["taf_raw"] if row else None


def save_last_taf(conn, city_id: UUID, taf_raw: str):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO run_logs (city_id, taf_raw, action, note)
        VALUES (%s, %s, 'taf_update', 'TAF TX changed')
    """, (str(city_id), taf_raw))
    conn.commit()


def get_open_trade(conn, city_id: UUID, market_config_id: UUID, market_id: str) -> dict | None:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, bin_label, yes_price, amount_usd, created_at
        FROM trades
        WHERE city_id = %s
          AND market_config_id = %s
          AND market_id = %s
          AND status = 'open'
        ORDER BY created_at DESC LIMIT 1
    """, (str(city_id), str(market_config_id), market_id))
    return cur.fetchone()


def log_trade(
    conn,
    city_id: UUID,
    market_config_id: UUID,
    market_id: str,
    bin_label: str,
    temp_estimate: float,
    yes_price: float,
    status: str,
    skip_reason: str = None,
):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO trades
            (city_id, market_config_id, market_id, bin_label,
             temp_estimate, yes_price, amount_usd, status, skip_reason)
        VALUES (%s, %s, %s, %s, %s, %s, 2.0, %s, %s)
    """, (str(city_id), str(market_config_id), market_id, bin_label,
          temp_estimate, yes_price, status, skip_reason))
    conn.commit()


def log_run(
    conn,
    city_id: UUID,
    market_config_id: UUID,
    taf_raw: str,
    tx_temp: float,
    tn_temp: float,
    metar_temp: float,
    wind_dir: int,
    action: str,
    note: str = None,
):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO run_logs
            (city_id, market_config_id, taf_raw, tx_temp, tn_temp,
             metar_temp, wind_dir, action, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (str(city_id), str(market_config_id), taf_raw, tx_temp, tn_temp,
          metar_temp, wind_dir, action, note))
    conn.commit()


def get_daily_loss(conn, city_id: UUID) -> float:
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM trades
        WHERE city_id = %s
          AND status = 'lost'
          AND created_at >= CURRENT_DATE
    """, (str(city_id),))
    row = cur.fetchone()
    return float(row["coalesce"]) if row else 0.0
