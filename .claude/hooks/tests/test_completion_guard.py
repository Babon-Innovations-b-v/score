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
    """Make the test place known to the guard (a places file naming it) and its stage folder empty."""
    kit = tmp_path / "within.json"
    kit.write_text(json.dumps({"shells": {_PLACE: {}}}))
    monkeypatch.setenv("SCORE_GUARD_WITHIN", str(kit))
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


def test_the_harness_runs_the_guard_under_the_projects_python_and_it_refuses_a_false_claim(tmp_path, monkeypatch):
    """The guard imports score.stages, which needs pxr: under the system python3 it crashed on every stop and so
    blocked nothing (2026-10-18). The settings run it with the project's .venv python; under that interpreter a false
    done claim is refused, with no import error."""
    repo = pathlib.Path(__file__).resolve().parents[3]
    settings = json.loads((repo / ".claude/settings.json").read_text())
    commands = [hook["command"] for groups in settings["hooks"].values() for group in groups
                for hook in group.get("hooks", []) if "completion_guard.py" in hook.get("command", "")]
    assert commands and all(command.startswith('"${CLAUDE_PROJECT_DIR:-$PWD}/.venv/bin/python"') for command in commands)
    python = repo / ".venv/bin/python" if (repo / ".venv/bin/python").exists() else pathlib.Path(sys.executable)
    kit = _with_place(tmp_path, monkeypatch)
    try:
        result = subprocess.run([str(python), str(_GUARD)], input=json.dumps(
            {"transcript_path": str(_transcript(tmp_path, f"The {_PLACE} is complete now."))}),
            capture_output=True, text=True)
    finally:
        kit.unlink()
    assert "ModuleNotFoundError" not in result.stderr
    assert result.returncode == 2 and _PLACE in result.stderr


def test_saying_no_place_is_complete_passes(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        code, _ = _run({"transcript_path": str(_transcript(tmp_path, f"No place is complete, {_PLACE} included."))})
    finally:
        kit.unlink()
    assert code == 0


def test_a_place_only_named_in_an_agents_prompt_was_not_worked_on(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    entries = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Agent", "input": {"prompt": f"read data/inventory/{_PLACE}.json"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": f"The {_PLACE} is done."}]}},
    ]
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n")
    try:
        code, _ = _run({"transcript_path": str(path)})
    finally:
        kit.unlink()
    assert code == 0


def test_something_else_done_that_names_the_place_passes(tmp_path, monkeypatch):
    kit = _with_place(tmp_path, monkeypatch)
    try:
        path = _transcript(tmp_path, f"The whole film is done too: it ends at the {_PLACE}.")
        code, _ = _run({"transcript_path": str(path)})
    finally:
        kit.unlink()
    assert code == 0  # the film is done, not the place (owner, 2026-10-21)


def test_no_scene_known_is_no_claim(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPS_WORK", str(tmp_path / "work"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("guard", _GUARD)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.touched([], []) == set()  # an empty scene list matched every sentence before (owner, 2026-10-21)
