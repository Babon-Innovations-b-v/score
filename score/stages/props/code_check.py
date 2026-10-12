"""The free pass on every place's code builds: each inventory row the parts check builds in code (`kind` code), its
packaged model ($PROPS_HOME/work/package/<place>/objects/<row>_1.gltf) held to the model checks that need no
close-up: thin and in proportion (tools/props/gates/model.py at the row's size) and, for a kind that stands square
(details.json `square`), lean (straight.py). The likeness check needs a close-up of each object and is not run here.

    .venv/bin/python -m score.stages.props.code_check <out.json>

Writes every model's measures and a summary per place: checked, passing, failing (by check), no model found. A build
that fails is a candidate for the prop route; one that passes stays (owner, 2026-10-12: no remake of the 92).
"""
import argparse
import json
import pathlib

import score.stages.props.likeness_row as likeness_row
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PACKAGES = PROPS_HOME / "work/package"


def package_of(inventory_path, inventory):
    """The place's package folder: by the inventory's name, else its `place` (prologue_flat packs as flat)."""
    for name in (inventory_path.stem, inventory.get("place"), inventory_path.stem.removeprefix("prologue_")):
        if name and (PACKAGES / name / "objects").exists():
            return PACKAGES / name / "objects"
    return None


def checked(place, row, model, square):
    """One code build's checks: model.py's (thin, proportion) and straight.py's for a square kind."""
    kind = f"{place}_{row['id']}"
    found = likeness_row.model_checks(model, row["size"], kind, kind in square)
    faults = [] if found["model_check"]["pass"] else ["thin or out of proportion"]
    faults += ["leans or warps"] if "straight" in found and not found["straight"]["pass"] else []
    return {**found, "faults": faults}


def place_check(inventory_path, square):
    """{row: record} of one place's code builds, and the place's summary."""
    inventory = json.loads(inventory_path.read_text())
    place, objects = inventory_path.stem, package_of(inventory_path, inventory)
    found = {}
    for row in inventory["rows"]:
        if row.get("kind") != "code":
            continue
        model = objects / f"{row['id']}_1.gltf" if objects else None
        found[row["id"]] = checked(place, row, model, square) if model and model.exists() else {"missing": True}
    measured = [entry for entry in found.values() if "missing" not in entry]
    summary = {"code rows": len(found), "checked": len(measured),
               "passing": sum(not entry["faults"] for entry in measured),
               "thin or out of proportion": sum("thin or out of proportion" in entry["faults"] for entry in measured),
               "leans or warps": sum("leans or warps" in entry["faults"] for entry in measured),
               "no model found": len(found) - len(measured)}
    return found, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    options = parser.parse_args()
    details = json.loads((REPO / "data/library/details.json").read_text())
    square = {kind for kind, entry in details.items() if isinstance(entry, dict) and entry.get("square")}
    places, summaries = {}, {}
    for path in sorted((REPO / "data/inventory").glob("*.json")):
        places[path.stem], summaries[path.stem] = place_check(path, square)
        print(path.stem, json.dumps(summaries[path.stem]), flush=True)
    options.out.write_text(json.dumps({"summary": summaries, "places": places}, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
