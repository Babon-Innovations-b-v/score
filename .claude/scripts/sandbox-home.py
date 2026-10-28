#!/usr/bin/env python3
"""Run one test command in a sandbox home, so no test can write, move or delete the real runtime (a test unlinked
the real cloud ledger, 2026-10-17). `make tests` and `make check` run every test through it:

    python3 .claude/scripts/sandbox-home.py -- <command> [<argument> ...]

PROPS_HOME is a fresh folder in the run's own temp folder (TMPDIR, PROPS_WORK unset, so it follows), both removed
after: whatever a test leaves in the temp folder goes with them. The tests read
environment data from the real home (seeds, kits, stages under work/), so where bubblewrap is installed the sandbox links to
the real home's folders and the command runs with the real home mounted read-only: a read works, a write through a
link fails loudly instead of landing. work/ and work/carry-commits are real folders in the sandbox with their entries
linked, so a test may add a folder of its own there. The real home's state (STATE: the cloud ledger and bills, the store and its
locks and logs, the run registry and frozen copies) is never linked, so a test that writes those gets its own empty ones. Without bubblewrap nothing is
linked, and a test that needs environment data fails rather than reach the real home. The library is none
(SCORE_LIB_ROOT empty): no test reaches the real score_lib checkout. The exit status is the command's.
"""
import os
import pathlib
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

REAL_HOME = pathlib.Path(os.environ.get("SCORE_REAL_HOME", pathlib.Path.home() / ".farm-factory-props"))
# A run's registry (runs/: score run writes its entry and active.json, score/graph/runs.py) and its frozen code copies
# (frozen/, score/graph/frozen.py) are state too: linked, a run driven by a test wrote into the read-only real home.
STATE = ("cloud", "store", "store-tests", "locks", "logs", "tmp", "replays", "runs", "frozen")
# Environment data folders made real folders in the sandbox, each entry in them linked, so a test can add an entry of its own
# beside the real ones (a work folder, a commit's files under work/carry-commits) while the real ones stay read-only.
MIRRORED = ("work", "work/carry-commits", "work/pixal")  # work/pixal: a test lays a take beside the real ones


def linked(entry):
    """True for a real home entry the sandbox links to: environment data, not state or scratch."""
    return entry.name not in STATE and not entry.name.startswith("scratch")


def link_into(real, sandbox, folder):
    """Link the real home's entries in `folder` ("" for the home itself) into the sandbox; a MIRRORED folder is made a
    real folder there and its own entries linked."""
    for entry in sorted((real / folder).iterdir()):
        name = f"{folder}/{entry.name}" if folder else entry.name
        if not folder and not linked(entry):
            continue
        if name in MIRRORED and entry.is_dir():
            (sandbox / name).mkdir()
            link_into(real, sandbox, name)
        else:
            (sandbox / name).symlink_to(entry)


def make_sandbox(real, link, temp=None):
    """A fresh sandbox home in the temp folder (`temp`, else the system's) with an empty store (store/cache, as a fresh
    real home has), linking the real home's environment data when `link`."""
    sandbox = pathlib.Path(tempfile.mkdtemp(prefix="score-test-", dir=temp))
    (sandbox / "store" / "cache").mkdir(parents=True)
    if link and real.is_dir():
        link_into(real, sandbox, "")
    return sandbox


def read_only_command(real, argv):
    """`argv` run with the real home mounted read-only (bubblewrap), or None where that cannot be done."""
    bubblewrap = shutil.which("bwrap")
    if not bubblewrap or not real.is_dir():
        return None
    return [bubblewrap, "--dev-bind", "/", "/", "--ro-bind", str(real), str(real), "--", *argv]


def writable_again(function, path, _error):
    """rmtree's retry for a read-only file the test left (the store keeps its files read-only): its folder and it
    made writable, then removed. Only paths inside the sandbox reach here (rmtree never follows a link), and a link a
    test made is removed, never changed, so nothing outside the sandbox has its permissions touched."""
    targets = [os.path.dirname(path)] + ([] if os.path.islink(path) else [path])
    for target in targets:
        os.chmod(target, os.stat(target).st_mode | stat.S_IWUSR | stat.S_IXUSR)
    function(path)


def remove(sandbox):
    """Remove a sandbox home: its links first (never followed), then everything the test wrote."""
    for entry in sandbox.iterdir():
        if entry.is_symlink():
            entry.unlink()
    shutil.rmtree(sandbox, onerror=writable_again)


def stopped(number, _frame):
    """A stopping signal as an exit: subprocess.run kills the test, and run's cleanup still removes the sandbox."""
    raise SystemExit(128 + number)


def run(argv, real=REAL_HOME):
    """Run `argv` in a sandbox home; its exit status."""
    command = read_only_command(real, argv)
    # the run's own temp folder (TMPDIR), its home inside it, removed with it: the tests' mkdtemp stores were never
    # removed and took every inode of /tmp (2026-10-25: 6,000 folders), so nothing else could write there
    temp = pathlib.Path(tempfile.mkdtemp(prefix="score-test-tmp-"))
    for number in (signal.SIGTERM, signal.SIGHUP):  # a stopped make or a closed terminal still removes both
        signal.signal(number, stopped)
    sandbox = make_sandbox(real, link=command is not None, temp=temp)
    environ = {name: value for name, value in os.environ.items() if name != "PROPS_WORK"}
    try:
        # SCORE_LIB_ROOT empty: no library, so a test never reaches the real score_lib checkout beside this one (its
        # takes fetched into the sandbox, 2026-10-28); a test that needs a library sets up a toy one
        return subprocess.run(command or argv, env={**environ, "PROPS_HOME": str(sandbox), "TMPDIR": str(temp),
                                                    "SCORE_LIB_ROOT": ""}).returncode
    finally:
        remove(sandbox)
        shutil.rmtree(temp, onerror=writable_again)


def main(argv):
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        raise SystemExit("usage: sandbox-home.py -- <command> [<argument> ...]")
    return run(argv[argv.index("--") + 1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
