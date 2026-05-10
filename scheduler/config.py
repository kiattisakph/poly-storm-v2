"""
config.py — STORM v2
Centralized configuration and constants.
"""

import os

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
