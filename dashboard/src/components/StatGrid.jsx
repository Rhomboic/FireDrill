import React from "react";

// stats: [{ label, value, sub, tone }]   tone: "purple"(default) | "accent" | "green" | "plain"
export default function StatGrid({ stats }) {
  return (
    <div className="stat-grid">
      {stats.map((s) => (
        <div className="stat-card" key={s.label}>
          <div className="stat-label">{s.label}</div>
          <div className={`stat-value${s.tone && s.tone !== "purple" ? " " + s.tone : ""}`}>
            {s.value}
          </div>
          {s.sub && <div className="stat-sub">{s.sub}</div>}
        </div>
      ))}
    </div>
  );
}
