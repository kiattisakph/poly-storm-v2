# STORM v2 — Polymarket Weather Bot

Automated weather prediction trading bot for Polymarket temperature markets. Fetches forecasts from multiple sources (TAF, ECMWF, GFS, KMA, HKO, NEA), estimates daily high/low temperatures, and places limit orders on the correct bin.

## Architecture

```
scheduler/
├── __main__.py        # APScheduler entrypoint
├── config.py          # env vars + constants
├── core/              # business logic
│   ├── executor.py    # Polymarket order execution
│   ├── fetcher.py     # TAF/METAR fetch
│   ├── market.py      # Gamma API + bin matching
│   ├── estimator.py   # multi-source weighted estimation
│   ├── risk.py        # entry gate + risk gate
│   └── resolver.py    # post-resolve PnL settlement
├── db/                # data layer
│   └── repository.py  # all SQL queries
├── models/            # dataclasses
│   └── domain.py      # City, MarketBin, TAFResult, etc.
├── sources/           # weather data sources
│   ├── taf_tx.py      # aviationweather.gov TAF TX
│   ├── ecmwf.py       # ECMWF via Open-Meteo
│   └── gfs_kma.py     # GFS + KMA via Open-Meteo
└── strategies/        # per-city logic
    ├── seoul.py       # TAF + wind adjustment
    ├── singapore.py   # NEA + forecast blend
    └── hongkong.py    # HKO API + TAF fallback
```

## Supported Cities

| City | Station | Strategy | Resolve Source |
|------|---------|----------|----------------|
| Seoul | RKSI | TAF TX + wind adj | Weather Underground |
| Singapore | WSSS | NEA + ECMWF blend | Weather Underground |
| Hong Kong | VHHH | HKO API + TAF fallback | Weather Underground |

## Setup

### 1. Clone & install

```bash
git clone <repo>
cd poly-storm-v2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your values
```

### 3. Derive Polymarket API credentials (first time)

```bash
python -m scheduler.core.executor
# Prints POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE → save to .env
```

### 4. Start database

```bash
docker compose up -d db
```

> **DB init เป็น automatic** — `db/Init.sql` ถูก mount เข้า Postgres `docker-entrypoint-initdb.d/`
> ดังนั้นตอน container สร้าง database ครั้งแรก จะ create tables + seed data ให้เอง
> ไม่ต้องรัน migration แยก
>
> ⚠️ ถ้า volume `pgdata` มีอยู่แล้ว (เคย up มาก่อน) Postgres จะ **ไม่** รัน init.sql ซ้ำ
> ถ้าต้องการ reset: `docker compose down -v && docker compose up -d db`

### 5. Run scheduler (local dev)

```bash
python -m scheduler
```

### 5b. Run ทุกอย่างผ่าน Docker (production)

```bash
docker compose up -d
```

Services จะ start ตามลำดับ: `db` (wait healthy) → `scheduler` + `api`

## Scheduler Jobs

| Job | Interval | Description |
|-----|----------|-------------|
| `normal` | 30 min | Standard estimation + order cycle |
| `resolver` | 30 min (offset 15m) | Settle resolved trades, calculate PnL |
| `taf_*` | 5 min windows | Frequent checks around TAF release times |

## Trading Rules

- Bet size: $2.00 USD per trade
- Min order: 5 shares
- Daily loss limit: $10.00
- Entry gates: TAF TX required + time windows (07-09, 13-15 local)
- No duplicate positions on same bin
- Risk gate: >1h to resolve, yes_price < 0.90

## Environment Variables

See [`.env.example`](.env.example) for all required variables.

## Docker

```bash
docker compose up -d
```

Runs PostgreSQL + scheduler + API (if configured).
