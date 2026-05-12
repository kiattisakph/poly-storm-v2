#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/Users/nb1003517/2026/bot/poly-storm-v2/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env file at $ENV_FILE" >&2
  exit 1
fi

DATABASE_URL="$(
  awk '
    /^DATABASE_URL=/ {
      sub(/^[^=]*=/, "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$ENV_FILE"
)"

if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL is not set in $ENV_FILE" >&2
  exit 1
fi

exec npx -y @modelcontextprotocol/server-postgres "$DATABASE_URL"
