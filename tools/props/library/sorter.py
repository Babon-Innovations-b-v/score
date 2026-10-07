"""The sorter: which kit pieces are built in code and which are made by the prop pipeline (job robust-exp,
2026-10-06; made an allow-list in hub round four, 2026-10-07).

    python3 tools/props/library/sorter.py data/kit/hub.json     # every kind of a kit layout, its class and route

The owner's ruling (2026-10-07): code may build only plain plates, pipes and trims; everything with detail (furniture,
lockers, desks, tool boards, machines, fittings with parts) is made by the prop pipeline (Pixal3D from its close-up,
made solid, library surfaces with the picture's own detail over them). So the route is an allow-list by name, never a
guess from a piece's proportions: round three's proportion routing sent a tool board, a hatch leaf and a hand wheel
to code because their boxes were thin, and a hard-coded furniture table sent seven pieces of furniture to code with
no check at all, and the room lost most of its detail (the detail-loss diagnosis, 2026-10-07).

    code     a kind named in PLAIN (plates, pipes, trims)
    model    everything else

The shape class (flat, slender, opening, repeat, chunky) stays as a fact about a kind's box: it says how a model is
made and judged (gates/model.py), never whether it is made.
"""
import json
import pathlib
import sys

OPENING_WORDS = ("frame", "surround", "porthole", "doorway", "hatch_leaf", "window")
REPEAT_WORDS = ("grating", "tray", "tread", "ladder")
DECAL_WORDS = ("sign", "label", "notice", "placard", "sticker")
FLAT_SHARE = 0.18
SLENDER_SHARE = 0.25
# The only kinds code may build (the owner, 2026-10-07), by their name without the room's prefix: plain plates and
# panels, pipes and cables, and trims (beams, ribs, struts, skirting, cornices, posts, stringers), none with parts of
# its own. A kind joins only by the owner's word that it is plain.
PLAIN = frozenset((
    # plates
    "wall_lower_plain", "wall_upper_plain", "ring_floor_plate", "pit_floor_plate", "pit_wall_panel", "roof_face_panel",
    "machine_bay_plate", "backer",
    # pipes and cables
    "pipe_straight", "cable_bundle", "cable_drop",
    # trims
    "wall_skirting", "wall_cornice", "wall_corner_post", "lattice_ring_rib", "lattice_hip_rib", "lattice_diamond_strut",
    "lattice_node_plate", "stair_stringer",
))


def own_name(kind):
    """A kind's name without its room's prefix (`hub_wall_lower_plain` -> `wall_lower_plain`); a bare name as it is."""
    return kind if kind in PLAIN else kind.split("_", 1)[-1]


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


def route(kind):
    """Where a kind is made: `code` for a plain kind on the allow-list, `model` (the prop pipeline) for every other."""
    return "code" if own_name(kind) in PLAIN else "model"


# Fittings that belong in a floor or a wall (vents, grates, drains, hatches, mats, light strips) are set into their host
# piece, flush, in an opening the layout cuts (the owner, 2026-10-06: the hub's floor grates and strips sat on the floor
# "like stickers"): kind -> the host kind it is set into. Their size is what their function needs, not what makes them
# stand out; one with nothing to do where it would lie is dropped, with the reason.
SET_IN = {"floor_grating": "ring_floor_plate", "floor_access_hatch": "ring_floor_plate", "tread_mat": "ring_floor_plate",
          "door_strip_lamp": "hatch_wall_surround"}
SET_IN_SIZES = {"floor_grating": (0.6, 0.6), "floor_access_hatch": (0.6, 0.6)}
DROPPED = {
    "floor_cable_cover": "a cable cover lies over a cable crossing the floor; the hub's cables run in the roof's trays",
    "pit_lip_segment": "the strips stood where the pit's rail was footed; the rail is gone (the owner, 2026-10-06)",
}


def set_in_size(kind, size):
    """A set-in fitting's size (wide, long, thick): its function's, as wide and long as SET_IN_SIZES says."""
    if kind in SET_IN_SIZES:
        wide, long = SET_IN_SIZES[kind]
        return (wide, long, size[2])
    return tuple(size)


def dropped(kind):
    """Why a kind is left out of a room, or None when it stays."""
    return DROPPED.get(kind)


def sorted_kinds(layout):
    """Every kind in a kit layout with its first laid size, class and route."""
    found = {}
    for laid in layout["pieces"]:
        if laid["kind"] not in found:
            found[laid["kind"]] = {"size": laid["size"], "class": shape_class(laid["kind"], laid["size"]),
                                   "route": route(laid["kind"])}
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
