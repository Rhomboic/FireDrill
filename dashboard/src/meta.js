export const MODEL_META = {
  "claude-opus-4-8": { label: "Claude Opus 4.8", tier: "Flagship · reasoning", vendor: "claude" },
  "gpt-5.5": { label: "GPT-5.5", tier: "Flagship · reasoning", vendor: "openai" },
  "claude-haiku-4-5": { label: "Claude Haiku 4.5", tier: "Small baseline", vendor: "claude" },
  "gpt-4.1-mini": { label: "GPT-4.1 mini", tier: "Small baseline", vendor: "openai" },
};

// Column order on the matrix / summary.
export const MODEL_ORDER = [
  "claude-opus-4-8",
  "gpt-5.5",
  "claude-haiku-4-5",
  "gpt-4.1-mini",
];

export const modelLabel = (m) => (MODEL_META[m]?.label ?? m);
export const modelVendor = (m) => (MODEL_META[m]?.vendor ?? "claude");
export const vendorBadge = (m) =>
  modelVendor(m) === "openai" ? "badge badge-openai" : "badge badge-claude";

// Composite → colour band (legacy, discrete).
export const scoreClass = (c) =>
  c >= 0.85 ? "s-good" : c >= 0.5 ? "s-mid" : "s-bad";

// Composite → continuous colour. 1.0 = green, 0.6 and below = red, and a smooth
// red, orange, yellow, green hue gradient over (0.6, 1.0). Returns
// { fg, bg } for the cell's text and (translucent) background.
export const scoreColor = (c) => {
  const t = Math.max(0, Math.min(1, Number(c ?? 0)));
  const u = Math.max(0, Math.min(1, (t - 0.6) / 0.4)); // 0 at <=0.6, 1 at 1.0
  const hue = u * 140; // 0 = red, 140 = green
  return {
    fg: `hsl(${hue}, 80%, 62%)`,
    bg: `hsla(${hue}, 70%, 45%, 0.20)`,
  };
};

export const money = (n) => "$" + Number(n ?? 0).toFixed(4);
export const pct = (n) => (n * 100).toFixed(0) + "%";
