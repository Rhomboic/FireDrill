#!/usr/bin/env python3
"""Held-out shutdown check for the containerised service — PROTECTED GRADER.

This is the production trap. A container that *serves* is necessary but not
sufficient: an orchestrator (Kubernetes, ECS, Compose) stops a container by
sending SIGTERM to PID 1 and only SIGKILLs after a grace period. If the app
never receives that SIGTERM it can't drain connections or flush state — every
deploy/rollback becomes a hard kill.

There is no Docker daemon here, so — exactly like verify_serves.py — this
reproduces what `docker build && docker run && docker stop` would do, daemon-free:

  build  -> stage into a clean dir ONLY the files the COPY lines would add
  run    -> set the env the ENV lines declare, then start the CMD in that dir,
            as its own process group (PID 1 in a container *is* the CMD process)
  stop   -> wait for the server to bind, send SIGTERM to the CMD process, and
            require it to exit cleanly (code 0) within a short grace window

The catch is the CMD *form*:

  exec form   CMD ["python3", "app.py"]   -> python IS the CMD process; it gets
                                             the SIGTERM, runs its handler, exits 0.
  shell form  CMD python3 app.py          -> the CMD process is /bin/sh -c, and
                                             python runs as its child. SIGTERM hits
                                             the shell, which does NOT forward it;
                                             python keeps running. No clean exit.

Exit 0 iff the CMD process shuts the app down gracefully on SIGTERM. Editing the
app to paper over the Dockerfile doesn't help: app.py is restored from golden
before this runs, and it already installs a correct SIGTERM handler.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCKERFILE = ROOT / "Dockerfile"

GRACE_SECONDS = 5  # orchestrator-style grace period before a SIGKILL would follow


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


def cmd_argv_and_shell(cmd):
    """Return (argv, used_shell_form).

    Exec form runs the program directly, so the program is the CMD process and
    receives SIGTERM.

    Shell form runs via `/bin/sh -c <cmd>`, exactly as Docker does — the app
    runs as a *child* of the shell, and the shell does not forward SIGTERM, so
    the app never shuts down gracefully. We prepend a `:` no-op so the shell has
    more than one command to run and therefore cannot tail-exec-optimize the
    single command into replacing itself (some host shells like dash/bash do
    that optimization, which would mask the very pitfall this models). This
    makes the shell-form failure mode deterministic across hosts and faithful to
    a container started with shell-form CMD under a non-execing /bin/sh."""
    cmd = cmd.strip()
    if cmd.startswith("["):
        return json.loads(cmd), False  # exec form
    return ["/bin/sh", "-c", f": ; {cmd}"], True  # shell form (shell stays PID 1)


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

    argv, used_shell = cmd_argv_and_shell(cmd)

    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp)
        for src in copies:
            s = ROOT / src
            dst = image / Path(src).name
            if s.is_dir():
                shutil.copytree(s, dst)
            elif s.exists():
                shutil.copy2(s, dst)

        run_env = dict(os.environ)
        run_env.update(env)
        # start_new_session=True puts the CMD process in its own process group,
        # mirroring "PID 1 in the container". We signal the CMD process itself —
        # exactly the one Docker delivers SIGTERM to.
        proc = subprocess.Popen(
            argv, cwd=image, env=run_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        # Capture the group id up front: with shell-form CMD the shell may exit
        # on SIGTERM while leaking the still-running app as an orphan; we use the
        # group id to guarantee we reap the whole tree in the finally block (so a
        # leaked app can't keep holding the port and poison the next run).
        try:
            pgid = os.getpgid(proc.pid)
        except Exception:
            pgid = None
        url = f"http://127.0.0.1:{expose}/health"
        bound = False
        try:
            for _ in range(40):  # up to ~10s for the server to bind
                if proc.poll() is not None:
                    out = proc.stdout.read().decode(errors="replace")[:600]
                    print(f"FAIL: container exited before serving:\n{out.strip()}")
                    return 1
                try:
                    with urllib.request.urlopen(url, timeout=1) as r:
                        if r.status == 200:
                            bound = True
                            break
                except Exception:
                    time.sleep(0.25)
            if not bound:
                print(f"FAIL: {url} never answered 200; cannot test shutdown")
                return 1

            # Deliver SIGTERM to the CMD process, the way an orchestrator stops
            # the container, then require a prompt clean exit.
            proc.send_signal(signal.SIGTERM)
            try:
                code = proc.wait(timeout=GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                print(
                    "FAIL: app did not exit within "
                    f"{GRACE_SECONDS}s of SIGTERM — no graceful shutdown. "
                    "The CMD process swallowed the signal (shell-form CMD does "
                    "not forward SIGTERM to the app); use exec-form CMD."
                )
                return 1
            if code != 0:
                print(f"FAIL: app exited on SIGTERM with non-zero code {code}")
                return 1
            print(f"OK: app shut down gracefully on SIGTERM (exit 0) within {GRACE_SECONDS}s")
            return 0
        finally:
            # Always SIGKILL the whole process group — even if `proc` (e.g. the
            # shell) has already exited, the app it spawned may still be alive
            # and holding the port. Reaping by group id leaves nothing behind.
            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    pass
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
