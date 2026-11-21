"""Read-only tools for the paper agent: `read` and `bash`.

Design notes
- `read` mirrors the (path, offset, limit) shape that models know from coding
  agents, but always prefixes line numbers so line-number citations are fair.
- `bash` is a command allowlist, not a security boundary. The real boundary is
  the container (corpus mounted read-only, scrubbed env for the subprocess).
"""
from __future__ import annotations

import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .draft import Draft

MAX_OUTPUT_CHARS = 8000
READ_DEFAULT_LIMIT = 200
READ_MAX_LIMIT = 2000
BASH_TIMEOUT_S = 10

# No sort/uniq/cut/tr: `sort -o` and `uniq in out` can write files.
ALLOWED_COMMANDS = {"ls", "grep", "egrep", "fgrep", "find", "head", "tail", "wc", "nl", "cat", "sed"}
FIND_FORBIDDEN = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
SED_SCRIPT = re.compile(r"^\d+(,(\d+|\$))?p$")

# Always part of the tool list (a fixed list keeps the prefix cache valid); the program
# refuses it until revision mode starts. See Draft.edit.
EDIT_DRAFT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "edit_draft",
        "description": (
            "Replace one unique substring of your previous answer (the draft). Only usable in revision mode, "
            "after a <verification> message. `old` must be an exact, unique substring (max 300 chars)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "old": {"type": "string", "description": "Exact text to replace; must occur exactly once."},
                "new": {"type": "string", "description": "Replacement text."},
            },
            "required": ["old", "new"],
        },
    },
}


@dataclass
class ToolResult:
    text: str
    truncated: bool = False
    is_error: bool = False
    duration_ms: int = 0


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    note = f"\n[output truncated: {len(text)} chars total, showing first {limit}]"
    return text[:limit] + note, True


class Tools:
    ALL = ("read", "bash", "edit_draft")

    def __init__(self, root: str | Path, enabled: tuple[str, ...] | None = None):
        self.root = Path(root).resolve()
        self.draft = Draft()
        # Which tools are offered. Fixed for the whole run (prefix cache); calls to others are refused.
        self.enabled = set(self.ALL if enabled is None else enabled)

    # ------------------------------------------------------------ schemas
    def schemas(self) -> list[dict]:
        return [s for s in self._base_schemas() + [EDIT_DRAFT_SCHEMA] if s["function"]["name"] in self.enabled]

    def _base_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "read",
                    "description": (
                        "Read a text file from the paper corpus. Every returned line is prefixed "
                        "with its line number. Reads up to `limit` lines starting at `offset` "
                        f"(1-indexed, default 1; default limit {READ_DEFAULT_LIMIT})."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to the corpus root."},
                            "offset": {"type": "integer", "description": "First line to read (1-indexed)."},
                            "limit": {"type": "integer", "description": "Maximum number of lines."},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": (
                        "Run a READ-ONLY shell command in the corpus root. Allowed commands: "
                        "ls, grep, egrep, fgrep, find, head, tail, wc, nl, cat, sed -n 'A,Bp'. "
                        "Pipes (|) are allowed; redirection, command substitution and absolute "
                        "paths are not. Use `grep -n` to search with line numbers."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                },
            },
        ]

    # ------------------------------------------------------------ dispatch
    def call(self, name: str, args: dict) -> ToolResult:
        start = time.monotonic()
        try:
            if name not in self.enabled:
                res = ToolResult(f"error: tool {name!r} is not available in this run", is_error=True)
            elif name == "read":
                res = self.read(**args)
            elif name == "bash":
                res = self.bash(**args)
            elif name == "edit_draft":
                ok, msg = self.draft.edit(**args)
                res = ToolResult(msg, is_error=not ok)
            else:
                res = ToolResult(f"error: unknown tool {name!r}", is_error=True)
        except TypeError as e:  # wrong / missing arguments
            res = ToolResult(f"error: bad arguments for {name}: {e}", is_error=True)
        res.duration_ms = int((time.monotonic() - start) * 1000)
        return res

    # ------------------------------------------------------------ read
    def _resolve(self, path: str) -> Path | None:
        p = (self.root / path).resolve()
        return p if p == self.root or p.is_relative_to(self.root) else None

    def read(self, path: str, offset: int = 1, limit: int = READ_DEFAULT_LIMIT) -> ToolResult:
        p = self._resolve(path)
        if p is None:
            return ToolResult("error: path is outside the corpus", is_error=True)
        if not p.is_file():
            return ToolResult(f"error: no such file: {path}", is_error=True)
        offset = max(1, int(offset))
        limit = min(max(1, int(limit)), READ_MAX_LIMIT)
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        chunk = lines[offset - 1 : offset - 1 + limit]
        if not chunk:
            return ToolResult(f"[{path} has {len(lines)} lines; offset {offset} is past the end]")
        # cut on a line boundary so the continuation hint is always exact
        shown: list[str] = []
        used = 0
        for i, line in enumerate(chunk):
            s = f"{offset + i:>6}\t{line}"
            if shown and used + len(s) + 1 > MAX_OUTPUT_CHARS:
                break
            shown.append(s)
            used += len(s) + 1
        last = offset + len(shown) - 1
        body = "\n".join(shown)
        if last < len(lines):
            body += f"\n[{path}: showing lines {offset}-{last} of {len(lines)}; use offset={last + 1} to continue]"
        text, truncated = _truncate(body)
        return ToolResult(text, truncated=truncated or len(shown) < len(chunk))

    # ------------------------------------------------------------ bash
    def _validate(self, command: str) -> str | None:
        """Return an error message if the command is not allowed, else None."""
        if "\n" in command or "`" in command or "$(" in command:
            return "newlines, backticks and $( ) are not allowed"
        try:
            lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError as e:
            return f"cannot parse command: {e}"
        if not tokens:
            return "empty command"
        segments: list[list[str]] = [[]]
        for tok in tokens:
            if tok == "|":
                segments.append([])
            elif set(tok) <= set("();<>|&"):
                return f"operator {tok!r} is not allowed (only | is)"
            else:
                segments[-1].append(tok)
        for argv in segments:
            if not argv:
                return "empty pipeline stage"
            if argv[0] not in ALLOWED_COMMANDS:
                return f"command {argv[0]!r} is not allowed; allowed: {', '.join(sorted(ALLOWED_COMMANDS))}"
            err = self._validate_args(argv)
            if err:
                return err
        return None

    def _validate_args(self, argv: list[str]) -> str | None:
        cmd, args = argv[0], argv[1:]
        for a in args:
            if a.startswith(("/", "~")) or ".." in a.split("/"):
                return f"path escapes the corpus: {a!r}"
        if cmd == "find" and FIND_FORBIDDEN & set(args):
            return "find with -exec/-delete/-fprint is not allowed"
        if cmd == "sed":
            flags = [a for a in args if a.startswith("-")]
            rest = [a for a in args if not a.startswith("-")]
            if flags != ["-n"] or not rest or not SED_SCRIPT.match(rest[0]):
                return "sed is only allowed as: sed -n 'A,Bp' file"
        return None

    def bash(self, command: str) -> ToolResult:
        err = self._validate(command)
        if err:
            return ToolResult(f"error: {err}", is_error=True)
        try:
            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=self.root,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8"},  # no API key leaks in
                capture_output=True,
                text=True,
                errors="replace",
                timeout=BASH_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(f"error: command timed out after {BASH_TIMEOUT_S}s", is_error=True)
        out = proc.stdout + (proc.stderr if proc.stderr else "")
        if proc.returncode != 0 and not out:
            out = f"[exit code {proc.returncode}, no output]"
        elif proc.returncode != 0:
            out += f"\n[exit code {proc.returncode}]"
        text, truncated = _truncate(out if out else "[no output]")
        # grep exits 1 for "no match": informative, not a tool failure
        return ToolResult(text, truncated=truncated, is_error=proc.returncode not in (0, 1))
