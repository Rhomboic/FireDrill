"""
tools.py

The environment's ACTION SPACE. Five tools let a policy observe and act on the
broken project inside the workspace; their results come back as Observations.
The environment (gym/environment.py) owns a ToolExecutor and routes Actions to
it — policies never call these directly, they emit Actions through the protocol.

Stdlib only. All paths are confined to the workspace root: a tool can never read
or write outside the sandbox, no matter what the policy asks for.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .protocol import Action, Observation, SUBMIT

# Bytes/chars we are willing to hand back in a single observation, so a policy
# can't blow its context window by catting a huge file or noisy command output.
MAX_OBS_CHARS = 20_000
DEFAULT_CMD_TIMEOUT = 120  # seconds


def _truncate(text: str, limit: int = MAX_OBS_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit]
    return f"{head}\n... [truncated {len(text) - limit} chars]"


class ToolExecutor:
    """Executes Actions against a single workspace directory."""

    def __init__(self, workspace: str | Path, logs_subdir: str = "logs",
                 cmd_timeout: int = DEFAULT_CMD_TIMEOUT):
        self.workspace = Path(workspace).resolve()
        self.logs_subdir = logs_subdir
        self.cmd_timeout = cmd_timeout

    # ── path safety ──────────────────────────────────────────────────────────
    def _resolve(self, rel_path: str) -> Path:
        """Resolve a policy-supplied path inside the workspace, refusing escapes."""
        # Treat the path as relative to the workspace even if it starts with "/".
        candidate = (self.workspace / str(rel_path).lstrip("/")).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise ValueError(f"path escapes workspace: {rel_path!r}")
        return candidate

    # ── the five tools ─────────────────────────────────────────────────────────
    def read_file(self, path: str) -> Observation:
        try:
            target = self._resolve(path)
            if not target.is_file():
                return Observation.error(f"not a file: {path}", source="read_file")
            text = target.read_text(errors="replace")
            return Observation(text=_truncate(text), source="read_file",
                               data={"path": path, "bytes": target.stat().st_size})
        except Exception as e:
            return Observation.error(f"read_file failed: {e}", source="read_file")

    def write_file(self, path: str, content: str) -> Observation:
        try:
            target = self._resolve(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            return Observation(text=f"wrote {len(content)} chars to {path}",
                               source="write_file", data={"path": path})
        except Exception as e:
            return Observation.error(f"write_file failed: {e}", source="write_file")

    def list_directory(self, path: str = ".") -> Observation:
        try:
            target = self._resolve(path)
            if not target.is_dir():
                return Observation.error(f"not a directory: {path}",
                                         source="list_directory")
            entries = []
            for child in sorted(target.iterdir()):
                marker = "/" if child.is_dir() else ""
                entries.append(f"{child.name}{marker}")
            listing = "\n".join(entries) if entries else "(empty)"
            return Observation(text=_truncate(listing), source="list_directory",
                               data={"path": path, "count": len(entries)})
        except Exception as e:
            return Observation.error(f"list_directory failed: {e}",
                                     source="list_directory")

    def read_logs(self, path: str = "") -> Observation:
        """Read a log file, or, if no path given, concatenate everything under
        the conventional logs/ directory — the natural first move on call."""
        try:
            if path:
                return self.read_file(path)
            logs_dir = self._resolve(self.logs_subdir)
            if not logs_dir.is_dir():
                return Observation.error(
                    f"no '{self.logs_subdir}/' directory; pass a path to read_logs",
                    source="read_logs")
            chunks = []
            for log in sorted(logs_dir.rglob("*")):
                if log.is_file():
                    rel = log.relative_to(self.workspace)
                    chunks.append(f"===== {rel} =====\n{log.read_text(errors='replace')}")
            text = "\n\n".join(chunks) if chunks else "(no log files)"
            return Observation(text=_truncate(text), source="read_logs")
        except Exception as e:
            return Observation.error(f"read_logs failed: {e}", source="read_logs")

    def run_command(self, command: str) -> Observation:
        try:
            proc = subprocess.run(
                command, shell=True, cwd=str(self.workspace),
                capture_output=True, text=True, timeout=self.cmd_timeout,
            )
            body = ""
            if proc.stdout:
                body += proc.stdout
            if proc.stderr:
                body += ("\n[stderr]\n" if body else "[stderr]\n") + proc.stderr
            body = body or "(no output)"
            text = f"$ {command}\n[exit {proc.returncode}]\n{_truncate(body)}"
            return Observation(text=text, ok=(proc.returncode == 0),
                               source="run_command", exit_code=proc.returncode,
                               data={"command": command})
        except subprocess.TimeoutExpired:
            return Observation.error(
                f"command timed out after {self.cmd_timeout}s: {command}",
                source="run_command")
        except Exception as e:
            return Observation.error(f"run_command failed: {e}", source="run_command")

    # ── dispatch ────────────────────────────────────────────────────────────────
    def execute(self, action: Action) -> Observation:
        """Route an Action to its tool. `submit` is terminal and handled by the
        environment, not here."""
        if action.tool == SUBMIT:
            raise ValueError("submit is a terminal action handled by the env")
        handler = _DISPATCH.get(action.tool)
        if handler is None:
            return Observation.error(
                f"unknown tool {action.tool!r}; valid tools: {', '.join(TOOL_NAMES)}",
                source=action.tool)
        try:
            return handler(self, **action.args)
        except TypeError as e:
            return Observation.error(f"bad args for {action.tool}: {e}",
                                     source=action.tool)


_DISPATCH = {
    "read_file": ToolExecutor.read_file,
    "write_file": ToolExecutor.write_file,
    "list_directory": ToolExecutor.list_directory,
    "read_logs": ToolExecutor.read_logs,
    "run_command": ToolExecutor.run_command,
}
TOOL_NAMES = list(_DISPATCH.keys())


# ── Tool specs + schema export ──────────────────────────────────────────────
#
# One canonical description of each tool, plus converters to the Anthropic and
# OpenAI tool-use schemas so any LLM policy can advertise the same action space
# without redefining it.

TOOL_SPECS = [
    {
        "name": "read_file",
        "description": "Read a text file in the project. Path is relative to the project root.",
        "properties": {"path": {"type": "string", "description": "File path, e.g. 'src/main.py'"}},
        "required": ["path"],
    },
    {
        "name": "write_file",
        "description": "Overwrite a file with new contents (creates it and parent dirs if needed).",
        "properties": {
            "path": {"type": "string", "description": "File path relative to project root"},
            "content": {"type": "string", "description": "Full new file contents"},
        },
        "required": ["path", "content"],
    },
    {
        "name": "list_directory",
        "description": "List the entries in a directory. Defaults to the project root.",
        "properties": {"path": {"type": "string", "description": "Directory path; defaults to '.'"}},
        "required": [],
    },
    {
        "name": "read_logs",
        "description": "Read the project's logs. With no path, concatenates everything under logs/.",
        "properties": {"path": {"type": "string", "description": "Optional specific log file path"}},
        "required": [],
    },
    {
        "name": "run_command",
        "description": "Run a shell command from the project root and return stdout, stderr, and exit code.",
        "properties": {"command": {"type": "string", "description": "Shell command, e.g. 'pytest -q'"}},
        "required": ["command"],
    },
    {
        "name": SUBMIT,
        "description": "End the episode. Provide a one-sentence root-cause diagnosis of what was broken and how you fixed it.",
        "properties": {"diagnosis": {"type": "string", "description": "One-sentence root-cause diagnosis"}},
        "required": ["diagnosis"],
    },
]


def anthropic_tools() -> list[dict]:
    """Tool definitions in Anthropic Messages API format."""
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": {
                "type": "object",
                "properties": spec["properties"],
                "required": spec["required"],
            },
        }
        for spec in TOOL_SPECS
    ]


def openai_tools() -> list[dict]:
    """Tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": {
                    "type": "object",
                    "properties": spec["properties"],
                    "required": spec["required"],
                },
            },
        }
        for spec in TOOL_SPECS
    ]
