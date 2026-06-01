"""
protocol.py

The policy-agnostic interface for a FireDrill environment. These are the only
types a policy needs to understand in order to drive the gym — it never imports
the agent, and the agent never reaches around the env. Anything that can produce
an `Action` from an `Observation` is a valid policy: our LLM agent, a scripted
test policy, a human at a REPL, or an RL training loop.

Nothing here depends on a model SDK. The gym is stdlib-only by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Action space ────────────────────────────────────────────────────────────
#
# An Action is a single tool call. Five tools operate on the workspace
# (read_file / write_file / list_directory / read_logs / run_command); one
# control action (`submit`) ends the episode and carries the agent's
# root-cause diagnosis. The set of legal tools lives in gym/tools.py.

SUBMIT = "submit"  # terminal action; args: {"diagnosis": str}


@dataclass
class Action:
    """One step the policy takes: a tool name plus its arguments."""
    tool: str
    args: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.args, dict):
            raise TypeError(f"Action.args must be a dict, got {type(self.args)!r}")


# ── Observation space ───────────────────────────────────────────────────────
#
# What the policy sees back. `text` is the human/LLM-readable rendering (file
# contents, a directory listing, command stdout/stderr, etc.); the structured
# fields let a programmatic policy branch without parsing text.

@dataclass
class Observation:
    text: str
    ok: bool = True                      # did the action succeed (vs. error)?
    source: str = ""                     # which tool produced this observation
    exit_code: Optional[int] = None      # set for run_command observations
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def error(cls, message: str, source: str = "") -> "Observation":
        return cls(text=message, ok=False, source=source)


# ── Reward ──────────────────────────────────────────────────────────────────
#
# The objective signal the environment can compute at ANY point via verify().
# It is deliberately NOT a single scalar: a gym caller (eval harness or RL loop)
# chooses how to weight the dimensions. Diagnosis quality is intentionally
# absent here — it requires an LLM judge and the agent's explanation, so the
# eval layer adds it on top of this objective core.

@dataclass
class RewardSignal:
    resolution: bool                          # success_condition passes now?
    steps: int                                # actions taken so far (efficiency)
    files_modified: list[str] = field(default_factory=list)
    files_expected: list[str] = field(default_factory=list)
    unexpected_files: list[str] = field(default_factory=list)  # blast radius
    regression_passed: Optional[bool] = None  # held-out check; None if undefined
    detail: dict[str, Any] = field(default_factory=dict)       # raw cmd output etc.

    @property
    def clean_fix(self) -> bool:
        """Resolved AND nothing outside the expected files was touched AND no
        regression — i.e. precise, zero-blast-radius success."""
        return (
            self.resolution
            and not self.unexpected_files
            and self.regression_passed in (None, True)
        )


# ── Step result ─────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    observation: Observation
    reward: RewardSignal
    done: bool
    info: dict[str, Any] = field(default_factory=dict)
