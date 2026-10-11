"""Pin the accept_guard PreToolUse decisions by driving the real script via stdin.

An agent cannot run the owner's accept or spend, call them from Python, or write the store's accepts, waivers or
spend yeses by any file or shell route or into an artifact's database; reading them, building a review page and
running the tests stay allowed; garbage fails open.

Run: python3 -m pytest .claude/hooks/tests/
"""

import json
import pathlib
import subprocess
import sys

_GUARD = pathlib.Path(__file__).resolve().parent.parent / "accept_guard.py"


def _run(payload):
    result = subprocess.run([sys.executable, str(_GUARD)], capture_output=True, text=True,
                            input=payload if isinstance(payload, str) else json.dumps(payload))
    return result.returncode, result.stderr


def _bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_the_owners_commands_are_blocked():
    for command in (".venv/bin/python -m score.review accept assembly@hangar abc123",
                    "cd wt && python3 -m score.review spend render@hub k1 4.5",
                    "python score/review/__main__.py accept a@b c"):
        code, err = _run(_bash(command))
        assert code == 2, command
        assert "only the owner accepts" in err


def test_calling_accept_from_python_is_blocked():
    for command in ("python -c 'from score import review; review.accept(store, \"a@b\", \"o\", \"me\")'",
                    ".venv/bin/python - <<EOF\nstore.write_accept('a@b', {})\nEOF"):
        assert _run(_bash(command))[0] == 2, command


def test_writing_the_store_accepts_by_shell_is_blocked():
    for command in ("echo '{}' > ~/.farm-factory-props/store/objects/accepts/a@b/1.json",
                    "cp x.json $HOME/.farm-factory-props/store/objects/spend-yes/a@b/k.json",
                    "rm -r store/objects/accepts/assembly@hangar",
                    "mkdir -p objects/waivers/x && touch objects/waivers/x/y.json"):
        assert _run(_bash(command))[0] == 2, command


def test_writing_the_store_accepts_by_file_tools_is_blocked():
    for tool in ("Write", "Edit"):
        payload = {"tool_name": tool, "tool_input": {"file_path": "/home/x/.farm-factory-props/store/objects/"
                                                                   "accepts/assembly@hangar/1.json"}}
        assert _run(payload)[0] == 2, tool


def test_writing_accepts_into_an_artifact_database_is_blocked():
    payload = {"tool_name": "Artifact", "tool_input": {"action": "write_db", "collection": "accepts",
                                                       "doc_id": "assembly@hangar", "data": {"output": "o"}}}
    assert _run(payload)[0] == 2
    reading = {"tool_name": "Artifact", "tool_input": {"action": "read_db", "collection": "accepts"}}
    assert _run(reading)[0] == 0


def test_reading_pages_and_tests_stay_allowed():
    for command in (".venv/bin/python -m score.review page assembly@hangar",
                    "ls ~/.farm-factory-props/store/objects/accepts/",
                    "cat ~/.farm-factory-props/store/objects/accepts/a@b/1.json",
                    "grep -n 'review.accept(' score/review/review_test.py",
                    ".venv/bin/python score/review/review_test.py",
                    "make check"):
        assert _run(_bash(command))[0] == 0, command
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "score/review/__init__.py"}}
    assert _run(edit)[0] == 0


def test_garbage_fails_open():
    assert _run("not json")[0] == 0
    assert _run({"tool_name": "Bash"})[0] == 0
