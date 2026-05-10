"""
config.py — STORM v2
Centralized configuration and constants.
"""

import os

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ─── Polymarket ───────────────────────────────────────────────────────────────
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
DEPOSIT_WALLET_ADDRESS = os.environ.get("DEPOSIT_WALLET_ADDRESS", "")
POLY_API_KEY = os.environ.get("POLY_API_KEY", "")
POLY_SECRET = os.environ.get("POLY_SECRET", "")
POLY_PASSPHRASE = os.environ.get("POLY_PASSPHRASE", "")

# ─── Trading ──────────────────────────────────────────────────────────────────
BET_AMOUNT = 2.0  # USD per bet
DAILY_LOSS_LIMIT_USD = 10.0
MIN_HOURS_TO_RESOLVE = 1.0
MAX_YES_PRICE = _env_float("MAX_YES_PRICE", 0.65)
MIN_BOUNDARY_MARGIN = _env_float("MIN_BOUNDARY_MARGIN", 0.20)
POLY_DRY_RUN = _env_bool("POLY_DRY_RUN", True)
SCHEDULER_HEARTBEAT_SECONDS = _env_int("SCHEDULER_HEARTBEAT_SECONDS", 60)
SCHEDULER_RUN_ON_START = _env_bool("SCHEDULER_RUN_ON_START", True)
