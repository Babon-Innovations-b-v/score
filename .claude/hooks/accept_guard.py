#!/usr/bin/env python3
"""PreToolUse guard: only the owner accepts a stage's output, waives a gate or says yes to a spend.

Reads the Claude Code PreToolUse payload on stdin and blocks an agent from:

1. Running the owner's commands: ``score.review accept`` or ``score.review spend`` (``python -m score.review ...``
   or ``score/review/__main__.py``), or Python that calls ``review.accept(``, ``review.spend(``,
   ``write_accept(`` or ``write_spend_yes(``.
2. Writing the store's accepts, waivers or spend yeses (``accepts/``, ``waivers/``, ``spend-yes/``): by Write, Edit
   or NotebookEdit on such a path, or a shell command that names one and writes (a redirect, ``tee``, ``cp``,
   ``mv``, ``ln``, ``rm``, ``touch``, ``install``, ``rsync``, ``dd``, ``sed -i``, ``chmod`` or Python).
3. Writing accepts, waivers or spend yeses into an artifact's database (``Artifact`` with ``write_db``).

Why (the layered framework's design, 2026-10-11): agent verdicts stood in for the owner's (a place declared complete
that he had not seen), and the newest take replaced the accepted one by itself. The accept is his alone; on one
machine under YOLO this guard is a barrier, not a lock, and every accept in the store names who gave it and when.

FAILURE POLICY: fail-open. Any parse error, unknown shape or unrelated call exits 0 (allow). Exit 2 + stderr is the
only block path (the harness feeds stderr back to the model as the block reason).
"""

import json
import re
import sys

_OWNER_COMMAND = re.compile(r"(score[./]review(?:/__main__\.py)?)\s+(accept|spend)\b")
_PYTHON = re.compile(r"\b(python3?|uv\s+run)\b|/python\b")
_OWNER_CALL = re.compile(r"\b(review\.(accept|spend)|write_accept|write_spend_yes)\s*\(")
_OWNER_AREA = re.compile(r"(^|[/\s'\"=])(accepts|waivers|spend-yes)/")
_WRITES = re.compile(r">|\b(tee|cp|mv|ln|rm|touch|install|rsync|dd|chmod)\b|\bsed\s+-i|\bpython3?\b|/python\b")
_OWNER_WORDS = re.compile(r"accept|waive|spend", re.IGNORECASE)

_MESSAGE = (
    "Blocked: only the owner accepts a stage's output, waives a gate or says yes to a spend.\n"
    "  {what}\n"
    "Build the review page instead (.venv/bin/python -m score.review page <node>) and ask the owner to accept it\n"
    "from his own terminal. An agent's verdict never stands in for his (docs/bible.md, the layered framework)."
)


def _bash_offence(command):
    """Why a shell command is the owner's alone, or None."""
    if _OWNER_COMMAND.search(command):
        return "runs the owner's accept or spend command"
    if _PYTHON.search(command) and _OWNER_CALL.search(command):
        return "calls the owner's accept or spend from Python"
    if _OWNER_AREA.search(command) and _WRITES.search(command):
        return "writes the store's accepts, waivers or spend yeses"
    return None


def _file_offence(path):
    if _OWNER_AREA.search(path):
        return f"writes {path}"
    return None


def _artifact_offence(tool_input):
    if tool_input.get("action") != "write_db":
        return None
    named = json.dumps([tool_input.get(name) for name in ("collection", "doc_id", "data", "writes")])
    return "writes accepts, waivers or spend yeses into an artifact's database" if _OWNER_WORDS.search(named) else None


def _offence(payload):
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool == "Bash":
        return _bash_offence(str(tool_input.get("command", "")))
    if tool in ("Write", "Edit", "NotebookEdit"):
        return _file_offence(str(tool_input.get("file_path") or tool_input.get("notebook_path") or ""))
    if tool == "Artifact":
        return _artifact_offence(tool_input)
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        offence = _offence(payload)
    except Exception:
        return 0
    if offence:
        print(_MESSAGE.format(what=offence), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
