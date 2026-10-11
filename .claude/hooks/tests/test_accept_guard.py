"""Pin the accept_guard PreToolUse decisions by driving the real script via stdin.

An agent cannot run the owner's accept, reject or spend, call them from Python, or write the store's accepts,
rejects, waivers, spend yeses or clearances by any file or shell route or into an artifact's database; running the
stages (the runner's own accepts and clearances), reading them, building a review page and running the tests stay
allowed; garbage fails open.

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
                    "python score/review/__main__.py accept a@b c",
                    ".venv/bin/python -m score.review reject assembly@hangar abc123 --reason x"):
        code, err = _run(_bash(command))
        assert code == 2, command
        assert "only the owner accepts or rejects" in err


def test_calling_accept_from_python_is_blocked():
    for command in ("python -c 'from score import review; review.accept(store, \"a@b\", \"o\", \"me\")'",
                    ".venv/bin/python - <<EOF\nstore.write_accept('a@b', {})\nEOF"):
        assert _run(_bash(command))[0] == 2, command


def test_writing_the_store_accepts_by_shell_is_blocked():
    for command in ("echo '{}' > ~/.farm-factory-props/store/objects/accepts/a@b/1.json",
                    "cp x.json $HOME/.farm-factory-props/store/objects/spend-yes/a@b/k.json",
                    "rm -r store/objects/accepts/assembly@hangar",
                    "mkdir -p objects/waivers/x && touch objects/waivers/x/y.json",
                    "cp c.json store/objects/clearances/render@hub/k1/1.json",
                    "echo '{}' > store/objects/rejects/a@b/1.json"):
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
                    "make check",
                    ".venv/bin/python -m score.stages run hangar hdoor"):
        assert _run(_bash(command))[0] == 0, command
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "score/review/__init__.py"}}
    assert _run(edit)[0] == 0


def test_the_reviews_ways_round_the_guard_are_blocked():
    """Fault (review of step 0, 2026-10-11): each of these got through (exit 0)."""
    for command in (".venv/bin/python -c 'from score.review import accept; accept(store, \"a@b\", \"o\", \"me\")'",
                    ".venv/bin/python -c 'import score.review as r; r.accept(store, \"a@b\", \"o\", \"me\")'",
                    ".venv/bin/python -c 'from score.store import Store; "
                    "Store.default().write_once(\"acc\"+\"epts/a@b/1.json\", {})'",
                    "python -m score.review \"accept\" a@b o",
                    "cd score/review && python __main__.py accept a@b o",
                    "script -qc '.venv/bin/python -m score.review page a@b' /dev/null",
                    "cat > /tmp/do_it.py <<EOF\nfrom score import review\nreview.accept(store, 'a@b', 'o', 'me')\nEOF"):
        assert _run(_bash(command))[0] == 2, command
    script = {"tool_name": "Write", "tool_input": {"file_path": "/tmp/do_it.py",
                                                   "content": "from score import review\nreview.accept(s, 'a', 'o')\n"}}
    assert _run(script)[0] == 2


def test_taking_the_agent_mark_off_a_process_is_blocked():
    for command in ("env -u CLAUDECODE .venv/bin/python /tmp/x.py", "unset CLAUDECODE; python3 /tmp/x.py",
                    "CLAUDECODE= .venv/bin/python /tmp/x.py", "env -i PATH=$PATH .venv/bin/python /tmp/x.py"):
        assert _run(_bash(command))[0] == 2, command
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.py",
                                                "new_string": "os.environ.pop('CLAUDECODE')"}}
    assert _run(edit)[0] == 2


def test_read_only_commands_and_unrelated_writes_stay_allowed():
    """Fault (review of step 0): any `>` or the words accept, waive or spend in an artifact write were blocked."""
    for command in ('grep -rn "accepts/" score 2>/dev/null',
                    "ls ~/.farm-factory-props/store/objects/accepts/ 2>&1 | head",
                    "git log > /tmp/x; echo spend-yes/",
                    "grep -c accept score/review/__init__.py > /tmp/count.txt"):
        assert _run(_bash(command))[0] == 0, command
    notes = {"tool_name": "Artifact", "tool_input": {"action": "write_db", "collection": "notes", "doc_id": "n1",
                                                     "data": {"text": "acceptance criteria, spend and waivers"}}}
    assert _run(notes)[0] == 0
    framework = {"tool_name": "Edit", "tool_input": {"file_path": "/repo/score/review/review_test.py",
                                                     "new_string": "review.accept(store, node, output, 'me')"}}
    assert _run(framework)[0] == 0


def test_a_batch_writing_accepts_into_an_artifact_database_is_blocked():
    batch = {"tool_name": "Artifact", "tool_input": {"action": "write_db", "db_op": "batch", "writes": [
        {"op": "set", "collection": "notes", "doc_id": "n1", "data": {}},
        {"op": "set", "collection": "store/x/accepts", "doc_id": "a@b", "data": {}}]}}
    assert _run(batch)[0] == 2


def test_garbage_fails_open():
    assert _run("not json")[0] == 0
    assert _run({"tool_name": "Bash"})[0] == 0
