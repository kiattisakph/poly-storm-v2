# STORM v2 — Polymarket Weather Bot

Automated weather prediction trading bot for Polymarket temperature markets. Fetches forecasts from multiple sources (TAF, ECMWF, GFS, KMA, HKO, NEA), estimates daily high/low temperatures, and places limit orders on the correct bin.

## Architecture

```
poly-storm-v2/
├── scheduler/             # Python — APScheduler background jobs
│   ├── __main__.py        # entrypoint (python -m scheduler)
│   ├── config.py          # env vars + constants
│   ├── core/              # business logic
│   │   ├── executor.py    # Polymarket order execution
│   │   ├── fetcher.py     # TAF/METAR fetch
│   │   ├── market.py      # Gamma API + bin matching
│   │   ├── estimator.py   # multi-source weighted estimation
│   │   ├── risk.py        # entry gate + risk gate
│   │   └── resolver.py    # post-resolve PnL settlement
│   ├── db/                # data layer
│   │   └── repository.py  # all SQL queries
│   ├── models/            # dataclasses
│   │   └── domain.py      # City, MarketBin, TAFResult, etc.
│   ├── sources/           # weather data sources
│   └── strategies/        # per-city logic
├── api/                   # Python — FastAPI REST backend
│   └── main.py            # uvicorn entrypoint
├── dashboard/             # TypeScript — React + Vite SPA
│   ├── src/               # React components
│   └── nginx.conf         # production Nginx config (SPA + API proxy)
├── db/
│   └── Init.sql           # Postgres schema + seed data
└── docker-compose.yml     # all services orchestration
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

Smoke test แบบไม่ยิง order จริง:

```bash
python -m scheduler --help
python -m scheduler --list-jobs
python -m scheduler --once
```

ค่าเริ่มต้นของ scheduler คือ `POLY_DRY_RUN=true` ดังนั้น order ที่ผ่าน gate จะถูก log เป็น `dry_run` แทนการส่งคำสั่งจริง ตั้ง `POLY_DRY_RUN=false` เฉพาะตอนพร้อมเทรดจริงแล้วเท่านั้น

Buy gates เริ่มต้นต้องมี TAF TX, target bin match กับตลาด, `yes_price <= 0.65`, estimate ไม่ใกล้ boundary, ไม่เคย trade slug เดียวกัน, ไม่เกิน daily loss และเหลือเวลาพอถึง resolve

เมื่อรัน `python -m scheduler` scheduler จะยิง normal cycle หนึ่งรอบทันที แล้วจึงรอรอบ job ถัดไปตาม schedule และ log heartbeat ทุก 60 วินาทีเพื่อบอกว่ายังทำงานอยู่ ปรับได้ด้วย `SCHEDULER_HEARTBEAT_SECONDS` และปิด startup cycle ได้ด้วย `SCHEDULER_RUN_ON_START=false`

### 5b. Run ทุกอย่างผ่าน Docker (production)

```bash
docker compose up -d
```

Services จะ start ตามลำดับ: `db` (wait healthy) → `scheduler` + `api` → `dashboard`

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

## Docker Services

```bash
docker compose up -d
```

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5433 → 5432 | PostgreSQL 16 — auto-init จาก `db/Init.sql` |
| `scheduler` | — | APScheduler jobs (trading + resolver) |
| `api` | 8000 | FastAPI REST backend |
| `dashboard` | 3000 | React SPA via Nginx (proxy `/api/` → api) |

## Dashboard

React + Vite + TypeScript SPA สำหรับดู trades, runs, และ city status

### Local dev

```bash
cd dashboard
npm install
npm run dev
# → http://localhost:5173
```

### Production

Dashboard ถูก build เป็น static files แล้ว serve ผ่าน Nginx ใน Docker
- Nginx proxy `/api/*` ไปที่ `api:8000` อัตโนมัติ
- SPA fallback ทุก route ไป `index.html`
