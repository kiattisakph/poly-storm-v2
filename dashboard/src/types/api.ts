export interface City {
  id: string
  name: string
  station: string
  latitude: number
  longitude: number
  timezone: string
  strategy_code: string
  active: boolean
}

export interface Trade {
  id: string
  city_name: string
  station: string
  bin_label: string
  temp_estimate: number
  yes_price: number
  amount_usd: number
  status: "open" | "won" | "lost" | "skipped" | "failed" | "closed"
  skip_reason: string | null
  pnl: number | null
  created_at: string
  resolved_at: string | null
}

export interface Stats {
  won: number
  lost: number
  open: number
  skipped: number
  total_pnl: number
  today_loss: number
}

export interface RunLog {
  id: string
  city_name: string
  station: string
  taf_raw: string | null
  tx_temp: number | null
  tn_temp: number | null
  metar_temp: number | null
  wind_dir: number | null
  action: string | null
  note: string | null
  updated_date?: string | null
  created_at: string
}

export type TradeStatus = Trade["status"]
