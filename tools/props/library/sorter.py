"""The sorter: which kit pieces are built in code and which are made by the prop pipeline (job robust-exp,
2026-10-06; made an allow-list in hub round four, 2026-10-07; the pipeline first for every kind, #19, 2026-10-20).

    python3 tools/props/library/sorter.py data/kit/hub.json     # every kind of a kit layout, its class and route

The owner's rule (2026-10-20, #19, #41): every object and every shell piece goes through the prop pipeline, the shared
loop (score/stages/shapes_first); code builds a kind only when the pipeline failed on that object, named in the
pipeline-failure record (data/library/pipeline_failures.json: the failure, where it was measured and when), or as one
of the owner's named exceptions there (the hangar ship's hull, engines and thrusters from his plan v7). Nothing routes
to code by default: neither plainness (PLAIN) nor a fitting's parts check (fittings.json) sends a kind there any more.

    code     a kind the pipeline-failure record names
    model    everything else

A scene inventory row is routed by its kind's route (row_route), never by its own `kind` (`code` or `generate`). Not
built yet: only the hand-in record's objects (data/props) reach the loop; no shell-section layer hands it kit kinds, so
a model-routed kit kind is a gap in route.py's and place_route.py's plans (GAP) unless an old labelled take of it is
stored, which route.py still makes by the old prop route (labels.py, inside/make_chunky.py).

PLAIN stays a fact about a kind (plain plates, pipes and trims have no parts of their own to show), and method B's
parts check (fittings.json, `missing_parts`) stays the check a code fallback's build must pass (route.py layout), until
the builders and the sorter go per #19's clean-up map. The shape class (flat, slender, opening, repeat, chunky) is a
fact about a kind's box: it says how a model is made and judged (gates/model.py), never whether it is made.
"""
import json
import pathlib
import sys

OPENING_WORDS = ("frame", "surround", "porthole", "doorway", "hatch_leaf", "window")
REPEAT_WORDS = ("grating", "tray", "tread", "ladder")
DECAL_WORDS = ("sign", "label", "notice", "placard", "sticker")
FLAT_SHARE = 0.18
SLENDER_SHARE = 0.25
# The plain kinds (the owner, 2026-10-07), by their name without the room's prefix: plain plates and panels, pipes and
# cables, and trims (beams, ribs, struts, skirting, cornices, posts, stringers), none with parts of its own. Plainness
# routes nothing since #19 (2026-10-20): a plain kind goes through the pipeline like any other.
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
    # the street's blocks up close (2026-10-10): their roofs' decks and parapets with their coping, which were the
    # scene record's plain whitewash boxes
    "block_roof", "parapet",
    # the ship's rooms (the overseer, 2026-10-14, by the paper's rule): the windows' plain frames and panes, plain
    # light strips and panels, the floor grate, the frame ribs, and the command spot's dais with its step
    "window_frame", "window_pane", "edge_light_strip", "dash_light_bar", "ceiling_light_panel", "floor_grate",
    "frame_rib", "command_platform", "platform_step",
))


FITTINGS = pathlib.Path(__file__).resolve().parents[3] / "data/library/fittings.json"
FAILURES = pathlib.Path(__file__).resolve().parents[3] / "data/library/pipeline_failures.json"
# Why a model-routed kind with no take is left out of a plan: a gap the plan names, never a code build (#41).
GAP = "no take yet: the shared loop has not made this model (#41)"
# The share of a part's front the room must see for the part to count as shown (a slat buried in its plate reads 0).
SEEN_AT_LEAST = 0.1


def fittings(path=FITTINGS):
    """Method B's room fittings, the parts check a code fallback's build is held to: {name: {"closeup", "parts",
    "built"}}."""
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


def fallback_parts_missing(kind, found=None):
    """The parts a code fallback's last build does not show (missing_parts) by its fitting's entry in fittings.json;
    none for a fallback fittings.json does not list (a plain piece, or a named exception with no close-up parts)."""
    entry = (fittings() if found is None else found).get(own_name(kind))
    return [] if entry is None else missing_parts(entry)


def failures(path=FAILURES):
    """The pipeline-failure record: {kind: {"failure", "evidence", "on"}}, the only kinds built in code."""
    return json.loads(pathlib.Path(path).read_text())["kinds"]


def route(kind, found=None):
    """Where a kind is made: `code` only when the pipeline-failure record names its failure, `model` (the prop
    pipeline, the shared loop) for every other."""
    return "code" if kind in (failures() if found is None else found) else "model"


def row_route(scene, row):
    """Where a scene inventory row is made: its kind's route (route), whatever the row's own `kind` says (`code` or
    `generate` route nothing since #19); `mechanic` for a mechanic row, made on its own line."""
    return "mechanic" if row.get("kind") == "mechanic" else route(f"{scene}_{row['id']}")


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
