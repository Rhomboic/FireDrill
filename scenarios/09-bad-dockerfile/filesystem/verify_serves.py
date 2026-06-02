#!/usr/bin/env python3
"""Objective check for the containerised service — PROTECTED GRADER, do not edit.

There is no Docker daemon inside the gym, so instead of `docker build && docker
run && curl`, this reproduces exactly what those would do, from the Dockerfile:

  build  -> stage into a clean dir ONLY the files the COPY lines would add
  run    -> set the env the ENV lines declare, then exec the CMD in that dir
  probe  -> curl http://127.0.0.1:<EXPOSE>/health

Exit 0 iff the service answers 200 — which it only does when the Dockerfile
copies every file the app needs AND provides the PORT the app reads. A Dockerfile
that forgets a COPY makes the import fail; one that forgets the port env makes
the app crash on startup. Editing the app to paper over a Dockerfile bug doesn't
help: the app sources are restored from golden before this runs.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCKERFILE = ROOT / "Dockerfile"


def parse_dockerfile(text):
    copies, env, expose, cmd = [], {}, None, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        verb = line.split(None, 1)[0].upper()
        if verb == "COPY":
            parts = line.split()[1:]
            if len(parts) >= 2:
                *srcs, _dst = parts
                copies.extend(srcs)
        elif verb == "ENV":
            rest = line[3:].strip()
            m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*[=\s]\s*(.+)", rest)
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        elif verb == "EXPOSE":
            nums = re.findall(r"\d+", line)
            if nums:
                expose = int(nums[0])
        elif verb == "CMD":
            cmd = line[3:].strip()
    return copies, env, expose, cmd


def cmd_to_argv(cmd):
    cmd = cmd.strip()
    if cmd.startswith("["):
        return json.loads(cmd)  # exec form
    return cmd.split()  # shell form (good enough for our CMDs)


def main():
    if not DOCKERFILE.exists():
        print("FAIL: no Dockerfile")
        return 1
    copies, env, expose, cmd = parse_dockerfile(DOCKERFILE.read_text())
    if not cmd:
        print("FAIL: Dockerfile has no CMD")
        return 1
    if not expose:
        print("FAIL: Dockerfile EXPOSEs no port")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp)
        # build: only files the COPY lines add are present in the image
        for src in copies:
            s = ROOT / src
            dst = image / Path(src).name
            if s.is_dir():
                shutil.copytree(s, dst)
            elif s.exists():
                shutil.copy2(s, dst)
            # a COPY of a non-existent path would fail the real build too, but
            # our scenario only ever omits a COPY, never adds a bogus one.

        run_env = dict(os.environ)
        run_env.update(env)
        proc = subprocess.Popen(
            cmd_to_argv(cmd), cwd=image, env=run_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        url = f"http://127.0.0.1:{expose}/health"
        try:
            for _ in range(40):  # up to ~10s for the server to bind
                if proc.poll() is not None:
                    out = proc.stdout.read().decode(errors="replace")[:600]
                    print(f"FAIL: container exited before serving:\n{out.strip()}")
                    return 1
                try:
                    with urllib.request.urlopen(url, timeout=1) as r:
                        if r.status == 200:
                            print(f"OK: {url} -> 200")
                            return 0
                except Exception:
                    time.sleep(0.25)
            print(f"FAIL: {url} never answered 200")
            return 1
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
