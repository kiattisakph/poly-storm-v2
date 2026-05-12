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
    POLY_SIGNATURE_TYPE,
    POLY_DRY_RUN,
    POLY_API_KEY,
    POLY_SECRET,
    POLY_PASSPHRASE,
)

logger = logging.getLogger(__name__)

SIGNATURE_TYPE_LABELS = {
    0: "EOA",
    1: "POLY_PROXY/Magic",
    2: "POLY_GNOSIS_SAFE/browser-wallet",
    3: "POLY_1271",
}


def _funder() -> str | None:
    if POLY_SIGNATURE_TYPE == 0:
        return DEPOSIT_WALLET_ADDRESS or None
    if not DEPOSIT_WALLET_ADDRESS:
        raise RuntimeError(
            "DEPOSIT_WALLET_ADDRESS is required for "
            f"POLY_SIGNATURE_TYPE={POLY_SIGNATURE_TYPE}"
        )
    return DEPOSIT_WALLET_ADDRESS


def _validate_signature_type() -> None:
    if POLY_SIGNATURE_TYPE not in {0, 1, 2, 3}:
        raise RuntimeError(
            "POLY_SIGNATURE_TYPE must be one of 0, 1, 2, or 3 "
            f"(got {POLY_SIGNATURE_TYPE})"
        )


def _short_address(address: str | None) -> str:
    if not address:
        return "none"
    return f"{address[:6]}…{address[-4:]}"


def _build_client() -> ClobClient:
    """Construct authenticated ClobClient."""
    _validate_signature_type()
    missing = [
        name for name, value in {
            "PRIVATE_KEY": PRIVATE_KEY,
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
    client = ClobClient(
        host="https://clob.polymarket.com",
        chain_id=137,
        key=PRIVATE_KEY,
        creds=creds,
        signature_type=POLY_SIGNATURE_TYPE,
        funder=_funder(),
        use_server_time=True,
    )
    logger.info(
        "polymarket client configured: signature_type=%s(%s) signer=%s funder=%s",
        POLY_SIGNATURE_TYPE,
        SIGNATURE_TYPE_LABELS.get(POLY_SIGNATURE_TYPE, "unknown"),
        _short_address(client.signer.address() if client.signer else None),
        _short_address(client.builder.funder),
    )
    return client


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
        _validate_signature_type()
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=PRIVATE_KEY,
            chain_id=137,
            signature_type=POLY_SIGNATURE_TYPE,
            funder=_funder(),
            use_server_time=True,
        )
        logger.info(
            "deriving polymarket creds: signature_type=%s(%s) signer=%s funder=%s",
            POLY_SIGNATURE_TYPE,
            SIGNATURE_TYPE_LABELS.get(POLY_SIGNATURE_TYPE, "unknown"),
            _short_address(client.signer.address() if client.signer else None),
            _short_address(client.builder.funder),
        )

        creds = client.create_or_derive_api_key()

        print("=== Polymarket L2 API Credentials ===")
        print(f"POLY_API_KEY={creds.api_key}")
        print(f"POLY_SECRET={creds.api_secret}")
        print(f"POLY_PASSPHRASE={creds.api_passphrase}")
        print("=====================================")
        print(f"Bound to address: {client.signer.address()}")
        print("Save these to your .env file.")

    except Exception as e:
        logger.error("Failed to derive credentials: %s", e)


if __name__ == "__main__":
    derive_credentials()
