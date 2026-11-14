"""The style measure (style.py) reads only the models' own pixels and its numbers come out as worked by hand: one
review root drawn in the test (no Blender, no cloud, no review pages), measured through style.py's own two steps
(write_pairs, then report over a likeness written by hand in place of similar.py's), every reading checked on that
one result.

Breaks (each applied once, seen red, reverted), in tools/review/style.py:
- told from the grey: foreground takes every pixel (`distance >= 0`).
- Lab back to linear: lab_to_linear's white point X is 0.95, not 0.9505.
- a palette colour at any brightness: shaded lights the palette at full brightness only.
- pairs within and across: pair_names adds no pair within a place.
- the style gap: place_features drops the silhouettes' part of the gap.
- renders by place: model_renders globs every png, the parts renders too.
- a model shown twice: without_copies keeps every pair.
- stains read as marks: marks reads every tile's spread as 0.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_the_style_measure_reads_only_the_models_own_pixels.py
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import style  # noqa: E402
import sweep  # noqa: E402

GREY = (100, 100, 102)
BLUE = np.array([0.05, 0.10, 0.60])  # the places' one palette colour, linear
HALF_BLUE = tuple(int(round(value * 255)) for value in (BLUE * 0.5) ** (1 / 2.4) * 1.055 - 0.055)  # at half light, sRGB
STAINS = (slice(16, 48, 3), slice(16, 48), (60, 50, 40))

# The review root: place, model, its colour, its square, stained; each a <place>/models/<model>--made--now.png.
MODELS = [
    ("hub", "blue", HALF_BLUE, (16, 48), False),
    ("hub", "red", (200, 40, 40), (16, 48), False),
    ("hub", "grey", (180, 180, 180), (16, 48), False),
    ("lab", "flat", (120, 120, 120), (16, 48), False),
    ("lab", "stained", (120, 120, 120), (16, 48), True),
    ("lab", "tiny", (120, 120, 120), (30, 34), False),
    ("lab", "wrench", (90, 90, 90), (16, 48), False),
    ("workshop", "wrench", (90, 90, 90), (16, 48), False),
    ("workshop", "vice", (90, 90, 90), (8, 56), False),
    ("camp", "lamp", (40, 160, 60), (16, 48), False),
]

# similar.py's answer, by hand: the copy's pair (lab's wrench is workshop's wrench) must leave it.
LIKENESS = {"colour|hub/blue|hub/red": 0.9, "colour|hub/blue|lab/flat": 0.5, "shape|hub/blue|hub/red": 0.7,
            "shape|hub/blue|lab/flat": 0.6, "colour|camp/lamp|lab/flat": 0.4, "shape|camp/lamp|lab/flat": 0.4,
            "colour|lab/wrench|workshop/wrench": 1.0, "shape|lab/wrench|workshop/wrench": 1.0,
            "colour|lab/wrench|workshop/vice": 0.6, "shape|lab/wrench|workshop/vice": 0.5}

# Each model's readings as worked by hand: its fit to the blue palette at any brightness (None: no coloured pixels).
FITS = {"hub/blue": 1.0, "hub/red": 0.0, "hub/grey": None, "camp/lamp": 0.0}


def render(path, colour, box, stained):
    """A made-model render as review_models.py leaves it: one grey with a square of the colour in the middle."""
    picture = np.full((64, 64, 3), GREY, dtype=np.uint8)
    picture[box[0]:box[1], box[0]:box[1]] = colour
    if stained:
        picture[STAINS[0], STAINS[1]] = STAINS[2]
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture).save(path)


def review_root(root):
    """Every model of MODELS drawn under root, and one parts render the measure must not read."""
    for place, model, colour, box, stained in MODELS:
        render(root / place / "models" / f"{model}{style.SUFFIX}", colour, box, stained)
    render(root / "hub/models/blue--parts--now.png", (90, 90, 90), (16, 48), False)


def test_the_style_measure_reads_only_the_models_own_pixels(tmp_path, monkeypatch):
    root, work = tmp_path / "review", tmp_path / "work"
    review_root(root)
    work.mkdir()
    monkeypatch.setattr(style, "palettes_of", lambda places: {place: sweep.lab(BLUE[None]) for place in places})

    renders = style.model_renders(root)
    assert {place: list(models) for place, models in renders.items()} == {
        "camp": ["lamp"], "hub": ["blue", "grey", "red"], "lab": ["flat", "stained", "tiny", "wrench"],
        "workshop": ["vice", "wrench"]}, f"the renders found are {renders}"

    mask = style.foreground(np.asarray(Image.open(renders["hub"]["red"])))
    assert mask.sum() == 32 * 32 and not mask[:16].any(), f"the model is {mask.sum()} pixels, not its square's 1024"

    colours = np.random.default_rng(1).random((50, 3))
    back = style.lab_to_linear(sweep.lab(colours))
    assert np.allclose(back, colours, atol=1e-4), f"Lab back to linear is off by {np.abs(back - colours).max():.5f}"

    pairs = [tuple(name.split("|")[1:]) for name in style.write_pairs(root, work) if name.startswith("colour|")]
    within = [pair for pair in pairs if pair[0].split("/")[0] == pair[1].split("/")[0]]
    assert len(within) == 3 + 6 + 1, f"{len(within)} pairs within, not the 10 of places of three, four and two"
    assert pairs == style.pair_names(renders) == style.pair_names(style.model_renders(root)), "the pairs change"
    assert any("camp/lamp" in pair for pair in pairs), "a place with one model has no pair across"
    assert len(list((work / "shapes").glob("*.png"))) == len(MODELS), "a silhouette per model is missing"

    (work / "likeness.json").write_text(json.dumps(LIKENESS))
    found = style.report(root, work)
    models = json.loads((work / "style-models.json").read_text())
    fits = {name: models[name.split("/")[0]][name.split("/")[1]]["fit"] for name in FITS}
    assert fits == FITS, f"the models fit {fits}, not {FITS}"

    flat, stained, tiny = (models["lab"][model]["marks"] for model in ("flat", "stained", "tiny"))
    assert stained > flat, f"the stained model reads {stained} marks, not above the flat one's {flat}"
    assert tiny is None, f"a model with no whole tile reads {tiny} marks"

    assert found["copies"] == [("lab/wrench", "workshop/wrench")], f"the copies are {found['copies']}"
    hub = found["places"]["hub"]["features"]
    assert hub["style_gap"] == round((0.9 - 0.5) - (0.7 - 0.6), 3), f"the hub's gap is {hub['style_gap']}, not 0.3"
    for place in ("camp", "workshop"):
        assert found["places"][place]["features"]["style_gap"] is None, f"{place}, no pair within, has a gap"
    world = found["features"]
    assert world["colour"]["pairs"] == [1, 3] and world["style_gap"] == round((0.9 - 0.5) - (0.7 - 0.5), 3), (
        f"the world's readings (the copy's pair out, the vice's in) are {world}")


if __name__ == "__main__":
    import runpy
    import pytest
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    raise SystemExit(pytest.main([__file__, "-q"]))
