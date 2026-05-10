interface MetricCardProps {
  label: string
  value: string
  sub?: string
  valueColor?: string
}

export function MetricCard({ label, value, sub, valueColor }: MetricCardProps) {
  return (
    <div style={{
      background: "var(--surface)",
      borderRadius: 10,
      padding: "14px 16px",
    }}>
      <div style={{
        fontSize: 15,
        color: "var(--muted)",
        marginBottom: 4,
        letterSpacing: "0.04em",
        textTransform: "uppercase" as const,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 26,
        fontWeight: 600,
        color: valueColor ?? "var(--text)",
        fontVariantNumeric: "tabular-nums",
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 15, color: "var(--muted)", marginTop: 3 }}>
          {sub}
        </div>
      )}
    </div>
  )
}
