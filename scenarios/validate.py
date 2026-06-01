"""
validate.py — the scenario validation gate.

Every FireDrill scenario must satisfy three properties before it is fit for use:

  1. BROKEN     : on the pristine project, the success condition fails.
  2. FIXABLE    : applying the scenario's reference fix makes it pass.
  3. CLEAN      : the reference fix touches only the files_expected_to_change
                  (so blast radius is well-defined and the answer key is honest).

This harness drives the real FireDrillEnv to check all three — the same env an
agent will face — so a scenario can never silently become a no-op or unsolvable.

Usage:
    python3 scenarios/validate.py                       # validate every scenario
    python3 scenarios/validate.py 01-payments-service-down   # just one
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path
from gym import FireDrillEnv  # noqa: E402

SCENARIOS_DIR = Path(__file__).resolve().parent


def validate_scenario(scenario_dir: Path) -> list[str]:
    """Return a list of failure messages; empty means the scenario passed."""
    failures: list[str] = []
    fix = None
    with tempfile.TemporaryDirectory() as tmp:
        env = FireDrillEnv(scenario_dir, Path(tmp) / "workspace")
        fix = env.metadata.get("reference_fix", {})
        fix_cmd = fix.get("cmd")

        # 1. BROKEN — pristine project must fail the success condition.
        env.reset()
        pre = env.verify()
        if pre.resolution:
            failures.append("not BROKEN: success condition already passes on the pristine project")

        if not fix_cmd:
            failures.append("no reference_fix.cmd in metadata; cannot check FIXABLE/CLEAN")
            return failures

        # 2 + 3. FIXABLE + CLEAN — apply the reference fix, re-verify.
        env.reset()
        fix_obs = env.tools.run_command(fix_cmd)
        if not fix_obs.ok:
            failures.append(f"reference_fix.cmd failed to run: {fix_obs.text.strip()[:200]}")
        post = env.verify()
        if not post.resolution:
            failures.append("not FIXABLE: success condition still fails after the reference fix")
        if post.unexpected_files:
            failures.append(
                "not CLEAN: reference fix touched files outside files_expected_to_change: "
                f"{post.unexpected_files}"
            )
        env.close()
    return failures


def discover() -> list[Path]:
    return sorted(
        p for p in SCENARIOS_DIR.iterdir()
        if p.is_dir() and (p / "metadata.json").is_file()
    )


def main() -> int:
    if len(sys.argv) > 1:
        targets = [SCENARIOS_DIR / sys.argv[1]]
    else:
        targets = discover()

    if not targets:
        print("no scenarios found")
        return 1

    all_ok = True
    for scenario_dir in targets:
        if not (scenario_dir / "metadata.json").is_file():
            print(f"✗ {scenario_dir.name}: missing metadata.json")
            all_ok = False
            continue
        failures = validate_scenario(scenario_dir)
        if failures:
            all_ok = False
            print(f"✗ {scenario_dir.name}")
            for f in failures:
                print(f"    - {f}")
        else:
            print(f"✓ {scenario_dir.name}  (broken → fixable → clean)")

    print()
    print("VALIDATION PASSED" if all_ok else "VALIDATION FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
