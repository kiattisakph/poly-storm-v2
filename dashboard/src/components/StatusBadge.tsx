import type { TradeStatus } from "../types/api"

const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  won:     { bg: "#EAF3DE", text: "#3B6D11" },
  lost:    { bg: "#FCEBEB", text: "#A32D2D" },
  open:    { bg: "#E6F1FB", text: "#185FA5" },
  skipped: { bg: "#F1EFE8", text: "#5F5E5A" },
  failed:  { bg: "#FCEBEB", text: "#A32D2D" },
  active:  { bg: "#EAF3DE", text: "#3B6D11" },
  paused:  { bg: "#F1EFE8", text: "#5F5E5A" },
}

interface StatusBadgeProps {
  status: TradeStatus | "active" | "paused"
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const style = STATUS_STYLE[status] ?? { bg: "#F1EFE8", text: "#5F5E5A" }
  return (
    <span style={{
      fontSize: 12,
      fontWeight: 600,
      padding: "2px 7px",
      borderRadius: 6,
      background: style.bg,
      color: style.text,
      letterSpacing: "0.04em",
      textTransform: "uppercase" as const,
    }}>
      {status}
    </span>
  )
}
