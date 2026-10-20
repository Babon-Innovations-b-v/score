"""The grain check: a clean render passes, a speckled one fails by name, a picture with no flat area is unknown; and
the light stage's guided smoothing keeps a look's edge while it takes out its lamp groups' specks.

Run: .venv/bin/python score/checks/grain_test.py
"""
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks  # noqa: E402
from score.checks import grain  # noqa: E402
from score.stages.light import mix  # noqa: E402


def wall(specks=0.0):
    """A 200 x 200 picture of a lit wall (a soft ramp, a hard edge across its middle), with `specks` of its pixels
    sparkling, seeded."""
    rows = np.linspace(60.0, 140.0, 200)[:, None] * np.ones((1, 200))
    rows[:, 100:] += 60.0
    sparkling = np.random.default_rng(1).random(rows.shape) < specks
    rows[sparkling] = 255.0
    return Image.fromarray(rows.astype(np.uint8)).convert("RGB")


def saved(folder, name, picture):
    path = pathlib.Path(folder) / name
    picture.save(path)
    return path


def test_a_clean_render_passes_and_a_sparkling_one_fails_by_name():
    with tempfile.TemporaryDirectory() as folder:
        clean, grainy = saved(folder, "clean.png", wall()), saved(folder, "camp.png", wall(0.02))
        assert grain.specks(clean) == 0.0 and grain.specks(grainy) > grain.GRAINY_PER_MILLE
        passed = grain.verdict("grain", [clean], folder)
        failed = grain.verdict("grain", [clean, grainy], folder)
    assert passed.answer == checks.PASS and "unmeasured" in passed.reason
    assert failed.answer == checks.FAIL and failed.measures["grainy"] == 1 and "unmeasured" in failed.reason
    assert failed.findings[0].startswith("grainy picture camp.png:")


def test_a_picture_with_no_flat_area_is_unknown():
    noise = np.random.default_rng(2).integers(0, 255, (200, 200), dtype=np.uint8)
    with tempfile.TemporaryDirectory() as folder:
        busy = saved(folder, "busy.png", Image.fromarray(noise))
        assert grain.specks(busy) is None
        assert grain.verdict("grain", [busy]).answer == checks.UNKNOWN
    assert grain.verdict("grain", []).answer == checks.UNKNOWN


def test_the_guided_smoothing_keeps_the_edge_and_takes_out_the_specks():
    guide = np.full((80, 80), 0.3)
    guide[:, 40:] = 0.7
    ratio = np.where(guide > 0.5, 1.5, 1.0)
    noisy = ratio + np.random.default_rng(3).normal(0.0, 0.2, ratio.shape)
    smooth = mix.smoothed(noisy, guide)
    assert np.abs(smooth - ratio)[:, 2:-2].std() < 0.25 * np.abs(noisy - ratio).std()
    assert abs(smooth[:, 30:38].mean() - 1.0) < 0.05 and abs(smooth[:, 42:50].mean() - 1.5) < 0.05


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
