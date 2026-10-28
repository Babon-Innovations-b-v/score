#!/usr/bin/env python3
"""Run one test command in a sandbox home, so no test can write, move or delete the real runtime (a test unlinked
the real cloud ledger, 2026-10-17). `make tests` and `make check` run every test through it:

    python3 .claude/scripts/sandbox-home.py -- <command> [<argument> ...]

PROPS_HOME is a fresh, empty folder (only store/cache, as a fresh real home has) in the run's own temp folder
(TMPDIR, PROPS_WORK unset, so it follows), both removed after: whatever a test leaves in the temp folder goes with
them. Nothing of the real home is linked into it (owner's rule: tests use small fixtures, never the real store or
home; linked design/plans let tests lean on real data unnoticed, 2026-10-28): a test lays out the data it needs
itself. Where bubblewrap is installed the command also runs with the real home mounted read-only, so a test that
names the real home's path still cannot write there. The library is none (SCORE_LIB_ROOT empty): no test reaches
the real score_lib checkout. The exit status is the command's.
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
def make_sandbox(temp=None):
    """A fresh, empty sandbox home in the temp folder (`temp`, else the system's) with an empty store (store/cache, as a
    fresh real home has)."""
    sandbox = pathlib.Path(tempfile.mkdtemp(prefix="score-test-", dir=temp))
    (sandbox / "store" / "cache").mkdir(parents=True)
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
    """Remove a sandbox home and everything the test wrote (rmtree never follows a link a test made)."""
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
    sandbox = make_sandbox(temp)
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
