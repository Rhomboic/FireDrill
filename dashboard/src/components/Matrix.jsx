import React from "react";
import { modelLabel, scoreColor, money } from "../meta.js";

export default function Matrix({ models, scenarios, cell, onSelect }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th>Scenario</th>
            {models.map((m) => (
              <th key={m} style={{ textAlign: "center" }}>
                {modelLabel(m)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => {
            const sample = models.map((m) => cell[`${s}|${m}`]).find(Boolean);
            return (
              <tr key={s}>
                <td className="scenario-name">
                  {sample?.scenario ?? s}
                  <span className="stack">{sample?.stack} · {sample?.difficulty}</span>
                </td>
                {models.map((m) => {
                  const job = cell[`${s}|${m}`];
                  if (!job) {
                    return (
                      <td key={m} className="matrix-cell empty">
                        —
                      </td>
                    );
                  }
                  const c = job.scores.composite;
                  const col = scoreColor(c);
                  return (
                    <td
                      key={m}
                      className="matrix-cell"
                      style={{ background: col.bg, color: col.fg }}
                      onClick={() => onSelect(job)}
                      title="Click for details"
                    >
                      {c.toFixed(2)}
                      <span className="sub">{money(job.cost?.cost_usd)}</span>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
