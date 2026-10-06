"""The sorter: which kit pieces are built in code and which go to the picture-to-3D model (job robust-exp,
2026-10-06; the robust route's shape router).

    python3 tools/props/library/sorter.py data/kit/hub.json     # every kind of a kit layout, its class and route

A single-picture model's errors depend on the shape (the hub kit log, 2026-10-05): a thin panel comes out about as
deep as it is wide, a beam 3 to 10 times too thick, a frame or a porthole with its hole filled in. So every kind gets a
shape class before any picture is drawn, from its laid size and its name, and only solid objects go to Pixal3D:

    flat      a panel, plate, roof face or mat: its thinnest side under 18% of its longest    -> code
    slender   a beam, rail, strut, pipe or cable: its two thinner sides under 25% of its length -> code
    opening   a frame, surround, porthole or hatch: what matters is the hole                  -> code
    repeat    a grating, tray or tread: one small part many times                             -> code
    decal     a sign, label or notice: printed on a surface, never modelled                  -> decal
    chunky    everything else: valves, boxes, lamps, consoles                                -> model
A chunky kind of a known simple family (a hinge) is built in code too: it is cheaper and exact.
"""
import json
import pathlib
import sys

OPENING_WORDS = ("frame", "surround", "porthole", "doorway", "hatch_leaf", "window")
REPEAT_WORDS = ("grating", "tray", "tread", "ladder")
DECAL_WORDS = ("sign", "label", "notice", "placard", "sticker")
CODE_FAMILIES = ("hinge",)
FLAT_SHARE = 0.18
SLENDER_SHARE = 0.25


def shape_class(kind, size):
    """A kind's shape class from its name and its laid size (wide, tall, deep)."""
    name = kind.lower()
    if any(word in name for word in DECAL_WORDS):
        return "decal"
    if any(word in name for word in OPENING_WORDS):
        return "opening"
    if any(word in name for word in REPEAT_WORDS):
        return "repeat"
    smallest, middle, largest = sorted(float(value) for value in size)
    if largest <= 0:
        return "chunky"
    if smallest / largest < FLAT_SHARE and middle / largest >= SLENDER_SHARE:
        return "flat"
    if middle / largest < SLENDER_SHARE:
        return "slender"
    return "chunky"


def route(kind, size):
    """Where a kind is made: `code`, `model` or `decal`."""
    found = shape_class(kind, size)
    if found == "decal":
        return "decal"
    if found == "chunky" and not any(family in kind.lower() for family in CODE_FAMILIES):
        return "model"
    return "code"


def sorted_kinds(layout):
    """Every kind in a kit layout with its first laid size, class and route."""
    found = {}
    for laid in layout["pieces"]:
        if laid["kind"] not in found:
            found[laid["kind"]] = {"size": laid["size"], "class": shape_class(laid["kind"], laid["size"]),
                                   "route": route(laid["kind"], laid["size"])}
    return found


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    found = sorted_kinds(json.loads(pathlib.Path(sys.argv[1]).read_text()))
    for kind, entry in sorted(found.items(), key=lambda item: (item[1]["route"], item[0])):
        print(f"{entry['route']:6} {entry['class']:8} {kind} {entry['size']}")
    counts = {}
    for entry in found.values():
        counts[entry["route"]] = counts.get(entry["route"], 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
