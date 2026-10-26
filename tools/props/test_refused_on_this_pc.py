"""No model step and no heavy step runs on this PC; both run where a cloud runner set FARM_LOCAL_MODELS=1
(local_models.py, heavy.py; owner, 2026-10-03 and 2026-10-12). Pixal3D's own entry point, pixal.py, run for real on a
picture, is refused before the cut-out, the card claim or the generator, and names the cloud batch that does it.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_a_model_step_is_refused_here_and_runs_on_a_marked_machine: local_models.allowed returns
  `os.environ.get(ALLOW) != "0"` (an unset switch lets a model run here).
- test_a_heavy_step_is_refused_here_and_runs_on_a_marked_machine: heavy.refuse_here's `if not local_models.allowed():`
  made `if False:`.
- test_pixal_refuses_before_the_cut_out_and_names_the_cloud: pixal.cut_out's `refuse_here("the cut-out (BiRefNet)",
  CLOUD)` dropped (the cut-out starts the lab's python on this PC instead).
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


@pytest.fixture
def no_switch(monkeypatch):
    monkeypatch.delenv(local_models.ALLOW, raising=False)


def test_a_model_step_is_refused_here_and_runs_on_a_marked_machine(no_switch, monkeypatch):
    with pytest.raises(SystemExit) as refused:
        local_models.refuse_here("a model", "the cloud")
    assert refused.value.code == 3
    monkeypatch.setenv(local_models.ALLOW, "1")
    local_models.refuse_here("a model", "the cloud")


def test_a_heavy_step_is_refused_here_and_runs_on_a_marked_machine(no_switch, monkeypatch):
    with pytest.raises(SystemExit, match="the paint runs on a cloud machine"):
        heavy.refuse_here("the paint")
    monkeypatch.setenv(local_models.ALLOW, "1")
    heavy.refuse_here("the paint")


def test_pixal_refuses_before_the_cut_out_and_names_the_cloud(tmp_path):
    picture = tmp_path / "crate.png"
    picture.write_bytes(b"")
    environment = {key: value for key, value in os.environ.items() if key != local_models.ALLOW}
    environment.update(PROPS_HOME=str(tmp_path), PROPS_WORK=str(tmp_path / "work"))
    done = subprocess.run([sys.executable, str(HERE / "pixal.py"), str(picture), "crate", "--who", "test"],
                          env=environment, capture_output=True, text=True, timeout=60)
    assert done.returncode == 3, (done.returncode, done.stderr)
    assert "cloud/batch.py" in done.stderr, done.stderr
    assert not (tmp_path / "card.claim").exists()
    assert not (tmp_path / "work" / "pixal" / "crate.glb").exists()
