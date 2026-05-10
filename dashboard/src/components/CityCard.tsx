import type { City } from "../types/api"
import { StatusBadge } from "./StatusBadge"

interface CityCardProps {
  city: City
}

export function CityCard({ city }: CityCardProps) {
  return (
    <div style={{
      background: "var(--card)",
      border: `0.5px solid ${city.active ? "#1D9E75" : "var(--border)"}`,
      borderRadius: 12,
      padding: "14px 16px",
    }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 10,
      }}>
        <div style={{ fontWeight: 600, fontSize: 13 }}>
          {city.name}
          <span style={{
            fontSize: 15,
            color: "var(--muted)",
            fontWeight: 400,
            marginLeft: 6,
          }}>
            {city.station}
          </span>
        </div>
        <StatusBadge status={city.active ? "active" : "paused"} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {(
          [
            ["strategy", city.strategy_code],
            ["timezone", city.timezone],
          ] as [string, string][]
        ).map(([k, v]) => (
          <div
            key={k}
            style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}
          >
            <span style={{ color: "var(--muted)" }}>{k}</span>
            <span style={{ fontWeight: 500 }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
