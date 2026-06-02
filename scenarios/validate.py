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

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path
from gym import FireDrillEnv  # noqa: E402

SCENARIOS_DIR = Path(__file__).resolve().parent
SKIP = "SKIP"  # sentinel: scenario's runtime isn't available here (e.g. playwright)


def validate_scenario(scenario_dir: Path) -> list[str]:
    """Return a list of failure messages; empty means the scenario passed.
    A single SKIP entry means the verifier's runtime isn't available locally."""
    failures: list[str] = []
    fix = None
    with tempfile.TemporaryDirectory() as tmp:
        env = FireDrillEnv(scenario_dir, Path(tmp) / "workspace")

        # Skip if the success-condition binary isn't installed here (UI scenarios
        # need playwright; validated inside the firedrill-ui image instead).
        cmd = env.metadata.get("success_condition", {}).get("cmd", "")
        binary = cmd.split()[0] if cmd else ""
        if binary and shutil.which(binary) is None:
            return [f"{SKIP}: needs '{binary}'"]

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
        # The reference fix must also pass the held-out regression (if defined),
        # otherwise the scenario punishes even a correct fix.
        if env.metadata.get("regression_check") and post.regression_passed is not True:
            failures.append("reference fix does NOT pass regression_check (scenario is unsound)")

        # 4. TRAP (optional) — a naive_fix must PASS the success condition but
        # FAIL the regression, proving the trap actually discriminates.
        naive = env.metadata.get("naive_fix", {})
        if naive.get("cmd"):
            if not env.metadata.get("regression_check"):
                failures.append("naive_fix defined but no regression_check to trip")
            else:
                env.reset()
                nobs = env.tools.run_command(naive["cmd"])
                if not nobs.ok:
                    failures.append(f"naive_fix.cmd failed to run: {nobs.text.strip()[:200]}")
                npost = env.verify()
                if not npost.resolution:
                    failures.append("TRAP broken: naive_fix should PASS the success condition")
                if npost.regression_passed is not False:
                    failures.append("TRAP broken: naive_fix should FAIL the regression_check")
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
        if failures and failures[0].startswith(SKIP):
            print(f"⊘ {scenario_dir.name}  (skipped — {failures[0].split(': ', 1)[1]})")
        elif failures:
            all_ok = False
            print(f"✗ {scenario_dir.name}")
            for f in failures:
                print(f"    - {f}")
        else:
            meta = json.loads((scenario_dir / "metadata.json").read_text())
            extra = " + trap" if meta.get("naive_fix", {}).get("cmd") else ""
            print(f"✓ {scenario_dir.name}  (broken → fixable → clean{extra})")

    print()
    print("VALIDATION PASSED" if all_ok else "VALIDATION FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
