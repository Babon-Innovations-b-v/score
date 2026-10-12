"""The hangar ship by the prop route, as a trial in a world of its own (owner, 2026-10-12: every object goes the prop
route first, code only if its measured checks fail; the look is settled: a flat wedge shuttle, white panels on a dark
hull, as the hangar's concept K01 draws it).

    .venv/bin/python -m score.stages.machines.ship_trial draw               # paid: Nano Banana Pro, about EUR 0.3
    .venv/bin/python -m score.stages.machines.ship_trial prepare            # free
    .venv/bin/python -m score.stages.machines.ship_trial run                # paid: Pixal3D and the surface line
    .venv/bin/python -m score.stages.machines.ship_trial verdicts           # free

`draw` draws the ship's close-up from its box on K01 as the closeup row does (closeup_row.draw_missing: the crop
alone, then with the whole concept beside, each kept only when the shape check's measured half passes). The box is
measured by hand on K01 (the one ship in the picture): no inventory row of the hangar has it, and the box gate needs
partition proposals the ship never had, so the drawn close-up is named in the prop data and taken as drawn.
`prepare` writes the trial's world data under $PROPS_HOME/machines-trial/hangar/prop-first/ (compare.py's layout): a
copy of the repository's data with a `ship` row in the hangar's inventory, prop data naming only the ship, and the
hangar's surface data with only the ship's take. `run` drives the hangar's line to the likeness row in that world's
own store (compare.run), so world 1's store and data stay untouched; start it in the background with
tools/props/cloud/detached.py -- .venv/bin/python -m score.stages.machines.ship_trial run. `verdicts` prints the likeness row's record of the
ship and its gates.
"""
import argparse
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.store import PROPS_HOME  # noqa: E402
import score.stages.props.closeup_row as closeup_row  # noqa: E402
import score.stages.props.compare as compare  # noqa: E402

PLACE, ORDER = "hangar", "prop-first"
FOLDER = PROPS_HOME / "machines-trial"
CLOSEUP = FOLDER / "closeup"
# Measured on K01 (2752 x 1536): the ship's hull from its nose spike to its engines and fins, with a small margin.
SHIP = {"id": "ship", "scene": PLACE, "view": "v1", "box": [950, 545, 1860, 1000], "kind": "generate",
        "anchor": "floor",
        "name": "the crew's Mars shuttle: a long flat wedge-shaped hull of white panels over a dark grey lower hull, a "
                "cluster of dark cockpit windows on its upper deck, a long nose spike, two round engine pods at the "
                "back and short swept fins, standing low on short landing legs",
        # x wide, z deep, y tall (the inventory's order): the plan's keep-out box, 12 x 31 m, and the cabin deck's 5.5 m
        # over its feet with the hull round it.
        "size": [12.0, 31.0, 6.0]}
TAKE = "ship-m1"


def concept():
    inventory = json.loads((REPO / "data/inventory" / f"{PLACE}.json").read_text())
    view = next(view for view in inventory["plan"]["views"] if view["id"] == SHIP["view"])
    return view["picture"].replace("WORK/", str(PROPS_HOME / "work") + "/")


def draw():
    """The ship's close-up by Pro, the first take whose measured faults are none, into CLOSEUP/ship.png."""
    row = {**SHIP, "words": SHIP["name"], "concept": concept()}
    found = closeup_row.draw_missing([row], CLOSEUP)
    passed = next((take for take, faults in found["ship"].items() if not faults), None)
    (CLOSEUP / "closeup.json").write_text(json.dumps({"takes": found, "passed": passed}, indent=1))
    if passed is None:
        raise SystemExit(f"no close-up of the ship passed the shape check: {found['ship']}")
    shutil.copy(CLOSEUP / passed / "ship.png", CLOSEUP / "ship.png")
    print(f"close-up: take {passed}, {CLOSEUP / 'ship.png'}")


def prepare():
    """The trial's world data: the repository's, with the ship's row, prop data and surface data."""
    if not (CLOSEUP / "ship.png").exists():
        raise SystemExit("draw the close-up first")
    compare.FOLDER = FOLDER
    data = compare.order_folder(PLACE, ORDER) / "data"
    if data.exists():
        raise SystemExit(f"{data} exists: the trial is prepared once (remove the folder to start it again)")
    shutil.copytree(REPO / "data", data)
    inventory = json.loads((data / "inventory" / f"{PLACE}.json").read_text())
    inventory["rows"].append(dict(SHIP))
    (data / "inventory" / f"{PLACE}.json").write_text(json.dumps(inventory, indent="\t") + "\n")
    objects = {"ship": {"route": "prop", "take": TAKE,
                        "closeup": "{home}/" + (CLOSEUP / "ship.png").relative_to(PROPS_HOME).as_posix()}}
    (data / "props").mkdir(exist_ok=True)
    (data / "props" / f"{PLACE}.json").write_text(json.dumps(
        {"place": PLACE, "order": ORDER, "objects": objects, "fallback": {}}, indent=1) + "\n")
    details = json.loads((data / "library/details.json").read_text())
    (data / "surfaces" / f"{PLACE}.json").write_text(
        json.dumps(compare.surface_record(PLACE, objects, inventory["rows"], details), indent=1) + "\n")
    print(f"prepared {data}")


def verdicts():
    """The likeness row's record of the ship and its gates' answers."""
    compare.FOLDER = FOLDER
    store, output, folder = compare.likeness_output(PLACE, ORDER)
    if folder is None:
        raise SystemExit("the likeness row has not run")
    print(json.dumps(json.loads((folder / "likeness.json").read_text())["objects"]["ship"], indent=1))
    for record in store.records(compare.NODE.format(place=PLACE))[-1:]:
        print(json.dumps(record, indent=1, default=str)[:4000])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("draw", "prepare", "run", "verdicts"))
    options = parser.parse_args()
    compare.FOLDER = FOLDER
    if options.command == "run":
        compare.run(PLACE, ORDER, jobs=4)
    else:
        {"draw": draw, "prepare": prepare, "verdicts": verdicts}[options.command]()


if __name__ == "__main__":
    main()
