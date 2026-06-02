import React from "react";
import { modelLabel, vendorBadge, MODEL_META, money } from "../meta.js";
import { modelStats } from "../stats.js";

export default function Summary({ jobs, models, onPickModel }) {
  const rows = models
    .map((m) => modelStats(jobs, m))
    .sort((a, b) => b.composite - a.composite || a.totalCost - b.totalCost);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th className="num">Jobs</th>
            <th className="num">Resolved</th>
            <th className="num">Composite</th>
            <th className="num">Blast</th>
            <th className="num">Diagnosis</th>
            <th className="num">Total cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model} style={{ cursor: onPickModel ? "pointer" : "default" }}
                onClick={() => onPickModel?.(r.model)}>
              <td>
                <span className="model-name">{modelLabel(r.model)}</span>
                <span className={vendorBadge(r.model)}>
                  {MODEL_META[r.model]?.vendor === "openai" ? "OpenAI" : "Anthropic"}
                </span>
              </td>
              <td className="num">{r.n}</td>
              <td className="num">{(r.resolution * 100).toFixed(0)}%</td>
              <td className="num">{r.composite.toFixed(2)}</td>
              <td className="num">{r.blast.toFixed(2)}</td>
              <td className="num">{r.diagnosis.toFixed(2)}</td>
              <td className="num">{money(r.totalCost)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
