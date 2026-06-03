#!/usr/bin/env python3
"""Held-out version check for the containerised service — PROTECTED GRADER.

A container that answers /health is necessary but not sufficient. The service
also exposes /version, whose body is read at request time from the packaged
templates/version.json asset. An image that COPYs the code but forgets that
asset directory still boots and still answers /health 200 — the gap only shows
up when /version is hit, where the missing asset yields a 500.

There is no Docker daemon here, so — exactly like verify_serves.py — this
reproduces what `docker build && docker run && curl /version` would do,
daemon-free:

  build  -> stage into a clean dir ONLY the files/dirs the COPY lines would add
  run    -> set the env the ENV lines declare, then exec the CMD in that dir
  probe  -> curl http://127.0.0.1:<EXPOSE>/version and require 200 with the body
            assembled from the asset (service + version fields)

Exit 0 iff /version answers 200 with the expected payload — which it only does
when the Dockerfile COPYs the templates/ asset dir in addition to the code.
Editing the app or the asset to paper over a Dockerfile bug doesn't help: the
app sources and the golden asset are restored before this runs.
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
EXPECTED = {"service": "status-service", "version": "1.4.2"}


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
        # build: only the files/dirs the COPY lines add are present in the image
        for src in copies:
            s = ROOT / src.rstrip("/")
            dst = image / Path(src.rstrip("/")).name
            if s.is_dir():
                shutil.copytree(s, dst)
            elif s.exists():
                shutil.copy2(s, dst)

        run_env = dict(os.environ)
        run_env.update(env)
        proc = subprocess.Popen(
            cmd_to_argv(cmd), cwd=image, env=run_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        url = f"http://127.0.0.1:{expose}/version"
        try:
            for _ in range(40):  # up to ~10s for the server to bind
                if proc.poll() is not None:
                    out = proc.stdout.read().decode(errors="replace")[:600]
                    print(f"FAIL: container exited before serving:\n{out.strip()}")
                    return 1
                try:
                    with urllib.request.urlopen(url, timeout=1) as r:
                        status = r.status
                        body = r.read()
                except urllib.error.HTTPError as e:
                    # Server is up but /version errored (e.g. asset not COPYed).
                    out = e.read().decode(errors="replace")[:200]
                    print(
                        f"FAIL: {url} -> {e.code} (the templates/ asset was not "
                        f"copied into the image): {out.strip()}"
                    )
                    return 1
                except Exception:
                    time.sleep(0.25)
                    continue
                if status != 200:
                    print(f"FAIL: {url} -> {status}")
                    return 1
                try:
                    got = json.loads(body)
                except ValueError:
                    print(f"FAIL: {url} returned non-JSON body: {body[:200]!r}")
                    return 1
                if got != EXPECTED:
                    print(f"FAIL: {url} body {got!r} != expected {EXPECTED!r}")
                    return 1
                print(f"OK: {url} -> 200 {got!r}")
                return 0
            print(f"FAIL: {url} never answered")
            return 1
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
