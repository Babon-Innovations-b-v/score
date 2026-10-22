"""The runs' slice on a conductor: every detached `score run` in score-runs.slice, capped at the machine's memory less
HEADROOM_GB, so an out-of-memory kill ends a run and never the listener, the sync or the size timer.

    tools/cloud/conductor/units/score-runs.slice    # the slice; its MemoryMax there is a safe share, set exactly here

A detached run starts as a transient scope of its own in the slice (scope_prefix: `systemd-run --user --scope
--slice=score-runs.slice`, which execs the run, so its pid is the one `score run --detach` prints). The heavy free
steps cap themselves with their own `systemd-run --user --scope -p MemoryMax=...`, which would land in app.slice,
outside the runs' cap: inside the slice, the run puts SHIM first on PATH (apply_shim), a `systemd-run` that adds
`--slice-inherit` (systemd 254 and later), so those scopes stay under score-runs.slice too. The cap is set at each
detach (ensure_cap), since the machine's memory changes with its size.
"""
import os
import pathlib
import shutil
import subprocess

from score import conductor

SLICE = "score-runs.slice"
HEADROOM_GB = 6
SHIM = pathlib.Path(__file__).resolve().parent / "bin"


def cap_bytes(total_gb=None):
    """The slice's MemoryMax: this machine's memory less HEADROOM_GB, at least 1 GB, in bytes."""
    total = conductor.meminfo_gb("MemTotal") if total_gb is None else total_gb
    return int(max(1.0, total - HEADROOM_GB) * 1024 ** 3)


def usable():
    """Whether detached runs go into the slice: on a conductor with systemd-run there."""
    return conductor.machine() is not None and shutil.which("systemd-run") is not None


def ensure_cap(run=subprocess.run):
    """Set the slice's MemoryMax for this boot to cap_bytes; whether systemd took it."""
    done = run(["systemctl", "--user", "set-property", "--runtime", SLICE, f"MemoryMax={cap_bytes()}"],
               capture_output=True, text=True)
    return done.returncode == 0


def scope_prefix(name):
    """The words that start a command as its own scope `name` in the runs' slice."""
    return ["systemd-run", "--user", "--scope", "--quiet", "--collect", f"--slice={SLICE}", f"--unit={name}", "--"]


def in_slice(cgroup=pathlib.Path("/proc/self/cgroup")):
    """Whether this process runs under score-runs.slice."""
    try:
        return f"/{SLICE}/" in cgroup.read_text()
    except OSError:
        return False


def apply_shim():
    """Inside the slice, put SHIM first on PATH so a step's own systemd-run scope stays in the slice; whether it did."""
    if not in_slice() or os.environ.get("PATH", "").startswith(f"{SHIM}:"):
        return False
    os.environ["PATH"] = f"{SHIM}:{os.environ.get('PATH', '')}"
    return True
