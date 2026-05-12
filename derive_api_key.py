"""Derive Polymarket CLOB API credentials from your wallet private key.

Usage:
    1. Set POLYMARKET_PRIVATE_KEY in your .env file (or pass it below)
    2. If using a Polymarket proxy wallet, set POLYMARKET_FUNDER and
       POLYMARKET_SIGNATURE_TYPE first
    2. Run: python derive_api_key.py
    3. Copy the output into your .env file
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY", "").strip()
    host = os.getenv("POLYMARKET_CLOB_URL", "https://clob.polymarket.com").strip()
    funder = os.getenv("POLYMARKET_FUNDER", "").strip() or None
    raw_signature_type = os.getenv("POLYMARKET_SIGNATURE_TYPE", "0").strip()

    if not private_key:
        print("ERROR: POLYMARKET_PRIVATE_KEY not found.")
        print("Set it in .env or export it before running this script.")
        print()
        print("  export POLYMARKET_PRIVATE_KEY=0xYourPrivateKeyHere")
        print("  python derive_api_key.py")
        sys.exit(1)

    # Ensure key has 0x prefix
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    try:
        signature_type = int(raw_signature_type)
    except ValueError:
        print(
            "ERROR: POLYMARKET_SIGNATURE_TYPE must be an integer "
            "(0=EOA, 1=POLY_PROXY/Magic, 2=GNOSIS_SAFE)."
        )
        sys.exit(1)

    if signature_type not in (0, 1, 2):
        print(
            "ERROR: POLYMARKET_SIGNATURE_TYPE must be 0, 1, or 2 "
            "(0=EOA, 1=POLY_PROXY/Magic, 2=GNOSIS_SAFE)."
        )
        sys.exit(1)

    if signature_type in (1, 2) and not funder:
        print(
            "ERROR: POLYMARKET_FUNDER is required when "
            "POLYMARKET_SIGNATURE_TYPE is 1 or 2."
        )
        sys.exit(1)

    try:
        from py_clob_client.client import ClobClient
    except ImportError:
        print("ERROR: py-clob-client is not installed.")
        print("  pip install py-clob-client")
        sys.exit(1)

    print("Connecting to Polymarket CLOB (Polygon mainnet)...")
    print(f"  Host:           {host}")
    print(f"  Signature type: {signature_type}")
    print(f"  Funder:         {funder or '(none / EOA)'}")

    client = ClobClient(
        host=host,
        key=private_key,
        chain_id=137,  # Polygon mainnet
        signature_type=signature_type,
        funder=funder,
    )

    print("Deriving API credentials (signing with your wallet)...\n")

    try:
        creds = client.create_or_derive_api_creds()
    except Exception as e:
        print(f"ERROR: Failed to derive credentials: {e}")
        print()
        print("Common causes:")
        print("  - Invalid private key")
        print("  - Network issue (can't reach clob.polymarket.com)")
        print("  - Wallet not registered on Polymarket")
        sys.exit(1)

    api_key = creds.api_key
    api_secret = creds.api_secret
    api_passphrase = creds.api_passphrase

    if not all([api_key, api_secret, api_passphrase]):
        print("ERROR: Received incomplete credentials from Polymarket.")
        print(f"  api_key:        {'OK' if api_key else 'MISSING'}")
        print(f"  api_secret:     {'OK' if api_secret else 'MISSING'}")
        print(f"  api_passphrase: {'OK' if api_passphrase else 'MISSING'}")
        sys.exit(1)

    print("=" * 50)
    print("  Polymarket CLOB Credentials")
    print("=" * 50)
    print(f"POLYMARKET_API_KEY={api_key}")
    print(f"POLYMARKET_API_SECRET={api_secret}")
    print(f"POLYMARKET_PASSPHRASE={api_passphrase}")
    print("=" * 50)
    print()
    print("Copy the 3 lines above into your .env file.")


if __name__ == "__main__":
    main()
