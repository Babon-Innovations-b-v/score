"""The style measure's checks (style.py), on renders drawn in the test: no Blender, no cloud, no review pages.

    .venv/bin/python tools/review/style_test.py
"""
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import style  # noqa: E402
import sweep  # noqa: E402

GREY = (100, 100, 102)


def render(path, colour, size=64, box=(16, 48)):
    """A made-model render as review_models.py leaves it: one grey with a square of the colour in the middle."""
    picture = np.full((size, size, 3), GREY, dtype=np.uint8)
    picture[box[0]:box[1], box[0]:box[1]] = colour
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture).save(path)
    return path


def the_model_is_told_from_the_grey():
    """The pixels away from the corners' grey are the model's, and only those."""
    with tempfile.TemporaryDirectory() as folder:
        path = render(pathlib.Path(folder) / "a.png", (200, 40, 40))
        mask = style.foreground(np.asarray(Image.open(path)))
    if mask.sum() != 32 * 32 or mask[:16].any():
        return [f"the model is {mask.sum()} pixels, not the 1024 of its square"]
    return []


def lab_goes_back_to_linear():
    """lab_to_linear undoes sweep.lab, so a palette can be lit and read again."""
    colours = np.random.default_rng(1).random((50, 3))
    back = style.lab_to_linear(sweep.lab(colours))
    return [] if np.allclose(back, colours, atol=1e-4) else [f"off by {np.abs(back - colours).max():.5f}"]


def a_palette_colour_fits_at_any_brightness():
    """A model drawn in a palette colour, darker than the colour itself, fits; one in another hue does not; a grey
    model has no coloured pixels and no fit."""
    palette = sweep.lab(np.array([[0.05, 0.10, 0.60]]))  # one blue
    problems = []
    with tempfile.TemporaryDirectory() as folder:
        darker = (np.array([0.05, 0.10, 0.60]) * 0.5) ** (1 / 2.4) * 1.055 - 0.055  # the blue at half its light, sRGB
        cases = {"blue": (tuple(int(round(value * 255)) for value in darker), 1.0), "red": ((200, 40, 40), 0.0),
                 "grey": ((180, 180, 180), None)}
        for name, (colour, expected) in cases.items():
            found = style.model_colour(render(pathlib.Path(folder) / f"{name}.png", colour), style.shaded(palette))
            if found["fit"] != expected:
                problems.append(f"the {name} model fits {found['fit']}, not {expected}")
    return problems


def pairs_cover_within_and_draw_across():
    """Every pair within a place is compared, and each model's partners across come from other places, the same on
    every run."""
    renders = {place: {f"m{index}": pathlib.Path(f"{place}{index}.png") for index in range(count)}
               for place, count in (("hub", 3), ("lab", 4), ("camp", 1))}
    pairs = style.pair_names(renders)
    problems = []
    within = [pair for pair in pairs if pair[0].split("/")[0] == pair[1].split("/")[0]]
    if len(within) != 3 + 6:
        problems.append(f"{len(within)} pairs within, not the 9 of a place of three and one of four")
    if pairs != style.pair_names(renders):
        problems.append("the pairs across change from run to run")
    if not any("camp/m0" in pair for pair in pairs):
        problems.append("a place with one model has no pair across")
    return problems


def the_style_gap_takes_the_shapes_away():
    """The gap is the colour renders' within-minus-across less the silhouettes'; a place with no pair within has none."""
    likeness = {"colour|hub/a|hub/b": 0.9, "colour|hub/a|lab/c": 0.5, "shape|hub/a|hub/b": 0.7,
                "shape|hub/a|lab/c": 0.6, "colour|camp/a|lab/c": 0.4, "shape|camp/a|lab/c": 0.4}
    problems = []
    gap = style.place_features(likeness, "hub")["style_gap"]
    if gap != round((0.9 - 0.5) - (0.7 - 0.6), 3):
        problems.append(f"the hub's gap is {gap}, not 0.3")
    if style.place_features(likeness, "camp")["style_gap"] is not None:
        problems.append("a place without a pair within has a gap")
    world = style.world_features(likeness)
    if world["colour"]["pairs"] != [1, 2] or world["style_gap"] != round((0.9 - 0.45) - (0.7 - 0.5), 3):
        problems.append(f"the world's readings are {world}")
    return problems


def the_renders_are_found_by_place():
    """model_renders reads <place>/models/<model>--made--now.png and nothing else."""
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        render(root / "hub/models/chair_1--made--now.png", (90, 90, 90))
        render(root / "hub/models/chair_1--parts--now.png", (90, 90, 90))
        found = style.model_renders(root)
    return [] if list(found) == ["hub"] and list(found["hub"]) == ["chair_1"] else [f"found {found}"]


def a_model_shown_twice_is_left_out():
    """The same render in two places is a copy, and its pair leaves the likeness; a different model stays."""
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        renders = {"hub": {"wrench": render(root / "hub.png", (90, 90, 90))},
                   "workshop": {"wrench": render(root / "workshop.png", (90, 90, 90)),
                                "vice": render(root / "vice.png", (90, 90, 90), box=(8, 56))}}
        copied = style.copies(renders)
    likeness = {"colour|hub/wrench|workshop/wrench": 1.0, "colour|hub/wrench|workshop/vice": 0.6}
    kept = style.without_copies(likeness, copied)
    return [] if list(kept) == ["colour|hub/wrench|workshop/vice"] else [f"copies {copied}, kept {kept}"]


def stains_read_as_marks():
    """A model with a stained surface reads more marks than one painted flat; one with no whole tile reads None."""
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        flat = style.marks(render(root / "flat.png", (120, 120, 120)))
        stained = render(root / "stained.png", (120, 120, 120))
        picture = np.asarray(Image.open(stained)).copy()
        picture[16:48:3, 16:48] = (60, 50, 40)
        Image.fromarray(picture).save(stained)
        marked = style.marks(stained)
        tiny = style.marks(render(root / "tiny.png", (120, 120, 120), box=(30, 34)))
    problems = []
    if not marked > flat:
        problems.append(f"the stained model reads {marked}, not above the flat one's {flat}")
    if tiny is not None:
        problems.append(f"a model with no whole tile reads {tiny}")
    return problems


CHECKS = (stains_read_as_marks, a_model_shown_twice_is_left_out, the_model_is_told_from_the_grey, lab_goes_back_to_linear, a_palette_colour_fits_at_any_brightness,
          pairs_cover_within_and_draw_across, the_style_gap_takes_the_shapes_away, the_renders_are_found_by_place)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
