import React from "react";

// rows: [{ label, value, display, accent? }]   max: domain upper bound
export default function Bars({ rows, max = 1 }) {
  return (
    <div className="bars">
      {rows.map((r) => (
        <div className="bar-row" key={r.label}>
          <span className="bar-label" title={r.label}>{r.label}</span>
          <div className="bar-track">
            <div
              className={`bar-fill${r.accent ? " accent" : ""}`}
              style={{ width: `${Math.max(0, Math.min(1, r.value / max)) * 100}%` }}
            />
          </div>
          <span className="bar-val">{r.display ?? r.value.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}
