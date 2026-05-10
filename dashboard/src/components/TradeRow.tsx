import type { Trade } from "../types/api"
import { StatusBadge } from "./StatusBadge"

interface TradeRowProps {
  trade: Trade
}

export function TradeRow({ trade }: TradeRowProps) {
  const pnl = trade.pnl
  const pnlColor =
    pnl == null ? "var(--muted)"
    : pnl > 0   ? "#3B6D11"
    : pnl < 0   ? "#A32D2D"
    :              "var(--muted)"

  const pnlLabel =
    pnl != null         ? `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`
    : trade.status === "open" ? `$${trade.amount_usd.toFixed(2)}`
    :                     "—"

  const date = new Date(trade.created_at).toLocaleString("th-TH", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "9px 14px",
      background: "var(--card)",
      border: "0.5px solid var(--border)",
      borderRadius: 8,
    }}>
      <div style={{ fontSize: 15, color: "var(--muted)", width: 80, flexShrink: 0 }}>
        {date}
      </div>
      <div style={{ flex: 1, fontSize: 15, fontWeight: 500 }}>
        {trade.bin_label}
        <span style={{ fontSize: 15, color: "var(--muted)", fontWeight: 400, marginLeft: 6 }}>
          {trade.city_name}
        </span>
      </div>
      <StatusBadge status={trade.status} />
      <div style={{ fontSize: 14, color: "var(--muted)", width: 36, textAlign: "right" }}>
        {(trade.yes_price * 100).toFixed(0)}¢
      </div>
      <div style={{
        fontSize: 14,
        fontWeight: 600,
        width: 56,
        textAlign: "right",
        color: pnlColor,
        fontVariantNumeric: "tabular-nums",
      }}>
        {pnlLabel}
      </div>
    </div>
  )
}
