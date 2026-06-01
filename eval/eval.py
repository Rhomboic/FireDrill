"""
eval.py — turn one episode into a scored, self-describing result.

The gym already produced the hard signals: env.verify() gives resolution, blast
radius, and regression; the policy's EpisodeResult gives the transcript, step
count, tokens, and the agent's diagnosis. This module:

  1. adds the one signal the env can't compute — diagnosis quality (LLM judge),
  2. normalises the QUALITY dimensions onto 0–1 and a single composite for ranking,
  3. assembles the results payload that gets written to S3 — a record that fully
     explains, after the container is gone, what broke, what the agent did, the
     judge's verdict, and the objective proof the fix works.

Cost is treated as a SEPARATE first-class axis, not folded into the composite:
quality answers "did it do the job well", cost answers "what did that cost", and
blending them hides the tradeoff a lab actually reasons about (cost vs capability).
Dimensions are kept separate on purpose: a gym consumer (or RL loop) can reweight
them. The composite is just a convenience for sorting a leaderboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .pricing import cost_usd, has_pricing

# Composite is QUALITY ONLY (cost is a separate axis). Weights sum to 1.
W_RESOLUTION = 0.60
W_BLAST = 0.20
W_DIAGNOSIS = 0.20

# Cost score is a saturating function k/(k+cost): no upper bound needed, just a
# scale. cost == COST_HALF_SCORE_USD scores 0.5; it decays toward 0 from there.
# Set to a "reasonable cost for one incident" reference, not a hard cap.
COST_HALF_SCORE_USD = 0.10


def _cost_score(cost: float) -> float:
    """Map an unbounded dollar cost to (0, 1]; cheaper is higher. No max needed."""
    if cost <= 0:
        return 1.0
    return round(COST_HALF_SCORE_USD / (COST_HALF_SCORE_USD + cost), 4)


def _blast_score(unexpected_files: list[str], regression_passed: Optional[bool]) -> float:
    """1.0 for a precise fix; a failed regression is a hard 0; otherwise decays
    with the number of files touched outside the expected set."""
    if regression_passed is False:
        return 0.0
    return round(1.0 / (1.0 + len(unexpected_files)), 4)


def score_episode(scenario_meta: dict, reward: Any, episode: Any,
                  judge_verdict: dict, *,
                  diffs: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Build the full scored results payload for one (scenario × model) job.

    Args:
        scenario_meta: the scenario's metadata.json (ground truth).
        reward:        RewardSignal from env.verify().
        episode:       EpisodeResult from the policy.
        judge_verdict: {"score", "rationale", "model"} from judge.score_diagnosis.
        diffs:         optional {path: unified_diff} of what the agent changed.
    """
    resolution = bool(reward.resolution)
    diag_score = int(judge_verdict.get("score", 1))

    blast = _blast_score(reward.unexpected_files, reward.regression_passed)
    diag_norm = round(diag_score / 5.0, 4)

    # Composite is QUALITY ONLY — cost stays out of it.
    composite = round(
        W_RESOLUTION * (1.0 if resolution else 0.0)
        + W_BLAST * blast
        + W_DIAGNOSIS * diag_norm,
        4,
    )

    # Cost axis (reported separately, not in the composite).
    usage = episode.usage
    cost = cost_usd(episode.model, usage)
    cost_score = _cost_score(cost)

    return {
        # ── identity ──
        "scenario": scenario_meta.get("name"),
        "stack": scenario_meta.get("stack"),
        "difficulty": scenario_meta.get("difficulty"),
        "model": episode.model,
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # ── what the agent figured out ──
        "diagnosis": {
            "agent": episode.diagnosis,
            "correct": scenario_meta.get("correct_diagnosis"),
            "score": diag_score,
            "rationale": judge_verdict.get("rationale", ""),
            "judge_model": judge_verdict.get("model"),
        },

        # ── how it fixed it ──
        "fix": {
            "files_modified": reward.files_modified,
            "files_expected": reward.files_expected,
            "unexpected_files": reward.unexpected_files,
            "diffs": diffs or {},
        },
        "transcript": episode.transcript,

        # ── objective verification (proof it works now) ──
        "verification": reward.detail,
        "regression_passed": reward.regression_passed,

        # ── efficiency (operational stats; steps shown but NOT scored) ──
        "efficiency": {
            "steps": episode.steps,
            "stopped_reason": episode.stopped_reason,
            "latency_ms": episode.latency_ms,
        },

        # ── cost: a separate first-class axis (NOT in the composite) ──
        "cost": {
            **usage,
            "total_tokens": sum(usage.values()),
            "cost_usd": cost,
            "cost_score": cost_score,
            "priced": has_pricing(episode.model),
        },

        # ── blast radius ──
        "blast_radius": {
            "unexpected_files": reward.unexpected_files,
            "regression_passed": reward.regression_passed,
            "clean_fix": reward.clean_fix,
        },

        # ── the QUALITY dimensions, normalised, plus composite ──
        "scores": {
            "resolution": 1.0 if resolution else 0.0,
            "blast_radius": blast,
            "diagnosis": diag_norm,
            "composite": composite,
        },

        "error": episode.error,
    }


def aggregate(results: list[dict]) -> dict[str, Any]:
    """Summarise a set of scored results (e.g. all scenarios for one model)."""
    n = len(results)
    if n == 0:
        return {"count": 0}

    def mean(path_a: str, path_b: str) -> float:
        return round(sum(r[path_a][path_b] for r in results) / n, 4)

    return {
        "count": n,
        # quality
        "resolution_rate": round(sum(r["scores"]["resolution"] for r in results) / n, 4),
        "clean_fix_rate": round(sum(1 for r in results if r["blast_radius"]["clean_fix"]) / n, 4),
        "avg_composite": mean("scores", "composite"),
        "avg_blast_radius": mean("scores", "blast_radius"),
        "avg_diagnosis": mean("scores", "diagnosis"),
        # cost axis (separate)
        "avg_steps": round(sum(r["efficiency"]["steps"] for r in results) / n, 2),
        "total_cost_usd": round(sum(r["cost"]["cost_usd"] for r in results), 6),
        "total_tokens": sum(r["cost"]["total_tokens"] for r in results),
    }
