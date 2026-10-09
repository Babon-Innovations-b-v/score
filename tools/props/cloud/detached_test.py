"""Check the detached mode without renting anything: the command's output goes to the log, not the terminal; exactly one
result line is printed with its status, exit code, log and outputs; a failing command says failed and passes its exit
code on; a tool's --detach reruns it without the flag.

Run: .venv/bin/python tools/props/cloud/detached_test.py   (make tests runs it)
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE / "detached.py"


def detached_call(arguments):
    return subprocess.run([sys.executable, str(TOOL), *arguments], capture_output=True, text=True)


def the_output_goes_to_the_log():
    with tempfile.TemporaryDirectory() as temporary:
        log = pathlib.Path(temporary) / "run.log"
        done = detached_call(["--log", str(log), "--outputs", "/a/out.json,/a/folder", "--", sys.executable, "-c",
                              "print('progress one'); print('progress two')"])
        lines = done.stdout.splitlines()
        problems = []
        if len(lines) != 1 or not lines[0].startswith("detached: ok exit=0 "):
            problems.append(f"the result is not one ok line: {lines}")
        if lines and (f"log={log}" not in lines[0] or "outputs=/a/out.json,/a/folder" not in lines[0]):
            problems.append(f"the result line lacks the log or the outputs: {lines[0]}")
        if "progress one\nprogress two" not in log.read_text():
            problems.append("the command's output is not in the log")
        if done.returncode != 0:
            problems.append(f"exit {done.returncode} for a command that passed")
        return problems


def a_failure_says_failed():
    with tempfile.TemporaryDirectory() as temporary:
        log = pathlib.Path(temporary) / "run.log"
        done = detached_call(["--log", str(log), "--", sys.executable, "-c",
                              "import sys; print('boom', file=sys.stderr); sys.exit(3)"])
        problems = []
        if done.returncode != 3:
            problems.append(f"the exit code passed on is {done.returncode}, not 3")
        if not done.stdout.startswith("detached: failed exit=3 ") or "outputs=-" not in done.stdout:
            problems.append(f"the result line is {done.stdout!r}")
        if "boom" not in log.read_text():
            problems.append("the command's errors are not in the log")
        return problems


def a_tool_reruns_itself_without_the_flag():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        tool = folder / "tool.py"
        tool.write_text(f"import sys\nsys.path.insert(0, {str(HERE)!r})\nimport detached\ndetached.LOGS = "
                        f"__import__('pathlib').Path({str(folder)!r})\nif detached.FLAG in sys.argv:\n"
                        "    detached.relaunch(sys.argv, 'tool', ['/x/page.html'])\nprint('ran with', sys.argv[1:])\n")
        done = subprocess.run([sys.executable, str(tool), "place", "--detach", "--cloud"], capture_output=True,
                              text=True)
        logs = list(folder.glob("tool-*.log"))
        problems = []
        if not done.stdout.startswith("detached: ok exit=0 ") or "outputs=/x/page.html" not in done.stdout:
            problems.append(f"the result line is {done.stdout!r}")
        if len(logs) != 1 or "ran with ['place', '--cloud']" not in logs[0].read_text():
            problems.append("the tool did not rerun without --detach into its log")
        return problems


CHECKS = (the_output_goes_to_the_log, a_failure_says_failed, a_tool_reruns_itself_without_the_flag)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
