"""Check that a model step is refused on this PC unless the emergency switch is thrown.

Runs the real entry point, pixal.py, with the system python on a picture that is not a model's
input, in a sandbox: refused, it never reaches the cut-out, the generator or the card.

Run: python3 tools/props/local_models_test.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import local_models  # noqa: E402


def test_refused_without_the_switch():
    kept = os.environ.pop(local_models.ALLOW, None)
    try:
        local_models.refuse_here("a model", "the cloud")
    except SystemExit as refused:
        assert refused.code == 3
    else:
        raise AssertionError("a model step ran without the switch")
    finally:
        if kept is not None:
            os.environ[local_models.ALLOW] = kept


def test_allowed_with_the_switch():
    kept = os.environ.get(local_models.ALLOW)
    os.environ[local_models.ALLOW] = "1"
    try:
        local_models.refuse_here("a model", "the cloud")
    finally:
        if kept is None:
            os.environ.pop(local_models.ALLOW)
        else:
            os.environ[local_models.ALLOW] = kept


def test_pixal_refuses_here_and_names_the_cloud():
    with tempfile.TemporaryDirectory() as sandbox:
        picture = pathlib.Path(sandbox) / "crate.png"
        picture.write_bytes(b"")
        environment = {key: value for key, value in os.environ.items() if key != local_models.ALLOW}
        environment.update(PROPS_HOME=sandbox, PROPS_WORK=str(pathlib.Path(sandbox) / "work"))
        done = subprocess.run([sys.executable, str(HERE / "pixal.py"), str(picture), "crate", "--who", "test"],
                              env=environment, capture_output=True, text=True, timeout=60)
        assert done.returncode == 3, (done.returncode, done.stderr)
        assert "cloud/batch.py" in done.stderr, done.stderr
        assert not (pathlib.Path(sandbox) / "card.claim").exists()
        assert not (pathlib.Path(sandbox) / "work" / "pixal" / "crate.glb").exists()


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("local_models_test: ok")
