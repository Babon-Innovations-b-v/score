"""Every pytest run in this repository works in a sandbox home: it refuses to start unless PROPS_HOME (and PROPS_WORK,
when set) points into a folder of its own inside the system's temp folder, so no test can write, move or delete the
real runtime (fault, 2026-10-17: park_test.py, collected after a test that had already imported ledger.py with the real
home, unlinked the real cloud ledger). `make tests` and `make check` give each run a fresh one; by hand:

    PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest <test file>

Plain-script tests (a `__main__` block) get the same fresh home from `make tests`.
"""
import os
import pathlib
import tempfile

import pytest


def outside_temp(name, value):
    """Why `value` of the variable `name` is not a sandbox: a folder of its own inside the temp folder; None when it
    is one."""
    if not value:
        return f"{name} is not set"
    temp = pathlib.Path(tempfile.gettempdir()).resolve()
    folder = pathlib.Path(value).expanduser().resolve()
    if folder == temp or not folder.is_relative_to(temp):
        return f"{name}={value} is not a folder of its own inside {temp}"
    return None


def sandbox_refusal(environ):
    """Why a test run with these variables could touch the real home, or None when it runs in a sandbox."""
    refusal = outside_temp("PROPS_HOME", environ.get("PROPS_HOME"))
    if refusal is None and environ.get("PROPS_WORK"):
        refusal = outside_temp("PROPS_WORK", environ["PROPS_WORK"])
    return refusal


def pytest_configure(config):
    """Refuse the whole run before any test module is imported when it has no sandbox home."""
    refusal = sandbox_refusal(os.environ)
    if refusal:
        pytest.exit(f"refused: {refusal}. Tests run in a sandbox home: PROPS_HOME=$(mktemp -d) (make tests gives "
                    f"each run one)", returncode=4)
