import { modelLabel } from "./meta.js";

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
    totalCost: sum(js.map((j) => j.cost?.cost_usd ?? 0)),
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
