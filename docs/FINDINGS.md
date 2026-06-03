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

## Finding 3 — Regression traps work: the gym goes from saturated to discriminating

**The intervention.** Findings 1 & 2 showed the easy/medium tier was quality-
saturated — every model resolved everything, so capability only showed up in the
*path*, not the outcome. So a **held-out regression trap** was added to all ten
scenarios (the lever from Finding 2's pivot): a second, production-shaped bug
where the obvious symptomatic fix passes the visible `success_condition` but
fails a **held-out `regression_check`**. A hasty model takes the bait; a careful
reasoner fixes the root cause.

**Result — full matrix, 10 × 4, reasoning flagships at high effort:**

| model | composite | resolution | blast | diagnosis | reg pass | $/job | $ total |
|---|---|---|---|---|---|---|---|
| claude-opus-4-8 | 0.98 | 100% | 0.90 | 0.98 | 9/10 | $0.0960 | $0.9601 |
| gpt-5.5 | 0.97 | 100% | 0.90 | 0.96 | 9/10 | $0.1080 | $1.0797 |
| claude-haiku-4-5 | 0.90 | 100% | 0.60 | 0.88 | 6/10 | $0.0374 | $0.3735 |
| gpt-4.1-mini | 0.88 | 100% | 0.60 | 0.78 | 6/10 | $0.0055 | $0.0550 |

**Composite spread across models: 0.024 → 0.100 (4×).** A clean two-tier split:
flagships ~0.97, small baselines ~0.89.

**Mechanism (precise).** Resolution stayed **100% for all four** — the trap does
not change whether the visible success condition passes. Discrimination comes
entirely from the held-out regression, and it flows through **blast radius**:
`_blast_score` returns a hard **0** when `regression_passed is False`. So taking
the symptomatic fix costs the full `W_BLAST` (0.2). Flagships pass 9/10
regressions → blast 0.90; small models pass 6/10 → blast 0.60. That 0.30 blast
gap × 0.2 weight, plus a diagnosis gap, *is* the composite gap. **Pass/fail
resolution alone is blind to all of it** — the multi-dimensional reward is what
makes the capability gap legible.

**Which traps fired** (`*` = model failed the held-out regression):

| scenario | opus | gpt-5.5 | haiku | 4.1-mini | spread |
|---|---|---|---|---|---|
| 08-malformed-config | 1.00 | 1.00 | 0.72* | 0.72* | 0.28 |
| 01-payments-service-down | 1.00 | 1.00 | 0.76* | 0.76* | 0.24 |
| 03-off-by-one | 1.00 | 0.96 | 0.76* | 0.76* | 0.24 |
| 02-silent-data-bug | 0.76* | 0.76* | 0.76* | 0.76* | 0.00 |
| 04-failing-test | 1.00 | 1.00 | 0.96 | 0.92 | 0.08 |
| 05-dead-submit-button | 1.00 | 1.00 | 1.00 | 0.92 | 0.08 |
| 06-layout-regression | 1.00 | 1.00 | 1.00 | 0.92 | 0.08 |
| 07-spinner-forever | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| 09-bad-dockerfile | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| 10-wrong-join | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |

**6/10 discriminate (up from 2/10), and three traps (08, 01, 03) fire on the
small models only — the ideal flagship-vs-baseline split.**

**Takeaways:**
1. **Traps are the discrimination lever, and they work *through blast radius*,
   not resolution.** The held-out regression is the mechanism; the multi-dim
   reward is what surfaces it.
2. **Cost finally tracks capability.** Flagships cost ~17× the cheapest model
   ($0.096–0.108 vs $0.0055/job) *and* now score measurably higher — the
   premium is earned, where in Findings 1 & 2 it bought nothing.
3. **Trap calibration is the real craft.** A trap only discriminates in the band
   where flagships catch it and small models don't:
   - **02 is too hard** — float-vs-Decimal fools all four (everyone 0.76).
   - **07 / 09 / 10 are too easy** — response-shape, SIGTERM, JOIN-fan-out edges
     were within every model's reach (all 1.00).
   - **04 / 05 / 06** discriminate only the *weakest* model, via diagnosis/blast,
     not the trap firing.
   Next iteration: soften 02, sharpen 07/09/10. The band is only findable
   empirically — run the matrix, read this table, retune. That loop is the work.

---

## Finding 4 — Single runs are noise; averaging over N reveals the real ordering

**The trap.** After Finding 3 I recalibrated the saturated scenarios (softened 02,
hardened 07/09/10, sharpened 04/05/06). A single re-run looked like a regression:
composite spread *fell* from 0.100 to 0.060, and an **untouched** scenario (08)
swung from 0.28 spread to 0.00. The recalibration looked like a failure.

It wasn't — it was variance. A model's fix quality on a trap varies run to run,
so one run per cell is too noisy to compare. So each cell now runs **N times and
averages** (`run_job --repeat N`; `run_matrix.sh REPEAT=`, default 3).

**Averaged over 6 runs/cell, the picture inverts:**

| model | composite | resolution | blast | diagnosis | $/run | actual |
|---|---|---|---|---|---|---|
| claude-opus-4-8 | 0.99 | 100% | 0.98 | 0.97 | $0.107 | $1.07 |
| gpt-5.5 | 0.99 | 100% | 0.95 | 1.00 | $0.108 | $1.08 |
| claude-haiku-4-5 | 0.94 | 100% | 0.78 | 0.92 | $0.040 | $0.40 |
| gpt-4.1-mini | 0.84 | 90% | 0.62 | 0.87 | $0.0066 | $0.066 |

**Composite spread 0.152 — the largest yet** (0.024 → 0.100 → 0.152), and a stable
ordering: **Opus ≈ GPT-5.5 > Haiku > GPT-4.1-mini**. 7/10 scenarios now
discriminate (>0.05).

**The crucial reversal:** the scenarios I "hardened" in the recalibration —
06-layout-regression (mini 0.67), 09-bad-dockerfile (mini 0.72),
07-spinner-forever (mini 0.83) — scored **0.00 spread on the single noisy run**
but are the **strongest discriminators once averaged**. The harden worked; the
single-run check was lying. Off-by-one-class traps (03, 01) still split both
small models from the flagships.

**Takeaways:**
1. **Average before you conclude.** n=1 per cell swings ±0.28 on an untouched
   scenario; comparing models or judging a recalibration on a single run is
   measuring noise. This is the single most important methodology fix.
2. **The recalibration was right, not wrong** — Finding 3's "negative" follow-up
   was an artifact of n=1. Don't revert on one run.
3. **Still saturated:** 10-wrong-join (the LEFT-JOIN trap every model handles)
   and 04-failing-test (marginal). The tuning band hunt continues — but now on a
   trustworthy average.
4. **Cost is reported two ways:** per-run mean (compare models) and actual spend
   across all runs (the real bill); `cost_score` is recomputed from the mean cost,
   not averaged, since it's non-linear (`k/(k+cost)`).

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
