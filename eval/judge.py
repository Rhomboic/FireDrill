"""
judge.py — LLM-as-judge for diagnosis quality.

The objective dimensions (resolution, efficiency, blast radius) come straight
from the environment. Diagnosis quality does not: it asks whether the agent
actually *understood* the incident. We grade the agent's one-sentence diagnosis
against the scenario's ground-truth root cause with a second model on a 1–5
rubric, returning a score plus a short rationale.

The judge client is injectable so the scoring path can be tested without network.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-opus-4-8")

RUBRIC = """You are a strict senior engineer grading an on-call agent's root-cause
diagnosis of a production incident. Compare the agent's diagnosis to the known
ground-truth root cause. Score the agent's diagnosis from 1 to 5:

5 — Correct and complete: identifies the true root cause(s) accurately.
4 — Correct main cause but misses a secondary cause or a detail.
3 — Partially correct: on the right track but vague, or only one of several causes.
2 — Mostly wrong: mentions a symptom, not the cause, or a plausible-but-wrong cause.
1 — Wrong, empty, or unrelated.

Judge ONLY the diagnosis text against the ground truth — not whether files were
changed. Reward understanding, penalize hand-waving and symptom-restating.

Respond with ONLY a JSON object: {"score": <1-5>, "rationale": "<one sentence>"}"""


def _build_prompt(scenario_description: str, correct: str, agent: str) -> str:
    return (
        f"Incident (as the agent saw it):\n{scenario_description}\n\n"
        f"GROUND-TRUTH root cause:\n{correct}\n\n"
        f"AGENT'S diagnosis:\n{agent or '(the agent submitted no diagnosis)'}\n\n"
        f"Score the agent's diagnosis."
    )


def _parse(text: str) -> dict[str, Any]:
    """Pull the JSON verdict out of the model's reply, defensively."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            score = int(obj.get("score", 1))
            score = max(1, min(5, score))
            return {"score": score, "rationale": str(obj.get("rationale", "")).strip()}
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return {"score": 1, "rationale": f"unparseable judge response: {text[:160]}"}


def score_diagnosis(agent_diagnosis: Optional[str], correct_diagnosis: str,
                    scenario_description: str = "", client: Any = None,
                    model: str = JUDGE_MODEL) -> dict[str, Any]:
    """Return {"score": 1-5, "rationale": str, "model": str}.

    An empty/None agent diagnosis scores 1 without spending a call.
    """
    if not agent_diagnosis or not agent_diagnosis.strip():
        return {"score": 1, "rationale": "no diagnosis submitted", "model": model}

    if client is None:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=120.0)

    try:
        resp = client.messages.create(
            model=model, max_tokens=300,
            system=[{"type": "text", "text": RUBRIC,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": _build_prompt(
                scenario_description, correct_diagnosis, agent_diagnosis)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        verdict = _parse(text)
    except Exception as e:  # noqa: BLE001
        return {"score": 1, "rationale": f"judge error: {type(e).__name__}: {e}",
                "model": model}

    verdict["model"] = model
    return verdict
