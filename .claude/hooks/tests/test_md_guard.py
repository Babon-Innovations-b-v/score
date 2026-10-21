"""Pin the md_guard PreToolUse decisions by driving the real script via stdin: a new .md is blocked unless the owner
said yes to it (md_allowed.json) or it is private memory.

Run: python3 -m pytest .claude/hooks/tests/
"""

import json
import pathlib
import subprocess
import sys

_GUARD = pathlib.Path(__file__).resolve().parent.parent / "md_guard.py"
_REPO = _GUARD.parents[2]


def _write(path):
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(_REPO / path)}, "cwd": str(_REPO)}
    return subprocess.run([sys.executable, str(_GUARD)], capture_output=True, text=True,
                          input=json.dumps(payload)).returncode


def test_a_new_md_without_a_yes_is_blocked():
    assert _write("docs/never-asked-for.md") == 2


def test_a_new_md_the_owner_said_yes_to_is_allowed():
    entries = json.loads((_GUARD.parent / "md_allowed.json").read_text())
    assert entries and _write(entries[0]["path"]) == 0


def test_private_memory_is_allowed():
    assert _write(".claude/memory/some-note.md") == 0
