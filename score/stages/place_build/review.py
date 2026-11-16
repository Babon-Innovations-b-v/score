"""A quick review of a laid scene (#128, owner 2026-11-16: "were missing a tool that allow for quick ways to review a
scene"): many builders each lay one compartment of a place (a zone: the bunks, a desk cluster, the tunnel, the shell,
the terrain) and judges read their work, so a review is one fast Blender call (Cycles on this PC's card at
REVIEW_SAMPLES, denoised: a check that never ships) whose pictures a vision model and the owner both read.

    review(folder, box, prefix, width, out)   the views rendered, labelled and laid on one contact sheet:
                                              {"sheet", "listing", "views", "faults", "seconds"}
    viewer(folder, path, box, prefix, megabytes)  the scene as one compressed GLB (its textures downsized until it
                                              fits `megabytes`) for a browser viewer: {"glb", "megabytes", "texture"}

The region is the whole scene (its ground and sky left out of its box), the objects inside `box` (x0,z0,x1,z1 on the
plan, metres) or those whose names start with `prefix`. Its views (`views_of`):
- plan: straight down, orthographic, cut CUT over the floor (the camera's near plane, so roofs do not hide the rooms),
  a 1 m grid and each object's name (a crowd of one entry, the stones, only as dots);
- corner_*: four three-quarter views from the region's corners;
- door_*: eye height (EYE over the floor) just inside each door (an object named or addressed door or airlock),
  looking at the region's middle; middle: eye height at the middle, along the region's longer side;
- part_*: a close three-quarter view of each compartment: place.json's `compartments` ({name: {"box": [x0, z0, x1, z1]}
  or {"prefix": p}}), else each dome shell structure (a dome, a tunnel) in the region.
A physics check's faults (<folder>/CHECK: {"faults": [{"object": name, "kind": "floating" | "penetrating" | ...}]})
are drawn on every view as the object's box in red, its kind beside it on the plan.

<out>/sheet.jpg is the sheet (the concept in its top-right corner), <out>/review.json lists each view (its eye, aim,
lens, picture and place on the sheet) and the faults drawn.
"""
import json
import math
import pathlib
import shutil
import subprocess
import time

import numpy as np

from score.stages import place_build
from score.stages.place_build import render

SCRIPT = pathlib.Path(__file__).resolve().parent / "review_views.py"
EXPORT = pathlib.Path(__file__).resolve().parent / "viewer_glb.py"
WIDTH = 960  # each view's pixels across (4:3)
TALL = 0.75
EYE = 1.6  # eye height over the floor, metres
CUT = 2.4  # the plan's cut over the floor, metres
GRID = 1.0  # the plan's grid, metres
DOOR_WORDS = ("door", "airlock")
CROWD = 6  # more objects than this of one entry in the region are a crowd: dots on the plan, no names
CHECK = "check.json"
TILE = 480  # a view's pixels across on the sheet (the plan's twice that)
MEGABYTES = 15.0  # the viewer's GLB at most
UP = [0.0, 1.0, 0.0]


def scene_objects(folder):
    """The laid objects with a box: {"name", "address", "low", "high", "ground"}; the ground and the sky marked."""
    stage, place = place_build.opened(folder)
    found = []
    for item in place_build.listing(folder)["objects"]:
        if item["box"] is None:
            continue
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{item['name']}")
        ground = bool(prim.GetAttribute("score:ground").Get()) or str(item["address"]).startswith("light/")
        found.append({"name": item["name"], "address": item["address"], "low": np.array(item["box"][0]),
                      "high": np.array(item["box"][1]), "ground": ground})
    return found


def overlaps(item, box):
    """Whether an object's plan footprint meets `box` (x0, z0, x1, z1)."""
    return (item["high"][0] >= box[0] and item["low"][0] <= box[2] and item["high"][2] >= box[1]
            and item["low"][2] <= box[3])


def region_of(objects, box=None, prefix=None):
    """{"low", "high", "names"}: the box round the chosen objects (never the ground or sky; a crowd of one entry, the
    scattered stones, inside it but not framing it), or `box` itself on the plan with the chosen objects' heights;
    refused when nothing is chosen."""
    laid = [item for item in objects if not item["ground"]]
    if box is not None:
        chosen = [item for item in laid if overlaps(item, box)]
    elif prefix:
        chosen = [item for item in laid if item["name"].startswith(prefix)]
    else:
        chosen = laid
    if not chosen:
        raise place_build.Refused(f"no laid object in the region ({'box ' + str(box) if box else prefix or 'scene'})")
    counts = {}
    for item in chosen:
        counts[item["address"]] = counts.get(item["address"], 0) + 1
    framed = [item for item in chosen if counts[item["address"]] <= CROWD] or chosen  # a crowd's spread never frames
    low = np.min([item["low"] for item in framed], axis=0)
    high = np.max([item["high"] for item in framed], axis=0)
    if box is not None:
        low[0], low[2], high[0], high[2] = box[0], box[1], box[2], box[3]
    return {"low": low, "high": high, "names": [item["name"] for item in chosen]}


def compartments_of(record, objects, region):
    """[{"name", "low", "high"}]: place.json's compartments meeting the region, else its dome shell structures."""
    inside = [item for item in objects if item["name"] in region["names"]]
    given = record.get("compartments") or {}
    found = []
    for name, spec in given.items():
        if "box" in spec:
            members = [item for item in inside if overlaps(item, spec["box"])]
        else:
            members = [item for item in inside if item["name"].startswith(spec["prefix"])]
        if members:
            low = np.min([item["low"] for item in members], axis=0)
            high = np.max([item["high"] for item in members], axis=0)
            if "box" in spec:
                low[0], low[2], high[0], high[2] = spec["box"]
            found.append({"name": name, "low": low, "high": high})
    if given:
        return found
    return [{"name": item["name"], "low": item["low"], "high": item["high"]} for item in inside
            if item["address"] == place_build.DOME]


def doors_of(objects, region):
    """The region's doors: objects whose name or address holds a DOOR_WORD."""
    return [item for item in objects if item["name"] in region["names"]
            and any(word in f"{item['name']} {item['address']}".lower() for word in DOOR_WORDS)]


def floor_of(objects, compartments, region):
    """The floor's height: the compartments' middle lowest point, else the region's objects'."""
    lows = [part["low"][1] for part in compartments] or \
        [item["low"][1] for item in objects if item["name"] in region["names"]]
    return float(np.median(lows))


def three_quarter(name, low, high, floor, corner, reach):
    """A three-quarter view of a box from its plan corner `corner` (signs of x and z), `reach` times its diagonal
    out and up."""
    middle = (low + high) / 2
    diagonal = max(float(np.linalg.norm((high - low)[[0, 2]])), 2.0)
    half = (high - low) / 2
    eye = [middle[0] + corner[0] * (half[0] + reach * diagonal), floor + max(reach * diagonal * 1.2, 2.5),
           middle[2] + corner[1] * (half[2] + reach * diagonal)]
    return {"name": name, "kind": "three_quarter", "eye": eye, "aim": [middle[0], floor + 0.8, middle[2]],
            "up": UP, "fov": 50.0}


def views_of(region, compartments, doors, floor):
    """The review's views (usd_views' listing, look only): the plan, the corners, the doors and the middle at eye
    height, a close-up of each compartment."""
    low, high = region["low"], region["high"]
    middle = (low + high) / 2
    across = max(high[0] - low[0], (high[2] - low[2]) / TALL, 2.0) * 1.1
    top = max(high[1], floor + CUT) + 50.0
    listed = [{"name": "plan", "kind": "plan", "eye": [middle[0], top, middle[2]],
               "aim": [middle[0], floor, middle[2]], "up": [0.0, 0.0, -1.0], "fov": 30.0, "ortho": across,
               "near": top - (floor + CUT)}]
    for corner in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        listed.append(three_quarter(f"corner_{'w' if corner[0] < 0 else 'e'}{'n' if corner[1] < 0 else 's'}",
                                    low, high, floor, corner, 0.35))
    for door in doors:
        at = (door["low"] + door["high"]) / 2
        inward = np.array([middle[0] - at[0], middle[2] - at[2]])
        inward = inward / max(np.linalg.norm(inward), 1e-6)
        listed.append({"name": f"door_{door['name']}", "kind": "eye", "eye": [at[0] + 0.8 * inward[0],
                       door["low"][1] + EYE, at[2] + 0.8 * inward[1]], "aim": [middle[0], floor + 1.2, middle[2]],
                       "up": UP, "fov": 75.0})
    along = [1.0, 0.0, 0.0] if high[0] - low[0] >= high[2] - low[2] else [0.0, 0.0, 1.0]
    listed.append({"name": "middle", "kind": "eye", "eye": [middle[0], floor + EYE, middle[2]],
                   "aim": [middle[0] + along[0], floor + EYE, middle[2] + along[2]], "up": UP, "fov": 90.0})
    for part in compartments:
        listed.append(dict(three_quarter(f"part_{part['name']}", part["low"], part["high"], floor, (-1, -1), 0.3),
                           kind="close"))
    return [dict(view, look_only=True) for view in listed]


def projected(view, size, points):
    """Pixels (n x 2) of stage points seen by a view (perspective, or orthographic with "ortho"), and which lie in
    front of it."""
    eye, aim, up = (np.asarray(view[key], float) for key in ("eye", "aim", "up"))
    back = (eye - aim) / np.linalg.norm(eye - aim)
    across = np.cross(up, back)
    across /= np.linalg.norm(across)
    upward = np.cross(back, across)
    relative = np.asarray(points, float) - eye
    sideways, height, depth = relative @ across, relative @ upward, -(relative @ back)
    wide, tall = size
    if view.get("ortho"):
        scale = wide / float(view["ortho"])
        return np.stack([wide / 2 + sideways * scale, tall / 2 - height * scale], 1), np.ones(len(relative), bool)
    focal = (wide / 2) / math.tan(math.radians(view["fov"]) / 2)
    ahead = depth > 0.05
    safe = np.where(ahead, depth, 1.0)
    return np.stack([wide / 2 + focal * sideways / safe, tall / 2 - focal * height / safe], 1), ahead


def faults_of(folder):
    """{object name: fault kind} from the physics check's result (<folder>/CHECK), none without one."""
    path = pathlib.Path(folder) / CHECK
    if not path.is_file():
        return {}
    found = {}
    for fault in json.loads(path.read_text()).get("faults", []):
        name = fault.get("object") or fault.get("name")
        if name:
            found.setdefault(name, fault.get("kind") or fault.get("fault") or "fault")
    return found


EDGES = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (2, 6), (3, 7)]


def corners(item):
    return np.array([[(item["low"], item["high"])[i >> 2 & 1][0], (item["low"], item["high"])[i >> 1 & 1][1],
                      (item["low"], item["high"])[i & 1][2]] for i in range(8)])


def font(size):
    from PIL import ImageFont
    return ImageFont.load_default(size=size)


def boxed_faults(drawing, view, size, objects, faults):
    """Each faulty object's box drawn in red on a view."""
    for item in objects:
        if item["name"] not in faults:
            continue
        pixels, ahead = projected(view, size, corners(item))
        for start, end in EDGES:
            if ahead[start] and ahead[end]:
                drawing.line([tuple(pixels[start]), tuple(pixels[end])], fill=(255, 30, 30), width=3)


def gridded(drawing, view, size, region):
    """The plan's GRID metre lines (every fifth stronger) over the region."""
    low, high = region["low"], region["high"]
    floor = view["aim"][1]
    for x in np.arange(math.floor(low[0]), math.ceil(high[0]) + GRID, GRID):
        ends, _ = projected(view, size, [[x, floor, low[2] - 50], [x, floor, high[2] + 50]])
        drawing.line([tuple(ends[0]), tuple(ends[1])], fill=(255, 255, 255, 110 if x % 5 == 0 else 45), width=1)
    for z in np.arange(math.floor(low[2]), math.ceil(high[2]) + GRID, GRID):
        ends, _ = projected(view, size, [[low[0] - 50, floor, z], [high[0] + 50, floor, z]])
        drawing.line([tuple(ends[0]), tuple(ends[1])], fill=(255, 255, 255, 110 if z % 5 == 0 else 45), width=1)


def labelled(drawing, view, size, objects, region, faults):
    """Each region object's name at its middle on the plan (a crowd's as a dot), largest first, none over another;
    a fault's kind after its name. The names drawn."""
    inside = [item for item in objects if item["name"] in region["names"]]
    entries = {}
    for item in inside:
        entries[item["address"]] = entries.get(item["address"], 0) + 1
    text_font = font(14)
    taken, drawn = [], []
    for item in sorted(inside, key=lambda item: -np.prod((item["high"] - item["low"])[[0, 2]])):
        middle, _ = projected(view, size, [(item["low"] + item["high"]) / 2])
        u, v = middle[0]
        if not (0 <= u < size[0] and 0 <= v < size[1]):
            continue
        if entries[item["address"]] > CROWD and item["name"] not in faults:
            drawing.ellipse([u - 2, v - 2, u + 2, v + 2], fill=(255, 255, 255, 160))
            continue
        text = item["name"] + (f" ({faults[item['name']]})" if item["name"] in faults else "")
        left, top, right, bottom = drawing.textbbox((u, v), text, font=text_font, anchor="mm")
        if any(left < other[2] and right > other[0] and top < other[3] and bottom > other[1] for other in taken):
            continue
        taken.append((left - 2, top - 1, right + 2, bottom + 1))
        drawing.rectangle(taken[-1], fill=(0, 0, 0, 150))
        drawing.text((u, v), text, font=text_font, anchor="mm",
                     fill=(255, 90, 90) if item["name"] in faults else (255, 255, 255))
        drawn.append(item["name"])
    return drawn


def annotated(picture, view, objects, region, faults):
    """A view's picture with its marks: on the plan the grid and names, on every view the faults' boxes."""
    from PIL import Image, ImageDraw
    shown = picture.convert("RGBA")
    marks = Image.new("RGBA", shown.size, (0, 0, 0, 0))
    drawing = ImageDraw.Draw(marks)
    if view["kind"] == "plan":
        gridded(drawing, view, shown.size, region)
        labelled(drawing, view, shown.size, objects, region, faults)
    boxed_faults(drawing, view, shown.size, objects, faults)
    return Image.alpha_composite(shown, marks).convert("RGB")


def sheet(pictures, views, concept, title):
    """The contact sheet: the plan two tiles square at the top left, the concept at the top right, then every other
    view, each under its name. The sheet and each view's place on it [left, top, wide, tall]."""
    from PIL import Image, ImageDraw
    tile = (TILE, round(TILE * TALL))
    head = 34
    columns = 4
    others = [view for view in views if view["kind"] != "plan"]
    slots = [(2, 0), (3, 0), (2, 1), (3, 1)] + [(column, 2 + row) for row in range(math.ceil(max(len(others) - 3, 0)
                                                                                              / columns))
                                                 for column in range(columns)]
    rows = max(slot[1] for slot in slots[:len(others) + 1]) + 1
    made = Image.new("RGB", (columns * tile[0], head + rows * (tile[1] + 22)), (24, 24, 26))
    drawing = ImageDraw.Draw(made)
    drawing.text((10, 8), title, font=font(18), fill=(235, 235, 235))
    placed = {}

    def laid(name, picture, column, row, span=1, caption=None):
        left, top = column * tile[0], head + row * (tile[1] + 22)
        size = (tile[0] * span, tile[1] * span + 22 * (span - 1))
        made.paste(picture.resize(size), (left, top + 22))
        drawing.text((left + 6, top + 3), caption or name, font=font(15), fill=(235, 235, 235))
        placed[name] = [left, top + 22, *size]

    laid("plan", pictures["plan"], 0, 0, span=2,
         caption=f"plan: +x right, +z down, grid {GRID:g} m, cut {CUT:g} m over the floor")
    if concept is not None:
        laid("concept", concept, *slots[0])
    for view, slot in zip(others, slots[1:]):
        laid(view["name"], pictures[view["name"]], *slot)
    return made, placed


def queued(folder, script, arguments, job, card=True):
    """The command running a Blender script in a memory-capped scope, through the card queue when it draws (`card`)."""
    return render.queued(f"{job}-{pathlib.Path(folder).name}", script, arguments, card)


def ran(command, log):
    """A queued Blender run, refused before it starts without memory to spare; its log's tail when it fails."""
    free = render.available_gb()
    if free <= render.FREE_GB:
        raise render.RenderFailed(f"{free:.1f} GB memory available, a Blender needs over {render.FREE_GB}")
    with pathlib.Path(log).open("w") as out:
        done = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, cwd=render.REPO)
    if done.returncode:
        tail = " | ".join(pathlib.Path(log).read_text(errors="replace").splitlines()[-6:])
        raise render.RenderFailed(f"exit {done.returncode}, log {log}: {tail}")


def review(folder, box=None, prefix=None, width=WIDTH, out=None):
    """The region's views rendered in one Blender call, marked, and laid on one contact sheet (module doc)."""
    from PIL import Image
    folder = pathlib.Path(folder).resolve()
    out = pathlib.Path(out) if out else folder / "review"
    out.mkdir(parents=True, exist_ok=True)
    record = place_build.record_of(folder)
    objects = scene_objects(folder)
    region = region_of(objects, box, prefix)
    compartments = compartments_of(record, objects, region)
    views = views_of(region, compartments, doors_of(objects, region), floor_of(objects, compartments, region))
    size = [width, round(width * TALL)]
    listing = out / "views.json"
    listing.write_text(json.dumps({"size": size, "review": True, "views": views}, indent=1))
    for view in views:
        (out / f"{view['name']}-look.png").unlink(missing_ok=True)
    began = time.time()
    ran(queued(folder, SCRIPT, [str(place_build.scene_path(folder)), str(listing), str(out)], "place-review"),
        out / "blender.log")
    seconds = round(time.time() - began, 1)
    faults = faults_of(folder)
    pictures = {}
    for view in views:
        made = out / f"{view['name']}-look.png"
        if not made.exists():
            raise render.RenderFailed(f"the view {view['name']} wrote no picture, log {out / 'blender.log'}")
        pictures[view["name"]] = annotated(Image.open(made), view, objects, region, faults)
        pictures[view["name"]].save(out / f"{view['name']}.jpg", quality=88)
    concept = folder / "concept.png"
    title = f"{record['place']}: {prefix or (f'box {box}' if box else 'whole scene')}, {len(region['names'])} " \
            f"objects, {len(faults)} faults"
    made, placed = sheet(pictures, views, Image.open(concept).convert("RGB") if concept.is_file() else None, title)
    made.save(out / "sheet.jpg", quality=88)
    listed = [{"name": view["name"], "kind": view["kind"], "eye": [round(value, 3) for value in view["eye"]],
               "aim": [round(value, 3) for value in view["aim"]], "fov": view["fov"], "ortho": view.get("ortho"),
               "picture": str(out / f"{view['name']}.jpg"), "on_sheet": placed[view["name"]]} for view in views]
    answer = {"sheet": str(out / "sheet.jpg"), "listing": str(out / "review.json"), "views": listed,
              "region": {"low": region["low"].round(3).tolist(), "high": region["high"].round(3).tolist(),
                         "objects": len(region["names"])},
              "faults": [{"object": name, "kind": kind} for name, kind in sorted(faults.items())],
              "seconds": seconds}
    (out / "review.json").write_text(json.dumps(answer, indent=1))
    return {"sheet": answer["sheet"], "listing": answer["listing"], "views": len(listed),
            "faults": len(faults), "seconds": seconds}


def kept_stage(folder, kept):
    """<folder>/render/viewer.usda: the scene with every object outside `kept` (and the sky's light) made inactive."""
    from pxr import Usd
    stage, place = place_build.opened(folder)
    path = pathlib.Path(folder) / "render" / "viewer.usda"
    path.parent.mkdir(exist_ok=True)
    shown = Usd.Stage.CreateNew(str(path))
    shown.GetRootLayer().subLayerPaths.append(str(place_build.scene_path(folder).resolve()))
    shown.SetDefaultPrim(shown.GetPrimAtPath(f"/{place}"))
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        if prim.GetName() not in kept:
            shown.OverridePrim(prim.GetPath()).SetActive(False)
    for part in ("Lights", "Environment"):
        if stage.GetPrimAtPath(f"/{place}/{part}"):
            shown.OverridePrim(f"/{place}/{part}").SetActive(False)
    shown.GetRootLayer().Save()
    return path


def viewer(folder, path=None, box=None, prefix=None, megabytes=MEGABYTES):
    """The scene (or the region's objects and the ground) as one Draco-compressed GLB, its textures halved until it
    fits `megabytes`; the sky left out."""
    folder = pathlib.Path(folder).resolve()
    path = pathlib.Path(path).resolve() if path else folder / "viewer.glb"
    objects = scene_objects(folder)
    kept = [item["name"] for item in objects if not str(item["address"]).startswith("light/")]
    if box is not None or prefix:
        region = region_of(objects, box, prefix)
        kept = [name for name in kept if name in region["names"]]
    shown = kept_stage(folder, kept)
    path.unlink(missing_ok=True)
    began = time.time()
    ran(queued(folder, EXPORT, [str(shown), str(path), str(megabytes)],
               "place-viewer", card=False), folder / "render" / "viewer.log")
    if not path.is_file():
        raise render.RenderFailed(f"no GLB written, log {folder / 'render' / 'viewer.log'}")
    report = json.loads(path.with_suffix(".json").read_text())
    shutil.move(path.with_suffix(".json"), folder / "render" / "viewer.json")
    return {"glb": str(path), "megabytes": round(path.stat().st_size / 1e6, 2), "texture": report["texture"],
            "objects": len(kept), "seconds": round(time.time() - began, 1)}
