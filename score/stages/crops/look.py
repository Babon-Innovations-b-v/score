"""crops-look@<place> (paid): the crops layer on its beds, rendered from above at a slant as the concept looks down
on its plot, and its plants counted with SAM 3 the way the concept's were: the concept-density check on the render.

    make     a stage of the beds alone (the plan's bed boxes as meshes, crop_data.beds_in, nothing else of the place)
             with the crops layer and its assets over it, rendered from VIEWS (tools/blender/inside/usd_views.py
             through tools/cloud/blender_cloud.py, the look's pictures), each view as far out as frames every bed
             and every laid plant whole; SAM 3 asked for every kind's nouns on each picture (box_masks_cloud.py),
             each plant once whatever noun found it; each plant's middle (its box's middle) taken back through the
             view's camera onto the level of its kind's middle (the beds' top plus half the kind's made height),
             and counted the kind of the bed it stands on;
             seen.json per view and kind: plants seen on the kind's beds and their spacing in plant widths
             (seen_spacing: the median over its seen plants of the distance to the nearest seen plant on its own
             bed, a plant seen alone on its bed its bed's side, over its laid width on that bed)
    gates    seen      every kind seen on its beds: at least SEEN_LEAST of its laid plants, in the view that sees it
                       best
             density   every kind's seen spacing within SEEN_WITHIN of the concept's: the plants read as the
                       concept's, not merged or sparse
"""
import json
import math
import pathlib
import shutil
import statistics
import subprocess

import numpy as np

from score import checks, contracts
import score.stages.crops.concept as concept
import score.stages.crops.crop_data as crop_data
import score.stages.crops.layer as layer
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
SIZE = [1536, 1024]
# Two cameras looking down at the plot's middle at the concept's slant (its plot's height over width, about 0.47,
# is the sine of a 28 degree look down; a little steeper so no plant hides another), from two sides, each at least
# AWAY metres out and further by STEP until every bed and laid plant is in its picture, MARGIN of each side clear
# (crops-look@greenhouse, 2026-11-03: at 6.5 m its 2.3 m trays ran off the picture's edges, 3 of 11 seen).
DOWN = 35.0
AWAY = 6.5
STEP = 0.25
FARTHEST = 60.0
MARGIN = 0.03
FOV = 50.0
SIDES = {"south-east": 45.0, "south-west": 135.0}
CARDS = "gpu-24gb"  # one class, the L4 priced in EUROS; never a fallback to a larger card (#21)
MINUTES = 12
SEEN_LEAST = 0.5
SEEN_WITHIN = 0.35
# Two Cycles views on one card (about EUR 1) and SAM 3 on one L4 (EUR 0.04 on 2026-10-12), rounded up.
EUROS = 3.0


def plot_middle(beds):
    """The beds' middle on their top: (x, y, z)."""
    return (statistics.mean(float(bed["centre"][0]) for bed in beds),
            max(float(bed["centre"][1]) + float(bed["size"][1]) / 2.0 for bed in beds),
            statistics.mean(float(bed["centre"][2]) for bed in beds))


def view_from(name, bearing, middle, away):
    """One look camera: `bearing` round, DOWN degrees down onto `middle` from `away` metres."""
    level = away * math.cos(math.radians(DOWN))
    eye = [middle[0] + level * math.cos(math.radians(bearing)), middle[1] + away * math.sin(math.radians(DOWN)),
           middle[2] + level * math.sin(math.radians(bearing))]
    return {"name": name, "eye": [round(value, 4) for value in eye], "aim": list(middle), "up": [0.0, 1.0, 0.0],
            "fov": FOV, "review": True}


def views_of(beds, framed=()):
    """The look's cameras: each SIDES' bearing, DOWN degrees down onto the plot's middle, each from the nearest of
    AWAY, AWAY + STEP, ... metres at which every bed's corners and every point of `framed` fall in its picture."""
    middle = plot_middle(beds)
    points = [*bed_corners(beds), *framed]
    found = []
    for name, bearing in SIDES.items():
        away = AWAY
        while not all(in_picture(view_from(name, bearing, middle, away), point, SIZE) for point in points):
            away += STEP
            if away > FARTHEST:
                raise ValueError(f"{name}: no view within {FARTHEST} m frames the beds and plants")
        found.append(view_from(name, bearing, middle, away))
    return found


def bed_corners(beds):
    """Every corner of every bed's box: (x, y, z)."""
    return [(float(bed["centre"][0]) + side_x * float(bed["size"][0]) / 2.0,
             float(bed["centre"][1]) + side_y * float(bed["size"][1]) / 2.0,
             float(bed["centre"][2]) + side_z * float(bed["size"][2]) / 2.0)
            for bed in beds for side_x in (-1, 1) for side_y in (-1, 1) for side_z in (-1, 1)]


def plant_reach(spots_record, heights):
    """The points a laid plant may reach: round each spot, its model's half width times its size (any turn) out from
    it across the floor, from its foot to its height."""
    found = []
    for spot in spots_record["spots"]:
        width, height = spots_record["widths"].get(spot["kind"]), heights.get(spot["kind"])
        if width is None or height is None:
            continue  # a kind the layer left out lays no model
        reach = width * float(spot["size"]) / 2.0
        x, y, z = map(float, spot["at"])
        found += [(x + side_x * reach, y + rise * height * float(spot["size"]), z + side_z * reach)
                  for side_x in (-1, 1) for side_z in (-1, 1) for rise in (0, 1)]
    return found


def camera_axes(view):
    """usd_views.py's camera: (eye, ahead, right, up, half_wide), `fov` across the picture's width, up the world's
    up."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    ahead = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(ahead, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, ahead)
    return eye, ahead, right, up, math.tan(math.radians(view["fov"]) / 2)


def in_picture(view, point, size):
    """Whether a point of the stage falls in the view's picture, MARGIN of each side clear (and before the eye)."""
    eye, ahead, right, up, half_wide = camera_axes(view)
    way = np.asarray(point, dtype=float) - eye
    depth = float(way @ ahead)
    if depth <= 0:
        return False
    pixel = (size[0] / 2 * (1 + float(way @ right) / depth / half_wide),
             size[1] / 2 - float(way @ up) / depth / half_wide * size[0] / 2)
    return all(MARGIN * side <= value <= (1 - MARGIN) * side for value, side in zip(pixel, size))


def on_floor(view, pixel, size, height):
    """Where a picture's pixel (x, y from the top left) meets the level plane at `height`, as (x, z); None when its
    ray never comes down to it. The camera is usd_views.py's: `fov` across the picture's width, up the world's up."""
    eye, ahead, right, up, half_wide = camera_axes(view)
    across = (pixel[0] / (size[0] / 2) - 1) * half_wide
    rise = (size[1] / 2 - pixel[1]) / (size[0] / 2) * half_wide
    way = ahead + across * right + rise * up
    if way[1] >= 0:
        return None
    reach = (height - eye[1]) / way[1]
    point = eye + reach * way
    return float(point[0]), float(point[2])


def beds_stage(place, beds, crops_folder, folder):
    """The look's stage: the beds as box meshes and the crops layer with its assets, under /<place>. A bed's prim is
    its plan item's name made a valid identifier ('PLANTER BED 1' is no prim name), its own name kept as score:name.
    A bed is a mesh with its corners written out, never a Cube scaled by an xform op: Blender's USD import stood the
    scaled cubes up, their depth as their height (crops-look@greenhouse, 2026-11-03: the 0.5 m beds rendered 1.7 m
    tall white slabs hiding the plants behind them)."""
    from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt
    tree = folder / place
    (tree / "layers").mkdir(parents=True)
    shutil.copy2(crops_folder / layer.LAYER, tree / layer.LAYER)
    shutil.copytree(crops_folder / "assets", tree / "assets")
    beds_layer = Usd.Stage.CreateNew(str(tree / "layers/beds.usda"))
    UsdGeom.SetStageUpAxis(beds_layer, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(beds_layer, 1.0)
    UsdGeom.Xform.Define(beds_layer, f"/{place}")
    prims = [Tf.MakeValidIdentifier(bed["name"]) for bed in beds]
    if len(set(prims)) < len(prims):
        raise ValueError(f"{place}: two beds make one prim name: {sorted(bed['name'] for bed in beds)}")
    for bed, prim in zip(beds, prims):
        mesh = UsdGeom.Mesh.Define(beds_layer, f"/{place}/Beds/{prim}")
        mesh.GetPrim().CreateAttribute("score:name", Sdf.ValueTypeNames.String).Set(bed["name"])
        corners = bed_corners([bed])
        mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*corner) for corner in corners]))
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray([4] * 6))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(BOX_FACES))
        mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*corners[0]), Gf.Vec3f(*corners[-1])]))
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDisplayColorAttr([Gf.Vec3f(0.24, 0.17, 0.11)])
    beds_layer.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(tree / f"{place}.usda"))
    UsdGeom.SetStageUpAxis(root, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(root, 1.0)
    root.GetRootLayer().subLayerPaths = [f"./{layer.LAYER}", "./layers/beds.usda"]
    root.SetDefaultPrim(root.GetPrimAtPath(f"/{place}"))
    root.GetRootLayer().Save()
    return tree / f"{place}.usda"


# A box's six faces over bed_corners' order (x, then y, then z, low side first), each wound outward.
BOX_FACES = (0, 1, 3, 2, 4, 6, 7, 5, 0, 4, 5, 1, 2, 3, 7, 6, 0, 2, 6, 4, 1, 5, 7, 3)


def render(stage_path, views, out):
    """The views rendered on a rented card into out/render (usd_views.py through blender_cloud.py)."""
    spec = out / "views.json"
    spec.write_text(json.dumps({"size": SIZE, "views": views}))
    job = {"script": "tools/blender/inside/usd_views.py", "args": [str(stage_path), str(spec), str(out / "render")],
           "inputs": [str(stage_path.parent), str(spec)], "outputs": [str(out / "render")], "minutes": MINUTES}
    (out / "job.json").write_text(json.dumps(job, indent=1))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/cloud/blender_cloud.py"), str(out / "job.json"),
                    "--who", "score crops look", "--classes", CARDS], check=True, cwd=REPO)


def count_jobs(record, views, out):
    """box_masks.py's jobs: every kind's nouns over each view's look."""
    return [{"picture": str(out / "render" / f"{view['name']}-look.png"),
             "rows": [dict(row, key=f"{view['name']}/{row['key']}") for row in concept.plant_rows(record, SIZE)]}
            for view in views]


def view_plants(view, instances):
    """Every plant SAM 3 found on one view under any kind's nouns, each once (the surest of boxes that are one plant,
    concept.same_plant), merged masses left out (concept.MERGED times the median width)."""
    found = sorted((instance for key, listed in instances.items() if key.startswith(f"{view['name']}/")
                    for instance in listed), key=lambda instance: -instance["score"])
    if not found:
        return []
    middle = statistics.median(concept.width(instance["box"]) for instance in found)
    kept = []
    for instance in found:
        if concept.width(instance["box"]) <= concept.MERGED * middle and \
                not any(concept.same_plant(instance["box"], other["box"]) for other in kept):
            kept.append(instance)
    return kept


def middle(box):
    """A plant's middle in the picture: its box's middle. Taken back onto the level of the plant's own middle, not
    the beds' top: a box's bottom middle is the nearest edge of a wide plant (a 2.3 m tray's front corner lands a
    metre in front of its bed, crops-look@greenhouse 2026-11-03) and a box's middle taken onto the beds' top lands a
    tall plant behind its bed."""
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def plant_heights(crops_folder, place, kinds):
    """{kind: its made model's height in metres, at size 1}: its prototype's bounds in the crops layer."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(crops_folder / layer.LAYER))
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    found = {}
    for kind in kinds:
        prototypes = stage.GetPrimAtPath(f"/{place}/Crops/{kind}/Prototypes")
        if not prototypes.IsValid():
            continue  # a kind the layer left out (a batch gap) lays no model
        ranges = [bounds.ComputeUntransformedBound(child).ComputeAlignedRange() for child in prototypes.GetChildren()]
        found[kind] = max(float(span.GetMax()[1] - span.GetMin()[1]) for span in ranges)
    return found


def seen_on_beds(record, view, instances, beds, shared, spots_record, heights):
    """{kind: plants seen on the kind's beds, their spacing in plant widths} on one view. A plant is the kind of the
    bed it stands on: the render's beds are laid by the layer, so where a plant stands says what it is, and the nouns
    only find plants (on the 2026-10-13 render SAM 3's 'rosemary' and 'small shrub' found none of the herbs that its
    'leafy bush' found). Each plant's middle is taken back onto the level of a kind's middle (the beds' top plus half
    its laid height, `heights` at size 1 times its plants' median size) for that kind's beds; its spacing is
    seen_spacing, in its laid width on each bed, its model's width times its plants' median size there (the layer
    sizes a plant to its bed)."""
    top = max(float(bed["centre"][1]) + float(bed["size"][1]) / 2.0 for bed in beds.values())
    plants = view_plants(view, instances)
    found = {}
    for kind in record["kinds"]:
        sizes = [float(spot["size"]) for spot in spots_record["spots"] if spot["kind"] == kind]
        level = top + heights.get(kind, 0.0) * (statistics.median(sizes) if sizes else 1.0) / 2.0
        spots = [on_floor(view, middle(plant["box"]), SIZE, level) for plant in plants]
        points = [(spot, bed_under(spot, shared[kind], beds)) for spot in spots if spot]
        points = [(spot, name) for spot, name in points if name]
        width = spots_record["widths"].get(kind)  # none for a kind the layer left out (a batch gap)
        spacing = (seen_spacing(points, beds, laid_widths(kind, width, shared[kind], spots_record["spots"]))
                   if len(points) >= 2 and width else None)
        found[kind] = {"seen": len(points), "laid": sum(spot["kind"] == kind for spot in spots_record["spots"]),
                       "spacing": round(spacing, 3) if spacing else None}
    return found


def bed_under(spot, names, beds):
    """The first of the bed names `names` whose bed a floor point stands on, else None."""
    return next((name for name in names if on_bed(spot, beds[name])), None)


def laid_widths(kind, width, names, spots):
    """{bed name: a kind's laid width there}: its model `width` times the median size of its plants laid on that bed
    (of all its plants on a bed the layer laid none of it on)."""
    sizes = [float(spot["size"]) for spot in spots if spot["kind"] == kind]
    found = {}
    for name in names:
        own = [float(spot["size"]) for spot in spots if spot["kind"] == kind and spot["bed"] == name] or sizes
        found[name] = width * (statistics.median(own) if own else 1.0)
    return found


def seen_spacing(points, beds, widths):
    """The median over seen plants, `points` [(floor point, its bed's name)], of each one's spacing in its laid width
    on its bed (`widths`, laid_widths): the distance to the nearest seen plant on its own bed (how far apart the beds
    stand is the plan's); a plant seen alone on its bed, its bed's side (the square root of its area)."""
    each = []
    for index, (spot, name) in enumerate(points):
        others = [other for number, (other, other_name) in enumerate(points) if number != index and other_name == name]
        bed = beds[name]
        apart = (min(math.dist(spot, other) for other in others) if others
                 else math.sqrt(float(bed["size"][0]) * float(bed["size"][2])))
        each.append(apart / widths[name])
    return statistics.median(each)


def on_bed(spot, bed):
    return (abs(spot[0] - float(bed["centre"][0])) <= float(bed["size"][0]) / 2.0
            and abs(spot[1] - float(bed["centre"][2])) <= float(bed["size"][2]) / 2.0)


def make_look(inputs, out, seed, params):
    """The beds and crops rendered on VIEWS, SAM 3 on each picture, seen.json."""
    record = crop_data.read(inputs)
    beds = crop_data.beds_in(inputs, record)
    crops_folder = pathlib.Path(inputs["crops-layer"])
    spots_record = json.loads((crops_folder / "spots.json").read_text())
    heights = plant_heights(crops_folder, record["place"], record["kinds"])
    views = views_of(beds, plant_reach(spots_record, heights))
    stage_path = beds_stage(record["place"], beds, crops_folder, out / "stage")
    render(stage_path, views, out)
    jobs = count_jobs(record, views, out)
    (out / "jobs.json").write_text(json.dumps(jobs, indent=1))
    with crop_data.tools("cloud", "props"):
        import box_masks_cloud
        box_masks_cloud.mask(out / "jobs.json", out / "instances.json")
    instances = json.loads((out / "instances.json").read_text())
    named = {bed["name"]: bed for bed in beds}
    seen = {view["name"]: seen_on_beds(record, view, instances, named, spots_record["beds"], spots_record, heights)
            for view in views}
    shutil.rmtree(out / "stage")
    (out / "seen.json").write_text(json.dumps({"views": views, "seen": seen}, indent=1))


def look_faults(folder):
    folder = pathlib.Path(folder)
    if not (folder / "seen.json").exists():
        return ["no seen.json"]
    views = json.loads((folder / "seen.json").read_text())["views"]
    return [f"{view['name']}: no look" for view in views
            if not (folder / "render" / f"{view['name']}-look.png").exists()]


def best_seen(output, kind):
    """The view that sees the most of a kind's plants: its entry for the kind."""
    seen = json.loads((output / "seen.json").read_text())["seen"]
    return max((entry[kind] for entry in seen.values()), key=lambda found: found["seen"])


def judge_seen(output, inputs, evidence):
    """Every kind seen on its beds: at least SEEN_LEAST of its laid plants."""
    record = crop_data.read(inputs)
    failing = []
    for kind in record["kinds"]:
        found = best_seen(output, kind)
        least = math.ceil(SEEN_LEAST * found["laid"])
        if found["seen"] < least:
            failing.append(f"{kind}: {found['seen']} seen of {found['laid']} laid")
    return checks.Verdict("seen", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {len(record['kinds'])} kinds not seen on their beds" if failing
                          else f"every one of {len(record['kinds'])} kinds seen on its beds",
                          {f"{kind} seen": best_seen(output, kind)["seen"] for kind in record["kinds"]},
                          findings=tuple(failing))


def judge_density(output, inputs, evidence):
    """Every plant kind's seen spacing in plant widths within SEEN_WITHIN of the concept's."""
    record = crop_data.read(inputs)
    measured = json.loads((pathlib.Path(inputs["crops-concept"]) / "concept.json").read_text())["kinds"]
    failing, spacings = [], {}
    for kind in record["kinds"]:
        wanted, got = measured[kind]["spacing"], best_seen(output, kind)["spacing"]
        spacings[f"{kind} spacing"] = got or 0.0
        if got is None:
            failing.append(f"{kind}: under two plants seen, no spacing")
        elif abs(got - wanted) > SEEN_WITHIN * wanted:
            failing.append(f"{kind}: seen {got:.2f} plant widths apart, the concept's {wanted:.2f}")
    return checks.Verdict("density", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} kinds off the concept's spacing as seen" if failing
                          else f"every plant kind within {SEEN_WITHIN:.0%} of the concept's spacing as seen",
                          spacings, findings=tuple(failing))


LOOK = contracts.Contract("crops-look", 1, look_faults)
CHECKS = (checks.Check("seen", judge_seen), checks.Check("density", judge_density))
