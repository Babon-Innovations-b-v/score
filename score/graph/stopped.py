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
# How long a detached run's command has to end after its signal is passed on: score run's own grace and a margin.
FORWARD_WAIT_SECONDS = 40


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


def children():
    """This process's live child processes (zombies left out), read from /proc."""
    found = []
    for entry in pathlib.Path("/proc").iterdir():
        try:
            fields = (entry / "stat").read_text().rpartition(")")[2].split() if entry.name.isdigit() else ()
        except OSError:  # gone while being read
            continue
        if fields and fields[0] != "Z" and int(fields[1]) == os.getpid():
            found.append(int(entry.name))
    return found


def forward(number, wait=FORWARD_WAIT_SECONDS):
    """Send the stopping signal on to this process's children and wait up to `wait` seconds for them to end: `score
    run` leads a process group of its own, so a signal to the detached session no longer reaches it, and without this
    the exit below would SIGKILL it before it ended its own group and released what it held."""
    for child in children():
        try:
            os.kill(child, number)
        except ProcessLookupError:
            pass
    deadline = time.time() + wait
    while children() and time.time() < deadline:
        time.sleep(0.2)


def detached_run(log, outputs, command):
    """detached.run (the command's output to the log, one result line at the end), its result line also on a stopping
    signal: `detached: stopped by signal N exit=128+N minutes=... log=... outputs=...`; the exit code."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    started = time.time()

    def say(number):
        forward(number)
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
