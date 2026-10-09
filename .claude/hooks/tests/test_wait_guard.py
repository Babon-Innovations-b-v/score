"""Pin the wait_guard PreToolUse decisions by driving the real script via stdin.

Runs the script exactly as the harness does: JSON on stdin, exit 2 = block, exit 0 = allow. Covers a long sleep after
another command, poll loops (while, until, for), foreground cloud Blender runs, what stays allowed (short sleeps, a
Python's time.sleep, reading the cloud tools' files, a dry run, anything in the background),
and fail-open on garbage.

Run: python3 -m pytest .claude/hooks/tests/
"""

import json
import pathlib
import subprocess
import sys

_GUARD = pathlib.Path(__file__).resolve().parent.parent / "wait_guard.py"


def _run(payload):
    result = subprocess.run([sys.executable, str(_GUARD)], capture_output=True, text=True,
                            input=payload if isinstance(payload, str) else json.dumps(payload))
    return result.returncode, result.stderr


def _bash(command, background=False):
    return {"tool_name": "Bash", "tool_input": {"command": command, "run_in_background": background}}


def test_long_sleep_after_another_command_is_blocked():
    code, err = _run(_bash("cd /tmp && sleep 300 && cat out.json"))
    assert code == 2
    assert "sleep of 300 s" in err and "run_in_background" in err


def test_sleep_in_minutes_counts_as_seconds():
    assert _run(_bash("make env; sleep 2m"))[0] == 2


def test_while_poll_loop_is_blocked():
    code, err = _run(_bash("while ! test -f done.json; do sleep 30; done; cat done.json"))
    assert code == 2
    assert "while loop" in err


def test_until_poll_loop_with_short_sleep_is_blocked():
    assert _run(_bash("until scw instance server list | grep -q stopped; do sleep 5; done"))[0] == 2


def test_for_loop_sleeping_long_rounds_is_blocked():
    assert _run(_bash("for i in $(seq 60); do kubectl get jobs; sleep 60; done"))[0] == 2


def test_foreground_cloud_blender_runs_are_blocked():
    for command in ("python tools/props/cloud/blender_cloud.py job.json --who me",
                    "cd wt && ~/.farm-factory-props/env/bin/python tools/props/cloud/blender_cloud.py j.json --who me > log",
                    ".venv/bin/python tools/usd/settle.py stage.usda --cloud",
                    ".venv/bin/python tools/review/page.py hub --run r --out o --cloud"):
        code, err = _run(_bash(command))
        assert code == 2, command
        assert "--detach" in err


def test_background_calls_pass():
    assert _run(_bash("while true; do sleep 30; done", background=True))[0] == 0
    assert _run(_bash("python tools/props/cloud/blender_cloud.py job.json --who me --detach", background=True))[0] == 0


def test_ordinary_commands_pass():
    for command in ("sleep 2; ls", "cd x && sleep 30 && ls", "for i in 1 2 3; do curl -s x && break; sleep 2; done",
                    "python -c 'import time\nwhile True: time.sleep(5)'", "git commit -m 'sleep 600'",
                    "python tools/props/cloud/blender_cloud.py job.json --who me --dry-run",
                    "python tools/review/page.py hub --run r --out o --cloud --no-render", "make tests"):
        assert _run(_bash(command))[0] == 0, command


def test_leading_long_sleep_is_blocked():
    assert _run(_bash("sleep 300; tail -n 20 run.log"))[0] == 2


def test_reading_the_cloud_tools_is_not_a_run():
    for command in ("sed -n 1,60p tools/props/cloud/blender_cloud.py; grep -n add_argument tools/props/cloud/blender_cloud.py",
                    "grep -n detach tools/props/cloud/blender_cloud*.py | head -40", "cat tools/usd/settle.py | grep cloud",
                    "git diff tools/review/page.py --stat"):
        assert _run(_bash(command))[0] == 0, command


def test_other_tools_and_garbage_fail_open():
    assert _run({"tool_name": "Read", "tool_input": {"file_path": "x"}})[0] == 0
    assert _run("not json")[0] == 0
