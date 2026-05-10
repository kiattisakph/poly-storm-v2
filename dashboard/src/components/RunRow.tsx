import type { RunLog } from "../types/api"

interface RunRowProps {
  run: RunLog
}

export function RunRow({ run }: RunRowProps) {
  const time = new Date(run.created_at).toLocaleTimeString("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
  })
  const isExecuted = run.action === "executed"

  return (
    <div style={{
      display: "flex",
      alignItems: "flex-start",
      gap: 10,
      padding: "6px 0",
      borderBottom: "0.5px solid var(--border)",
      fontSize: 14,
    }}>
      <span style={{
        color: "var(--muted)",
        width: 44,
        flexShrink: 0,
        fontFamily: "monospace",
      }}>
        {time}
      </span>
      <span style={{
        width: 8,
        height: 8,
        borderRadius: "50%",
        marginTop: 4,
        flexShrink: 0,
        display: "inline-block",
        background: isExecuted ? "#1D9E75" : "#B4B2A9",
      }} />
      <span style={{ flex: 1, color: isExecuted ? "var(--text)" : "var(--muted)" }}>
        <span style={{ fontWeight: 500 }}>{run.city_name}</span>
        {" · "}
        {run.action}
        {run.note && (
          <span style={{ color: "var(--muted)", marginLeft: 6 }}>
            — {run.note}
          </span>
        )}
      </span>
      {run.tx_temp != null && (
        <span style={{ color: "var(--muted)", fontSize: 13, flexShrink: 0 }}>
          {run.tx_temp}°C
        </span>
      )}
    </div>
  )
}
