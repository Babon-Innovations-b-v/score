"""A made model's face budget (2099's prologue, 2026-11-28: every TRELLIS.2 model over 2 m came at 500k faces whatever
it was and however far it stood, the pad's 52 at 18.9 million, more than a game draws a place and more than three
laying checks held in memory): the faces a model needs are those that show from the nearest a player's eye comes.

    faces_seen(area, hull, near)           -> the faces a model of surface `area` and convex hull surface `hull` (m^2)
                                              needs seen from `near` m
    areas_of(document, binary)             -> the GLB's surface and its convex hull's (m^2) in its scene's frame
    with_cut(document, binary, cut_document, cut_binary) -> (document, binary): each mesh's geometry the cut's
    budgeted(final, near, work)            -> the made GLB at `final` cut to its budget in place; its counts
    nearest(folder)                        -> {made entry: metres from the nearest walker's eye} in a laid place
    rebudgeted(folder, entry, near)        -> a laid made entry cut to its budget and taken in again (same draft)

`make` cuts at NEAREST (where it will stand is not known yet: only a small model is cut); `budget <folder>`, after a
place is laid, reads how near the walkers' eyes come to each made model (the scene package's eyes: ready's walkers'
floor with every door open, LOOK_HEIGHTS over it) and cuts each to that, taking it into score_lib again.

A model seen from `near` m (at least NEAREST) by the game's view (2099's walker camera: VIEW_DEGREES tall on VIEW_ROWS
rows) needs the more of: one face a FACE_PIXELS patch of its whole surface seen square on (what the view resolves of
a surface held close), and SHOWN_FACES a pixel of its outline (its convex hull's mean outline, a quarter of the hull's
surface by Cauchy's formula, in pixels), which keeps a far thin thing whole (the pad's ferris wheel at 400 m: its
spokes went to blobs at 17k faces and 50k, held at 180k, made at 452k on 5,458 pixels). Blender's quadric edge
collapse (budget_blender.py) spends them where the shape bends, so a flat side gives its faces to the silhouette, the
small hardware and the holes. A model is never given more faces than it holds,
nor cut under LEAST: a 2 cm nail keeps a round head. Every attribute of a primitive is the cut's; the rest of the GLB
(nodes and their matrices, moving parts, materials, pictures) is kept byte for byte.
"""
import json
import math
import pathlib
import subprocess

import numpy as np

from score.stages.place_build.maker import glb, repair

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "budget_blender.py"
VIEW_ROWS = 1080  # 2099's viewport height (project.godot)
VIEW_DEGREES = 70.0  # its walker camera's field of view, top to bottom (game/player/walker.tscn)
SHOWN_FACES = 16  # faces a pixel of the model's outline (front and back, and its depth: a wheel's spokes)
FACE_PIXELS = 2.0  # screen pixels a face covers seen nearest (4 drew a door knob's highlight in facets at 0.5 m)
NEAREST = 0.3  # metres: no eye comes nearer a surface (a walker's half WALKWAY, leaning in)
LEAST = 2000  # faces no model is cut under
MEMORY_GB = 6  # the Blender's scope: a 500k-face model held 1.6 GB
KEPT_ATTRIBUTES = {"POSITION", "NORMAL", "TEXCOORD_0"}


def faces_seen(area, hull, near):
    """The faces a model of surface `area` and convex hull surface `hull` (square metres) needs seen from `near`
    metres (None: NEAREST)."""
    square_pixels = (VIEW_ROWS / math.radians(VIEW_DEGREES) / max(float(near or NEAREST), NEAREST)) ** 2  # a m^2's
    surface = float(area) * square_pixels / FACE_PIXELS
    shown = float(hull) / 4 * square_pixels * SHOWN_FACES
    return max(LEAST, int(math.ceil(max(surface, shown))))


def node_matrix(node):
    """A node's own matrix (4x4, row-major as numpy gives it); refused for a TRS node (the maker writes matrices)."""
    if any(key in node for key in ("translation", "rotation", "scale")):
        raise ValueError(f"node {node.get('name')}: a TRS transform; the maker's GLBs carry matrices")
    return np.asarray(node.get("matrix", np.eye(4).T.reshape(-1)), dtype=float).reshape(4, 4).T


def mesh_frames(document):
    """[(node index, its matrix in the scene's frame)] for every node drawing a mesh."""
    found, stack = [], [(number, np.eye(4)) for number in document["scenes"][document.get("scene", 0)]["nodes"]]
    while stack:
        number, above = stack.pop()
        node = document["nodes"][number]
        frame = above @ node_matrix(node)
        if "mesh" in node:
            found.append((number, frame))
        stack.extend((child, frame) for child in node.get("children", []))
    return found


def primitive(document, node):
    """The one indexed triangle primitive of a node's mesh; refused for any other."""
    primitives = document["meshes"][document["nodes"][node]["mesh"]]["primitives"]
    if len(primitives) != 1 or primitives[0].get("mode", 4) != 4 or "indices" not in primitives[0]:
        raise ValueError(f"node {document['nodes'][node].get('name')}: not one indexed triangle primitive")
    return primitives[0]


def areas_of(document, binary):
    """(surface, its convex hull's surface) in m^2 of every mesh the GLB draws, in its scene's frame."""
    from scipy.spatial import ConvexHull
    total, every = 0.0, []
    for node, frame in mesh_frames(document):
        found = primitive(document, node)
        points = repair.accessor_array(document, binary, found["attributes"]["POSITION"]) @ frame[:3, :3].T
        faces = repair.accessor_array(document, binary, found["indices"]).reshape(-1, 3)
        total += float(repair.areas(points, faces).sum())
        every.append(points)
    return total, float(ConvexHull(np.vstack(every), qhull_options="QJ").area)  # QJ: a flat model too


def faces_of(document):
    return sum(document["accessors"][primitive(document, node)["indices"]]["count"] // 3
               for node, _ in mesh_frames(document))


def welded(values, faces):
    """(values, faces) with vertices of equal values made one (Blender writes a vertex a face where it has no normal
    to keep)."""
    kept, back = np.unique(values, axis=0, return_inverse=True)
    return kept, back.reshape(-1)[faces]


def cut_geometry(document, binary, node, cut_document, cut_binary, cut_node):
    """{attribute: values} and faces of `node`'s primitive as the cut's `cut_node` holds them: the original's
    attributes only, refused when the cut lacks one."""
    mine, theirs = primitive(document, node), primitive(cut_document, cut_node)
    names = sorted(mine["attributes"])
    if set(names) - KEPT_ATTRIBUTES or set(names) - set(theirs["attributes"]):
        raise ValueError(f"node {document['nodes'][node].get('name')}: attributes {names}, the cut holds "
                         f"{sorted(theirs['attributes'])}")
    columns = [np.asarray(repair.accessor_array(cut_document, cut_binary, theirs["attributes"][name]), np.float64)
               for name in names]
    faces = np.asarray(repair.accessor_array(cut_document, cut_binary, theirs["indices"])).reshape(-1, 3)
    widths = np.cumsum([0] + [column.shape[1] for column in columns])
    values, faces = welded(np.hstack(columns), faces)
    return {name: values[:, widths[number]:widths[number + 1]] for number, name in enumerate(names)}, faces


def own_accessor(document, number, taken):
    """Accessor `number`, or, when another primitive already took it (`taken`, a writer may share one between
    meshes: trimesh does identical arrays), a copy of it on a new buffer view; its number, marked taken."""
    if number in taken:
        document["bufferViews"].append({"buffer": 0, "byteOffset": 0, "byteLength": 0})
        document["accessors"].append({**document["accessors"][number], "bufferView": len(document["bufferViews"]) - 1})
        number = len(document["accessors"]) - 1
    taken.add(number)
    return number


def with_cut(document, binary, cut_document, cut_binary):
    """(document, binary): every mesh's primitive given the geometry of the cut's mesh at the node of its name, all
    else of the GLB as it was."""
    theirs = {node.get("name"): number for number, node in enumerate(cut_document["nodes"]) if "mesh" in node}
    pieces, taken = {}, set()
    for node, _ in mesh_frames(document):
        name = document["nodes"][node].get("name")
        if name not in theirs:
            raise ValueError(f"the cut has no mesh node {name!r} (it has {sorted(map(str, theirs))})")
        values, faces = cut_geometry(document, binary, node, cut_document, cut_binary, theirs[name])
        found = primitive(document, node)
        for attribute, column in [*values.items(), ("indices", faces.reshape(-1))]:
            number = own_accessor(document, found["indices"] if attribute == "indices" else
                                  found["attributes"][attribute], taken)
            found.update(indices=number) if attribute == "indices" else found["attributes"].update({attribute: number})
            pieces[document["accessors"][number]["bufferView"]] = repair.with_accessor(document, number, column)
    return document, glb.with_views(document, binary, pieces)


def cut_file(source, out, faces, log):
    """Blender's cut of the GLB at `source` to about `faces`, its geometry written at `out` (budget_blender.py)."""
    from score.stages.place_build import render
    command = render.queued(f"budget-{pathlib.Path(source).stem}", SCRIPT, [str(source), str(out), str(int(faces))],
                            card=False, seconds=1800, memory_gb=MEMORY_GB)
    done = subprocess.run(command, capture_output=True, text=True)
    pathlib.Path(log).write_text(done.stdout + done.stderr)
    if done.returncode != 0 or not pathlib.Path(out).is_file():
        raise RuntimeError(f"Blender's cut of {source} failed (exit {done.returncode}"
                           f"{render.unlinked_hint(done.returncode)}): "
                           f"{(done.stderr or done.stdout)[-400:]}")


def budgeted(final, near, work):
    """The made GLB at `final` cut in place to faces_seen of its surfaces from `near` (None: NEAREST) when it holds
    more; {near_m, area_m2, hull_m2, faces_before, faces_asked, faces}."""
    document, binary = glb.read(final)
    (area, hull), before = areas_of(document, binary), faces_of(document)
    asked = faces_seen(area, hull, near)
    counts = {"near_m": round(max(float(near or NEAREST), NEAREST), 3), "area_m2": round(area, 4),
              "hull_m2": round(hull, 4),
              "faces_before": int(before), "faces_asked": int(asked), "faces": int(before)}
    if asked >= before:
        return counts
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    cut = work / f"{pathlib.Path(final).stem}-cut.glb"
    cut_file(final, cut, asked, work / "budget.log")
    cut_document, cut_binary = glb.read(cut)
    document, binary = with_cut(document, binary, cut_document, cut_binary)
    glb.write(final, document, binary)
    cut.unlink()
    counts["faces"] = int(faces_of(document))
    return counts


def record_of(path, counts):
    """The made record at `path` with its `budget` counts."""
    record = json.loads(pathlib.Path(path).read_text())
    record["budget"] = counts
    pathlib.Path(path).write_text(json.dumps(record, indent=1))


def nearest(folder):
    """{made entry id: metres from the nearest walker's eye to its laid box} over every TRELLIS.2 entry laid in the
    place (its copies' least), the eyes thinned as the scene package's (each read less its cube's diagonal); {} when
    the place has no walkers' floor."""
    from pxr import Usd, UsdGeom
    import scipy.spatial
    from score.stages import place_build
    from score.stages.place_build import ready, scene_package
    folder = pathlib.Path(folder)
    stage = Usd.Stage.Open(str(place_build.scene_path(folder)))
    place = place_build.record_of(folder)["place"]
    laid = ready.Place(stage, place)
    eyes = scene_package.thinned(ready.look_points(ready.walkers_floor(laid)[:4])) if laid.names else np.zeros((0, 3))
    if not len(eyes):
        return {}
    tree = scipy.spatial.cKDTree(eyes)
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = {}
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        address = prim.GetAttribute("score:library").Get() if prim.HasAttribute("score:library") else None
        entry = str(address or "").split("/", 1)[-1].split("@", 1)[0]
        if not str(address).startswith("model/") or "_trellis." not in entry:
            continue
        box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
        if box.IsEmpty():
            continue
        low, high = np.array(box.GetMin()), np.array(box.GetMax())
        middle, half = (low + high) / 2, (high - low) / 2
        # the box's distance from its nearest eye: the eyes within its half diagonal and the farthest asked
        reach = float(np.linalg.norm(half))
        candidates = tree.query_ball_point(middle, reach + float(tree.query(middle)[0]))
        outside = np.linalg.norm(np.maximum(np.abs(eyes[candidates] - middle) - half, 0.0), axis=1)
        metres = max(0.0, float(outside.min()) - scene_package.EYE_CELL * math.sqrt(3.0))
        found[entry] = min(found.get(entry, math.inf), metres)
    return {entry: round(metres, 3) for entry, metres in sorted(found.items())}


def entry_files(folder, entry):
    """The laid entry's version folder under the place's assets (its newest)."""
    from score.stages import place_build
    versions = sorted((pathlib.Path(folder) / "assets" / "model" / entry).glob("*"), key=lambda path: int(path.name))
    if not versions:
        raise place_build.Refused(f"{entry}: not laid in {folder} (no assets/model/{entry})")
    return versions[-1]


def library_record(entry, version):
    """The score_lib record of `entry` at `version` (SCORE_LIB_ROOT's checkout)."""
    import os
    from score.stages import place_build
    root = os.environ.get("SCORE_LIB_ROOT")
    path = pathlib.Path(root or ".") / "entries" / "model" / entry / str(version) / "entry.json"
    if not root or not path.is_file():
        raise place_build.Refused(f"{entry}@{version}: no library record (SCORE_LIB_ROOT={root})")
    return json.loads(path.read_text())


def rebudgeted(folder, entry, near):
    """The laid made `entry` (its files under the place's assets) cut to its budget from `near` metres and taken into
    score_lib again as the same draft (take-in writes a changed draft over), its record's `budget` the counts; its
    hulls, physics and moving parts as made. Nothing taken in when the budget cuts nothing. The counts."""
    from score.stages import place_build
    from score.stages.place_build import maker
    source = entry_files(folder, entry)
    record = library_record(entry, source.name)
    if record.get("state") != "draft":
        raise place_build.Refused(f"{entry}@{source.name} is {record.get('state')}, not a draft: cut it as a new "
                                  "version")
    work = pathlib.Path(folder) / "made" / entry
    work.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in record["files"]:
        target = work / name
        target.write_bytes((source / name).read_bytes())
        files[name] = target
    final = work / f"{entry}-final.glb"
    counts = budgeted(final, near, work / "budget")
    if counts["faces"] == counts["faces_before"]:
        return {"entry": entry, **counts, "taken_in": None}
    record_of(work / f"{entry}.json", counts)
    made_with = [{"what": made["what"], "source": made["by"]} for made in record["provenance"]["made_with"]]
    address = maker.taken_in(entry, files, record["title"], made_with, work)
    return {"entry": entry, **counts, "taken_in": address}
