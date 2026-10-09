"""The character maker: one entry point for a person or an animal, from a picture or a short description to a rigged,
clothed, textured, animated character (glTF and UsdSkel) with its crowd levels and its clips, made in the cloud.

    .venv/bin/python tools/characters/maker/make.py data/characters/makes/<name>.json [...] --who "<session>"
        [--classes gpu-24gb,gpu-80gb] [--dry-run]

Each spec (spec.py says what it holds) gets a make folder, ~/.farm-factory-motion/made/<name>/: `in/` is written here
(the spec with its files renamed to where they lie up there, the files, and what every person shares: the boots,
MakeHuman's eyes, the garment designs and the clips already made), and `out/` comes back from the machine. People go
to the person chain on rented cards (tools/props/cloud/characters.py, tools/characters/maker/chain.py), one machine a
person; animals go to the animal route (tools/characters/animals/). Nothing here loads a model.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))

import spec as specs  # noqa: E402

MOTION_HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))
MADE = MOTION_HOME / "made"
# What every person shares, kept on this box (the bible's workflow/bootstrap): the boots Hi3DGen made, MakeHuman's
# CC0 base mesh and eyes (the eyes are seated on each head from them), and the clips Kimodo made.
SHARED = {
    "work_boot.npz": MOTION_HOME / "look" / "work_boot.npz",
    "space_boot.npz": MOTION_HOME / "look" / "space_boot.npz",
    "makehuman/base.obj": MOTION_HOME / "rnd/garmentcode/round3/assets/base.obj",
    "makehuman/eyes/low-poly.mhclo": MOTION_HOME / "rnd/garmentcode/round3/assets/mh/eyes/low-poly/low-poly.mhclo",
    "makehuman/eyes/low-poly.obj": MOTION_HOME / "rnd/garmentcode/round3/assets/mh/eyes/low-poly/low-poly.obj",
}
MOTIONS = MOTION_HOME / "work" / "motions"


def bundle(spec):
    """Write the make folder's `in/` for a person: the spec as the machine reads it, its files and the shared ones.
    The make folder."""
    folder = MADE / spec["name"]
    inputs = folder / "in"
    if inputs.exists():
        shutil.rmtree(inputs)
    (inputs / "files").mkdir(parents=True)
    machine_spec = dict(spec)
    for name, path in specs.inputs_of(spec).items():
        target = inputs / "files" / f"{name}{path.suffix}"
        shutil.copy2(path, target)
        machine_spec[name] = f"in/files/{target.name}"
    machine_spec["references"] = [f"in/files/reference_{number}{pathlib.Path(path).suffix}"
                                  for number, path in enumerate(spec.get("references", []))]
    for name, path in SHARED.items():
        target = inputs / "shared" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    if MOTIONS.exists():
        shutil.copytree(MOTIONS, inputs / "motions", ignore=shutil.ignore_patterns("*.bvh"))
    (inputs / "spec.json").write_text(json.dumps(machine_spec, indent=1))
    return folder


def make_people(folders, who, classes, dry_run):
    """The people's chains on rented cards, one machine a person."""
    command = [sys.executable, str(REPO / "tools/props/cloud/characters.py"), *map(str, folders), "--who", who]
    if classes:
        command += ["--classes", classes]
    if dry_run:
        command.append("--dry-run")
    subprocess.run(command, check=True)


def make_animals(found, who, dry_run):
    """The animals through the animal route (tools/characters/animals/route.py)."""
    sys.path.insert(0, str(REPO / "tools/characters/animals"))
    import route
    for spec in found:
        route.make(spec, MADE / spec["name"], who=who, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("specs", nargs="+", type=pathlib.Path, help="data/characters/makes/<name>.json")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--classes", help="capability classes for the people's cards, comma separated")
    parser.add_argument("--dry-run", action="store_true", help="check, bundle and price, rent nothing")
    options = parser.parse_args()
    found = [specs.read(path) for path in options.specs]
    people = [bundle(spec) for spec in found if spec["kind"] == "person"]
    if people:
        make_people(people, options.who, options.classes, options.dry_run)
    animals = [spec for spec in found if spec["kind"] == "animal"]
    if animals:
        make_animals(animals, options.who, options.dry_run)


if __name__ == "__main__":
    main()
