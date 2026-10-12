"""crops-look@<place> (paid): the crops layer on its beds, rendered from above at a slant as the concept looks down
on its plot, and its plants counted with SAM 3 the way the concept's were: the concept-density check on the render.

    make     a stage of the beds alone (the scene record's bed boxes, nothing else of the place) with the crops layer
             and its assets over it, rendered from VIEWS (tools/blender/inside/usd_views.py through
             tools/props/cloud/blender_cloud.py, the look's pictures); SAM 3 asked for every kind's nouns on each
             picture (box_masks_cloud.py); each plant's centre taken back onto the beds' top through the view's
             camera; seen.json per view and kind: plants seen on the kind's beds and their spacing in plant widths
             (the median distance to the nearest seen neighbour over the made model's width)
    gates    seen      every kind seen on its beds: at least SEEN_LEAST of its laid plants (a canopy at least one mass),
                       in the view that sees it best
             density   every plant kind's seen spacing within SEEN_WITHIN of the concept's (a canopy kind's is the
                       crop data's word, not measured): the plants read as the concept's, not merged or sparse
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
# is the sine of a 28 degree look down; a little steeper so no plant hides another), from two sides.
DOWN = 35.0
AWAY = 6.5
FOV = 50.0
SIDES = {"south-east": 45.0, "south-west": 135.0}
CARDS = "gpu-24gb,gpu-48gb,gpu-80gb"
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


def views_of(beds):
    """The look's cameras: each SIDES' bearing, DOWN degrees down onto the plot's middle from AWAY metres."""
    middle = plot_middle(beds)
    found = []
    for name, bearing in SIDES.items():
        level = AWAY * math.cos(math.radians(DOWN))
        eye = [middle[0] + level * math.cos(math.radians(bearing)), middle[1] + AWAY * math.sin(math.radians(DOWN)),
               middle[2] + level * math.sin(math.radians(bearing))]
        found.append({"name": name, "eye": [round(value, 4) for value in eye], "aim": list(middle), "fov": FOV,
                      "review": True})
    return found


def on_floor(view, pixel, size, height):
    """Where a picture's pixel (x, y from the top left) meets the level plane at `height`, as (x, z); None when its
    ray never comes down to it. The camera is usd_views.py's: `fov` across the picture's width, up the world's up."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    ahead = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(ahead, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, ahead)
    half_wide = math.tan(math.radians(view["fov"]) / 2)
    across = (pixel[0] / (size[0] / 2) - 1) * half_wide
    rise = (size[1] / 2 - pixel[1]) / (size[0] / 2) * half_wide
    way = ahead + across * right + rise * up
    if way[1] >= 0:
        return None
    reach = (height - eye[1]) / way[1]
    point = eye + reach * way
    return float(point[0]), float(point[2])


def beds_stage(place, beds, crops_folder, folder):
    """The look's stage: the beds as boxes and the crops layer with its assets, under /<place>."""
    from pxr import Gf, Usd, UsdGeom
    tree = folder / place
    (tree / "layers").mkdir(parents=True)
    shutil.copy2(crops_folder / layer.LAYER, tree / layer.LAYER)
    shutil.copytree(crops_folder / "assets", tree / "assets")
    beds_layer = Usd.Stage.CreateNew(str(tree / "layers/beds.usda"))
    UsdGeom.SetStageUpAxis(beds_layer, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(beds_layer, 1.0)
    UsdGeom.Xform.Define(beds_layer, f"/{place}")
    for bed in beds:
        cube = UsdGeom.Cube.Define(beds_layer, f"/{place}/Beds/{bed['name']}")
        cube.AddTranslateOp().Set(Gf.Vec3d(*map(float, bed["centre"])))
        cube.AddScaleOp().Set(Gf.Vec3f(*(float(value) / 2.0 for value in bed["size"])))
        cube.CreateDisplayColorAttr([Gf.Vec3f(0.24, 0.17, 0.11)])
    beds_layer.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(tree / f"{place}.usda"))
    UsdGeom.SetStageUpAxis(root, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(root, 1.0)
    root.GetRootLayer().subLayerPaths = [f"./{layer.LAYER}", "./layers/beds.usda"]
    root.SetDefaultPrim(root.GetPrimAtPath(f"/{place}"))
    root.GetRootLayer().Save()
    return tree / f"{place}.usda"


def render(stage_path, views, out):
    """The views rendered on a rented card into out/render (usd_views.py through blender_cloud.py)."""
    spec = out / "views.json"
    spec.write_text(json.dumps({"size": SIZE, "views": views}))
    job = {"script": "tools/blender/inside/usd_views.py", "args": [str(stage_path), str(spec), str(out / "render")],
           "inputs": [str(stage_path.parent), str(spec)], "outputs": [str(out / "render")], "minutes": MINUTES}
    (out / "job.json").write_text(json.dumps(job, indent=1))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), str(out / "job.json"),
                    "--who", "score crops look", "--classes", CARDS], check=True, cwd=REPO)


def count_jobs(record, views, out):
    """box_masks.py's jobs: every kind's nouns over each view's look."""
    return [{"picture": str(out / "render" / f"{view['name']}-look.png"),
             "rows": [dict(row, key=f"{view['name']}/{row['key']}") for row in concept.plant_rows(record, SIZE)]}
            for view in views]


def seen_on_beds(record, view, instances, beds, shared, spots_record):
    """{kind: seen plants on the kind's beds, their spacing in plant widths} on one view."""
    own = {key.split("/", 1)[1]: listed for key, listed in instances.items() if key.startswith(f"{view['name']}/")}
    plants = concept.plants_in(own, [0, 0, *SIZE], record["kinds"])
    height = max(float(bed["centre"][1]) + float(bed["size"][1]) / 2.0 for bed in beds.values())
    found = {}
    for kind in record["kinds"]:
        points = []
        for plant in (plant for plant in plants if plant["kind"] == kind):
            spot = on_floor(view, concept.centre(plant["box"]), SIZE, height)
            if spot and any(on_bed(spot, beds[name]) for name in shared[kind]):
                points.append(spot)
        spacing = (statistics.median(concept.nearest_distances(points)) / spots_record["widths"][kind]
                   if len(points) >= 2 else None)
        found[kind] = {"seen": len(points), "laid": sum(spot["kind"] == kind for spot in spots_record["spots"]),
                       "spacing": round(spacing, 3) if spacing else None}
    return found


def on_bed(spot, bed):
    return (abs(spot[0] - float(bed["centre"][0])) <= float(bed["size"][0]) / 2.0
            and abs(spot[1] - float(bed["centre"][2])) <= float(bed["size"][2]) / 2.0)


def make_look(inputs, out, seed, params):
    """The beds and crops rendered on VIEWS, SAM 3 on each picture, seen.json."""
    record = json.loads(pathlib.Path(inputs["crops"]).read_text())
    beds = layer.beds_of(json.loads(pathlib.Path(inputs["scene"]).read_text()), record["beds"])
    crops_folder = pathlib.Path(inputs["crops-layer"])
    spots_record = json.loads((crops_folder / "spots.json").read_text())
    views = views_of(beds)
    stage_path = beds_stage(record["place"], beds, crops_folder, out / "stage")
    render(stage_path, views, out)
    jobs = count_jobs(record, views, out)
    (out / "jobs.json").write_text(json.dumps(jobs, indent=1))
    with crop_data.tools("props/cloud", "props"):
        import box_masks_cloud
        box_masks_cloud.mask(out / "jobs.json", out / "instances.json")
    instances = json.loads((out / "instances.json").read_text())
    named = {bed["name"]: bed for bed in beds}
    seen = {view["name"]: seen_on_beds(record, view, instances, named, spots_record["beds"], spots_record)
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
    """Every kind seen on its beds: at least SEEN_LEAST of its laid plants, a canopy at least one mass."""
    record = json.loads(pathlib.Path(inputs["crops"]).read_text())
    failing = []
    for kind, entry in record["kinds"].items():
        found = best_seen(output, kind)
        least = 1 if entry.get("canopy") else math.ceil(SEEN_LEAST * found["laid"])
        if found["seen"] < least:
            failing.append(f"{kind}: {found['seen']} seen of {found['laid']} laid")
    return checks.Verdict("seen", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {len(record['kinds'])} kinds not seen on their beds" if failing
                          else f"every one of {len(record['kinds'])} kinds seen on its beds",
                          {f"{kind} seen": best_seen(output, kind)["seen"] for kind in record["kinds"]},
                          findings=tuple(failing))


def judge_density(output, inputs, evidence):
    """Every plant kind's seen spacing in plant widths within SEEN_WITHIN of the concept's."""
    record = json.loads(pathlib.Path(inputs["crops"]).read_text())
    measured = json.loads((pathlib.Path(inputs["crops-concept"]) / "concept.json").read_text())["kinds"]
    failing, spacings = [], {}
    for kind, entry in record["kinds"].items():
        if entry.get("canopy"):
            continue
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
