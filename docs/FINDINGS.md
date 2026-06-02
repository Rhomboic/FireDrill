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

## Pricing (now sourced — numbers below are corrected)

Prices in `eval/pricing.py` are the published per-1M-token API rates (fetched
2026-06, cited in that file): opus-4-8 $5/$25, haiku-4-5 $1/$5, gpt-5.5 $5/$30,
gpt-4.1-mini $0.40/$1.60. Earlier drafts had Opus at old $15/$75 (3× too high)
and gpt-5.5 as a placeholder — those are fixed, and the tables below use the
corrected figures.

Remaining caveats:
- **Confirm the gpt-5.5 API snapshot id** (`MODEL_API_ID`) — price is right, but
  make sure we're billing the model we think we are.
- Token accounting is cache-aware (4 buckets), but cross-provider caching behavior
  varies run-to-run (cold cache → 0 cache reads).

---

## Finding 1 — The easy tier is quality-saturated; it only separates models on cost

**Scenario:** `01-payments-service-down` (easy, Python). Two layered bugs in
`config/.env` (missing `STRIPE_API_KEY`, non-integer `MAX_RETRIES`); the planted
traceback names the exact failing line.

**Data (all four models, reasoning at parity):**

| model | reasoning | steps | latency | cost | cost_score | composite | resolution | blast | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| gpt-4.1-mini | — | 6 | 10.0s | $0.0025 | 0.975 | 1.0 | ✓ | 1.0 | 5/5 |
| claude-haiku-4-5 | — | 8 | 10.7s | $0.020 | 0.832 | 1.0 | ✓ | 1.0 | 5/5 |
| gpt-5.5 | high | 15 | 30.8s | $0.060 | 0.625 | 1.0 | ✓ | 1.0 | 5/5 |
| claude-opus-4-8 | high | 9 | 19.1s | $0.081 | 0.553 | 1.0 | ✓ | 1.0 | 5/5 |

(Corrected pricing. Flagship-vs-mini spread ≈ 32×; with real prices gpt-5.5 is
slightly *cheaper* than Opus here.)

**Takeaways:**
1. **All four score composite 1.0** — identical quality. The easy tier does not
   discriminate on quality, *even with the flagships reasoning*. Repeatable result.
2. **Reasoning was pure cost, zero quality gain.** The reasoning flagships cost
   ~24–32× the small models for the identical answer. Lesson: match the model to
   the task — reasoning on a well-signposted incident is wasted spend.
3. **Capability shows up only in the *path*, not the outcome:** gpt-5.5 reasoning
   wandered (15 steps, 30.8s) where the cheap models went straight (6–8 steps).
   Opus reasoning was tighter (9 steps) but pricier per token.
4. **A single composite would hide all of this.** Splitting cost out is what makes
   the ~32× spread visible behind identical quality — the core design argument.

**Implication for the project:** the discriminating signal must come from the
medium/hard scenarios, where weaker models should actually *fail to resolve*,
misdiagnose, or inflate blast radius. Build those next.

### Side note — non-reasoning baseline (pre-parity, for reference)

Before enabling reasoning, Opus and Haiku both solved 01 at composite 1.0 in 10
steps; gpt-4.1-mini in 6. Enabling reasoning on the flagships changed cost and
step-count but **not** the outcome — reinforcing Finding 1.

---

## Finding 2 — "Silent / no traceback" does NOT make a task hard; scale and indirection do

**Scenario:** `02-silent-data-bug` (medium, Python). A revenue pipeline that runs
clean (exit 0) but undercounts: `summarize()` indexes transactions into a dict
keyed by `customer_id`, silently dropping repeat customers (10/$964.50 → 7/$564).
No crash, no traceback — designed to force the model to read and reason.

**Data (all four, reasoning at parity, corrected pricing):**

| model | reasoning | steps | cost | cost_score | composite | resolution | blast | diagnosis |
|---|---|---|---|---|---|---|---|---|
| gpt-4.1-mini | — | 7 | $0.0027 | 0.974 | 1.0 | ✓ | 1.0 | 5/5 |
| claude-haiku-4-5 | — | 10 | $0.023 | 0.814 | 1.0 | ✓ | 1.0 | 5/5 |
| gpt-5.5 | high | 6 | $0.030 | 0.771 | 1.0 | ✓ | 1.0 | 5/5 |
| claude-opus-4-8 | high | 6 | $0.059 | 0.628 | 1.0 | ✓ | 1.0 | 5/5 |

**The prediction was wrong, and that's the finding.** We expected the silent bug
to separate the models (a weak one fixing the symptom but misdiagnosing). Instead
**all four — including the cheapest, gpt-4.1-mini — precisely identified the
`customer_id` dedup, fixed exactly `pipeline.py`, and earned a clean 5/5.** Their
diagnoses are genuinely correct, not lucky (e.g. gpt-4.1-mini: *"wrongly grouped
transactions by unique customers… fixed by summing and counting all transactions
directly"*).

**Takeaways:**
1. **Bug *type* (silent vs. crashing) is the wrong difficulty axis.** A ~10-line
   function with the expected figures sitting in the logs is trivial for every
   modern model. Both tiers so far (easy + medium) are quality-saturated.
2. **The axis that actually discriminates is scale & indirection** — large
   codebases, the bug several call-hops from the symptom, multiple plausible
   suspects, bugs that require *running experiments* to localize. Our scenarios
   are too small/local.
3. **Cost is again the only differentiator** (~22× spread; gpt-4.1-mini wins).
   Reasoning bought nothing — though here the flagships were *step*-efficient
   (6 steps) vs. Haiku (10).

### Design pivot (the important takeaway)

To produce a real quality spread, future scenarios must discriminate on one of:

- **A. Scale / indirection** — bigger, multi-file projects where localizing the
  bug is the hard part. Produces a *resolution* spread.
- **B. Traps (the Fleet-unique lever)** — the *obvious* fix passes the success
  condition but **breaks a held-out `regression_check`**. A weak model takes the
  bait (resolves but high **blast radius**); a careful one doesn't. This
  discriminates without a huge codebase and exercises the blast-radius dimension
  directly — exactly what a gym is for. **Prioritize this.**

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
