-- enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- cities
CREATE TABLE IF NOT EXISTS cities (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,
    station       VARCHAR(10)  NOT NULL,
    latitude      FLOAT        NOT NULL,
    longitude     FLOAT        NOT NULL,
    timezone      VARCHAR(50)  NOT NULL,
    strategy_code VARCHAR(30)  NOT NULL,   -- 'SEOUL', 'SINGAPORE', etc.
    active        BOOLEAN      DEFAULT true,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- sources config per city
CREATE TABLE IF NOT EXISTS city_sources (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id     UUID         REFERENCES cities(id) ON DELETE CASCADE,
    source_type VARCHAR(20)  NOT NULL,
    priority    INT          NOT NULL,
    weight      FLOAT        NOT NULL DEFAULT 1.0,
    enabled     BOOLEAN      DEFAULT true
);

-- market configs per city
CREATE TABLE IF NOT EXISTS market_configs (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id      UUID         REFERENCES cities(id) ON DELETE CASCADE,
    market_type  VARCHAR(30)  NOT NULL,
    slug_pattern VARCHAR(200) NOT NULL,
    temp_field   VARCHAR(10)  NOT NULL,
    enabled      BOOLEAN      DEFAULT true
);

-- trade log
CREATE TABLE IF NOT EXISTS trades (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id          UUID         REFERENCES cities(id),
    market_config_id UUID         REFERENCES market_configs(id),
    market_id        VARCHAR(100) NOT NULL,
    market_slug      VARCHAR(200),
    bin_label        VARCHAR(20)  NOT NULL,
    temp_estimate    FLOAT        NOT NULL,
    yes_price        FLOAT        NOT NULL,
    amount_usd       FLOAT        NOT NULL DEFAULT 2.0,
    status           VARCHAR(20)  NOT NULL DEFAULT 'open',
    skip_reason      VARCHAR(100),
    resolved_at      TIMESTAMPTZ,
    pnl              FLOAT,
    created_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_market_slug
ON trades (city_id, market_config_id, market_slug, status);

-- run log
CREATE TABLE IF NOT EXISTS run_logs (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id          UUID         REFERENCES cities(id),
    market_config_id UUID         REFERENCES market_configs(id),
    taf_raw          TEXT,
    tx_temp          FLOAT,
    tn_temp          FLOAT,
    metar_temp       FLOAT,
    wind_dir         INT,
    action           VARCHAR(20),
    note             TEXT,
    updated_date     TIMESTAMPTZ  DEFAULT NOW(),
    created_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_run_logs_taf_values
ON run_logs (city_id, market_config_id, updated_date DESC, created_at DESC);

-- ─── seed: Seoul ─────────────────────────────────────────────────────────────

INSERT INTO cities (name, station, latitude, longitude, timezone, strategy_code)
VALUES ('Seoul', 'RKSI', 37.4631, 126.4400, 'Asia/Seoul', 'SEOUL')
ON CONFLICT DO NOTHING;

INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'TAF_TX', 1, 1.0, true  FROM cities WHERE station = 'RKSI' ON CONFLICT DO NOTHING;
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'ECMWF',  2, 0.4, false FROM cities WHERE station = 'RKSI' ON CONFLICT DO NOTHING;
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'GFS',    3, 0.2, false FROM cities WHERE station = 'RKSI' ON CONFLICT DO NOTHING;
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'KMA',    4, 0.6, false FROM cities WHERE station = 'RKSI' ON CONFLICT DO NOTHING;

INSERT INTO market_configs (city_id, market_type, slug_pattern, temp_field, enabled)
SELECT id, 'HIGHEST_TEMP', 'highest-temperature-in-seoul-on-{date}', 'TX', true
FROM cities WHERE station = 'RKSI' ON CONFLICT DO NOTHING;
INSERT INTO market_configs (city_id, market_type, slug_pattern, temp_field, enabled)
SELECT id, 'LOWEST_TEMP', 'lowest-temperature-in-seoul-on-{date}', 'TN', false
FROM cities WHERE station = 'RKSI' ON CONFLICT DO NOTHING;

-- ─── seed: Singapore ─────────────────────────────────────────────────────────

INSERT INTO cities (name, station, latitude, longitude, timezone, strategy_code)
VALUES ('Singapore', 'WSSS', 1.3502, 103.9940, 'Asia/Singapore', 'SINGAPORE')
ON CONFLICT DO NOTHING;

-- Singapore ไม่ใช้ TAF_TX — ใช้ DATA_GOV_SG + ECMWF
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'DATA_GOV_SG', 1, 0.6, true  FROM cities WHERE station = 'WSSS' ON CONFLICT DO NOTHING;
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'ECMWF',       2, 0.4, true  FROM cities WHERE station = 'WSSS' ON CONFLICT DO NOTHING;

INSERT INTO market_configs (city_id, market_type, slug_pattern, temp_field, enabled)
SELECT id, 'HIGHEST_TEMP', 'highest-temperature-in-singapore-on-{date}', 'TX', true
FROM cities WHERE station = 'WSSS' ON CONFLICT DO NOTHING;

-- ─── seed: Hong Kong ─────────────────────────────────────────────────────────

INSERT INTO cities (name, station, latitude, longitude, timezone, strategy_code)
VALUES ('Hong Kong', 'VHHH', 22.3080, 113.9185, 'Asia/Hong_Kong', 'HONG_KONG')
ON CONFLICT DO NOTHING;

-- HKO API ใช้โดยตรง — ไม่ต้องใช้ TAF_TX เป็น primary
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'ECMWF', 1, 0.4, true  FROM cities WHERE station = 'VHHH' ON CONFLICT DO NOTHING;
INSERT INTO city_sources (city_id, source_type, priority, weight, enabled)
SELECT id, 'GFS',   2, 0.2, false FROM cities WHERE station = 'VHHH' ON CONFLICT DO NOTHING;

-- market config
INSERT INTO market_configs (city_id, market_type, slug_pattern, temp_field, enabled)
SELECT id, 'HIGHEST_TEMP', 'highest-temperature-in-hong-kong-on-{date}', 'TX', true
FROM cities WHERE station = 'VHHH' ON CONFLICT DO NOTHING;
