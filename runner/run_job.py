"""
run_job.py — run one (scenario × model) job end to end.

This is the single entrypoint that ties the gym together: it builds the
environment for a scenario, drives it with a model policy, verifies the fix,
judges the diagnosis, scores all four dimensions, and writes the self-describing
results payload — locally and (optionally) to S3.

It is LOCAL-FIRST: no Docker or AWS required.

    python3 runner/run_job.py --scenario 01-payments-service-down --model claude-opus-4-8

The same entrypoint runs inside a scenario container, where SCENARIO, MODEL, and
S3_BUCKET come from the environment (CLI flags override env vars).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

from gym import FireDrillEnv  # noqa: E402
from agent.agent import run_episode, ALL_MODELS  # noqa: E402
from eval.judge import score_diagnosis  # noqa: E402
from eval.eval import score_episode  # noqa: E402

SCENARIOS_DIR = REPO_ROOT / "scenarios"


# ── diffs: show what the agent actually changed ─────────────────────────────

def compute_diffs(golden_dir: Path, workspace: Path, files: list[str]) -> dict[str, str]:
    """Unified diff (golden → workspace) for each modified file, best-effort."""
    diffs: dict[str, str] = {}
    for rel in files:
        try:
            g = golden_dir / rel
            w = workspace / rel
            before = g.read_text().splitlines(keepends=True) if g.exists() else []
            after = w.read_text().splitlines(keepends=True) if w.exists() else []
            diffs[rel] = "".join(difflib.unified_diff(
                before, after, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        except (UnicodeDecodeError, OSError):
            diffs[rel] = "(binary or unreadable file)"
    return diffs


# ── S3 (optional) ───────────────────────────────────────────────────────────

def upload_to_s3(local_path: Path, model: str, scenario: str) -> None:
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        print("  S3_BUCKET not set — skipping S3 upload")
        return
    import boto3
    prefix = os.environ.get("S3_KEY_PREFIX", "runs/")
    key = f"{prefix}{model}/{scenario}.json"
    s3 = boto3.client("s3")
    print(f"  uploading to s3://{bucket}/{key}")
    s3.upload_file(str(local_path), bucket, key)
    _update_manifest(s3, bucket, prefix, model, scenario)


def _update_manifest(s3, bucket: str, prefix: str, model: str, scenario: str) -> None:
    """manifest.json maps each model to the scenarios it has results for."""
    key = f"{prefix}manifest.json"
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(obj["Body"].read())
    except Exception:  # noqa: BLE001 — missing manifest is fine on first write
        data = {}
    scenarios = set(data.get(model, []))
    scenarios.add(scenario)
    data[model] = sorted(scenarios)
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(data),
                  ContentType="application/json")
    print(f"  manifest updated: {model} -> {data[model]}")


# ── the job ─────────────────────────────────────────────────────────────────

def run_job(scenario: str, model: str, *, max_steps: Optional[int] = None,
            workspace: Optional[str] = None, out_dir: str = "results",
            do_judge: bool = True, s3: bool = False,
            agent_client: Any = None, judge_client: Any = None) -> dict:
    """Run one job and return the scored payload. Clients are injectable for tests."""
    scenario_dir = SCENARIOS_DIR / scenario
    if not (scenario_dir / "metadata.json").is_file():
        raise FileNotFoundError(f"no scenario at {scenario_dir}")
    meta = json.loads((scenario_dir / "metadata.json").read_text())

    ws = Path(workspace) if workspace else (REPO_ROOT / out_dir / "_workspaces"
                                            / f"{model}__{scenario}")
    env = FireDrillEnv(scenario_dir, ws, max_steps=max_steps or 30)

    print(f"\n{'='*64}\nFireDrill job: {scenario}  ×  {model}\n{'='*64}")
    episode = run_episode(env, model, client=agent_client)
    print(f"  policy: {episode.stopped_reason} in {episode.steps} steps")
    if episode.error:
        print(f"  policy error: {episode.error}")

    reward = env.verify()
    print(f"  resolution={reward.resolution}  clean_fix={reward.clean_fix}  "
          f"modified={reward.files_modified}")

    diffs = compute_diffs(env.golden, env.workspace, reward.files_modified)

    if do_judge:
        verdict = score_diagnosis(episode.diagnosis, meta.get("correct_diagnosis", ""),
                                  meta.get("description", ""), client=judge_client)
    else:
        verdict = {"score": 0, "rationale": "judge disabled", "model": None}
    print(f"  diagnosis score: {verdict['score']}/5 — {verdict['rationale']}")

    payload = score_episode(meta, reward, episode, verdict, diffs=diffs)

    # write locally
    out_path = REPO_ROOT / out_dir / model / f"{scenario}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    try:
        shown = out_path.relative_to(REPO_ROOT)
    except ValueError:
        shown = out_path
    print(f"  wrote {shown}")
    c = payload["cost"]
    print(f"  quality={payload['scores']}")
    print(f"  cost=${c['cost_usd']:.4f} ({c['total_tokens']} tok, score {c['cost_score']}) "
          f"| steps={payload['efficiency']['steps']}")

    if s3 or os.environ.get("S3_BUCKET"):
        upload_to_s3(out_path, model, scenario)

    return payload


def main() -> int:
    load_dotenv()
    p = argparse.ArgumentParser(description="Run one FireDrill (scenario × model) job.")
    p.add_argument("--scenario", default=os.environ.get("SCENARIO"))
    p.add_argument("--model", default=os.environ.get("MODEL"))
    p.add_argument("--max-steps", type=int,
                   default=int(os.environ.get("MAX_STEPS", "30")))
    p.add_argument("--workspace", default=os.environ.get("WORKSPACE"))
    p.add_argument("--out", default="results")
    p.add_argument("--no-judge", action="store_true", help="skip the LLM diagnosis judge")
    p.add_argument("--s3", action="store_true", help="force S3 upload (also auto if S3_BUCKET set)")
    args = p.parse_args()

    if not args.scenario or not args.model:
        p.error("both --scenario and --model are required (or set SCENARIO/MODEL)")
    if args.model not in ALL_MODELS:
        p.error(f"unknown model {args.model!r}; choose from {ALL_MODELS}")

    payload = run_job(args.scenario, args.model, max_steps=args.max_steps,
                      workspace=args.workspace, out_dir=args.out,
                      do_judge=not args.no_judge, s3=args.s3)
    # exit non-zero if the incident was not resolved, so callers/CI can branch.
    return 0 if payload["scores"]["resolution"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
