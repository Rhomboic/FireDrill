import React from "react";
import StatGrid from "./StatGrid.jsx";
import Bars from "./Bars.jsx";
import { modelLabel, vendorBadge, MODEL_META, money, scoreColor } from "../meta.js";
import { modelStats, modelBlurb } from "../stats.js";

export default function ModelTab({ model, jobs, allModels, onSelect }) {
  const s = modelStats(jobs, model);
  const all = allModels.map((m) => modelStats(jobs, m));
  const vendor = MODEL_META[model]?.vendor === "openai";

  const stats = [
    { label: "Resolution rate", value: `${(s.resolution * 100).toFixed(0)}%`, tone: "green", sub: `${s.jobs.filter((j) => j.scores.resolution).length} / ${s.n} resolved` },
    { label: "Avg composite", value: s.composite.toFixed(2), sub: "quality only — cost excluded" },
    { label: "Avg blast radius", value: s.blast.toFixed(2), sub: "1.0 = touched only expected files" },
    { label: "Avg diagnosis", value: s.diagnosis.toFixed(2), sub: "LLM-as-judge, normalised 0–1" },
    { label: "Total cost", value: money(s.totalCost), tone: "accent", sub: `${money(s.avgCost)} / job` },
  ];

  const byScenario = [...s.jobs]
    .sort((a, b) => b.scores.composite - a.scores.composite)
    .map((j) => ({
      label: j.scenario,
      value: j.scores.composite,
      display: j.scores.composite.toFixed(2),
      accent: vendor,
      job: j,
    }));

  return (
    <div>
      <div className="model-header" style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>{modelLabel(model)}</h2>
        <span className={vendorBadge(model)}>{vendor ? "OpenAI" : "Anthropic"}</span>
        <span className="tier-tag">{MODEL_META[model]?.tier}</span>
      </div>

      <StatGrid stats={stats} />

      <div className="card section analysis">
        <div className="card-title">Profile</div>
        <p>{modelBlurb(s, all)}</p>
      </div>

      <div className="card section">
        <div className="card-title">Composite by scenario</div>
        <div className="card-desc">How the model did per incident. Click a bar to open the run.</div>
        <div onClick={(e) => {
          const idx = e.target.closest(".bar-row");
          if (!idx) return;
          const label = idx.querySelector(".bar-label")?.title;
          const row = byScenario.find((r) => r.label === label);
          if (row) onSelect(row.job);
        }} style={{ cursor: "pointer" }}>
          <Bars rows={byScenario} max={1} />
        </div>
      </div>

      <div className="card section">
        <div className="card-title">Runs</div>
        <div className="card-desc">Click any row for the transcript, fix diff, diagnosis and verification.</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Scenario</th>
                <th className="num">Composite</th>
                <th className="num">Resolved</th>
                <th className="num">Blast</th>
                <th className="num">Diagnosis</th>
                <th className="num">Cost</th>
              </tr>
            </thead>
            <tbody>
              {s.jobs
                .slice()
                .sort((a, b) => b.scores.composite - a.scores.composite)
                .map((j) => (
                  <tr key={j.scenario} style={{ cursor: "pointer" }} onClick={() => onSelect(j)}>
                    <td>
                      <span className="scenario-name">{j.scenario}</span>
                      <span className="stack" style={{ display: "block", fontSize: "0.72rem", color: "var(--text-muted)" }}>
                        {j.stack} · {j.difficulty}
                      </span>
                    </td>
                    <td className="num" style={{
                      background: scoreColor(j.scores.composite).bg,
                      color: scoreColor(j.scores.composite).fg,
                    }}>
                      {j.scores.composite.toFixed(2)}
                    </td>
                    <td className="num">{j.scores.resolution ? "✓" : "✗"}</td>
                    <td className="num">{j.scores.blast_radius.toFixed(2)}</td>
                    <td className="num">{j.scores.diagnosis.toFixed(2)}</td>
                    <td className="num">{money(j.cost?.cost_usd)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
