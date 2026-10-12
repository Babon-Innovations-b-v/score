"""A run stopped from outside still says so (2026-10-12: a `score run` whose process group was sent SIGTERM ended its
log with no line). `stop_on_signals` makes SIGTERM, SIGINT and SIGHUP say one line and exit 128 + the signal's number;
run as a script it is tools/props/cloud/detached.py's run with that line as its result line, which `score run
--detach` starts. Outside detached.py on purpose: most stages' code version hashes that file, and an edit there would
re-make them all.

    python score/graph/stopped.py --log <log> --outputs <paths> -- <command ...>
"""
import os
import pathlib
import signal
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
STOPPING = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


def stop_on_signals(say):
    """On SIGTERM, SIGINT or SIGHUP: say(the signal's number) once, then exit 128 + it (a running subprocess.run kills
    its command on the way out). A process forked from this one (a node's) takes the signal's default instead."""
    owner = os.getpid()

    def stop(number, frame):
        if os.getpid() != owner:
            signal.signal(number, signal.SIG_DFL)
            os.kill(os.getpid(), number)
            return
        for each in STOPPING:
            signal.signal(each, signal.SIG_IGN)
        say(number)
        sys.exit(128 + number)
    for number in STOPPING:
        signal.signal(number, stop)


def detached_run(log, outputs, command):
    """detached.run (the command's output to the log, one result line at the end), its result line also on a stopping
    signal: `detached: stopped by signal N exit=128+N minutes=... log=... outputs=...`; the exit code."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    started = time.time()

    def say(number):
        line = detached.result_line(128 + number, (time.time() - started) / 60, log, outputs)
        print(line.replace("detached: failed", f"detached: stopped by signal {number}", 1), flush=True)
    stop_on_signals(say)
    return detached.run(command, log, outputs)


if __name__ == "__main__":
    arguments = sys.argv[1:]
    split = arguments.index("--")
    options = dict(zip(arguments[:split:2], arguments[1:split:2]))
    sys.exit(detached_run(pathlib.Path(options["--log"]), [word for word in options.get("--outputs", "").split(",")
                                                            if word], arguments[split + 1:]))
