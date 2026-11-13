"""Invariant of detached.py: a detached command's every printed line goes to its log, never to the caller, and the
caller gets exactly one result line naming the status, the exit code, the log and the outputs; the exit code is passed
on; a tool's --detach reruns it without the flag. An agent relies on that one line to learn what happened without
reading a log or polling (owner, 2026-10-09).

The one test runs each case as the agent does (a subprocess), through detached.py's command line or through a tool's
own --detach, on a command whose output and exit code the case chose, and checks the same answer for every case: one
line back with the status, exit code, log and outputs, the exit code passed on, and the log holding the command's lines.
The breaks that turn it red (each applied once, seen red, reverted):

- in `run`, `stdout=log` -> `stdout=None` (the command prints to the caller, so more than one line comes back and the
  log is empty): every case red.
- in `result_line`, `"ok" if code == 0 else "failed"` -> `"ok"`: the "fails with exit 3" case red.
- in `relaunch`, `*[word for word in argv if word != FLAG]` -> `*argv[:1]` (the tool reruns without its own
  arguments): the "tool --detach" case red.
"""
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE / "detached.py"


def launch(entry, script, arguments, outputs, folder):
    """Run the case's script detached through its entry; return the finished process and the log it wrote."""
    if entry == "cli":
        log = folder / "run.log"
        done = subprocess.run([sys.executable, str(TOOL), "--log", str(log), "--outputs", ",".join(outputs), "--",
                               sys.executable, "-c", script], capture_output=True, text=True)
        return done, log
    tool = folder / "tool.py"
    tool.write_text(f"import pathlib, sys\nsys.path.insert(0, {str(HERE)!r})\nimport detached\n"
                    f"detached.LOGS = pathlib.Path({str(folder)!r})\n"
                    f"if detached.FLAG in sys.argv:\n    detached.relaunch(sys.argv, 'tool', {outputs!r})\n{script}\n")
    done = subprocess.run([sys.executable, str(tool), *arguments], capture_output=True, text=True)
    [log] = folder.glob("tool-*.log")
    return done, log


CASES = [
    pytest.param("cli", "print('progress one'); print('progress two')", [], ["/a/out.json", "/a/folder"],
                 "ok", 0, "progress one\nprogress two\n", id="prints two lines"),
    pytest.param("cli", "import sys; print('boom', file=sys.stderr); sys.exit(3)", [], [],
                 "failed", 3, "boom\n", id="fails with exit 3"),
    pytest.param("tool", "print('ran with', sys.argv[1:])", ["place", "--detach", "--cloud"], ["/x/page.html"],
                 "ok", 0, "ran with ['place', '--cloud']\n", id="tool --detach"),
]


@pytest.mark.parametrize("entry, script, arguments, outputs, status, code, logged", CASES)
def test_detached_logs_everything_and_says_one_line(entry, script, arguments, outputs, status, code, logged,
                                                    tmp_path):
    done, log = launch(entry, script, arguments, outputs, tmp_path)
    [line] = done.stdout.splitlines()
    assert line.startswith(f"detached: {status} exit={code} ") and done.returncode == code
    assert f"log={log}" in line and line.endswith(f"outputs={','.join(outputs) or '-'}")
    assert log.read_text() == logged
