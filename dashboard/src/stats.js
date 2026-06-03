import { modelLabel, MODEL_META } from "./meta.js";

export const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
const sum = (xs) => xs.reduce((a, b) => a + b, 0);

export function modelStats(jobs, model) {
  const js = jobs.filter((j) => j._model === model);
  return {
    model,
    n: js.length,
    jobs: js,
    resolution: mean(js.map((j) => j.scores.resolution)),
    composite: mean(js.map((j) => j.scores.composite)),
    blast: mean(js.map((j) => j.scores.blast_radius)),
    diagnosis: mean(js.map((j) => j.scores.diagnosis)),
    // totalCost = actual money spent (across all repeat runs); avgCost = mean
    // cost per run (the per-cell, cost-vs-capability value). Old single-run
    // results have no cost_usd_total, so fall back to cost_usd.
    totalCost: sum(js.map((j) => j.cost?.cost_usd_total ?? j.cost?.cost_usd ?? 0)),
    avgCost: mean(js.map((j) => j.cost?.cost_usd ?? 0)),
  };
}

// One-paragraph generated read on a model, relative to the field.
export function modelBlurb(s, all) {
  const resolved = s.jobs.filter((j) => j.scores.resolution).length;
  const rank = [...all].sort((a, b) => b.composite - a.composite).findIndex((x) => x.model === s.model) + 1;
  const cheapest = [...all].sort((a, b) => a.totalCost - b.totalCost)[0];
  const costNote =
    cheapest.model === s.model
      ? "the cheapest model in the field"
      : `${(s.totalCost / cheapest.totalCost).toFixed(0)}× the spend of ${modelLabel(cheapest.model)}`;
  return (
    `${modelLabel(s.model)} resolved ${resolved}/${s.n} incidents ` +
    `(composite ${s.composite.toFixed(2)}, rank ${rank} of ${all.length}). ` +
    `It averaged a blast-radius score of ${s.blast.toFixed(2)} and a judge diagnosis of ` +
    `${s.diagnosis.toFixed(2)}/1.0, at ${costNote} ($${s.totalCost.toFixed(4)} total).`
  );
}

// A substantive, data-driven analysis of a model relative to the field: its
// standing, its character (precision / diagnostician / value / floor, derived
// from the data, not hardcoded), where it loses ground, and its cost position.
export function modelAnalysis(s, all) {
  const byComp = [...all].sort((a, b) => b.composite - a.composite);
  const rank = byComp.findIndex((x) => x.model === s.model) + 1;
  const cheapest = [...all].sort((a, b) => a.avgCost - b.avgCost)[0];
  const tightest = [...all].sort((a, b) => b.blast - a.blast)[0];
  const bestDiag = [...all].sort((a, b) => b.diagnosis - a.diagnosis)[0];
  const isFlagship = (MODEL_META[s.model]?.tier || "").toLowerCase().includes("flagship");
  const isBottom = rank === all.length;
  const costRatio = s.avgCost / Math.max(cheapest.avgCost, 1e-9);

  const weak = [...s.jobs]
    .sort((a, b) => a.scores.composite - b.scores.composite)
    .filter((j) => j.scores.composite < 0.97)
    .slice(0, 3)
    .map((j) => `${j.scenario} (${j.scores.composite.toFixed(2)})`);

  let character;
  if (tightest.model === s.model)
    character = "the precision pick: its blast radius is the tightest in the field, so its fixes touch only what they should";
  else if (bestDiag.model === s.model)
    character = "the strongest diagnostician, with the clearest root-cause explanations in the field";
  else if (isBottom)
    character = "where the capability floor shows: it trips the hardest traps and is the weakest resolver";
  else
    character = "the value tier, near-flagship quality at a fraction of the cost";

  const standing =
    `Ranks ${rank} of ${all.length} at composite ${s.composite.toFixed(2)} ` +
    `(${(s.resolution * 100).toFixed(0)}% resolution, blast ${s.blast.toFixed(2)}, diagnosis ${s.diagnosis.toFixed(2)}). `;
  const charSent = `It is ${character}. `;
  const weakSent = weak.length
    ? `Its lowest cells are ${weak.join(", ")}` +
      (s.blast < 0.85
        ? ". There it clears the visible check but fails the held-out regression, a symptomatic rather than root-cause fix. "
        : ", a hair off the ceiling. ")
    : "It scores at or near the ceiling on every scenario. ";
  const costSent =
    `On cost it is ${cheapest.model === s.model
      ? `the cheapest model in the field at $${s.avgCost.toFixed(4)}/run`
      : `$${s.avgCost.toFixed(4)}/run, ${costRatio.toFixed(0)}× the cheapest`}, ` +
    (isFlagship
      ? "the premium choice, worth it when fix correctness is non-negotiable."
      : isBottom
      ? "the throughput option where errors are cheap to catch."
      : "the rational default for the median incident.");

  return standing + charSent + weakSent + costSent;
}
