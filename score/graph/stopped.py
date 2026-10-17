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
import tempfile
import threading
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
STOPPING = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
# How long a detached run's command has to end after its signal is passed on: score run's own grace and a margin.
FORWARD_WAIT_SECONDS = 40
# What a stopped `score run` sends its own nodes when the stop reached it alone (score/__main__.py): a node that has
# not had a stop of its own passes SIGTERM on to its children and ends after them (pass_stop_on). A real-time signal,
# numbered above every stopping one: Python runs pending handlers in signal number order, so a node whose main thread
# was busy when the whole group was signalled handles that stop first, and passes nothing on (a batch stops deleting
# at its second signal).
PASS_ON = signal.SIGRTMIN


def stop_on_signals(say):
    """On SIGTERM, SIGINT or SIGHUP: say(the signal's number) once, then exit 128 + it (a running subprocess.run kills
    its command on the way out). A process forked from this one (a node's) ends after its children instead
    (end_after_children), and passes on a stop its run sends it with PASS_ON (pass_stop_on)."""
    owner = os.getpid()

    def stop(number, frame):
        if os.getpid() != owner:
            end_after_children(number)
            return
        for each in STOPPING:
            signal.signal(each, signal.SIG_IGN)
        say(number)
        sys.exit(128 + number)

    def passed_on(number, frame):
        if os.getpid() != owner:
            pass_stop_on()
    for number in STOPPING:
        signal.signal(number, stop)
    signal.signal(PASS_ON, passed_on)


def pass_stop_on():
    """A forked process's (a node's) stop sent by its run alone (PASS_ON): SIGTERM to each of its children, then its end
    after them (end_after_children). Nothing when it is already stopping: the stop reached its children too."""
    if signal.getsignal(signal.SIGTERM) == signal.SIG_IGN:
        return
    for child in children():
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass
    end_after_children(signal.SIGTERM)


def end_after_children(number):
    """A forked process's (a node's) stop: it ignores every further stopping signal (shows_stop) and exits 128 +
    `number` once the children it has now have ended, its main thread going on meanwhile. A cloud batch it started
    deletes its machines on the same signal and writes about each to this process's pipe; this process ending first
    broke that pipe and the batch's delete loop with it (2026-10-17)."""
    for each in STOPPING:
        signal.signal(each, signal.SIG_IGN)
    threading.Thread(target=exit_after, args=(children(), 128 + number), daemon=True).start()


def exit_after(waited, code):
    """Exit with `code` once none of `waited` is alive; a child started since gets SIGTERM first."""
    while set(waited) & set(children()):
        time.sleep(0.2)
    for child in children():
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass
    os._exit(code)


def shows_stop(pid):
    """Whether a process ignores every stopping signal, as a stopped node does (end_after_children); False when it is
    gone."""
    try:
        status = pathlib.Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return False
    ignored = int(next(line.split()[1] for line in status.splitlines() if line.startswith("SigIgn:")), 16)
    wanted = sum(1 << (number - 1) for number in STOPPING)
    return ignored & wanted == wanted


def catches_pass_on(pid):
    """Whether a process has a handler for PASS_ON (a node forked from a run that called stop_on_signals); False when it
    is gone."""
    try:
        status = pathlib.Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return False
    caught = int(next(line.split()[1] for line in status.splitlines() if line.startswith("SigCgt:")), 16)
    return bool(caught & 1 << (PASS_ON - 1))


def stop_mark(runner_pid):
    """The file whose making sends a runner's process group its one stop: named for the runner's pid and its start
    time, so a later process with the same pid has a mark of its own. Read while the runner lives."""
    started = pathlib.Path(f"/proc/{runner_pid}/stat").read_text().rpartition(")")[2].split()[19]
    return pathlib.Path(tempfile.gettempdir()) / f"score-stop-{runner_pid}-{started}"


def claim_stop(mark):
    """Make the stop mark; True for the one process that made it, False for every other (a runner's group is sent
    SIGTERM once: a batch stops deleting at its second signal)."""
    try:
        os.close(os.open(mark, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        return False
    return True


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
