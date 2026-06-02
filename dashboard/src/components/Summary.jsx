import React from "react";
import { modelLabel, MODEL_META, money } from "../meta.js";

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);

export default function Summary({ jobs, models }) {
  const rows = models.map((m) => {
    const js = jobs.filter((j) => j._model === m);
    return {
      model: m,
      n: js.length,
      resolution: mean(js.map((j) => j.scores.resolution)),
      composite: mean(js.map((j) => j.scores.composite)),
      blast: mean(js.map((j) => j.scores.blast_radius)),
      diagnosis: mean(js.map((j) => j.scores.diagnosis)),
      totalCost: js.reduce((a, j) => a + (j.cost?.cost_usd ?? 0), 0),
    };
  });
  rows.sort((a, b) => b.composite - a.composite || a.totalCost - b.totalCost);

  return (
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th className="num">Jobs</th>
          <th className="num">Resolved</th>
          <th className="num">Avg composite</th>
          <th className="num">Avg blast</th>
          <th className="num">Avg diagnosis</th>
          <th className="num">Total cost</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.model}>
            <td>
              {modelLabel(r.model)}{" "}
              <span className="pill">{MODEL_META[r.model]?.tier ?? ""}</span>
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
  );
}
