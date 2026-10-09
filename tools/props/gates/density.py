"""The concept density check (the owner, 2026-10-08, on the lab: "lost a massive amount of detail" beside its concept):
a place's inventory must be an exhaustive partition of its picked concept. Run on the kit layout, before any spend.

    ~/.farm-factory-props/env/bin/python tools/props/gates/density.py <inventory.json> <kit layout.json>

The inventory lists every element seen in the concept, crop by crop (`concept_elements`: [{"element", "where",
"count", "row" or "dropped", and "part" for an element that is a part of its row's piece}]): each must name an inventory row, or say why it is dropped (a person, what stands outside
the shell); and the kit layout must lay each named row at least as often as the concept shows its elements. It fails on
an element with neither, a row that is not in the inventory, a row laid fewer times than the concept shows, and an
inventory with no element list at all. The after-install half of the rule (the built room drawn from the concept's own
camera beside the concept) is a picture, shown on the place's page.
"""
import collections
import json
import pathlib
import sys


def check(inventory, layout):
    """Every fault: [text]."""
    elements = inventory.get("concept_elements")
    if not elements:
        return ["no concept_elements: list every element the picked concept shows, crop by crop"]
    room = inventory.get("scene", "")
    rows = {row["id"]: row for row in inventory["rows"]}
    laid = collections.Counter(piece["kind"] for piece in layout["pieces"] if "part" not in piece)
    wanted, found = collections.Counter(), []
    for element in elements:
        if element.get("row"):
            if element["row"] not in rows:
                found.append(f"{element['element']}: its row {element['row']} is not in the inventory")
            if not element.get("part"):  # a part of its row's piece (a pod's control column) adds no piece
                wanted[element["row"]] += int(element.get("count", 1))
        elif not element.get("dropped"):
            found.append(f"{element['element']}: neither a row nor a reason it is dropped")
    for ident, count in wanted.items():
        have = laid.get(f"{room}_{ident}", 0)
        # A row a game node draws (an airlock's moving door leaf) or places as furniture is not in the kit's layout.
        drawn_by_game = ident in rows and (rows[ident].get("made_as") == "prop"
                                           or rows[ident].get("made") == "made by the route")
        if ident in rows and have < count and not drawn_by_game:
            found.append(f"{ident}: the concept shows {count}, the layout lays {have}")
    return found


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    inventory = json.loads(pathlib.Path(sys.argv[1]).read_text())
    found = check(inventory, json.loads(pathlib.Path(sys.argv[2]).read_text()))
    for fault in found:
        print("FAIL", fault)
    elements = inventory.get("concept_elements", [])
    print(f"{len(elements)} concept elements, {sum(1 for element in elements if element.get('dropped'))} dropped, "
          f"{len(found)} faults")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
