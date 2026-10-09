#!/usr/bin/env python3
"""PreToolUse guard: a new markdown file needs the owner's go-ahead (ADR-0003).

Reads the Claude Code PreToolUse payload on stdin and blocks creating a ``.md`` that does not exist yet anywhere under
the repo, by ``Write`` or by a Bash redirect, ``tee``, ``touch`` or ``cp``. Allowed: editing an existing ``.md``,
anything outside the repo (``/tmp``, a job scratch dir: where generated pages belong), ``mv``/``git mv`` (a rename
leaves the count unchanged; ``cp`` adds a file), and a per-directory ``CLAUDE.md`` overlay (the standing exception: it
is the mechanism that loads a directory's rules, so a code directory without one is a gap, not a document).

Why: every markdown file here is living, read by someone and kept current. A summary file dropped at a session's end
has nobody keeping it current and the next session reads it as truth, so each new file is the owner's decision.

FAILURE POLICY: fail-open. Any parse error, unknown shape or unrelated call exits 0 (allow). Exit 2 + stderr is the
only block path (the harness feeds stderr back to the model as the block reason).
"""

import json
import os
import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_SHELL_TARGETS = (
    re.compile(r">>?\s*(?P<path>[^\s|;&<>()]+\.md)\b", re.IGNORECASE),
    re.compile(r"\btee\s+(?:-a\s+)?(?P<path>[^\s|;&<>()-][^\s|;&<>()]*\.md)\b", re.IGNORECASE),
    re.compile(r"\btouch\s+(?P<path>[^\s|;&<>()]+\.md)\b", re.IGNORECASE),
    re.compile(r"\bcp\s+[^;|&]*?\s(?P<path>[^\s|;&<>()]+\.md)\b", re.IGNORECASE),
)
# A `cd` and a `NAME=value` earlier in the same command change where a relative path lands.
_CD = re.compile(r"(?:^|[;&|\n(])\s*cd\s+(?P<dir>[^\s|;&<>()]+)")
_ASSIGN = re.compile(r"(?:^|[;&|\n(])\s*(?P<name>[A-Za-z_]\w*)=(?P<value>[^\s|;&<>()]+)")

_MESSAGE = (
    "Blocked: creating a new markdown file needs the owner's go-ahead (CLAUDE.md, ADR-0003).\n"
    "  would create: {path}\n"
    "Every .md in this repo is living and earns its place, so the count stays minimal.\n"
    "Instead: put it in an existing file, add a section to docs/bible.md, or post it as a\n"
    "comment on the issue it belongs to. ADRs are covered too: offer one in a line and\n"
    "write it after the yes. Generated pages render outside the repo (/tmp or the job\n"
    "scratch dir), which this guard allows.\n"
    "If the file genuinely has to exist, ask the owner in this session first."
)


def _blocked(raw: str, base: pathlib.Path) -> pathlib.Path | None:
    """The offending path when `raw` names a new .md inside the repo, else None. A relative path resolves against
    `base`, the directory the command writes from (a command that cd's to scratch first writes outside the repo)."""
    if not raw:
        return None
    candidate = base / raw.strip().strip("'\"")  # an absolute path replaces base
    try:
        resolved = candidate.resolve()
        resolved.relative_to(_REPO_ROOT)
    except (ValueError, OSError):
        return None  # outside the repo, or unresolvable: not ours to police
    if resolved.exists() or resolved.name == "CLAUDE.md":
        return None
    return resolved


def _expanded(raw: str, known: dict[str, str]) -> str | None:
    """`raw` with its shell variables filled in (those set earlier in the command first, then the environment), or
    None when one is still unknown: the failure policy says allow."""
    text = raw.strip().strip("'\"")
    for name, value in known.items():
        text = re.sub(r"\$(?:\{%s\}|%s(?!\w))" % (name, name), lambda _match: value, text)
    text = os.path.expanduser(os.path.expandvars(text))
    return None if "$" in text else text


def _shell_candidates(command: str, base: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    """Each markdown path a shell command could create, with the directory it lands in. Walks the command in order,
    so a `cd` or a variable counts only for the writes after it; after a `cd` somewhere unknowable, relative paths are
    left unjudged."""
    steps = [(match.start(), "cd", "", match.group("dir")) for match in _CD.finditer(command)]
    steps += [(match.start(), "set", match.group("name"), match.group("value")) for match in _ASSIGN.finditer(command)]
    steps += [(match.start("path"), "path", "", match.group("path"))
              for pattern in _SHELL_TARGETS for match in pattern.finditer(command)]
    known: dict[str, str] = {}
    here: pathlib.Path | None = base
    found: list[tuple[str, pathlib.Path]] = []
    for _, kind, name, text in sorted(steps, key=lambda step: step[0]):
        filled = _expanded(text, known)
        if kind == "set":
            if filled is not None:
                known[name] = filled
        elif kind == "cd":
            here = None if filled is None or filled == "-" or here is None else here / filled
        elif filled is not None and (here is not None or filled.startswith("/")):
            found.append((filled, here or base))
    return found


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    base = pathlib.Path(payload.get("cwd") or _REPO_ROOT)
    candidates: list[tuple[str, pathlib.Path]] = []
    if tool == "Write" and str(tool_input.get("file_path", "")).lower().endswith(".md"):
        candidates = [(str(tool_input.get("file_path", "")), base)]
    elif tool == "Bash":
        candidates = _shell_candidates(str(tool_input.get("command", "")), base)
    for raw, where in candidates:
        offender = _blocked(raw, where)
        if offender is not None:
            print(_MESSAGE.format(path=offender.relative_to(_REPO_ROOT)), file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
