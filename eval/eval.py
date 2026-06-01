"""
eval.py — turn one episode into a scored, self-describing result.

The gym already produced the hard signals: env.verify() gives resolution, blast
radius, and regression; the policy's EpisodeResult gives the transcript, step
count, tokens, and the agent's diagnosis. This module:

  1. adds the one signal the env can't compute — diagnosis quality (LLM judge),
  2. normalises the four dimensions onto 0–1 and a single composite for ranking,
  3. assembles the results payload that gets written to S3 — a record that fully
     explains, after the container is gone, what broke, what the agent did, the
     judge's verdict, and the objective proof the fix works.

Dimensions are kept separate on purpose: a gym consumer (or RL loop) can reweight
them. The composite is just a convenience for sorting a leaderboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

# Composite weights (for ranking only — the raw dimensions are the real output).
W_RESOLUTION = 0.50
W_EFFICIENCY = 0.15
W_BLAST = 0.15
W_DIAGNOSIS = 0.20

DEFAULT_STEP_BUDGET = 30


def _efficiency_score(steps: int, step_budget: int) -> float:
    """Fewer steps is better; reaches 0 at the step budget."""
    if step_budget <= 0:
        return 0.0
    return round(max(0.0, 1.0 - steps / step_budget), 4)


def _blast_score(unexpected_files: list[str], regression_passed: Optional[bool]) -> float:
    """1.0 for a precise fix; a failed regression is a hard 0; otherwise decays
    with the number of files touched outside the expected set."""
    if regression_passed is False:
        return 0.0
    return round(1.0 / (1.0 + len(unexpected_files)), 4)


def score_episode(scenario_meta: dict, reward: Any, episode: Any,
                  judge_verdict: dict, *, step_budget: int = DEFAULT_STEP_BUDGET,
                  diffs: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Build the full scored results payload for one (scenario × model) job.

    Args:
        scenario_meta: the scenario's metadata.json (ground truth).
        reward:        RewardSignal from env.verify().
        episode:       EpisodeResult from the policy.
        judge_verdict: {"score", "rationale", "model"} from judge.score_diagnosis.
        step_budget:   env.max_steps, for normalising efficiency.
        diffs:         optional {path: unified_diff} of what the agent changed.
    """
    resolution = bool(reward.resolution)
    diag_score = int(judge_verdict.get("score", 1))

    eff = _efficiency_score(episode.steps, step_budget)
    blast = _blast_score(reward.unexpected_files, reward.regression_passed)
    diag_norm = round(diag_score / 5.0, 4)

    composite = round(
        W_RESOLUTION * (1.0 if resolution else 0.0)
        + W_EFFICIENCY * eff
        + W_BLAST * blast
        + W_DIAGNOSIS * diag_norm,
        4,
    )

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

        # ── efficiency / cost ──
        "efficiency": {
            "steps": episode.steps,
            "stopped_reason": episode.stopped_reason,
            "input_tokens": episode.input_tokens,
            "output_tokens": episode.output_tokens,
            "latency_ms": episode.latency_ms,
        },

        # ── blast radius ──
        "blast_radius": {
            "unexpected_files": reward.unexpected_files,
            "regression_passed": reward.regression_passed,
            "clean_fix": reward.clean_fix,
        },

        # ── the four dimensions, normalised, plus composite ──
        "scores": {
            "resolution": 1.0 if resolution else 0.0,
            "efficiency": eff,
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
        "resolution_rate": round(sum(r["scores"]["resolution"] for r in results) / n, 4),
        "clean_fix_rate": round(sum(1 for r in results if r["blast_radius"]["clean_fix"]) / n, 4),
        "avg_composite": mean("scores", "composite"),
        "avg_efficiency": mean("scores", "efficiency"),
        "avg_blast_radius": mean("scores", "blast_radius"),
        "avg_diagnosis": mean("scores", "diagnosis"),
        "avg_steps": round(sum(r["efficiency"]["steps"] for r in results) / n, 2),
        "total_input_tokens": sum(r["efficiency"]["input_tokens"] for r in results),
        "total_output_tokens": sum(r["efficiency"]["output_tokens"] for r in results),
    }
