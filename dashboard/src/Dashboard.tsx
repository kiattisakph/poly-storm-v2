import { useState } from "react"
import type { City, Trade, Stats, RunLog } from "./types/api"
import { useFetch } from "./hooks/useFetch"
import { MetricCard } from "./components/MetricCard"
import { CityCard } from "./components/CityCard"
import { TradeRow } from "./components/TradeRow"
import { RunRow } from "./components/RunRow"

// ── toggle mock mode ──────────────────────────────────────────────────────────
const MOCK_MODE = true

const MOCK_STATS: Stats = {
  won: 13, lost: 5, open: 2, skipped: 8,
  total_pnl: 4.82, today_loss: 0,
}

const MOCK_CITIES: City[] = [
  {
    id: "1", name: "Seoul", station: "RKSI",
    latitude: 37.46, longitude: 126.44,
    timezone: "Asia/Seoul", strategy_code: "SEOUL", active: true,
  },
  {
    id: "2", name: "Hong Kong", station: "VHHH",
    latitude: 22.31, longitude: 113.92,
    timezone: "Asia/Hong_Kong", strategy_code: "HONG_KONG", active: true,
  },
  {
    id: "3", name: "Singapore", station: "WSSS",
    latitude: 1.35, longitude: 103.99,
    timezone: "Asia/Singapore", strategy_code: "SINGAPORE", active: false,
  },
]

const MOCK_TRADES: Trade[] = [
  {
    id: "t1", city_name: "Seoul", station: "RKSI",
    bin_label: "19°C", temp_estimate: 19, yes_price: 0.33,
    amount_usd: 2, status: "open", skip_reason: null,
    pnl: null, created_at: new Date(Date.now() - 3600000).toISOString(), resolved_at: null,
  },
  {
    id: "t2", city_name: "Hong Kong", station: "VHHH",
    bin_label: "29°C", temp_estimate: 29, yes_price: 0.35,
    amount_usd: 2, status: "open", skip_reason: null,
    pnl: null, created_at: new Date(Date.now() - 3800000).toISOString(), resolved_at: null,
  },
  {
    id: "t3", city_name: "Seoul", station: "RKSI",
    bin_label: "22°C or higher", temp_estimate: 22, yes_price: 0.60,
    amount_usd: 2, status: "won", skip_reason: null,
    pnl: 1.33, created_at: new Date(Date.now() - 86400000).toISOString(),
    resolved_at: new Date(Date.now() - 80000000).toISOString(),
  },
  {
    id: "t4", city_name: "Hong Kong", station: "VHHH",
    bin_label: "25°C", temp_estimate: 25, yes_price: 0.75,
    amount_usd: 2, status: "lost", skip_reason: null,
    pnl: -2.00, created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    resolved_at: new Date(Date.now() - 86400000 * 2 + 50000000).toISOString(),
  },
  {
    id: "t5", city_name: "Seoul", station: "RKSI",
    bin_label: "21°C", temp_estimate: 21, yes_price: 0.28,
    amount_usd: 2, status: "won", skip_reason: null,
    pnl: 3.14, created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    resolved_at: new Date(Date.now() - 86400000 * 3 + 50000000).toISOString(),
  },
]

const MOCK_RUNS: RunLog[] = [
  {
    id: "r1", city_name: "Seoul", station: "RKSI",
    taf_raw: "TAF RKSI 101100Z...", tx_temp: 19, tn_temp: 10,
    metar_temp: 11, wind_dir: 60, action: "executed",
    note: "bin=19°C price=0.33 taf_triggered=true",
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "r2", city_name: "Hong Kong", station: "VHHH",
    taf_raw: null, tx_temp: 29, tn_temp: 24,
    metar_temp: null, wind_dir: null, action: "executed",
    note: "bin=29°C price=0.35",
    created_at: new Date(Date.now() - 3700000).toISOString(),
  },
  {
    id: "r3", city_name: "Seoul", station: "RKSI",
    taf_raw: null, tx_temp: 19, tn_temp: null,
    metar_temp: null, wind_dir: null, action: "skipped",
    note: "outside entry windows (hour=6)",
    created_at: new Date(Date.now() - 5400000).toISOString(),
  },
  {
    id: "r4", city_name: "Seoul", station: "RKSI",
    taf_raw: null, tx_temp: 19, tn_temp: null,
    metar_temp: null, wind_dir: null, action: "taf_update",
    note: "TAF TX changed: 22 → 19",
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: "r5", city_name: "Singapore", station: "WSSS",
    taf_raw: null, tx_temp: null, tn_temp: null,
    metar_temp: null, wind_dir: null, action: "skipped",
    note: "city inactive",
    created_at: new Date(Date.now() - 7400000).toISOString(),
  },
]
// ─────────────────────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 17,
      color: "var(--muted)",
      letterSpacing: "0.06em",
      textTransform: "uppercase" as const,
      marginBottom: 10,
    }}>
      {children}
    </div>
  )
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 17, color: "var(--muted)", padding: "8px 0" }}>
      {children}
    </div>
  )
}

function SkeletonCard() {
  return (
    <div style={{
      height: 120,
      background: "var(--surface)",
      borderRadius: 12,
      opacity: 0.5,
    }} />
  )
}

export default function Dashboard() {
  const live_stats  = useFetch<Stats>("/trades/stats", 15_000)
  const live_cities = useFetch<City[]>("/cities", 60_000)
  const live_trades = useFetch<Trade[]>("/trades?limit=10", 15_000)
  const live_runs   = useFetch<RunLog[]>("/runs/latest?limit=8", 15_000)

  const stats  = MOCK_MODE ? MOCK_STATS  : live_stats.data
  const cities = MOCK_MODE ? MOCK_CITIES : live_cities.data
  const trades = MOCK_MODE ? MOCK_TRADES : live_trades.data
  const runs   = MOCK_MODE ? MOCK_RUNS   : live_runs.data

  const [lastRefresh, setLastRefresh] = useState(new Date())

  const handleRefresh = () => {
    if (!MOCK_MODE) live_stats.refetch()
    setLastRefresh(new Date())
  }

  const pnlColor = !stats
    ? "var(--text)"
    : stats.total_pnl > 0 ? "#3B6D11"
    : stats.total_pnl < 0 ? "#A32D2D"
    : "var(--text)"

  const winRate = stats
    ? Math.round((stats.won / Math.max(stats.won + stats.lost, 1)) * 100)
    : 0

  const cssVars = {
    "--text": "#1a1a1a",
    "--muted": "#888780",
    "--surface": "#F1EFE8",
    "--card": "#ffffff",
    "--border": "rgba(0,0,0,0.1)",
  } as React.CSSProperties

  return (
    <div style={{ ...cssVars, minHeight: "100vh", background: "#F7F6F2" }}>
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap"
        rel="stylesheet"
      />

      <div style={{
        fontFamily: "'DM Sans', system-ui, sans-serif",
        padding: "20px 32px",
        maxWidth: "100%",
      }}>

        {/* mock mode banner */}
        {MOCK_MODE && (
          <div style={{
            background: "#FFF8E1",
            border: "0.5px solid #F9A825",
            borderRadius: 8,
            padding: "6px 14px",
            fontSize: 14,
            color: "#795500",
            marginBottom: 16,
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
          }}>
            ⚠ mock mode — ข้อมูลจำลอง เปลี่ยน MOCK_MODE = false เพื่อดึงข้อมูลจริง
          </div>
        )}

        {/* header */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: "#1D9E75",
              boxShadow: "0 0 0 3px rgba(29,158,117,0.2)",
              animation: "pulse 2s infinite",
            }} />
            <span style={{ fontWeight: 600, fontSize: 15 }}>STORM v2</span>
            <span style={{
              fontSize: 17, padding: "2px 8px", borderRadius: 20,
              background: "#EAF3DE", color: "#3B6D11", fontWeight: 600,
            }}>
              running
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 17, color: "var(--muted)" }}>
              {lastRefresh.toLocaleTimeString("th-TH", {
                hour: "2-digit", minute: "2-digit",
              })} ICT
            </span>
            <button
              onClick={handleRefresh}
              style={{
                fontSize: 14, padding: "5px 12px", borderRadius: 8,
                border: "0.5px solid var(--border)",
                background: "var(--card)",
                color: "var(--muted)", cursor: "pointer",
              }}
            >
              ↻ refresh
            </button>
          </div>
        </div>

        {/* metrics */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: 10,
          marginBottom: 24,
        }}>
          <MetricCard
            label="total P&L"
            value={stats
              ? `${stats.total_pnl >= 0 ? "+" : ""}$${stats.total_pnl.toFixed(2)}`
              : "—"
            }
            sub="all time"
            valueColor={pnlColor}
          />
          <MetricCard
            label="win rate"
            value={stats ? `${winRate}%` : "—"}
            sub={stats ? `${stats.won} won · ${stats.lost} lost` : "loading"}
          />
          <MetricCard
            label="open positions"
            value={String(stats?.open ?? "—")}
            sub={stats ? `$${(stats.open * 2).toFixed(2)} at risk` : "loading"}
          />
          <MetricCard
            label="today's loss"
            value={stats ? `$${stats.today_loss.toFixed(2)}` : "—"}
            sub="limit $10.00"
            valueColor={stats && stats.today_loss > 8 ? "#A32D2D" : undefined}
          />
        </div>

        {/* cities */}
        <SectionLabel>cities</SectionLabel>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 10,
          marginBottom: 24,
        }}>
          {cities
            ? cities.map(city => <CityCard key={city.id} city={city} />)
            : [1, 2, 3].map(i => <SkeletonCard key={i} />)
          }
        </div>

        {/* trades + run log */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div>
            <SectionLabel>recent trades</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {!trades
                ? <Empty>loading...</Empty>
                : trades.length === 0
                ? <Empty>no trades yet</Empty>
                : trades.map(t => <TradeRow key={t.id} trade={t} />)
              }
            </div>
          </div>

          <div>
            <SectionLabel>run log</SectionLabel>
            <div>
              {!runs
                ? <Empty>loading...</Empty>
                : runs.length === 0
                ? <Empty>no runs yet</Empty>
                : runs.map(r => <RunRow key={r.id} run={r} />)
              }
            </div>
          </div>
        </div>

      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { width: 100%; height: 100%; min-height: 100vh; }
        body { background: #F7F6F2; }
      `}</style>
    </div>
  )
}
