import React from "react";
import StatGrid from "./StatGrid.jsx";
import Summary from "./Summary.jsx";
import Matrix from "./Matrix.jsx";
import { money } from "../meta.js";
import { mean, modelStats } from "../stats.js";

export default function Overview({ jobs, models, scenarios, cell, onSelect, onPickModel }) {
  const stats = models.map((m) => modelStats(jobs, m));
  const best = [...stats].sort((a, b) => b.composite - a.composite)[0];
  const cheapest = [...stats].sort((a, b) => a.avgCost - b.avgCost)[0];
  // actual money spent across all repeat runs (cost_usd is the mean per run)
  const totalSpend = jobs.reduce((a, j) => a + (j.cost?.cost_usd_total ?? j.cost?.cost_usd ?? 0), 0);
  const maxRuns = jobs.reduce((m, j) => Math.max(m, j.runs ?? 1), 1);
  const resolved = jobs.filter((j) => j.scores.resolution).length;
  const spread = best && cheapest ? best.avgCost / Math.max(cheapest.avgCost, 1e-9) : 0;

  const overviewStats = [
    { label: "Jobs run", value: jobs.length, tone: "plain", sub: `${scenarios.length} scenarios × ${models.length} models` },
    { label: "Incidents resolved", value: `${((resolved / jobs.length) * 100).toFixed(0)}%`, tone: "green", sub: `${resolved} / ${jobs.length} success conditions met` },
    { label: "Avg composite", value: mean(jobs.map((j) => j.scores.composite)).toFixed(2), sub: "0.6 resolution + 0.2 blast + 0.2 diagnosis" },
    { label: "Total spend", value: money(totalSpend), tone: "accent", sub: maxRuns > 1 ? `actual, across ${maxRuns} runs/cell · ${spread.toFixed(0)}× spread per run` : `${spread.toFixed(0)}× cost spread, cheapest → priciest` },
  ];

  return (
    <div>
      <StatGrid stats={overviewStats} />

      <div className="card section analysis">
        <div className="card-title">The headline</div>
        <p>
          FireDrill drops each model into a broken software project and scores it on four axes —
          did it <strong>resolve</strong> the incident, how tight was the <strong>blast radius</strong>,
          how good was its <strong>diagnosis</strong> (LLM-as-judge), and what did it <strong>cost</strong>.
          Cost is a deliberately <strong>separate axis</strong>, never folded into the composite, so
          capability and price can be read independently.
        </p>
        <p>
          The matrix below shows a clean two-tier split: the reasoning flagships{" "}
          <span className="accent">(Opus 4.8, GPT-5.5)</span> clear the regression-trap scenarios that the
          small baselines partially handle — but at <strong>{spread.toFixed(0)}× the cost per job</strong>.
        </p>
      </div>

      <div className="card section">
        <div className="card-title">Models</div>
        <div className="card-desc">Quality composite vs. cost — ranked by composite, ties broken by spend. Click a row to open its tab.</div>
        <Summary jobs={jobs} models={models} onPickModel={onPickModel} />
      </div>

      <div className="card section">
        <div className="card-title">Scenario × model</div>
        <div className="card-desc">Each cell is the composite score and dollar cost. Colour runs continuously: green at 1.0, red at ≤ 0.6, a red→green gradient between.</div>
        <div className="click-hint">
          <span className="click-hint-icon">↗</span>
          <span><strong>Click any cell</strong> for the full transcript, fix diff, judge verdict and objective verification.</span>
        </div>
        <Matrix models={models} scenarios={scenarios} cell={cell} onSelect={onSelect} />
      </div>
    </div>
  );
}
