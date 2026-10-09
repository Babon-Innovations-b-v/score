"""Run a long command detached, so an agent never waits on it in the foreground (owner, 2026-10-09, WAITING): every
line the command prints goes to a log file, and at the end exactly one result line is printed, its status, minutes,
log and output paths. An agent starts it with the Bash tool's run_in_background and goes on with other work or ends
its turn; the completion notice wakes it and the one line says what happened, with no poll loop and no log in the
conversation. A turn more than 5 minutes after the previous one re-writes the agent's whole context to the cache.

    python3 tools/props/cloud/detached.py --log /tmp/score-detached/gate.log [--outputs a,b] -- make tests
    <tool> ... --detach        # blender_cloud.py, tools/usd/settle.py, tools/review/page.py: the same, a default log

The result line:  detached: ok exit=0 minutes=7.3 log=<path> outputs=<path>,<path>
"""
import argparse
import pathlib
import subprocess
import sys
import time

LOGS = pathlib.Path("/tmp/score-detached")
FLAG = "--detach"


def log_path_for(name):
    """A fresh log path for one detached run of the named tool."""
    LOGS.mkdir(parents=True, exist_ok=True)
    return LOGS / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000000:06d}.log"


def result_line(code, minutes, log_path, outputs):
    status = "ok" if code == 0 else "failed"
    return (f"detached: {status} exit={code} minutes={minutes:.1f} log={log_path} "
            f"outputs={','.join(str(path) for path in outputs) or '-'}")


def run(command, log_path, outputs):
    """Run the command with its output in the log; print the one result line and return the command's exit code."""
    log_path = pathlib.Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with log_path.open("w") as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    print(result_line(code, (time.time() - started) / 60, log_path, outputs), flush=True)
    return code


def relaunch(argv, name, outputs):
    """Rerun this tool (its argv without --detach) detached under a fresh log, then exit with its exit code."""
    command = [sys.executable, *[word for word in argv if word != FLAG]]
    sys.exit(run(command, log_path_for(name), outputs))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--log", type=pathlib.Path, help="the log file (default: a fresh one under /tmp/score-detached)")
    parser.add_argument("--outputs", default="", help="the paths the command writes, comma separated, for the result")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- then the command and its arguments")
    options = parser.parse_args()
    command = options.command[1:] if options.command[:1] == ["--"] else options.command
    if not command:
        parser.error("give the command after --")
    outputs = [word for word in options.outputs.split(",") if word]
    sys.exit(run(command, options.log or log_path_for(pathlib.Path(command[0]).name), outputs))


if __name__ == "__main__":
    main()
