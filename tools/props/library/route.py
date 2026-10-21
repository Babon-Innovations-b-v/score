"""The route's sizes and densities a model is baked at: what the surface line's bake job
(score/stages/surfaces/bake_job.py) and the props' compare read.

    route.foot_of(high)          how high a laid piece's foot stands over its floor
    route.faces_for(size)        a generated model's triangle budget at its size
    route.made_size(size)        a laid size rounded to the step two pieces of a kind share a model at
    route.density_of(entry)      a model's texels a metre (NEAR, FAR, DISTANT by its own name)

The kit room route that used these (`plan`, `layout`, `install`, `late-plan`, `late-lay`, `fittings`, `precheck`: a
kit layout's models sorted, made in shared picture sets and laid into data/kit/<room>.json, its screens' and lamps'
models written) went with the old kits on
2026-10-21 (the owner: "remove all old, all old stuff is retired"); every scene's shell is laid from its locked plan
(score/stages/earth_seed/design_shell.py).
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
DETAILS = REPO / "data/library/details.json"
# Composites split into one model per real-world object (round six): a parent kind's children, each its own kind
# standing where the parent leaves room for it, in the parent's kit frame.
COMPOSITES = REPO / "data/library/composites.json"
# Texels a metre (the normal map's; colour gets half), by how near the player's hands a piece comes (the coordinator,
# hub round four): NEAR within arm's reach of the walkway or the pit floor, FAR for the roof and the high walls; a
# generated piece is near when its middle stands under REACH_HIGH above the walkway.
NEAR = 1024
FAR = 512
# Scenery seen only from afar (the prologue build, 2026-10-07: the square, the launch pad and the city round them are
# 10 to 300 m from the balcony): a kind whose own name starts with DISTANT_PREFIX takes DISTANT texels a metre.
DISTANT = 128
DISTANT_PREFIX = "far_"
REACH_HIGH = 1.8
PIT_DEEP = 0.9  # the hub's pit floor under its walkway (the old hub kit's)
CHUNKY_FACES = 19000  # triangles: a prop's furniture budget is 20,000 (asset_check), its detail parts take the rest
# A smaller object gets fewer (round six: 26 tools of 19,000 each put half a million triangles on one tool board): the
# budget by the square of its largest side against a metre, never under SMALLEST_FACES (the owner's check on the tools
# up close: at 800 to 1,700 the pliers' outline went angular; at 5,000 they match the 19,000 model, baked alike).
SMALLEST_FACES = 5000
# A room piece's solid wall, named in its job so make_chunky's two-voxel default (for jobs that name none) never
# reaches it: the rooms' pieces were baked and accepted at 5 mm (hub round six), and thicker their thin sheets read as
# slabs (place_route's THIN_WALLED). A kind closed thicker names its own in details.json `wall` (thin rails and
# hooks, so the solid copy keeps a 3 mm wall).
ROOM_WALL = 0.005
SIZE_STEP = 0.005  # two pieces of a kind within this of each other's size share a model


def own_name(kind):
    """A kind's name without its room's prefix (`hub_wall_lower_plain` -> `wall_lower_plain`)."""
    return kind.split("_", 1)[1]


def made_size(size):
    return tuple(round(round(value / SIZE_STEP) * SIZE_STEP, 4) for value in size)


def density_of(entry):
    """A generated piece's texels a metre: DISTANT for scenery seen only from afar, else NEAR or FAR by its reach."""
    if own_name(entry["kind"]).startswith(DISTANT_PREFIX):
        return DISTANT
    return NEAR if entry.get("near", True) else FAR


def foot_of(high):
    """How high a foot at `high` (over the walkway) stands over the floor it stands on: the walkway's, or the pit's
    PIT_DEEP below it (the kick wear, method B)."""
    return round(max(0.0, high + PIT_DEEP if high < -0.05 else high), 3)


def faces_for(size):
    """A generated piece's triangle budget by its size: CHUNKY_FACES for a metre or more, by the square of its largest
    side below that, never under SMALLEST_FACES."""
    return int(max(SMALLEST_FACES, min(CHUNKY_FACES, CHUNKY_FACES * max(size) ** 2)))


