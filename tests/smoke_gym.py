"""Smoke test: drive FireDrillEnv with a SCRIPTED policy (no LLM) to prove the
gym core works and is policy-agnostic.

Run from the repo root:  python3 tests/smoke_gym.py
"""
import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path
from gym import FireDrillEnv, Action, SUBMIT, anthropic_tools, openai_tools

# Build a throwaway scenario: a script that crashes because GREETING is unset.
tmp = Path(tempfile.mkdtemp())
scen = tmp / "scenario"; fs = scen / "filesystem"; (fs / "logs").mkdir(parents=True)
(fs / "main.py").write_text(
    "import os\n"
    "g = os.environ['GREETING']  # KeyError when unset\n"
    "print(g)\n"
)
(fs / "logs" / "error.log").write_text("KeyError: 'GREETING'\n")
(scen / "metadata.json").write_text(json.dumps({
    "name": "greeting-crash", "stack": "python",
    "description": "main.py crashes on startup with a KeyError.",
    "bugs": ["GREETING env var read but never set"],
    "success_condition": {"cmd": "python3 main.py", "exit": 0},
    "files_expected_to_change": ["main.py"],
    "correct_diagnosis": "main.py read an undefined GREETING env var; gave it a default.",
}))

ws = tmp / "workspace"
env = FireDrillEnv(scen, ws, max_steps=10)

print("anthropic tools:", [t["name"] for t in anthropic_tools()])
print("openai tools:   ", [t["function"]["name"] for t in openai_tools()])

obs = env.reset()
assert "Incident report" in obs.text and "main.py" in obs.text
print("\n[reset] task shown, root listing present ✓")

# verify BEFORE fix → must be broken
r0 = env.verify()
print(f"[verify pre-fix] resolution={r0.resolution} (expect False)")
assert r0.resolution is False

# scripted policy: read logs, read file, write fix, submit
env.reset()
sr = env.step(Action("read_logs"))
assert "KeyError" in sr.observation.text
sr = env.step(Action("read_file", {"path": "main.py"}))
assert "GREETING" in sr.observation.text
fix = "import os\ng = os.environ.get('GREETING', 'hello')\nprint(g)\n"
sr = env.step(Action("write_file", {"path": "main.py", "content": fix}))
assert sr.observation.ok
# blast radius mid-episode
print(f"[mid] files_modified={sr.reward.files_modified} unexpected={sr.reward.unexpected_files}")
assert sr.reward.files_modified == ["main.py"]
assert sr.reward.unexpected_files == []

sr = env.step(Action(SUBMIT, {"diagnosis": "GREETING env var was unset; added a default."}))
assert sr.done
rw = sr.reward
print(f"[submit] resolution={rw.resolution} clean_fix={rw.clean_fix} steps={rw.steps} diagnosis={env.diagnosis!r}")
assert rw.resolution is True
assert rw.clean_fix is True

# test unexpected blast radius + path escape + snapshot/restore
env.reset()
env.step(Action("write_file", {"path": "extra.py", "content": "x=1"}))
r = env.verify()
print(f"[blast] modified={r.files_modified} unexpected={r.unexpected_files} (extra.py should be unexpected)")
assert "extra.py" in r.unexpected_files
esc = env.step(Action("read_file", {"path": "../../../etc/passwd"}))
print(f"[escape] ok={esc.observation.ok} text={esc.observation.text[:40]!r}")
assert esc.observation.ok is False

snap = env.snapshot()
env.step(Action("write_file", {"path": "main.py", "content": "broken"}))
env.restore(snap)
assert (ws / "main.py").read_text() != "broken"
print("[snapshot/restore] state restored ✓")

env.close()
assert not ws.exists()
print("\nALL SMOKE CHECKS PASSED ✓")
