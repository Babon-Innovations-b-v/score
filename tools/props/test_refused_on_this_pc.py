"""No model step and no heavy step runs on this PC; both run where a cloud runner set FARM_LOCAL_MODELS=1
(local_models.py, heavy.py; owner, 2026-10-03 and 2026-10-12). Pixal3D's own entry point, pixal.py, run for real on a
picture, is refused before the cut-out, the card claim or the generator, and names the cloud batch that does it.

One test, test_refused_on_this_pc: each row is a way a step starts (a model step's guard, a heavy step's guard, pixal.py
as a process); each is started once with the switch unset and must stop with its exit code, naming where it runs and
leaving nothing behind, and the in-process guards are started again on a marked machine, where they let the step run.

Breaks that turn the test red (each applied once and seen red, 2026-11-13):
- row "model step": local_models.allowed returns `os.environ.get(ALLOW) != "0"` (an unset switch lets a model run
  here).
- row "heavy step": heavy.refuse_here's `if not local_models.allowed():` made `if False:`.
- row "pixal": pixal.cut_out's `refuse_here("the cut-out (BiRefNet)", CLOUD)` dropped (the cut-out starts the lab's
  python on this PC instead).
"""
import os
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import heavy  # noqa: E402
import local_models  # noqa: E402


def _in_process(start):
    """Start a step's guard here; return (the exit code a process would get or None, its stderr and exit text)."""
    def run(tmp_path, environment, capfd):
        try:
            start()
        except SystemExit as stopped:
            code = stopped.code if isinstance(stopped.code, int) else 1
            return code, capfd.readouterr().err + str(stopped.code)
        return None, capfd.readouterr().err
    return run


def _pixal(tmp_path, environment, capfd):
    """Run pixal.py for real on a picture as its own process; return (its exit code, its stderr)."""
    picture = tmp_path / "crate.png"
    picture.write_bytes(b"")
    environment = dict(environment, PROPS_HOME=str(tmp_path), PROPS_WORK=str(tmp_path / "work"))
    done = subprocess.run([sys.executable, str(HERE / "pixal.py"), str(picture), "crate", "--who", "test"],
                          env=environment, capture_output=True, text=True, timeout=60)
    return done.returncode, done.stderr


# (row, how the step starts, exit code when refused, text the refusal names, whether it is started on a marked machine)
ROWS = [
    ("model step", _in_process(lambda: local_models.refuse_here("a model", "the cloud")), 3,
     "Run it in the cloud instead: the cloud", True),
    ("heavy step", _in_process(lambda: heavy.refuse_here("the paint")), 1,
     "the paint runs on a cloud machine", True),
    ("pixal", _pixal, 3, "cloud/batch.py", False),
]


@pytest.mark.parametrize("row,start,code,names,marked", ROWS, ids=[row[0] for row in ROWS])
def test_refused_on_this_pc(row, start, code, names, marked, tmp_path, monkeypatch, capfd):
    monkeypatch.delenv(local_models.ALLOW, raising=False)
    unmarked = dict(os.environ)
    refused_code, said = start(tmp_path, unmarked, capfd)
    assert refused_code == code, (row, refused_code, said)
    assert names in said, (row, said)
    assert not (tmp_path / "card.claim").exists(), row
    assert not (tmp_path / "work" / "pixal" / "crate.glb").exists(), row
    if marked:
        monkeypatch.setenv(local_models.ALLOW, "1")
        ran_code, said = start(tmp_path, dict(os.environ), capfd)
        assert ran_code is None, (row, said)
