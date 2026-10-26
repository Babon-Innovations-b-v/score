"""Invariant of detached.py: a detached command's every printed line goes to its log, never to the caller, and the
caller gets exactly one result line naming the status, the exit code, the log and the outputs; the exit code is passed
on; a tool's --detach reruns it without the flag. An agent relies on that one line to learn what happened without
reading a log or polling (owner, 2026-10-09).

Each test runs detached.py as the agent does (a subprocess) on a command whose output and exit code the test chose.
The break that turns each red (applied once, seen red, reverted):

- test_the_commands_lines_go_to_the_log_and_one_ok_line_comes_back: in `run`, `stdout=log` -> `stdout=None` (the
  command prints to the caller, so more than one line comes back and the log is empty).
- test_a_failing_command_says_failed_and_passes_its_exit_code_on: in `result_line`, `"ok" if code == 0 else "failed"`
  -> `"ok"`.
- test_a_tools_detach_reruns_it_without_the_flag: in `relaunch`, `*[word for word in argv if word != FLAG]` ->
  `*argv[:1]` (the tool reruns without its own arguments).
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE / "detached.py"


def detached(arguments):
    return subprocess.run([sys.executable, str(TOOL), *arguments], capture_output=True, text=True)


def test_the_commands_lines_go_to_the_log_and_one_ok_line_comes_back(tmp_path):
    log = tmp_path / "run.log"
    done = detached(["--log", str(log), "--outputs", "/a/out.json,/a/folder", "--", sys.executable, "-c",
                     "print('progress one'); print('progress two')"])
    [line] = done.stdout.splitlines()
    assert line.startswith("detached: ok exit=0 ") and done.returncode == 0
    assert f"log={log}" in line and line.endswith("outputs=/a/out.json,/a/folder")
    assert log.read_text() == "progress one\nprogress two\n"


def test_a_failing_command_says_failed_and_passes_its_exit_code_on(tmp_path):
    log = tmp_path / "run.log"
    done = detached(["--log", str(log), "--", sys.executable, "-c",
                     "import sys; print('boom', file=sys.stderr); sys.exit(3)"])
    assert done.returncode == 3
    assert done.stdout.startswith("detached: failed exit=3 ") and done.stdout.rstrip().endswith("outputs=-")
    assert log.read_text() == "boom\n"


def test_a_tools_detach_reruns_it_without_the_flag(tmp_path):
    tool = tmp_path / "tool.py"
    tool.write_text(f"import pathlib, sys\nsys.path.insert(0, {str(HERE)!r})\nimport detached\n"
                    f"detached.LOGS = pathlib.Path({str(tmp_path)!r})\n"
                    "if detached.FLAG in sys.argv:\n    detached.relaunch(sys.argv, 'tool', ['/x/page.html'])\n"
                    "print('ran with', sys.argv[1:])\n")
    done = subprocess.run([sys.executable, str(tool), "place", "--detach", "--cloud"], capture_output=True, text=True)
    [log] = tmp_path.glob("tool-*.log")
    assert done.stdout.startswith("detached: ok exit=0 ") and done.stdout.rstrip().endswith("outputs=/x/page.html")
    assert log.read_text() == "ran with ['place', '--cloud']\n"
