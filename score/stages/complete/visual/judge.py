"""The visual check's rules on one place's evidence (measure.py's folder): what the owner saw by eye in a film and no
gate flagged (2026-10-18: a flat grey plane cutting through the old station's view, the wreck's untextured light floor).

    found = judge.findings(evidence, folder)    # [finding], the worst picture of each fault
    answer = judge.verdict(evidence, found)     # "fail" with a finding, "unknown" with no picture, else "pass"

A finding is {"rule", "picture" (its number), "name" (the picture's), "prim", "share", "cells" (the grid it marks),
"grid", "sentence"}. The rules, each on every picture:

    blocking plane   one surface drawn without texture covers BLOCK_SHARE of the picture or more and reads plain
                     there (most of its cells plain in the picture, plain.py), so a flat plane stands across the view;
                     a plain region of the picture the camera's rays meet nothing on is a plane the stage does not
                     hold (the film's renderer's stand-in ground, tools/blender/inside/usd_views.py `ground`)
    untextured       a surface with no material, the default grey, a texture that does not resolve or no texture
                     coordinates covers MISSING_SHARE or more; or a floor, ground or wall surface drawn in a plain
                     colour with no texture covers FLOOR_SHARE or more and reads plain there
    little seen      one object covers ONE_OBJECT_SHARE of the picture or more, or one flat plane (within
                     PLANE_TOLERANCE) holds ONE_PLANE_SHARE of it: mostly one wall, one door or one prop
    neighbour inside a neighbouring place's geometry stands inside the place's room (room.py, on the stage):
                     one finding a neighbour, its deepest prim named, marked on the picture showing most of it
                     (the owner, 2026-10-18: the walkway tube cutting through the airlock room)

The same fault on several pictures is one finding, shown on the picture where it covers the most.
"""
import json

import numpy as np
from PIL import Image

from score.stages.complete.visual import measure, plain, seen

BLOCKING, UNTEXTURED, LITTLE_SEEN, INSIDE = "blocking plane", "untextured", "little seen", "neighbour inside"
BLOCK_SHARE = 0.25
PLAIN_ENOUGH = 0.5  # the share of a surface's cells the picture shows plain for it to read as a flat plane
STRAY_SHARE = 0.25  # a plain region the rays meet nothing on, this share of the picture or more
MISSING_SHARE = 0.02
FLOOR_SHARE = 0.10
ONE_OBJECT_SHARE = 0.6
ONE_PLANE_SHARE = 0.75  # a small room's view (the cockpit) reads 0.67 at most; a door filling it 0.77 and over
PLANE_TOLERANCE = 0.15  # metres
PLANE_TRIES = 300
MISSING = (seen.NO_MATERIAL, seen.DEFAULT_GREY, seen.TEXTURE_MISSING, seen.NO_TEXTURE_COORDINATES)
# Words in a prim's path that make it a floor, ground or wall surface.
FLOOR_WORDS = ("ground", "floor", "wall", "outside", "terrain", "deck", "ceiling", "roof")
STAND_IN = "the film's grey stand-in ground (not on the stage)"


def surface_cells(sight):
    """(cells as an array of surface numbers, -1 nothing) of a sight record."""
    return np.asarray(sight["cells"])


def object_of(path):
    """The object a prim belongs to: the path up to its last `Objects/<name>`, else the prim itself."""
    parts = path.split("/")
    if "Objects" in parts[:-1]:
        last = len(parts) - 1 - parts[::-1].index("Objects")
        return "/".join(parts[:last + 2])
    return path


def is_floor(path):
    """True for a prim whose path names a floor, ground or wall."""
    lowered = path.lower()
    return any(word in lowered for word in FLOOR_WORDS)


def on_grid(region, shape):
    """A plain region's cells (plain.CELL grid) laid on another grid shape, by nearest cell."""
    rows = (np.arange(shape[0]) * region.shape[0] // shape[0])
    columns = (np.arange(shape[1]) * region.shape[1] // shape[1])
    return region[np.ix_(rows, columns)]


def plain_mask(image, shape):
    """Every plain cell of the picture on a grid of `shape`."""
    colours = plain.cell_colours(image)
    return on_grid(plain.plain_cells(plain.cell_detail(image), colours), shape)


def finding(rule, number, picture, prim, cells, sentence):
    """One finding on one picture."""
    return {"rule": rule, "picture": number, "name": picture["name"], "prim": prim,
            "share": round(float(cells.mean()), 3), "cells": cells.astype(int).tolist(), "grid": list(cells.shape),
            "sentence": sentence}


def per_surface(sight):
    """{prim path: (its cells, its worst kind)} of a sight record, every material of a prim together."""
    cells = surface_cells(sight)
    found = {}
    for number, (path, _, kind) in enumerate(sight["surfaces"]):
        mask = cells == number
        held, worst = found.get(path, (np.zeros(cells.shape, dtype=bool), seen.TEXTURED))
        order = (*MISSING, seen.PLAIN_COLOUR, seen.TEXTURED)
        found[path] = (held | mask, kind if order.index(kind) < order.index(worst) else worst)
    return found


def untextured_cells(sight, path):
    """The cells of a prim drawn without a texture."""
    cells = surface_cells(sight)
    numbers = [number for number, (prim, _, kind) in enumerate(sight["surfaces"])
               if prim == path and kind != seen.TEXTURED]
    return np.isin(cells, numbers)


def blocking(number, picture, sight, plain_cells):
    """Each untextured surface that covers BLOCK_SHARE or more and reads plain in the picture."""
    found = []
    for path in per_surface(sight):
        cells = untextured_cells(sight, path)
        if cells.mean() >= BLOCK_SHARE and plain_cells[cells].mean() >= PLAIN_ENOUGH:
            across = np.flatnonzero(cells.any(axis=0))
            found.append(finding(BLOCKING, number, picture, path, cells,
                                 f"a flat untextured plane ({path}) covers {cells.mean():.0%} of the picture, "
                                 f"{(across.max() - across.min() + 1) / cells.shape[1]:.0%} of its width"))
    return found


def stray_planes(number, picture, sight, image):
    """A plain region of the picture where the rays meet nothing: a plane the stage does not hold."""
    nothing = surface_cells(sight) < 0
    found = []
    for region in plain.regions(image):
        cells = on_grid(region["cells"], nothing.shape)
        if region["share"] >= STRAY_SHARE and nothing[cells].mean() >= PLAIN_ENOUGH:
            found.append(finding(BLOCKING, number, picture, STAND_IN, cells,
                                 f"a flat plain plane the stage does not hold covers {region['share']:.0%} of the "
                                 f"picture: the film's renderer drew its own grey ground there"))
    return found


def untextured(number, picture, sight, plain_cells):
    """Each surface drawn without a texture it should have, at MISSING_SHARE, or a plain floor at FLOOR_SHARE."""
    found = []
    for path, (cells, kind) in per_surface(sight).items():
        if kind in MISSING and cells.mean() >= MISSING_SHARE:
            found.append(finding(UNTEXTURED, number, picture, path, cells,
                                 f"{path} is drawn with {kind} over {cells.mean():.0%} of the picture"))
            continue
        bare = untextured_cells(sight, path)
        if (kind == seen.PLAIN_COLOUR and is_floor(path) and bare.mean() >= FLOOR_SHARE
                and plain_cells[bare].mean() >= PLAIN_ENOUGH):
            found.append(finding(UNTEXTURED, number, picture, path, bare,
                                 f"the floor or wall {path} has a plain colour and no texture over "
                                 f"{bare.mean():.0%} of the picture"))
    return found


def hit_points(picture, sight):
    """(cells hit as a mask, the stage points they meet) of a sight record."""
    distances = np.array([[np.inf if value is None else value for value in row] for row in sight["distances"]])
    eye, directions = seen.camera_rays(picture["view"], tuple(sight["grid"]))
    hit = np.isfinite(distances)
    return hit, eye + directions[hit.ravel()] * distances[hit][:, None]


def largest_plane(picture, sight):
    """The cells of the flat plane (within PLANE_TOLERANCE) holding most of the picture's hits, from PLANE_TRIES
    planes through three hits each, drawn the same way every run."""
    hit, points = hit_points(picture, sight)
    best = np.zeros(hit.shape, dtype=bool)
    if len(points) < 3:
        return best
    draws = np.random.default_rng(0)
    for _ in range(PLANE_TRIES):
        first, second, third = points[draws.choice(len(points), 3, replace=False)]
        normal = np.cross(second - first, third - first)
        if np.linalg.norm(normal) < 1e-9:
            continue
        near = np.abs((points - first) @ (normal / np.linalg.norm(normal))) < PLANE_TOLERANCE
        if near.sum() > best.sum():
            best = np.zeros(hit.shape, dtype=bool)
            best[hit] = near
    return best


def most_of(sight, cells):
    """The object most of the cells meet."""
    surfaces = surface_cells(sight)[cells]
    numbers, counts = np.unique(surfaces[surfaces >= 0], return_counts=True)
    return object_of(sight["surfaces"][numbers[counts.argmax()]][0])


def one_plane(number, picture, sight):
    """One flat plane holding ONE_PLANE_SHARE of the picture or more."""
    plane = largest_plane(picture, sight)
    if plane.mean() < ONE_PLANE_SHARE:
        return []
    return [finding(LITTLE_SEEN, number, picture, most_of(sight, plane), plane,
                    f"the picture shows little of the place, one flat face fills {plane.mean():.0%} of it, mostly "
                    f"{most_of(sight, plane)}")]


def one_object(number, picture, sight):
    """One object covering ONE_OBJECT_SHARE of the picture or more."""
    cells = surface_cells(sight)
    objects = {}
    for surface, (path, _, _) in enumerate(sight["surfaces"]):
        objects.setdefault(object_of(path), []).append(surface)
    found = []
    for name, surfaces in objects.items():
        mask = np.isin(cells, surfaces)
        if mask.mean() >= ONE_OBJECT_SHARE:
            found.append(finding(LITTLE_SEEN, number, picture, name, mask,
                                 f"the picture shows little of the place, {name} fills {mask.mean():.0%} of it"))
    return found


def picture_findings(number, picture, image):
    """Every finding on one picture (none without a sight record)."""
    sight = picture["sight"]
    if sight is None:
        return []
    plain_cells = plain_mask(image, surface_cells(sight).shape)
    return (blocking(number, picture, sight, plain_cells) + stray_planes(number, picture, sight, image)
            + untextured(number, picture, sight, plain_cells) + one_object(number, picture, sight)
            + one_plane(number, picture, sight))


def neighbour_of(path):
    """The neighbouring place a prim under /<place>/Places/<neighbour> belongs to."""
    parts = path.split("/")
    return parts[parts.index("Places") + 1]


def intruders(evidence):
    """{neighbour: its meshes inside the room, deepest first} over every stage the pictures were drawn from."""
    found = {}
    for meshes in evidence.get("rooms", {}).values():
        for item in meshes:
            found.setdefault(neighbour_of(item["prim"]), []).append(item)
    return {neighbour: sorted(meshes, key=lambda item: -item["depth"]) for neighbour, meshes in found.items()}


def best_view(evidence, prims):
    """(picture number, the cells meeting the prims) of the picture showing most of them; picture 0 with no cells
    when none shows them."""
    best = (0, None)
    for number, picture in enumerate(evidence["pictures"]):
        sight = picture["sight"]
        if sight is None:
            continue
        numbers = [index for index, (path, _, _) in enumerate(sight["surfaces"]) if path in prims]
        cells = np.isin(surface_cells(sight), numbers)
        if best[1] is None or cells.sum() > best[1].sum():
            best = (number, cells)
    return best


def neighbours_inside(evidence):
    """One finding a neighbour standing inside the room."""
    found = []
    for neighbour, meshes in intruders(evidence).items():
        number, cells = best_view(evidence, {item["prim"] for item in meshes})
        if cells is None:
            cells = np.zeros(tuple(reversed(seen.GRID)), dtype=bool)
        deepest = meshes[0]
        shown = "marked where the picture shows it" if cells.any() else "not in view of any picture"
        found.append(finding(INSIDE, number, evidence["pictures"][number], deepest["prim"], cells,
                             f"{neighbour} stands inside the room: {len(meshes)} of its meshes, {deepest['prim']} "
                             f"{deepest['depth']} m in ({shown})"))
    return found


def worst_each(found):
    """One finding per rule and prim: the one covering most of its picture. A prim found as a blocking plane is not
    found again as untextured or little seen: the blocking plane says it."""
    blocked = {item["prim"] for item in found if item["rule"] == BLOCKING}
    kept = {}
    for item in found:
        key = (item["rule"], item["prim"])
        if item["rule"] != BLOCKING and item["prim"] in blocked:
            continue
        if key not in kept or item["share"] > kept[key]["share"]:
            kept[key] = item
    return sorted(kept.values(), key=lambda item: (item["rule"], -item["share"]))


def findings(evidence, folder):
    """Every finding of a place's evidence, the worst picture of each."""
    found = []
    for number, picture in enumerate(evidence["pictures"]):
        image = Image.open(folder / picture["file"]).convert("RGB")
        found += picture_findings(number, picture, image)
    return worst_each(found) + neighbours_inside(evidence)


def verdict(evidence, found):
    """fail on any finding, unknown when no picture had a sight record to judge, else pass."""
    if found:
        return "fail"
    return "pass" if any(picture["sight"] for picture in evidence["pictures"]) else "unknown"


def read(folder):
    """The evidence of a place's folder."""
    return json.loads((folder / measure.EVIDENCE).read_text())
