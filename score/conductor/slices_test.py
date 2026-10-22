"""On a conductor a detached run starts in score-runs.slice, capped at the machine's memory less 6 GB, and a step's
own systemd-run scope stays in that slice; elsewhere nothing changes.

Run: .venv/bin/python score/conductor/slices_test.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.conductor import slices  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
SLICE_FILE = REPO / "tools/cloud/conductor/units/score-runs.slice"


def test_the_cap_is_the_memory_less_six_gigabytes_at_both_sizes():
    assert slices.cap_bytes(16) == 10 * 1024 ** 3
    assert slices.cap_bytes(128) == 122 * 1024 ** 3
    assert slices.cap_bytes(4) == 1024 ** 3  # never below one


def test_the_slice_files_own_cap_is_no_more_than_the_idle_sizes():
    lines = SLICE_FILE.read_text().splitlines()
    assert "MemoryMax=62%" in lines and int(16 * 0.62) <= 16 - slices.HEADROOM_GB


def test_a_detached_run_is_its_own_scope_in_the_slice():
    assert slices.scope_prefix("score-run-x") == ["systemd-run", "--user", "--scope", "--quiet", "--collect",
                                                  "--slice=score-runs.slice", "--unit=score-run-x", "--"]


def test_off_a_conductor_no_run_goes_into_a_slice():
    from score import __main__ as command
    assert not slices.usable() and command.run_scope(pathlib.Path("/tmp/score-run-x.log")) == []


def test_the_shim_is_used_only_inside_the_slice():
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = os.environ.get("PATH")
    try:
        (folder / "cgroup").write_text("0::/user.slice/user@1000.service/app.slice/run-p1.scope\n")
        assert not slices.in_slice(folder / "cgroup")
        (folder / "cgroup").write_text("0::/user.slice/user@1000.service/score.slice/score-runs.slice/run-p1.scope\n")
        assert slices.in_slice(folder / "cgroup")
        assert not slices.apply_shim() and os.environ.get("PATH") == kept  # this test runs outside the slice
    finally:
        shutil.rmtree(folder)


def test_the_shim_adds_slice_inherit_to_a_user_unit_without_a_slice_of_its_own():
    folder = pathlib.Path(tempfile.mkdtemp())
    try:
        real = folder / "real"
        real.mkdir()
        (real / "systemd-run").write_text("#!/bin/sh\necho \"$@\"\n")
        (real / "systemd-run").chmod(0o755)
        path = f"{slices.SHIM}:{real}:/usr/bin:/bin"

        def shimmed(*words):
            return subprocess.run(["systemd-run", *words], env={**os.environ, "PATH": path}, capture_output=True,
                                  text=True, check=True).stdout.strip()
        assert shimmed("--user", "--scope", "-q", "-p", "MemoryMax=16G", "nice", "x") == \
            "--slice-inherit --user --scope -q -p MemoryMax=16G nice x"
        assert shimmed("--user", "--slice=other.slice", "x") == "--user --slice=other.slice x"
        assert shimmed("--scope", "x") == "--scope x"  # not a user unit: left alone
        assert shimmed("--user", "--", "x", "--slice") == "--slice-inherit --user -- x --slice"
    finally:
        shutil.rmtree(folder)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
