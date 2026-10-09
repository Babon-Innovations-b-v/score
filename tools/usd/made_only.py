"""The made-only check on a place's OpenUSD stage: every visible mesh was made by the framework, and says how.

    .venv/bin/python tools/usd/made_only.py <stage.usda> [<stage.usda> ...]

The game's made-only check (in the engine, never waived) found 26 old models still standing in a room after every
other check had passed. This is the same rule on the stage, read as composed: every mesh drawn (judged as the
placeholder check judges what is drawn: not a guide, not hidden, not another place's stage or the cast) must sit
under something that says what made it:

    score:model    a made model (an object of the inventory, its model from the prop pipeline or a code builder) or
                   a world's own model placed as a fixture
    score:builder  a mesh one of the scene record's code builders drew (builders.py)
    score:kind     the ground, the backdrop, the sky and the other things the stage's own writers mark

A mesh with none of these came from nowhere the framework knows, and fails. An object of the inventory whose model did
not load (it has no `geo` under it: its asset file is missing) fails too, since the scene then lacks a made piece.
Prints one line a fault and exits 1 when there is any.
"""
import argparse
import pathlib
import sys

from pxr import Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import placeholders  # noqa: E402

MADE_BY = ("score:model", "score:builder", "score:kind")


def made_by(prim):
    """What made a prim, from itself or the nearest prim above it that says: (attribute, value), or None."""
    while prim and prim.GetPath() != prim.GetPath().absoluteRootPath:
        for name in MADE_BY:
            found = prim.GetAttribute(name)
            if found and found.HasValue() and found.Get():
                return name, found.Get()
        prim = prim.GetParent()
    return None


def unmade_meshes(stage):
    """Every drawn mesh with nothing above it saying what made it."""
    return [{"prim": str(prim.GetPath()), "why": "a mesh nothing says the framework made (no score:model, "
                                                  "score:builder or score:kind on it or above it)"}
            for prim in placeholders.judged_prims(stage) if prim.IsA(UsdGeom.Gprim) and made_by(prim) is None]


def unloaded_objects(stage):
    """Every object of the inventory whose model did not load: no `geo` under it."""
    root = stage.GetDefaultPrim().GetChild("Objects")
    if not root.IsValid():
        return []
    return [{"prim": str(prim.GetPath()), "why": f"its model {prim.GetAttribute('score:model').Get()} did not load "
                                                  "(no geometry under it: the asset file is missing)"}
            for prim in Usd.PrimRange(root) if prim.HasAttribute("score:row") and not prim.GetChild("geo").IsValid()]


def check(stage_path):
    """Every fault on the stage: [{"prim", "why"}], empty when everything drawn was made by the framework."""
    stage = Usd.Stage.Open(str(stage_path))
    return unmade_meshes(stage) + unloaded_objects(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stages", type=pathlib.Path, nargs="+")
    options = parser.parse_args()
    found = {str(path): check(path) for path in options.stages}
    for path, faults in found.items():
        for fault in faults:
            print(f"{path}: {fault['prim']}: {fault['why']}")
        print(f"{path}: {'made only' if not faults else f'{len(faults)} not made by the framework'}")
    sys.exit(1 if any(found.values()) else 0)


if __name__ == "__main__":
    main()
