export const MODEL_META = {
  "claude-opus-4-8": { label: "Claude Opus 4.8", tier: "Flagship · reasoning" },
  "gpt-5.5": { label: "GPT-5.5", tier: "Flagship · reasoning" },
  "claude-haiku-4-5": { label: "Claude Haiku 4.5", tier: "Small" },
  "gpt-4.1-mini": { label: "GPT-4.1 mini", tier: "Small" },
};

// Column order on the matrix / summary.
export const MODEL_ORDER = [
  "claude-opus-4-8",
  "gpt-5.5",
  "claude-haiku-4-5",
  "gpt-4.1-mini",
];

export const modelLabel = (m) => (MODEL_META[m]?.label ?? m);

// Composite → colour band.
export const scoreClass = (c) =>
  c >= 0.85 ? "s-good" : c >= 0.5 ? "s-mid" : "s-bad";

export const money = (n) => "$" + Number(n ?? 0).toFixed(4);
