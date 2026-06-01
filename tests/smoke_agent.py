"""Smoke test for the LLM policy loop WITHOUT hitting any API.

Injects fake Anthropic/OpenAI clients that script a realistic tool-call sequence,
proving run_episode() correctly: translates tool calls into env Actions, feeds
observations back, handles the terminal `submit`, and leaves the env resolved.

Run from the repo root:  python3 tests/smoke_agent.py
"""

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gym import FireDrillEnv  # noqa: E402
from agent.agent import run_episode  # noqa: E402

SCENARIO = Path(__file__).resolve().parent.parent / "scenarios" / "01-payments-service-down"

FIXED_ENV = (
    "# Payments service configuration\n"
    "PORT=8080\nMAX_RETRIES=3\n"
    "STRIPE_API_KEY=sk_test_51FireDrillExampleKeyDoNotUse\nENV=production\n"
)

# The tool-call script both fake models follow to fix the incident.
SCRIPT = [
    ("read_logs", {}),
    ("read_file", {"path": "config/.env"}),
    ("write_file", {"path": "config/.env", "content": FIXED_ENV}),
    ("run_command", {"command": "python3 main.py"}),
    ("submit", {"diagnosis": "config/.env was missing STRIPE_API_KEY and had a "
                "non-integer MAX_RETRIES; fixed both so the service boots."}),
]


# ── Fake Anthropic client ────────────────────────────────────────────────────
class FakeAnthropicMessages:
    def __init__(self): self.i = 0
    def create(self, **kwargs):
        name, args = SCRIPT[self.i]; self.i += 1
        block = SimpleNamespace(type="tool_use", id=f"t{self.i}", name=name, input=args)
        usage = SimpleNamespace(input_tokens=100, output_tokens=20)
        return SimpleNamespace(content=[block], usage=usage, stop_reason="tool_use")

class FakeAnthropic:
    def __init__(self): self.messages = FakeAnthropicMessages()


# ── Fake OpenAI client ───────────────────────────────────────────────────────
class FakeMsg:
    def __init__(self, tool_calls): self.tool_calls = tool_calls
    def model_dump(self, exclude_none=True): return {"role": "assistant", "content": None}

class FakeOpenAICompletions:
    def __init__(self): self.i = 0
    def create(self, **kwargs):
        name, args = SCRIPT[self.i]; self.i += 1
        tc = SimpleNamespace(id=f"c{self.i}",
                             function=SimpleNamespace(name=name, arguments=json.dumps(args)))
        choice = SimpleNamespace(message=FakeMsg([tc]))
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20)
        return SimpleNamespace(choices=[choice], usage=usage)

class FakeOpenAI:
    def __init__(self): self.chat = SimpleNamespace(completions=FakeOpenAICompletions())


def run_one(model: str, client) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env = FireDrillEnv(SCENARIO, Path(tmp) / "workspace", max_steps=30)
        res = run_episode(env, model, client=client)
        reward = env.verify()
        print(f"\n[{model}] stopped={res.stopped_reason} steps={res.steps} "
              f"tokens={res.input_tokens}/{res.output_tokens}")
        print(f"   diagnosis: {res.diagnosis}")
        print(f"   resolution={reward.resolution} clean_fix={reward.clean_fix} "
              f"unexpected={reward.unexpected_files}")
        print(f"   transcript tools: {[t['tool'] for t in res.transcript]}")
        assert res.error is None, res.error
        assert res.stopped_reason == "submit"
        assert res.diagnosis is not None
        assert reward.resolution is True
        assert reward.clean_fix is True
        assert [t["tool"] for t in res.transcript] == [s[0] for s in SCRIPT]
        env.close()


def main() -> int:
    run_one("claude-opus-4-8", FakeAnthropic())
    run_one("gpt-5.5", FakeOpenAI())
    print("\nALL AGENT SMOKE CHECKS PASSED ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
