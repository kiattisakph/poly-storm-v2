# Scheduler Runbook

Detailed scheduler guidance for AI coding agents.

## Runtime Model

Local venv commands:

```bash
source .venv/bin/activate
python -m scheduler --help
python -m scheduler --list-jobs
POLY_DRY_RUN=true python -m scheduler --once
```

Docker commands:

```bash
docker compose config
docker compose ps
docker compose up -d db
docker compose build scheduler
docker compose run --rm --no-deps scheduler python -m scheduler --help
```

Expected Docker DB port mapping:

```text
0.0.0.0:5433->5432/tcp
```

Host port `5433` is only for host-to-container access.
Inside Docker, services must keep using `db:5432`.

## CLI Modes

- `python -m scheduler`: start the blocking APScheduler loop.
- `python -m scheduler --help`: print help and exit.
- `python -m scheduler --list-jobs`: print configured jobs and exit.
- `python -m scheduler --once`: run one normal cycle and exit.
- `python -m scheduler --force`: with `--once`, treat as TAF-triggered.
- `python -m scheduler --resolve-once`: run resolver once and exit.

## Scheduled Jobs

- `normal`: every 30 minutes.
- `resolver`: every 30 minutes, offset by 15 minutes.
- `taf_*`: frequent checks around TAF release windows.

## Trading Behavior

- `scheduler/core/executor.py` places Polymarket orders.
- `POLY_DRY_RUN=true` logs the intended order and returns a dry-run response.
- Dry-run trades are logged with status `dry_run`.
- `POLY_DRY_RUN=false` can place live orders if credentials are valid.

Do not run live trading paths without explicit user approval.

## Entry And Risk Gates

Entry behavior:

- Seoul requires TAF TX.
- Singapore does not require TAF TX.
- Hong Kong does not require TAF TX.
- Normal entry windows are 07:00-09:00 and 13:00-15:00 local city time.
- TAF-triggered cycles may enter immediately when TAF TX changes.

Risk behavior:

- Daily loss limit is configured in `scheduler/config.py`.
- Minimum time to resolve is configured in `scheduler/config.py`.
- YES price above `0.90` is blocked.

## Database

Primary tables:

- `cities`
- `city_sources`
- `market_configs`
- `trades`
- `run_logs`

Seeded cities:

- Seoul, station `RKSI`, strategy `SEOUL`.
- Singapore, station `WSSS`, strategy `SINGAPORE`.
- Hong Kong, station `VHHH`, strategy `HONG_KONG`.

If tables are missing, initialize with `db/Init.sql` only after confirming
the target `DATABASE_URL`.

Safe read-only checks:

```bash
python -c "from scheduler.db import get_conn; c=get_conn(); cur=c.cursor(); cur.execute('SELECT 1 AS ok'); print(cur.fetchone()['ok']); c.close()"
```

```bash
python -c "from scheduler.db import get_conn, load_active_cities; c=get_conn(); print([x.name for x in load_active_cities(c)]); c.close()"
```

## External APIs

Scheduler code may call:

- AviationWeather TAF/METAR.
- Open-Meteo model endpoints.
- Singapore data.gov.sg APIs.
- Hong Kong Observatory APIs.
- Polymarket Gamma API.
- Polymarket CLOB API for live orders.

External APIs can fail or rate-limit. Network failures should not crash the
entire scheduler cycle where avoidable.

## Common Pitfalls

- `python -m scheduler` starts a blocking loop; use `--once` for smoke tests.
- A healthy DB container does not guarantee schema exists for local venv runs.
- TAF fetch can succeed but have no TX field, especially for Singapore.
- Resolver updates open trades; avoid running it against production-like data
  unless intended.
