"""Check the straightening step's rules on shapes whose right answer is obvious.

The step needs numpy and trimesh, which only the prop environment has. Run by the gate with the
system python, this hands itself to the prop environment when the box has one, and says it skipped
when it does not, so a box without the tool chain still passes. The cutter itself (CoACD) is not
run here: the checks are on the rules round it, which are ours.

Run: python3 tools/props/straighten_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("STRAIGHTEN_TEST_HANDED") != "1":
        os.environ["STRAIGHTEN_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
from denoise import denoise  # noqa: E402
from parts import adopt, choose, join, seen_parts  # noqa: E402
from straighten import named  # noqa: E402

_failures = []


def check(what, holds):
    print(("ok   " if holds else "FAIL ") + what)
    if not holds:
        _failures.append(what)


def box(low, high):
    return trimesh.creation.box(bounds=[low, high])


def halves_of_one_wall_join():
    halves = [box([0, 0, 0], [1, 1, 0.1]), box([1, 0, 0], [2, 1, 0.1])]
    hulls, chosen = join(halves, ["white", "white"])
    check("two halves of one flat wall join into one part", len(hulls) == 1)


def a_tank_off_a_drum_stays_its_own():
    drum = trimesh.creation.cylinder(radius=1.0, height=3.0)
    tank = trimesh.creation.icosphere(radius=0.6)
    tank.apply_translation([1.3, 0, -1.0])
    hulls, _ = join([drum, tank], ["gold", "gold"])
    check("a tank bulging off a drum is not swallowed into it", len(hulls) == 2)


def different_finishes_never_join():
    halves = [box([0, 0, 0], [1, 1, 0.1]), box([1, 0, 0], [2, 1, 0.1])]
    hulls, _ = join(halves, ["white", "solar"])
    check("parts of two finishes stay apart", len(hulls) == 2)


def solar_needs_a_clear_majority():
    check("a part only half dark is not solar", choose([[("solar", 0.5), ("silver", 0.5)]]) == ["silver"])
    check("a part mostly dark is solar", choose([[("solar", 0.8), ("silver", 0.2)]]) == ["solar"])


def a_stray_blob_takes_its_neighbours_finish():
    drum = box([0, 0, 0], [2, 2, 4])
    blob = box([2, 0.9, 1.9], [2.2, 1.1, 2.1])
    check("a small blob of solar on a gold drum turns gold", adopt([drum, blob], ["gold", "solar"]) == ["gold", "gold"])
    check("a small blob only partly solar turns gold", adopt([drum, blob], ["gold", "solar"], [1.0, 0.5]) == ["gold", "gold"])
    check("a small part clearly yellow stays yellow", adopt([drum, blob], ["gold", "yellow"], [1.0, 0.9]) == ["gold", "yellow"])


def ironing_flattens_a_wall_but_keeps_its_corner():
    wall = trimesh.creation.box(extents=[2, 2, 2], transform=None)
    wall = wall.subdivide().subdivide().subdivide()
    wall.merge_vertices()
    generator = np.random.default_rng(1)
    noisy = wall.copy()
    noisy.vertices = noisy.vertices + generator.normal(0, 0.02, noisy.vertices.shape)
    before = np.abs(np.abs(noisy.vertices).max(axis=1) - 1).mean()
    ironed = denoise(noisy.copy())
    after = np.abs(np.abs(ironed.vertices).max(axis=1) - 1).mean()
    check("ironing takes most of the wobble out of a box's walls", after < 0.5 * before)
    check("ironing keeps the box's size, so its corners are not rounded off",
          abs(np.ptp(ironed.vertices[:, 0]) - 2) < 0.1)


def a_part_no_face_belongs_to_goes():
    outer, inner, other = box([0, 0, 0], [2, 2, 2]), box([0.5, 0.5, 0.5], [1, 1, 1]), box([3, 0, 0], [4, 1, 1])
    kept, piece = seen_parts([outer, inner, other], np.array([0, 0, 2, 2]))
    check("a part hidden inside others is dropped", len(kept) == 2)
    check("faces point at the parts that are left", list(piece) == [0, 0, 1, 1])


def names_follow_colour_unless_told():
    colours = np.array([[0.86, 0.64, 0.24], [0.9, 0.91, 0.9]])
    group = np.array([0, 1])
    check("a gold group is named gold", named(colours, group, {})[0] == "gold")
    check("a name given by hand wins", named(colours, group, {1: "solar"})[1] == "solar")


halves_of_one_wall_join()
a_tank_off_a_drum_stays_its_own()
different_finishes_never_join()
solar_needs_a_clear_majority()
a_stray_blob_takes_its_neighbours_finish()
ironing_flattens_a_wall_but_keeps_its_corner()
a_part_no_face_belongs_to_goes()
names_follow_colour_unless_told()

if _failures:
    print(f"\n{len(_failures)} failed")
    sys.exit(1)
print("\nall good")
