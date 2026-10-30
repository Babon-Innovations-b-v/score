"""The run of one of the adjoint's Newton check scripts by path, in Newton's own Python, and the real store's
inputs (`SCORE_ADJOINT_REAL`); test support only, never imported by the adjoint's modules."""
import json
import os
import pathlib
import subprocess

import pytest

HERE = pathlib.Path(__file__).parent


def newton_python():
    """Newton's own Python: `SCORE_NEWTON_PYTHON`, else $PROPS_HOME/envs/newton_env's; None when neither exists."""
    named = os.environ.get("SCORE_NEWTON_PYTHON")
    if named:
        return pathlib.Path(named)
    found = pathlib.Path(os.environ.get("PROPS_HOME", "/nonexistent")) / "envs/newton_env/bin/python"
    return found if found.exists() else None


def newton_ran(script, *arguments, timeout=110):
    """`script` (a check beside this file) run in Newton's Python with this folder first, its stdout; skipped
    without Newton's Python."""
    python = newton_python()
    if python is None:
        pytest.skip("no Newton Python (SCORE_NEWTON_PYTHON or $PROPS_HOME/envs/newton_env)")
    ran = subprocess.run([str(python), "-B", str(HERE / script), str(HERE), *map(str, arguments)],
                         capture_output=True, text=True, timeout=timeout)
    assert ran.returncode == 0, ran.stderr[-2000:]
    return ran.stdout


def real_inputs():
    """`SCORE_ADJOINT_REAL`'s JSON {seeds, set, reference, cases: {case: job}} (absolute paths): one tuning body's
    set and its card solve; skipped without it or without Newton's Python (the real store's inputs)."""
    named = os.environ.get("SCORE_ADJOINT_REAL")
    if newton_python() is None or not named:
        pytest.skip("no Newton Python or no SCORE_ADJOINT_REAL")
    given = json.loads(pathlib.Path(named).read_text())
    return given, [f"{case}={job}" for case, job in given["cases"].items()]


def last_json(stdout):
    """A check script's last line, its JSON result."""
    return json.loads(stdout.strip().splitlines()[-1])
