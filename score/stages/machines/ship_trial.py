"""The hangar ship by the prop route, as a trial in a world of its own (owner, 2026-10-12: every object goes the prop
route first, code only if its measured checks fail; the look is settled: a flat wedge shuttle, white panels on a dark
hull, as the hangar's concept K01 draws it).

    .venv/bin/python -m score.stages.machines.ship_trial prepare            # free
    .venv/bin/python -m score.stages.machines.ship_trial run                # paid: Pro, Pixal3D and the surface line
    .venv/bin/python -m score.stages.machines.ship_trial verdicts           # free

The ship is the hangar inventory's `ship` row (a machine row: its box the partition's proposals round the hull,
grounded by machines-boxes@hangar). `prepare` writes the trial's world data under
$PROPS_HOME/machines-trial/hangar/prop-first/ (compare.py's layout): a copy of the repository's data with prop data
naming only the ship and the hangar's surface data holding only the ship's take, so the hangar's own surface line
in world 1 never waits on it. `run` drives the hangar's line to the likeness row in that world's own store
(compare.run: the close-up row draws it with Pro from its box, Pixal3D makes the take, the surface line splits, paints
and bakes it, the likeness row judges it), so world 1's store stays untouched; start it in the background with
tools/props/cloud/detached.py -- .venv/bin/python -m score.stages.machines.ship_trial run. `verdicts` prints the
likeness row's record of the ship and its gates.
"""
import argparse
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.store import PROPS_HOME  # noqa: E402
import score.stages.props.compare as compare  # noqa: E402

PLACE, ORDER = "hangar", "prop-first"
FOLDER = PROPS_HOME / "machines-trial"
TAKE = "ship-m1"


def prepare():
    """The trial's world data: the repository's, with the ship's prop data and surface data."""
    compare.FOLDER = FOLDER
    data = compare.order_folder(PLACE, ORDER) / "data"
    if data.exists():
        raise SystemExit(f"{data} exists: the trial is prepared once (remove the folder to start it again)")
    shutil.copytree(REPO / "data", data)
    inventory = json.loads((data / "inventory" / f"{PLACE}.json").read_text())
    objects = {"ship": {"route": "prop", "take": TAKE}}
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
    parser.add_argument("command", choices=("prepare", "run", "verdicts"))
    options = parser.parse_args()
    compare.FOLDER = FOLDER
    if options.command == "run":
        compare.run(PLACE, ORDER, jobs=4)
    else:
        {"prepare": prepare, "verdicts": verdicts}[options.command]()


if __name__ == "__main__":
    main()
