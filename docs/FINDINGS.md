# FireDrill — Findings Log

A running log of results and observations as we run the matrix, so the dashboard
write-up and README "key findings" can be assembled from real data instead of
reconstructed later. Newest findings at the top. Mark anything provisional.

## Methodology (so numbers are interpretable)

- **Models (4):** flagships `claude-opus-4-8` + `gpt-5.5` (both reasoning at high
  effort); small baselines `claude-haiku-4-5` + `gpt-4.1-mini` (no reasoning).
  - Opus high effort = adaptive thinking + `output_config.effort="high"`.
  - gpt-5.5 high effort = `reasoning_effort="high"` via the Responses API.
  - Parity rationale: gpt-5.5 reasons intrinsically, so Opus must also reason or
    the hard scenarios would be skewed. See PR #10.
- **Reward dims (quality composite):** resolution (0.6) · blast radius (0.2) ·
  diagnosis (0.2). **Cost is a separate first-class axis**, never in the composite.
- **Judge:** diagnosis graded 1–5 by `claude-opus-4-8` regardless of the model
  under test (consistent strong judge).
- **Cost score:** `k/(k+cost_usd)`, k = $0.10 (saturating; no upper bound).

## ⚠️ Caveats that affect absolute $ (fix before quoting hard numbers)

- **Opus mispriced in `eval/pricing.py`:** set to **$15/$75 per 1M**, but Opus 4.8
  is actually **$5/$25**. Opus dollar figures below are ~3× too high; real cost is
  ~1/3 of what's shown. This changes the *flagship ordering*. TODO: fix to $5/$25.
- **gpt-5.5 pricing is a placeholder** ($10/$30). Its absolute $ is a guess until
  the real rate is set (and its API id confirmed).
- Token accounting is cache-aware (4 buckets), but cross-provider caching behavior
  varies run-to-run (cold cache → 0 cache reads).

---

## Finding 1 — The easy tier is quality-saturated; it only separates models on cost

**Scenario:** `01-payments-service-down` (easy, Python). Two layered bugs in
`config/.env` (missing `STRIPE_API_KEY`, non-integer `MAX_RETRIES`); the planted
traceback names the exact failing line.

**Data (all four models, reasoning at parity):**

| model | reasoning | steps | latency | cost (see caveat) | cost_score | composite | resolution | blast | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| gpt-4.1-mini | — | 6 | 10.0s | $0.0025 | 0.975 | 1.0 | ✓ | 1.0 | 5/5 |
| claude-haiku-4-5 | — | 8 | 10.7s | $0.020 | 0.832 | 1.0 | ✓ | 1.0 | 5/5 |
| gpt-5.5 | high | 15 | 30.8s | $0.107* | 0.484 | 1.0 | ✓ | 1.0 | 5/5 |
| claude-opus-4-8 | high | 9 | 19.1s | $0.242* | 0.292 | 1.0 | ✓ | 1.0 | 5/5 |

`*` inflated/placeholder per caveats (Opus ~3× high → real ≈ $0.08; gpt-5.5 placeholder).

**Takeaways:**
1. **All four score composite 1.0** — identical quality. The easy tier does not
   discriminate on quality, *even with the flagships reasoning*. Repeatable result.
2. **Reasoning was pure cost, zero quality gain.** The reasoning flagships cost
   ~10–96× the small models for the identical answer. Lesson: match the model to
   the task — reasoning on a well-signposted incident is wasted spend.
3. **Capability shows up only in the *path*, not the outcome:** gpt-5.5 reasoning
   wandered (15 steps, 30.8s) where the cheap models went straight (6–8 steps).
   Opus reasoning was tighter (9 steps) but pricier per token.
4. **A single composite would hide all of this.** Splitting cost out is what makes
   the 10–96× spread visible behind identical quality — the core design argument.

**Implication for the project:** the discriminating signal must come from the
medium/hard scenarios, where weaker models should actually *fail to resolve*,
misdiagnose, or inflate blast radius. Build those next.

### Side note — non-reasoning baseline (pre-parity, for reference)

Before enabling reasoning, Opus and Haiku both solved 01 at composite 1.0 in 10
steps; gpt-4.1-mini in 6. Enabling reasoning on the flagships changed cost and
step-count but **not** the outcome — reinforcing Finding 1.

---

## Open questions / things to watch as scenarios get harder

- Does reasoning start buying *resolution* (not just spend) on medium/hard, where
  small models fail? That's the hypothesis the harder tier tests.
- Does any model trade resolution for **blast radius** (fixing the bug but breaking
  an unrelated test)? Not yet observed — all fixes clean on 01.
- Diagnosis quality vs resolution: do models ever fix the symptom but misdiagnose
  the root cause (judge < 5 with resolution = ✓)? Watch the silent-data-bug and
  off-by-one scenarios.
- Cost-vs-capability scatter (composite Y, $/job X) is the headline dashboard view.
