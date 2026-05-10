# Security Policy

## Scope

This project is an automated Polymarket weather trading bot. Security-sensitive
areas include:

- Wallet private keys.
- Polymarket API credentials.
- Order execution logic.
- Database trade and run logs.
- Environment configuration.
- Docker and runtime deployment.

## Secrets

Never commit:

- `.env`
- Private keys.
- Polymarket API keys, secrets, or passphrases.
- Database passwords.
- Wallet or funder addresses if they are private to the deployment.

Use `.env.example` only for placeholders. When sharing logs, mask sensitive
values before posting them.

Acceptable masked examples:

```text
DATABASE_URL=***@localhost:5432/StormDB
PRIVATE_KEY=***
POLY_API_KEY=***
POLY_SECRET=***
POLY_PASSPHRASE=***
```

## Trading Safety

Development and smoke tests must use:

```bash
POLY_DRY_RUN=true
```

Set `POLY_DRY_RUN=false` only when intentionally enabling live trading.

Before live trading, verify:

- `DATABASE_URL` points to the intended database.
- Wallet and funder address are correct.
- Polymarket API credentials are correct.
- City and market configs are expected.
- Daily loss limit is acceptable.
- Entry and risk gates are enabled and understood.
- There are no stale open trades that can block or confuse behavior.

## Database Safety

Local Docker Postgres maps host `5433` to container `5432`.

Do not expose Postgres publicly. Do not run destructive database operations
against production-like data unless explicitly intended.

Destructive operations include:

- Dropping tables.
- Truncating tables.
- Deleting trade history.
- Deleting Docker volumes.
- Running `docker compose down -v`.

## Dependency And Runtime Safety

- Review dependency changes before installing or deploying.
- Avoid running untrusted scripts with access to `.env`.
- Do not log full external API responses if they may contain credentials.
- Prefer dry-run smoke tests before enabling long-running scheduler jobs.

## Reporting Vulnerabilities

Do not open a public issue containing secrets or exploitable details.
Contact the maintainer privately.

Include:

- Impact.
- Reproduction steps.
- Affected files or services.
- Suggested mitigation if known.

## Incident Response

If credentials leak:

1. Stop the scheduler immediately.
2. Set `POLY_DRY_RUN=true`.
3. Rotate Polymarket API credentials.
4. Move funds if a wallet private key leaked.
5. Rotate the database password if exposed.
6. Review recent `trades` and `run_logs`.
7. Audit git history for exposed secrets.
8. Remove exposed secrets from history if needed.

If unexpected live orders are placed:

1. Stop the scheduler immediately.
2. Set `POLY_DRY_RUN=true`.
3. Review scheduler logs and `trades`.
4. Check open Polymarket positions manually.
5. Identify whether entry gates, risk gates, or credentials were misconfigured.
6. Do not restart live trading until the root cause is understood.
