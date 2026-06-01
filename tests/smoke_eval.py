"""Smoke test for eval + judge WITHOUT hitting any API.

Runs a real episode against scenario 01 (driven by a fake agent client), scores
the objective dimensions from the env, judges the diagnosis with a fake judge
client, and asserts the assembled results payload is well-formed.

Run from the repo root:  python3 tests/smoke_eval.py
"""

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gym import FireDrillEnv  # noqa: E402
from agent.agent import run_episode  # noqa: E402
from eval.judge import score_diagnosis, _parse  # noqa: E402
from eval.eval import score_episode, aggregate  # noqa: E402

SCENARIO = Path(__file__).resolve().parent.parent / "scenarios" / "01-payments-service-down"
META = json.loads((SCENARIO / "metadata.json").read_text())

FIXED_ENV = ("# Payments service configuration\nPORT=8080\nMAX_RETRIES=3\n"
             "STRIPE_API_KEY=sk_test_51FireDrillExampleKeyDoNotUse\nENV=production\n")
SCRIPT = [
    ("read_logs", {}),
    ("write_file", {"path": "config/.env", "content": FIXED_ENV}),
    ("run_command", {"command": "python3 main.py"}),
    ("submit", {"diagnosis": "config/.env lacked STRIPE_API_KEY and had a "
                "non-integer MAX_RETRIES; set both so the service boots."}),
]


class _FakeAgentMessages:
    def __init__(self): self.i = 0
    def create(self, **k):
        name, args = SCRIPT[self.i]; self.i += 1
        block = SimpleNamespace(type="tool_use", id=f"t{self.i}", name=name, input=args)
        return SimpleNamespace(content=[block],
                               usage=SimpleNamespace(input_tokens=80, output_tokens=15),
                               stop_reason="tool_use")

class FakeAgent:
    def __init__(self): self.messages = _FakeAgentMessages()


class _FakeJudgeMessages:
    def create(self, **k):
        text = '{"score": 5, "rationale": "identifies both the missing key and bad retry value"}'
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

class FakeJudge:
    def __init__(self): self.messages = _FakeJudgeMessages()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        env = FireDrillEnv(SCENARIO, Path(tmp) / "ws", max_steps=30)
        episode = run_episode(env, "claude-opus-4-8", client=FakeAgent())
        reward = env.verify()

        verdict = score_diagnosis(episode.diagnosis, META["correct_diagnosis"],
                                  META["description"], client=FakeJudge())
        assert verdict["score"] == 5, verdict

        payload = score_episode(META, reward, episode, verdict)
        env.close()

    s = payload["scores"]
    cost = payload["cost"]
    print("quality scores:", s)
    print("cost axis:", {k: cost[k] for k in ("total_tokens", "cost_usd", "cost_score", "priced")})
    print("diagnosis:", payload["diagnosis"]["score"], "-", payload["diagnosis"]["rationale"])

    # composite is QUALITY ONLY: 0.6*res + 0.2*blast + 0.2*diag; cost is excluded
    assert s["resolution"] == 1.0
    assert s["blast_radius"] == 1.0
    assert s["diagnosis"] == 1.0
    assert s["composite"] == 1.0, s["composite"]      # 0.6 + 0.2 + 0.2, no cost term
    assert "efficiency" not in s and "cost" not in s  # cost stays out of the composite
    assert payload["blast_radius"]["clean_fix"] is True

    # cost is its own first-class axis
    assert cost["priced"] is True
    assert cost["cost_usd"] > 0
    assert 0.0 < cost["cost_score"] <= 1.0
    assert cost["total_tokens"] == sum(payload["cost"][k] for k in
                                       ("input_tokens", "output_tokens",
                                        "cache_read_tokens", "cache_write_tokens"))

    assert payload["diagnosis"]["agent"]
    assert payload["diagnosis"]["correct"] == META["correct_diagnosis"]
    assert "success_condition" in payload["verification"]
    assert payload["transcript"] and payload["transcript"][-1]["tool"] == "submit"
    assert payload["error"] is None

    agg = aggregate([payload])
    assert agg["resolution_rate"] == 1.0 and agg["count"] == 1
    assert agg["total_cost_usd"] == cost["cost_usd"]

    # judge robustness (no network)
    assert score_diagnosis("", "anything")["score"] == 1           # empty -> 1, no call
    assert _parse("total garbage")["score"] == 1                   # unparseable -> 1
    assert _parse('noise {"score": 7, "rationale": "x"} tail')["score"] == 5  # clamp 7->5

    print("\nALL EVAL SMOKE CHECKS PASSED ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
