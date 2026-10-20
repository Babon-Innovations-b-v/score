"""The terrain adapter's hand-in (#27, #41; CONTEXT.md "layer adapter", "shapes first"): an outdoor place's detail
areas, split free from its plan, its concept and its rough model registered to the plan (rough-align, the shared
loop's), and handed to the shared loop as rows of the terrain layer, which makes them into models (close-up, Pixal3D,
the finish route, the bake) like any other; the adapter's one after-step (join.py) lays them into the ground.

A detail area is a landform of the place's ground plan (data/ground/plan/<body>.json: its named craters and its
`landforms`, each built here by the terrain's own builder on a coarse grid) whose footprint reaches into the place's
fine patch (its own box grown by outside.NEAR_MARGIN, the ground the place draws finely); its part inside the patch is
the area: its middle and size in the place's frame (through the place's copied ground record, tools/usd/ground.py),
its relief, and the close-up's words from the plan's own description and the concept's ground elements (the plan's
`elements` whose drop sends them to the made ground). The registered rough model (the concept made whole, in the
place's metres) is read over each area: the share of its footprint the rough model covers and the relief the rough
model shows there (`rough`), which the close-up's words carry. The plan says where and how big, the concept and its
rough model what is there, as an outside shell's split takes its rooms from its concept and its outline from its plan
drawn to its rough model (shell_split). Areas are landed only from a registered rough model: the loop splits a place's
parts once its rough model stands in its plan.

    found = areas.detail_areas(place, data, rough)   # [{id, kind, landform, words, plan_at, at, size, rough}]
    rough = areas.rough_points(<rough-align output>) # the aligned rough model's points in the place's frame
    rows = areas.inventory_rows(place, found)        # the scene inventory rows (prop route, anchor ground)
    python -m score.stages.terrain.areas write <place> [<rough-align output>]
        # lands them (default: the accepted rough-align@<place>): inventory rows, terrain-layer objects in the
        # place's hand-in record, surface takes

A place whose body has no copied ground record (data/ground/<body>.json) gets no areas: none can be placed.
"""
import json
import pathlib
import re
import sys

import numpy as np

from score.stages.terrain import landforms, outside, plan as ground_plan
import score.stages.shapes_first.align as align

REPO = pathlib.Path(__file__).resolve().parents[3]
LAYER = "terrain"  # the layer its rows carry in the place's hand-in record (shapes_first.ADAPTERS)
# The coarse plan grid the footprints are read on: one point a metre on a 260 m plan.
GRID_STEP = 1.0
# A landform's footprint: where it moves the ground by at least this share of its own largest rise or fall.
FOOT_SHARE = 0.05
# A crater's footprint is its bowl and rim: where landforms.crater_profile erases what lay there.
# The words a plan's dropped concept element names when the made ground draws it.
GROUND_WORDS = re.compile(r"made ground|ground step|terrain")


def read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.is_file() else None


def body_plan(place, data):
    """(the ground plan that seats the place, its file's stem), or (None, None)."""
    for path in sorted((pathlib.Path(data) / "ground/plan").glob("*.json")):
        found = json.loads(path.read_text())
        if place in found.get("seats", {}):
            return found, path.stem
    return None, None


def laid_ground(place, data):
    """The place's tools/usd/ground.Ground from its copied ground record, or None when it has none."""
    sys.path.insert(0, str(REPO / "tools/usd"))  # already on the path by the assembly stage's import
    import ground as grounds
    kit = read(pathlib.Path(data) / "kit" / f"{place}.json") or {}
    return grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))


def patch_box(place, data, laid):
    """The place's fine patch as a box of the plan's flat numbers: its own box (terrain gates.footprint) grown by
    outside.NEAR_MARGIN, mapped onto the plan (ground.plan_box)."""
    from score.stages.terrain import gates
    import ground as grounds
    scene = read(pathlib.Path(data) / "scene" / f"{place}.json") or {}
    low, high = gates.footprint(scene, read(pathlib.Path(data) / "kit" / f"{place}.json"))
    return grounds.plan_box(laid, low - outside.NEAR_MARGIN, high + outside.NEAR_MARGIN)


def plan_grid(record):
    side = float(record["side"])
    return landforms.Grid(side, int(round(side / GRID_STEP)) + 1)


def crater_footprints(record, grid):
    """{name: (kind words, heights, footprint)} of the plan's named craters on the grid."""
    found = {}
    for crater in record.get("craters") or []:
        height, erase = landforms.crater_profile(crater, grid, grid.x, grid.z)
        found[f"crater {crater['name']}"] = (f"crater {crater['name']}, {crater['kind']}", height, erase > 0)
    return found


def landform_footprints(record, grid):
    """{name: (kind words, heights, footprint)} of the plan's landforms its shape steps lay, each by its own builder."""
    found = {}
    for step in record.get("shape", []):
        if step.get("op") not in ("add", "over") or step.get("name") not in (record.get("landforms") or {}):
            continue
        spec = record["landforms"][step["name"]]
        height = ground_plan.LANDFORMS[step["kind"]](grid, spec)
        peak = float(np.abs(height).max())
        found[spec.get("name", step["name"])] = (f"{step['kind']}, {spec.get('name', step['name'])}", height,
                                                 np.abs(height) >= FOOT_SHARE * peak if peak else height != 0)
    return found


def in_box(grid, box):
    low, high = box
    return (grid.x >= low[0]) & (grid.x <= high[0]) & (grid.z >= low[1]) & (grid.z <= high[1])


def place_points(laid, plan_x, plan_z):
    """Points of the plan (flat numbers) in the place's frame, on the plan's ground there."""
    directions = laid.plan[1] * laid.radius + np.outer(plan_x, laid.plan[0]) + np.outer(plan_z, laid.plan[2])
    directions = directions / np.linalg.norm(directions, axis=1, keepdims=True)
    height, _ = laid.height(directions)
    return laid.in_place_frame(directions * (laid.radius + height)[:, None])


def area_id(name):
    return "ground_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def concept_words(place, data):
    """The concept's elements the place's plan sends to the made ground (their own words), for the close-ups."""
    found = read(pathlib.Path(data) / "plans" / f"{place}.json") or {}
    return [entry["element"] for entry in found.get("elements") or []
            if "drop" in entry and GROUND_WORDS.search(entry["drop"])]


def rough_points(registration):
    """The registered rough model's points in the place's frame, metres (rough-align's aligned.glb: its root node
    carries the registration); ValueError for a rough model the registration refused."""
    import trimesh
    registration = pathlib.Path(registration)
    found = json.loads((registration / align.REGISTRATION).read_text())
    if found["unregistrable"]:
        raise ValueError(f"{found['place']}'s rough model is not registered: " + "; ".join(found["unregistrable"]))
    return np.asarray(trimesh.load(registration / align.ALIGNED, force="mesh").vertices, dtype=float)


def within(points, low, high):
    """Which points lie inside the box low..high across and along (x, z)."""
    return np.all((points[:, [0, 2]] >= low) & (points[:, [0, 2]] <= high), axis=1)


def rough_reading(points, rough):
    """The registered rough model over an area's footprint points (place frame): the share of them inside its
    footprint, and the relief its points show over the area's box (None where it has none there)."""
    covered = within(points, rough[:, [0, 2]].min(axis=0), rough[:, [0, 2]].max(axis=0))
    over = rough[within(rough, points[:, [0, 2]].min(axis=0), points[:, [0, 2]].max(axis=0)), 1]
    return {"share": round(float(covered.mean()), 3), "relief": round(float(np.ptp(over)), 2) if len(over) else None}


def area_words(words, size, concept, reading):
    """The close-up's words: the plan's landform and its metres, the concept's ground and its rough model's relief."""
    seen = f"; the concept shows {'; '.join(concept)}" if concept else ""
    shown = f"; the concept's rough model shows {reading['relief']:.1f} m of relief there" \
        if reading and reading["relief"] is not None else ""
    return f"ground detail: {words}, {size[0]:.0f} by {size[1]:.0f} m, {size[2]:.1f} m of relief{seen}{shown}"


def area_of(name, words, footprint, laid, concept, rough=None):
    """One area from its footprint cells inside the patch: middle and size in the place's frame, relief, words, and
    the registered rough model's reading over it (None without one)."""
    grid_x, grid_z, rise = footprint
    points = place_points(laid, grid_x, grid_z)
    low, high = points.min(axis=0), points.max(axis=0)
    size = [round(float(high[0] - low[0]), 2), round(float(high[2] - low[2]), 2), round(float(np.ptp(rise)), 2)]
    middle = place_points(laid, np.array([grid_x.mean()]), np.array([grid_z.mean()]))[0]
    reading = rough_reading(points, rough) if rough is not None else None
    return {"id": area_id(name), "landform": name, "kind": words.split(",")[0].split(" ")[0],
            "words": area_words(words, size, concept, reading),
            "plan_at": [round(float(grid_x.mean()), 2), round(float(grid_z.mean()), 2)],
            "at": [round(float(value), 3) for value in middle], "size": size, "rough": reading}


def detail_areas(place, data, rough=None):
    """The place's detail areas, nearest first: [{id, kind, landform, words, plan_at, at, size, rough}], read over the
    registered rough model's points (`rough`, rough_points) when given."""
    record, _ = body_plan(place, data)
    laid = laid_ground(place, data) if record else None
    if laid is None:
        return []
    grid = plan_grid(record)
    patch = in_box(grid, patch_box(place, data, laid))
    concept = concept_words(place, data)
    found = []
    for name, (words, height, footprint) in {**crater_footprints(record, grid),
                                              **landform_footprints(record, grid)}.items():
        inside = footprint & patch
        if inside.any():
            found.append(area_of(name, words, (grid.x[inside], grid.z[inside], height[inside]), laid,
                                 concept, rough))
    return sorted(found, key=lambda area: float(np.hypot(area["at"][0], area["at"][2])))


# --- the rows they land as --------------------------------------------------------------------------------------------

def inventory_rows(place, found):
    """The areas as scene inventory rows: made by the prop route (kind generate), standing on the ground at their
    middle, one each, the close-up's words their name, the plan's landform named."""
    return [{"id": area["id"], "name": area["words"], "kind": "generate", "anchor": "ground", "size": area["size"],
             "count": 1, "thing": f"prop:{place}_{area['id']}", "parent": "", "made": "made by the route",
             "prop": f"{place}_{area['id']}", "at": [{"x": area["at"][0], "y": area["at"][1], "z": area["at"][2],
                                                       "facing": 0.0, "level": "ground"}],
             "area": {"landform": area["landform"], "plan_at": area["plan_at"], "rough": area["rough"]},
             "why": f"a detail area of the ground (#27): the plan's {area['landform']} reaches into the place's fine "
                    "patch, so its close-up is made into a model through the prop pipeline"} for area in found]


def take_of(area):
    return f"{area['id']}-g1"


def landed(inventory, props, surfaces, place, found):
    """The place's inventory, hand-in record (its prop data) and surface data with every area's row, terrain-layer
    object and take added (rows and takes already there kept as they are)."""
    have = {row["id"] for row in inventory["rows"]}
    rows = [row for row in inventory_rows(place, found) if row["id"] not in have]
    objects = {area["id"]: {"route": "prop", "take": take_of(area), "layer": LAYER} for area in found}
    takes = {take_of(area): {"places": [place], "place": place, "kind": f"{place}_{area['id']}",
                             "object": area["words"]} for area in found}
    return (dict(inventory, rows=inventory["rows"] + rows),
            dict(props, objects={**objects, **props.get("objects", {})}),
            dict(surfaces, takes={**takes, **surfaces.get("takes", {})},
                 bake=dict(surfaces.get("bake", {}), models={**{area["id"]: take_of(area) for area in found},
                                                            **surfaces.get("bake", {}).get("models", {})})))


def write(place, registration, data=REPO / "data"):
    """Land the place's areas, read over its registered rough model (a rough-align output folder), in its inventory,
    hand-in record and surface data (its surface data must exist: it names the place's library)."""
    data = pathlib.Path(data)
    found = detail_areas(place, data, rough_points(registration))
    paths = (data / "inventory" / f"{place}.json", data / "props" / f"{place}.json",
             data / "surfaces" / f"{place}.json")
    props = read(paths[1]) or {"place": place, "order": "prop-first", "objects": {}, "fallback": {}}
    for path, written in zip(paths, landed(json.loads(paths[0].read_text()), props,
                                           json.loads(paths[2].read_text()), place, found)):
        path.write_text(json.dumps(written, indent=1, ensure_ascii=False) + "\n")
    return found


def accepted_registration(place):
    """A read-only checkout of the place's accepted rough-align output in the default store; SystemExit with none."""
    from score.store import Store
    store = Store.default()
    output = store.accepted(f"rough-align@{place}")
    if output is None:
        raise SystemExit(f"{place}: no accepted rough-align: the loop splits a place's parts only once its rough model "
                         f"stands in its plan (python -m score run <environment> --place {place} --detach)")
    return store.checkout(output)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[1] != "write":
        raise SystemExit(__doc__)
    registered = pathlib.Path(sys.argv[3]) if len(sys.argv) == 4 else accepted_registration(sys.argv[2])
    print(f"{sys.argv[2]}: {len(write(sys.argv[2], registered))} detail areas landed")
