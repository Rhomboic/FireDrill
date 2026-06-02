"""
environment.py

FireDrillEnv — the core gym primitive. A stateful, resettable, Gymnasium-style
environment wrapping one broken software project. It is fully decoupled from any
agent: it exposes reset / step / verify / snapshot / restore, and any policy that
speaks the gym/protocol.py types can drive it.

A scenario directory contains:
    metadata.json     ground truth (success condition, expected files, diagnosis)
    filesystem/       the pristine "golden" broken project

reset() restores filesystem/ into the workspace, so episodes are reproducible and
one container can host many rollouts. Ground truth lives in the scenario dir,
never inside the workspace, so the agent cannot read the answer key.

Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from .protocol import Action, Observation, RewardSignal, StepResult, SUBMIT
from .tools import ToolExecutor, TOOL_NAMES

DEFAULT_MAX_STEPS = 30

# Blast radius must track SOURCE changes, not runtime byproducts. Executing the
# project (e.g. running its tests or `python main.py` during verify()) generates
# bytecode caches, build output, and tool caches that are not edits the agent
# made — counting them would inflate blast radius nondeterministically across
# machines. These are excluded from hashing, snapshot, and the modified-file set.
IGNORED_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "node_modules", ".git", ".venv", "venv", ".cache", "dist", "build",
    ".next", ".parcel-cache", "test-results", "playwright-report",
}
IGNORED_SUFFIXES = (".pyc", ".pyo")
IGNORED_NAMES = {".DS_Store"}

TASK_PREAMBLE = """It's 11pm and you are the on-call engineer. A service is broken.
Investigate the project, find the root cause, and fix it. You have these tools:
  read_file, write_file, list_directory, read_logs, run_command
Work inside the project directory. When you are confident the incident is
resolved, call `submit` with a one-sentence root-cause diagnosis of what was
wrong and how you fixed it.

Incident report:
"""


class FireDrillEnv:
    def __init__(self, scenario_dir: str | Path, workspace: str | Path,
                 max_steps: int = DEFAULT_MAX_STEPS, cmd_timeout: int = 120):
        self.scenario_dir = Path(scenario_dir).resolve()
        self.workspace = Path(workspace).resolve()
        self.golden = self.scenario_dir / "filesystem"
        self.max_steps = max_steps
        self.cmd_timeout = cmd_timeout

        if not self.golden.is_dir():
            raise FileNotFoundError(f"scenario has no filesystem/ at {self.golden}")
        self.metadata = self._load_metadata()

        # Grader files (tests / verifiers) the agent must not be able to tamper
        # with. They are restored from golden before scoring (so resolution is
        # un-gameable) and excluded from blast radius (so editing them isn't
        # counted as collateral damage). Paths are relative to the workspace;
        # a value may be a file or a directory prefix.
        self.protected_paths = list(self.metadata.get("protected_paths", []))

        self.tools = ToolExecutor(self.workspace, cmd_timeout=cmd_timeout)

        # episode state (populated by reset)
        self.steps = 0
        self.done = False
        self.diagnosis: Optional[str] = None
        self._initial_hashes: dict[str, str] = {}

    # ── metadata ────────────────────────────────────────────────────────────────
    def _load_metadata(self) -> dict[str, Any]:
        meta_path = self.scenario_dir / "metadata.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"scenario has no metadata.json at {meta_path}")
        return json.loads(meta_path.read_text())

    @property
    def task(self) -> str:
        """The prompt shown to a policy. Deliberately excludes ground truth
        (bugs, correct_diagnosis, expected files)."""
        return TASK_PREAMBLE + self.metadata.get("description", "(no description)")

    # ── filesystem helpers ──────────────────────────────────────────────────────
    def _restore_golden(self) -> None:
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        shutil.copytree(self.golden, self.workspace)

    def _is_protected(self, rel: str) -> bool:
        """True if a relative path is (under) a protected grader path."""
        rel = rel.replace("\\", "/")
        for p in self.protected_paths:
            p = str(p).strip("/").replace("\\", "/")
            if rel == p or rel.startswith(p + "/"):
                return True
        return False

    def _restore_protected(self) -> None:
        """Reset the grader files to their pristine golden state so the agent's
        edits to them can't influence scoring. Run right before verify()."""
        for p in self.protected_paths:
            rel = str(p).strip("/")
            golden_src = self.golden / rel
            ws_dst = self.workspace / rel
            if not golden_src.exists():
                continue
            if golden_src.is_dir():
                if ws_dst.exists():
                    shutil.rmtree(ws_dst)
                shutil.copytree(golden_src, ws_dst)
            else:
                ws_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(golden_src, ws_dst)

    def _is_ignored(self, f: Path) -> bool:
        """True for runtime byproducts (caches, bytecode) that are not agent edits."""
        rel_parts = f.relative_to(self.workspace).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            return True
        return f.suffix in IGNORED_SUFFIXES or f.name in IGNORED_NAMES

    def _tracked_files(self):
        """Yield workspace files that count as source (excludes generated artifacts)."""
        for f in sorted(self.workspace.rglob("*")):
            if f.is_file() and not self._is_ignored(f):
                yield f

    def _hash_workspace(self) -> dict[str, str]:
        """sha256 of every source file under the workspace, keyed by relative path."""
        return {
            str(f.relative_to(self.workspace)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in self._tracked_files()
        }

    def _modified_files(self) -> list[str]:
        """Files created, deleted, or changed since reset — the raw blast radius.
        Protected grader files are excluded (editing a test is not collateral
        damage, and resolution is graded against the pristine copy anyway)."""
        current = self._hash_workspace()
        before, after = self._initial_hashes, current
        changed = {p for p in after if before.get(p) != after[p]}
        deleted = {p for p in before if p not in after}
        return sorted(p for p in (changed | deleted) if not self._is_protected(p))

    # ── gym API ───────────────────────────────────────────────────────────────
    def reset(self) -> Observation:
        """Restore the pristine project and start a fresh episode."""
        self._restore_golden()
        self.steps = 0
        self.done = False
        self.diagnosis = None
        self._initial_hashes = self._hash_workspace()
        listing = self.tools.list_directory(".").text
        text = f"{self.task}\n\nProject root:\n{listing}"
        return Observation(text=text, source="reset")

    def step(self, action: Action) -> StepResult:
        """Apply one action. `submit` ends the episode; max_steps also ends it."""
        if self.done:
            raise RuntimeError("episode is done; call reset() before stepping again")

        # terminal action: record the diagnosis and finish.
        if action.tool == SUBMIT:
            self.diagnosis = str(action.args.get("diagnosis", "")).strip()
            self.done = True
            obs = Observation(text="episode submitted", source=SUBMIT)
            return StepResult(obs, self.verify(), done=True,
                              info={"reason": "submit", "diagnosis": self.diagnosis})

        obs = self.tools.execute(action)
        self.steps += 1
        if self.steps >= self.max_steps:
            self.done = True
            return StepResult(obs, self.verify(), done=True,
                              info={"reason": "max_steps"})

        # Cheap signals only between steps; the full objective verify() runs on
        # demand (it executes the success command, which has a cost).
        return StepResult(obs, self._cheap_reward(), done=False, info={})

    def _cheap_reward(self) -> RewardSignal:
        """Per-step reward that avoids re-running the success command — just the
        running step count and current blast radius."""
        modified = self._modified_files()
        expected = list(self.metadata.get("files_expected_to_change", []))
        unexpected = [f for f in modified if f not in expected]
        return RewardSignal(resolution=False, steps=self.steps,
                            files_modified=modified, files_expected=expected,
                            unexpected_files=unexpected)

    def verify(self) -> RewardSignal:
        """Run the objective checks against the current workspace state. Callable
        at any point in an episode (this is what makes the reward RL-usable)."""
        # Grade against the PRISTINE grader, not whatever the agent may have done
        # to the test files — resolution must be un-gameable.
        self._restore_protected()

        sc = self.metadata.get("success_condition", {})
        cmd = sc.get("cmd", "")
        expected_exit = sc.get("exit", 0)

        resolution = False
        detail: dict[str, Any] = {}
        if cmd:
            obs = self.tools.run_command(cmd)
            resolution = (obs.exit_code == expected_exit)
            detail["success_condition"] = {
                "cmd": cmd, "expected_exit": expected_exit,
                "exit_code": obs.exit_code, "output": obs.text,
            }

        regression_passed: Optional[bool] = None
        rc = self.metadata.get("regression_check")
        if rc and rc.get("cmd"):
            robs = self.tools.run_command(rc["cmd"])
            regression_passed = (robs.exit_code == rc.get("exit", 0))
            detail["regression_check"] = {
                "cmd": rc["cmd"], "exit_code": robs.exit_code, "output": robs.text,
            }

        modified = self._modified_files()
        expected = list(self.metadata.get("files_expected_to_change", []))
        unexpected = [f for f in modified if f not in expected]

        return RewardSignal(
            resolution=resolution, steps=self.steps,
            files_modified=modified, files_expected=expected,
            unexpected_files=unexpected, regression_passed=regression_passed,
            detail=detail,
        )

    # ── reproducibility ─────────────────────────────────────────────────────────
    def snapshot(self) -> dict[str, Any]:
        """Capture the full episode state so it can be restored exactly — for
        deterministic rollouts and RL branching."""
        files = {
            str(f.relative_to(self.workspace)): f.read_bytes()
            for f in self._tracked_files()
        }
        return {
            "files": files,
            "steps": self.steps,
            "done": self.done,
            "diagnosis": self.diagnosis,
            "initial_hashes": dict(self._initial_hashes),
        }

    def restore(self, state: dict[str, Any]) -> None:
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        for rel, data in state["files"].items():
            target = self.workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.steps = state["steps"]
        self.done = state["done"]
        self.diagnosis = state["diagnosis"]
        self._initial_hashes = dict(state["initial_hashes"])

    def close(self) -> None:
        """Drop the workspace. The scenario (golden) dir is left untouched."""
        if self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)
