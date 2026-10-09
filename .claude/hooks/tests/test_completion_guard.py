"""Pin the completion_guard Stop decisions by driving the real script via stdin with a transcript made here.

Runs the script exactly as the harness does: JSON on stdin, exit 2 = block, exit 0 = allow. Covers: a claim that a
place the session worked on is done is blocked when the place has no passing gate (here: no stage at all, so every
requirement is unknown); a sentence saying the place is not complete passes; a claim about a place the session never
touched passes; a session that claims nothing passes; and garbage fails open.

Run: python3 -m pytest .claude/hooks/tests/
"""

import json
import pathlib
import subprocess
import sys

_GUARD = pathlib.Path(__file__).resolve().parent.parent / "completion_guard.py"
_PLACE = "zz_test_place"


def _transcript(folder, last_text, touched_place=_PLACE):
    """A session that edited one place's inventory and ended with this text."""
    entries = [
        {"type": "user", "message": {"role": "user", "content": "finish the place"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": f"/x/data/inventory/{touched_place}.json"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": last_text}]}},
    ]
    path = folder / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n")
    return path


def _run(payload, env=None):
    result = subprocess.run([sys.executable, str(_GUARD)], input=payload if isinstance(payload, str)
                            else json.dumps(payload), capture_output=True, text=True, env=env)
    return result.returncode, result.stderr


def _with_place(tmp_path, monkeypatch):
    """Make the test place known to the guard (a kit file of its name) and its stage folder empty."""
    kit = pathlib.Path(__file__).resolve().parents[3] / "data/kit" / f"{_PLACE}.json"
    kit.write_text("{}")
    monkeypatch.setenv("PROPS_WORK", str(tmp_path / "work"))
    return kit


def test_a_done_claim_without_a_passing_gate_is_blocked(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        code, said = _run({"transcript_path": str(_transcript(tmp_path, f"The {_PLACE} is complete now."))})
    finally:
        kit.unlink()
    assert code == 2
    assert _PLACE in said and "unknown" in said


def test_a_sub_agents_done_claim_is_judged_on_its_own_transcript(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    session = tmp_path / "session"
    session.mkdir()
    try:
        code, said = _run({"transcript_path": str(_transcript(session, "Nothing claimed here.")),
                           "agent_transcript_path": str(_transcript(tmp_path, f"The {_PLACE} is done."))})
    finally:
        kit.unlink()
    assert code == 2
    assert _PLACE in said


def test_the_payloads_last_message_counts_when_the_transcript_lags(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        code, said = _run({"transcript_path": str(_transcript(tmp_path, "Reading the inventory now.")),
                           "last_assistant_message": f"The {_PLACE} is done."})
    finally:
        kit.unlink()
    assert code == 2
    assert _PLACE in said


def test_a_quoted_command_is_not_a_claim(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        code, _ = _run({"transcript_path": str(_transcript(
            tmp_path, f"Left: export it, then run `complete.py done {_PLACE}`."))})
    finally:
        kit.unlink()
    assert code == 0


def test_saying_it_is_not_complete_passes(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        code, _ = _run({"transcript_path": str(_transcript(tmp_path, f"The {_PLACE} is not complete: rows remain."))})
    finally:
        kit.unlink()
    assert code == 0


def test_a_claim_about_an_untouched_place_passes(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        path = _transcript(tmp_path, f"The {_PLACE} is done.", touched_place="nowhere_else")
        code, _ = _run({"transcript_path": str(path)})
    finally:
        kit.unlink()
    assert code == 0


def test_no_claim_passes(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        code, _ = _run({"transcript_path": str(_transcript(tmp_path, "I moved two crates."))})
    finally:
        kit.unlink()
    assert code == 0


def test_garbage_fails_open():
    assert _run("not json")[0] == 0
    assert _run({"transcript_path": "/nowhere/at/all.jsonl"})[0] == 0
