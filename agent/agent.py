"""
agent.py

An LLM POLICY that drives a FireDrillEnv. This is just one consumer of the gym:
it speaks only the gym/protocol.py types (Actions in, Observations out) and never
reaches around the environment. Swap it for a scripted policy or an RL loop and
the env is unchanged.

Supports Anthropic (Claude) and OpenAI models behind one registry. The loop is
the same for both providers: show the model the task + tool results, take its
tool calls, turn each into an Action, step the env, feed the Observation back,
and stop when the model calls `submit` or the env ends the episode (max_steps).

The policy produces a transcript, token/latency stats, and the diagnosis. It does
NOT score the run — the eval layer does that by calling env.verify().
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from gym import FireDrillEnv, Action, SUBMIT, anthropic_tools, openai_tools

# ── Model registry ──────────────────────────────────────────────────────────
# Keys are the names we use everywhere (filenames, dashboard, ECS overrides);
# values are the upstream API ids. gpt-5.5's exact snapshot id can be overridden
# at runtime with MODEL_API_ID without touching code.

ANTHROPIC_MODELS = {
    "claude-opus-4-8": "claude-opus-4-8",
    "claude-haiku-4-5": "claude-haiku-4-5-20251001",
}

OPENAI_MODELS = {
    "gpt-5.5": "gpt-5.5",
    "gpt-4.1-mini": "gpt-4.1-mini",
}

ALL_MODELS = list(ANTHROPIC_MODELS) + list(OPENAI_MODELS)


def resolve_api_id(model: str) -> str:
    """Upstream API id for a registry key, with a MODEL_API_ID env override."""
    override = os.environ.get("MODEL_API_ID")
    if override:
        return override
    if model in ANTHROPIC_MODELS:
        return ANTHROPIC_MODELS[model]
    if model in OPENAI_MODELS:
        return OPENAI_MODELS[model]
    raise ValueError(f"unknown model {model!r}; choose from {ALL_MODELS}")


SYSTEM_PROMPT = (
    "You are an expert on-call software engineer responding to a production incident. "
    "You operate inside the project directory using the provided tools. Work methodically: "
    "read the logs and relevant files, form a hypothesis, then make the SMALLEST change that "
    "resolves the incident. Verify your fix by running the relevant command. Do not make "
    "unrelated changes or refactors. When the incident is resolved, call `submit` with a "
    "one-sentence root-cause diagnosis describing what was wrong and how you fixed it. "
    "Be efficient — minimize the number of tool calls."
)

MAX_OBS_IN_HISTORY = 8000  # keep tool-result text bounded in the running history


# ── Episode result ──────────────────────────────────────────────────────────

@dataclass
class EpisodeResult:
    model: str
    diagnosis: Optional[str]
    steps: int                         # tool calls that acted on the workspace
    stopped_reason: str                # "submit" | "max_steps" | "gave_up" | "error"
    transcript: list[dict] = field(default_factory=list)
    # Token usage, normalised across providers into four billable buckets so the
    # eval layer can price it. "input_tokens" is UNCACHED input only; cached
    # reads/writes are tracked separately because they bill at different rates.
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: int = 0
    error: Optional[str] = None

    @property
    def usage(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "diagnosis": self.diagnosis,
            "steps": self.steps,
            "stopped_reason": self.stopped_reason,
            "transcript": self.transcript,
            **self.usage,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


# ── Shared helpers ──────────────────────────────────────────────────────────

def _short(args: dict, limit: int = 300) -> dict:
    """Trim long arg values (e.g. full file contents) for the transcript."""
    out = {}
    for k, v in args.items():
        s = v if isinstance(v, str) else json.dumps(v)
        out[k] = s if len(s) <= limit else s[:limit] + f"... [+{len(s) - limit} chars]"
    return out


def _apply_action(env: FireDrillEnv, name: str, args: dict,
                  transcript: list[dict]) -> tuple[str, bool]:
    """Turn a model tool call into an env Action, step, and record it.
    Returns (observation_text_for_model, episode_done)."""
    if env.done:
        return "the episode has already ended", True
    action = Action(tool=name, args=args or {})
    result = env.step(action)
    obs_text = result.observation.text
    entry = {
        "tool": name,
        "args": _short(args or {}),
        "ok": result.observation.ok,
    }
    if name == SUBMIT:
        entry["observation"] = "episode submitted"
        entry["diagnosis"] = env.diagnosis
    else:
        entry["observation"] = obs_text
        entry["unexpected_files"] = result.reward.unexpected_files
    transcript.append(entry)
    return obs_text, result.done


def _retry(fn, *, tries: int = 5):
    """Exponential backoff for transient API errors (rate limits / overload)."""
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — provider SDKs raise varied types
            msg = str(e).lower()
            transient = any(s in msg for s in
                            ("429", "529", "overloaded", "rate limit", "connection",
                             "timeout", "503", "500"))
            if attempt < tries - 1 and transient:
                wait = 2 ** attempt + random.uniform(0, 1)
                print(f"   [retry in {wait:.1f}s: {type(e).__name__}]", flush=True)
                time.sleep(wait)
            else:
                raise


# ── Anthropic driver ────────────────────────────────────────────────────────

def _run_claude(env: FireDrillEnv, api_id: str, client, max_steps: int) -> EpisodeResult:
    tools = anthropic_tools()
    first_obs = env.reset()
    messages = [{"role": "user", "content": first_obs.text}]
    result = EpisodeResult(model=api_id, diagnosis=None, steps=0, stopped_reason="gave_up")
    start = time.time()

    # Safety bound on turns: every acting step consumes one env step, plus slack
    # for thinking turns that produce no tool call.
    for _turn in range(max_steps * 3 + 5):
        resp = _retry(lambda: client.messages.create(
            model=api_id, max_tokens=4096,
            system=[{"type": "text", "text": SYSTEM_PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            tools=tools, messages=messages,
        ))
        # Anthropic reports cache reads/writes as SEPARATE fields (not included
        # in input_tokens), so we just add each bucket.
        u = resp.usage
        result.input_tokens += u.input_tokens
        result.output_tokens += u.output_tokens
        result.cache_read_tokens += getattr(u, "cache_read_input_tokens", 0) or 0
        result.cache_write_tokens += getattr(u, "cache_creation_input_tokens", 0) or 0

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        messages.append({"role": "assistant", "content": resp.content})

        if not tool_uses:
            # No tool call — nudge once toward acting/submitting, then give up.
            messages.append({"role": "user", "content":
                             "Use a tool to investigate or fix the issue, or call "
                             "submit with your diagnosis when the incident is resolved."})
            if resp.stop_reason == "end_turn":
                continue
            continue

        tool_results = []
        done = False
        for tu in tool_uses:
            if done:  # episode already ended earlier in this batch
                tool_results.append({"type": "tool_result", "tool_use_id": tu.id,
                                     "content": "the episode has already ended"})
                continue
            obs_text, done = _apply_action(env, tu.name, dict(tu.input), result.transcript)
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id,
                                 "content": obs_text[:MAX_OBS_IN_HISTORY]})
        messages.append({"role": "user", "content": tool_results})

        if done:
            result.stopped_reason = "submit" if env.diagnosis is not None else "max_steps"
            break

    result.steps = env.steps
    result.diagnosis = env.diagnosis
    result.latency_ms = int((time.time() - start) * 1000)
    return result


# ── OpenAI driver ───────────────────────────────────────────────────────────

def _run_openai(env: FireDrillEnv, api_id: str, client, max_steps: int) -> EpisodeResult:
    tools = openai_tools()
    first_obs = env.reset()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": first_obs.text},
    ]
    result = EpisodeResult(model=api_id, diagnosis=None, steps=0, stopped_reason="gave_up")
    start = time.time()

    for _turn in range(max_steps * 3 + 5):
        resp = _retry(lambda: client.chat.completions.create(
            model=api_id, messages=messages, tools=tools,
        ))
        if resp.usage:
            # OpenAI nests cached tokens INSIDE prompt_tokens, so subtract them
            # out into the cache-read bucket to match the Anthropic accounting.
            details = getattr(resp.usage, "prompt_tokens_details", None)
            cached = getattr(details, "cached_tokens", 0) or 0
            result.input_tokens += resp.usage.prompt_tokens - cached
            result.cache_read_tokens += cached
            result.output_tokens += resp.usage.completion_tokens

        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            messages.append({"role": "user", "content":
                             "Use a tool to investigate or fix the issue, or call "
                             "submit with your diagnosis when the incident is resolved."})
            continue

        done = False
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if done:
                content = "the episode has already ended"
            else:
                content, done = _apply_action(env, tc.function.name, args, result.transcript)
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": content[:MAX_OBS_IN_HISTORY]})

        if done:
            result.stopped_reason = "submit" if env.diagnosis is not None else "max_steps"
            break

    result.steps = env.steps
    result.diagnosis = env.diagnosis
    result.latency_ms = int((time.time() - start) * 1000)
    return result


# ── Public entry point ──────────────────────────────────────────────────────

def run_episode(env: FireDrillEnv, model: str, max_steps: Optional[int] = None,
                client: Any = None) -> EpisodeResult:
    """Drive `env` to completion with `model`. `client` may be injected for tests;
    otherwise the appropriate SDK client is constructed from env vars."""
    if model not in ALL_MODELS:
        raise ValueError(f"unknown model {model!r}; choose from {ALL_MODELS}")
    api_id = resolve_api_id(model)
    steps = max_steps if max_steps is not None else env.max_steps

    try:
        if model in ANTHROPIC_MODELS:
            if client is None:
                import anthropic
                client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                             timeout=600.0)
            res = _run_claude(env, api_id, client, steps)
        else:
            if client is None:
                from openai import OpenAI
                client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=600.0)
            res = _run_openai(env, api_id, client, steps)
    except Exception as e:  # noqa: BLE001
        res = EpisodeResult(model=api_id, diagnosis=env.diagnosis, steps=env.steps,
                            stopped_reason="error", error=f"{type(e).__name__}: {e}")
    res.model = model  # report by registry key, not raw api id
    return res
