"""The character maker: one entry point for a person or an animal, from a picture or a short description to a rigged,
clothed, textured, animated character (glTF and UsdSkel) with its crowd levels and its clips, made in the cloud.

    .venv/bin/python tools/characters/maker/make.py data/people/specs/<name>.json [...] --who "<session>"
        [--dry-run] [--experimental]

A person spec ("route": "prop") goes to the prop route (prop_person.py: Pixal3D's mesh with SOMA-X's skeleton fitted
inside it, made on rented cards); an animal to the animal route (tools/characters/animals/), each in its make folder
~/.farm-factory-motion/made/<name>/. The shipped person chain (GarmentCode's drapes on a body read off an A-pose
picture) was retired with its garment designs (owner, 2026-10-21: all old stuff is retired): a person spec on no
route is refused. Nothing here loads a model.

Experimental, so refused unless asked for (docs/bible.md, architecture/experimental): the prop route and the animal
route run only with --experimental. Every refusal is said before anything is rented.
"""
import argparse
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))

import spec as specs  # noqa: E402

MOTION_HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))
MADE = MOTION_HOME / "made"
# The routes that run only with --experimental: each the fault it is for, and why it is not proven yet.
EXPERIMENTAL_ROUTES = {
    "prop": ("the prop route (#5, bloated clothes on SOMA-made people): the player fails tucks and pokes, Nev is not "
             "made"),
    "animal": "the animal route (#1, places with no animals): no fish swims in any place yet",
}


def route_of(spec):
    """The route a spec takes: "prop", "animal" or "person" (the retired shipped person chain)."""
    if spec["kind"] == "animal":
        return "animal"
    return "prop" if spec.get("route") == "prop" else "person"


def refusals(found, experimental):
    """Why the specs in `found` may not be made as asked, one line a spec: an experimental route without
    `experimental`, a person on the retired shipped chain. Empty when all may."""
    lines = []
    for spec in found:
        route = route_of(spec)
        if route in EXPERIMENTAL_ROUTES and not experimental:
            lines.append(f"{spec['name']}: {EXPERIMENTAL_ROUTES[route]}; experimental, so only with --experimental")
        if route == "person":
            lines.append(f"{spec['name']}: the shipped person chain and its garment drapes are retired "
                         "(2026-10-21): a person is made on the prop route (\"route\": \"prop\")")
    return lines


def make_prop_person(path, who, dry_run):
    """A person on the prop route (prop_person.py), every stage in turn."""
    command = [sys.executable, str(HERE / "prop_person.py"), str(path), "--who", who, "--experimental"]
    subprocess.run(command + (["--dry-run"] if dry_run else []), check=True)


def make_animals(found, who, dry_run):
    """The animals through the animal route (tools/characters/animals/route.py)."""
    sys.path.insert(0, str(REPO / "tools/characters/animals"))
    import route
    for spec in found:
        route.make(spec, MADE / spec["name"], who=who, dry_run=dry_run, experimental=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("specs", nargs="+", type=pathlib.Path, help="data/people/specs/<name>.json")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check, bundle and price, rent nothing")
    parser.add_argument("--experimental", action="store_true", help="allow the prop and animal routes")
    options = parser.parse_args()
    found = [specs.read(path) for path in options.specs]
    refused = refusals(found, options.experimental)
    if refused:
        raise SystemExit("refused:\n" + "\n".join(refused))
    for spec, path in zip(found, options.specs):
        if spec["kind"] == "person" and spec.get("route") == "prop":
            make_prop_person(path, options.who, options.dry_run)
    animals = [spec for spec in found if spec["kind"] == "animal"]
    if animals:
        make_animals(animals, options.who, options.dry_run)


if __name__ == "__main__":
    main()
