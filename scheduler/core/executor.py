"""
executor.py — STORM v2
Places BUY YES orders on Polymarket via py-clob-client-v2.
"""

import logging

from py_clob_client_v2 import (
    ApiCreds,
    ClobClient,
    OrderArgs,
    OrderType,
    PartialCreateOrderOptions,
    Side,
)

from scheduler.config import (
    BET_AMOUNT,
    PRIVATE_KEY,
    DEPOSIT_WALLET_ADDRESS,
    POLY_DRY_RUN,
    POLY_API_KEY,
    POLY_SECRET,
    POLY_PASSPHRASE,
)

logger = logging.getLogger(__name__)


def _build_client() -> ClobClient:
    """Construct authenticated ClobClient."""
    missing = [
        name for name, value in {
            "PRIVATE_KEY": PRIVATE_KEY,
            "DEPOSIT_WALLET_ADDRESS": DEPOSIT_WALLET_ADDRESS,
            "POLY_API_KEY": POLY_API_KEY,
            "POLY_SECRET": POLY_SECRET,
            "POLY_PASSPHRASE": POLY_PASSPHRASE,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"missing Polymarket credentials: {', '.join(missing)}")

    creds = ApiCreds(
        api_key=POLY_API_KEY,
        api_secret=POLY_SECRET,
        api_passphrase=POLY_PASSPHRASE,
    )
    return ClobClient(
        host="https://clob.polymarket.com",
        chain_id=137,
        key=PRIVATE_KEY,
        creds=creds,
        signature_type=2,
        funder=DEPOSIT_WALLET_ADDRESS,
    )


def buy_yes(target_bin) -> dict | None:
    """
    Place a GTC BUY YES limit order for the given MarketBin.

    Returns:
        Order response dict on success, None on failure.
    """
    try:
        shares = BET_AMOUNT / target_bin.yes_price
        shares = max(shares, target_bin.order_min)

        if POLY_DRY_RUN:
            logger.info(
                "DRY RUN order: bin=%s price=%.3f shares=%.2f token=%s",
                target_bin.label,
                target_bin.yes_price,
                shares,
                target_bin.yes_token_id,
            )
            return {
                "dry_run": True,
                "bin": target_bin.label,
                "price": target_bin.yes_price,
                "shares": round(shares, 2),
            }

        client = _build_client()

        tick_size = client.get_tick_size(target_bin.yes_token_id)

        args = OrderArgs(
            token_id=target_bin.yes_token_id,
            price=target_bin.yes_price,
            size=round(shares, 2),
            side=Side.BUY,
        )

        options = PartialCreateOrderOptions(tick_size=tick_size)

        response = client.create_and_post_order(
            args,
            options=options,
            order_type=OrderType.GTC,
        )

        logger.info(
            "Order placed: bin=%s price=%.3f shares=%.2f response=%s",
            target_bin.label,
            target_bin.yes_price,
            shares,
            response,
        )
        return response

    except Exception as e:
        logger.error("Failed to place order for bin %s: %s", target_bin.label, e)
        return None


def derive_credentials() -> None:
    """
    First-time setup: derive L2 API credentials from private key.
    Prints api_key, api_secret, api_passphrase for the user to save to .env.
    """
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=PRIVATE_KEY,
            chain_id=137,
            signature_type=0,
            funder=None,
        )

        creds = client.create_or_derive_api_creds()

        print("=== Polymarket L2 API Credentials ===")
        print(f"POLY_API_KEY={creds.api_key}")
        print(f"POLY_SECRET={creds.api_secret}")
        print(f"POLY_PASSPHRASE={creds.api_passphrase}")
        print("=====================================")
        print("Save these to your .env file.")

    except Exception as e:
        logger.error("Failed to derive credentials: %s", e)


if __name__ == "__main__":
    derive_credentials()
