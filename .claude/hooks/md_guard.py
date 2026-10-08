#!/usr/bin/env python3
"""PreToolUse guard: a new markdown file needs the owner's go-ahead (ADR-0003).

Reads the Claude Code PreToolUse hook payload on stdin (``{tool_name, tool_input,
...}``) and blocks the creation of a markdown file that does not exist yet, anywhere
under the repo. Editing an existing ``.md`` is untouched, and so is anything written
outside the repo (``/tmp``, a job scratch dir), which is where generated pages belong.

Two creation routes are covered:

1. ``Write`` with a ``file_path`` ending in ``.md``.
2. ``Bash`` shell creation: a redirect, ``tee``, ``touch``, and ``cp`` with a markdown
   destination.

A move is not a creation: ``mv`` and ``git mv`` rename a file that already exists and
leave the count unchanged, so they are allowed. ``cp`` still counts, because it adds a
file.

Per-directory ``CLAUDE.md`` overlays are the one standing exception. An overlay is the
mechanism that loads a directory's rules, so a new code directory without one is a gap
rather than a document, and asking for each is friction with no reader on the other end.

Why: every markdown file in this repo is living, read by someone and kept current. A
session that ends by dropping a summary file breaks that, because nothing keeps the file
current and the next session reads it as truth. So the count stays minimal and each new
file is a decision the owner makes, not a side effect of a session.

FAILURE POLICY: fail-open. Any parse error, unknown shape or unrelated call exits 0
(allow). Exit 2 + stderr is the only block path (the harness feeds stderr back to the
model as the block reason).
"""

import json
import os
import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Shell forms that can bring a new file into existence.
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
    """Return the offending path when `raw` names a new .md inside the repo.

    A relative path is resolved against `base`, the directory the command stands in when
    it writes, and not against this repository's root: a command that changes into a
    scratch directory before writing a markdown file writes outside the repo.
    """
    if not raw:
        return None
    candidate = pathlib.Path(raw.strip().strip("'\""))
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(_REPO_ROOT)
    except (ValueError, OSError):
        return None  # outside the repo, or unresolvable: not ours to police
    if resolved.exists():
        return None  # editing an existing file is free
    if resolved.name == "CLAUDE.md":
        return None  # per-directory overlay: standing exception, see module docstring
    return resolved


def _expanded(raw: str, known: dict[str, str]) -> str | None:
    """`raw` with its shell variables filled in, or None when one cannot be known here.

    Variables set earlier in the same command come first, then the environment. A path
    that still holds a `$` after both is unknowable, and the failure policy says allow.
    """
    text = raw.strip().strip("'\"")
    for name, value in known.items():
        text = re.sub(r"\$(?:\{%s\}|%s(?!\w))" % (name, name), lambda _match: value, text)
    text = os.path.expanduser(os.path.expandvars(text))
    return None if "$" in text else text


def _shell_candidates(command: str, base: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    """Each markdown path a shell command could create, with the directory it lands in.

    Walks the command in order, so a `cd` or a variable only counts for the writes after
    it. After a `cd` to somewhere unknowable, relative paths are left unjudged.
    """
    steps: list[tuple[int, str, tuple[str, str]]] = []
    steps.extend((match.start(), "cd", ("", match.group("dir"))) for match in _CD.finditer(command))
    steps.extend((match.start(), "set", (match.group("name"), match.group("value")))
                 for match in _ASSIGN.finditer(command))
    for pattern in _SHELL_TARGETS:
        steps.extend((match.start("path"), "path", ("", match.group("path")))
                     for match in pattern.finditer(command))
    steps.sort(key=lambda step: step[0])
    known: dict[str, str] = {}
    here: pathlib.Path | None = base
    found: list[tuple[str, pathlib.Path]] = []
    for _, kind, (name, text) in steps:
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

    if tool == "Write":
        path = tool_input.get("file_path", "")
        if str(path).lower().endswith(".md"):
            candidates.append((str(path), base))
    elif tool == "Bash":
        candidates = _shell_candidates(str(tool_input.get("command", "")), base)

    for raw, where in candidates:
        offender = _blocked(raw, where)
        if offender is not None:
            rel = offender.relative_to(_REPO_ROOT)
            print(_MESSAGE.format(path=rel), file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
