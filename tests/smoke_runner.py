"""Smoke test for the job runner WITHOUT hitting any API.

Drives run_job() with injected fake agent + judge clients, then asserts it wrote
a well-formed results JSON including the unified diff of the agent's fix.

Run from the repo root:  python3 tests/smoke_runner.py
"""

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner.run_job import run_job  # noqa: E402

FIXED_ENV = ("# Payments service configuration\nPORT=8080\nMAX_RETRIES=3\n"
             "STRIPE_API_KEY=sk_test_51FireDrillExampleKeyDoNotUse\nENV=production\n")

# The agent's full fix: repair config/.env AND correct the off-by-one in
# call_with_retries (the held-out regression trap) so the fix scores as clean.
SCEN_DIR = (Path(__file__).resolve().parent.parent
            / "scenarios" / "01-payments-service-down" / "filesystem")
FIXED_PAYMENTS = (SCEN_DIR / "app" / "payments.py").read_text().replace(
    "for attempt in range(1, attempts):", "for attempt in range(1, attempts + 1):")
assert "range(1, attempts + 1)" in FIXED_PAYMENTS, "off-by-one line not found to patch"

SCRIPT = [
    ("read_logs", {}),
    ("write_file", {"path": "config/.env", "content": FIXED_ENV}),
    ("write_file", {"path": "app/payments.py", "content": FIXED_PAYMENTS}),
    ("run_command", {"command": "python3 main.py"}),
    ("submit", {"diagnosis": "config/.env lacked STRIPE_API_KEY and had a bad "
                "MAX_RETRIES; set both so the service boots. Also fixed the "
                "off-by-one in call_with_retries so it uses the full retry budget."}),
]


class _AgentMsgs:
    def __init__(self): self.i = 0
    def create(self, **k):
        name, args = SCRIPT[self.i]; self.i += 1
        b = SimpleNamespace(type="tool_use", id=f"t{self.i}", name=name, input=args)
        return SimpleNamespace(content=[b], stop_reason="tool_use",
                               usage=SimpleNamespace(input_tokens=80, output_tokens=15))

class FakeAgent:
    def __init__(self): self.messages = _AgentMsgs()


class _JudgeMsgs:
    def create(self, **k):
        return SimpleNamespace(content=[SimpleNamespace(
            type="text", text='{"score": 4, "rationale": "right root cause"}')])

class FakeJudge:
    def __init__(self): self.messages = _JudgeMsgs()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        payload = run_job("01-payments-service-down", "claude-opus-4-8",
                          out_dir=tmp, agent_client=FakeAgent(), judge_client=FakeJudge())

        # results file written where the dashboard/S3 layout expects it
        out_file = Path(tmp) / "claude-opus-4-8" / "01-payments-service-down.json"
        assert out_file.is_file(), "results JSON not written"
        on_disk = json.loads(out_file.read_text())
        assert on_disk == payload

    assert payload["scores"]["resolution"] == 1.0
    assert payload["scores"]["composite"] > 0
    assert "cost" not in payload["scores"]          # cost is its own axis
    assert payload["diagnosis"]["score"] == 4
    assert payload["blast_radius"]["clean_fix"] is True
    assert payload["cost"]["cost_usd"] > 0 and 0 < payload["cost"]["cost_score"] <= 1

    diffs = payload["fix"]["diffs"]
    assert "config/.env" in diffs
    assert "STRIPE_API_KEY" in diffs["config/.env"]
    assert diffs["config/.env"].startswith("---") or "@@" in diffs["config/.env"]

    print("results scores:", payload["scores"])
    print("diff (config/.env):")
    print(diffs["config/.env"])
    print("ALL RUNNER SMOKE CHECKS PASSED ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
