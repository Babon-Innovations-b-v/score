"""The sorter: which kit pieces are built in code and which are made by the prop pipeline (job robust-exp,
2026-10-06; made an allow-list in hub round four, 2026-10-07).

    python3 tools/props/library/sorter.py data/kit/hub.json     # every kind of a kit layout, its class and route

The owner's ruling (2026-10-07): code may build only plain plates, pipes and trims; everything with detail (furniture,
lockers, desks, tool boards, machines, fittings with parts) is made by the prop pipeline (Pixal3D from its close-up,
made solid, library surfaces with the picture's own detail over them). So the route is an allow-list by name, never a
guess from a piece's proportions: round three's proportion routing sent a tool board, a hatch leaf and a hand wheel
to code because their boxes were thin, and a hard-coded furniture table sent seven pieces of furniture to code with
no check at all, and the room lost most of its detail (the detail-loss diagnosis, 2026-10-07).

    code     a kind named in PLAIN (plates, pipes, trims), or a room fitting whose code build shows every part its
             close-up has (method B, below)
    model    everything else

Method B (hub round five, 2026-10-07, a test for the owner's pick: "we need a more robust method of deciding what to
make in code and what via the prop pipeline"): a kind is routed by the job it does in the room. The room's shell and
the fittings that repeat or join it (wall plates, the porthole's frame, door leaves and frames, vent covers,
gratings, hatches, ducts, lamp housings, trims) are built in code with library surfaces, so every copy matches the
room exactly; the objects that stand in the room (furniture, equipment, tools, machines) go through the pipeline. A
fitting may go to code only if its code build shows every part its close-up has: data/library/fittings.json lists,
per fitting, the parts its clean close-up shows and, from the last build (pieces.parts_seen, written back by
`route.py fittings`), how much of each part the room can see. A part missing or under SEEN_AT LEAST fails the
fitting, and a failing fitting goes to the pipeline.

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
    # under the floor: an open box of plates under a set-in fitting's opening (hub round four)
    "under_floor_box",
    # a walkway tube's curved hull plates (and the plain rails along its glass band) and its hoops, plain bands of its
    # section (modules batch one, 2026-10-07: for the owner's nod, as under_floor_box was)
    "hull_plate", "hoop",
    # Earth's street (world 1, 2026-10-07, the owner's ruling read as written: plain plates and trims): road and
    # pavement slabs, kerbs, a facade's render plates (openings cut, nothing set on them), its floor bands, drainpipes
    "ground_asphalt", "ground_paving", "kerb_stone", "render_upper", "render_lower", "render_shop", "facade_band",
    "drainpipe",
    # Earth's square and launch view (world 1): the square's paving and terraces, the roads, the promenade and its
    # rail, the launch pad's apron, the lanterns' cable, the bay's balcony slabs and rails, the far blocks' plates
    "far_paving", "far_terrace", "far_road", "far_promenade", "far_pad", "far_cable", "far_promenade_rail",
    "bay_balcony_slab", "bay_balcony_rail", "far_render_upper", "far_render_lower", "far_render_shop", "far_facade_band",
    "far_drainpipe",
    # the street's density pass: its yellow lines, the pipes and cables along its faces, the harbour wall and fence
    "road_line", "facade_pipe", "end_wall", "end_fence",
))


FITTINGS = pathlib.Path(__file__).resolve().parents[3] / "data/library/fittings.json"
# The share of a part's front the room must see for the part to count as shown (a slat buried in its plate reads 0).
SEEN_AT_LEAST = 0.1


def fittings(path=FITTINGS):
    """The room fittings method B may build in code: {name: {"closeup", "parts", "built"}}."""
    return json.loads(pathlib.Path(path).read_text())["fittings"]


def missing_parts(entry):
    """The parts a fitting's close-up shows that its last code build does not (missing, or seen under
    SEEN_AT_LEAST), and its prints that do not lie on a clear flat area (round six: never over a vent, a handle or
    a tool; pieces.prints_off); every part when it was never built."""
    built = entry.get("built") or {}
    return ([part for part in entry["parts"] if built.get(part, 0.0) < SEEN_AT_LEAST]
            + [f"print off a clear area: {off}" for off in entry.get("prints_off", [])])


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


def planned_route(kind):
    """Where a kind is planned to be made: `code` for a plain kind and for every listed fitting (its code build is
    what its check reads; a fitting that then fails is held back by route.py's layout and goes to the pipeline),
    `model` for every other."""
    return "code" if own_name(kind) in PLAIN or kind.split("_", 1)[-1] in fittings() else "model"


def route(kind, found=None):
    """Where a kind is made: `code` for a plain kind on the allow-list or a room fitting whose code build shows every
    part its close-up has (method B), `model` (the prop pipeline) for every other."""
    name = own_name(kind)
    if name in PLAIN:
        return "code"
    entry = (fittings() if found is None else found).get(kind.split("_", 1)[-1])
    return "code" if entry is not None and not missing_parts(entry) else "model"


# Fittings that belong in a floor or a wall (vents, grates, drains, hatches, mats, light strips) are set into their host
# piece, flush, in an opening the layout cuts (the owner, 2026-10-06: the hub's floor grates and strips sat on the floor
# "like stickers"): kind -> the host kind it is set into. Their size is what their function needs, not what makes them
# stand out; one with nothing to do where it would lie is dropped, with the reason.
SET_IN = {"floor_grating": "ring_floor_plate", "floor_access_hatch": "ring_floor_plate", "tread_mat": "ring_floor_plate"}
DROPPED = {
    "floor_cable_cover": "a cable cover lies over a cable crossing the floor; the hub's cables run in the roof's trays",
    "pit_lip_segment": "the strips stood where the pit's rail was footed; the rail is gone (the owner, 2026-10-06)",
}


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
