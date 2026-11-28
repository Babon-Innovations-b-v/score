"""A made model's faces cut to what shows (2099's prologue, 2026-11-28: every TRELLIS.2 model over 2 m came at 500k
faces whatever it was and however far it stood, the prologue's made models at 28 million, the square's checks dead
for memory at 73 million, more than a game draws): TRELLIS.2's meshes are uniformly dense, marching-cube triangles on
a flat panel as on a knob, so the waste is where the surface is flat, and a face count set by the distance kept it all
(a walker's eye comes within 0.3 m of nearly everything: the window's security bars kept 236k faces).

    error_bound(near)                      -> the metres a cut may move the surface seen from `near` m
    simplified(points, faces, bound)       -> the faces of a quadric-error cut of (points, faces) within `bound` m
    with_cut(document, binary, bound)      -> (document, binary): every mesh cut within `bound` in its scene's frame
    budgeted(final, near)                  -> the made GLB at `final` cut in place; its counts
    nearest(folder)                        -> {made entry: metres from the nearest walker's eye} in a laid place
    rebudgeted(folder, entry, near)        -> a made entry cut and taken in again (same draft)

A cut is meshoptimizer's quadric-error simplification (meshopt_simplifyWithAttributes, MIT) with an absolute error:
the surface may move by what a pixel of 2099's walker camera (VIEW_DEGREES tall on VIEW_ROWS rows) subtends at the
nearest a walker's eye comes, and always by LEAST_ERROR (0.5 mm: an eye 0.3 m off still keeps sub-millimetre detail),
so a flat panel gives up its faces and an edge, a ridge or a small knob keeps its own; each kept vertex's smooth
normal is an attribute of the cut (NORMAL_CHANGE, a fixed weight), so near at hand a long triangle tilted within the
bound draws no crease in the shading. Every open edge is locked (SIMPLIFY_LOCK_BORDER: a model's outline, a part's
boundary, a moving part's split, each its own primitive), a UV seam is kept (under SEAM_FREE its vertices and its
faces' locked, else collapsed only along it), only existing vertices are kept (every attribute of a kept vertex as it
was) and no face is added. Each primitive's indices and vertex attributes are the cut's; the rest of the GLB (nodes
and their matrices, moving parts, materials, pictures) is kept byte for byte.

`make` knows no distance and cuts at NEAREST; `budget <folder>`, after a place is laid, reads how near the walkers'
eyes come to each made model (the scene package's eyes: ready's walkers' floor with every door open, LOOK_HEIGHTS over
it) and `budget <folder> --entry <e> --near <m>` cuts each to that, taking it into score_lib again.
"""
import json
import math
import pathlib

import numpy as np

from score.stages.place_build.maker import glb, repair

VIEW_ROWS = 1080  # 2099's viewport height (project.godot)
VIEW_DEGREES = 70.0  # its walker camera's field of view, top to bottom (game/player/walker.tscn)
NEAREST = 0.3  # metres: no eye comes nearer a surface (a walker's half WALKWAY, leaning in)
LEAST_ERROR = 0.0005  # metres a cut may always move the surface (0.5 mm)
# a kept vertex's smooth normal moved NORMAL_CHANGE costs LEAST_ERROR (none: the wardrobe's flat door drew a crease
# along a long triangle tilted within the bound; scaled with the bound, the square's launch tower 426 m off kept 238k
# faces of 486k, 32k at this fixed weight; 2026-11-28)
NORMAL_CHANGE = 0.005
# under SEAM_FREE metres of bound a UV seam's vertices and those of every face touching it are locked (collapsed along
# its seam, a chart's edge went straight across its atlas gutter: the capsule's indicator lamp showed dark specks; a
# vertex next to a concave chart edge moved its triangle over the gutter: a speck on the stairwell's door handle at
# any bound, 2026-11-28); over it they may go (the launch tower 426 m off: 168k faces locked, 32k free)
SEAM_FREE = 0.01


def error_bound(near):
    """The metres a cut may move the surface seen from `near` metres (None: NEAREST): what a pixel subtends there, at
    least LEAST_ERROR."""
    metres = NEAREST if near is None else max(float(near), 0.0)
    return max(LEAST_ERROR, metres * math.radians(VIEW_DEGREES) / VIEW_ROWS)


def smooth_normals(points, faces):
    """Each vertex's smooth normal: the area-weighted normal of the faces round its position (a UV seam's copies share
    one), unit length."""
    _, spot = np.unique(points, axis=0, return_inverse=True)
    spot = spot.reshape(-1)
    crossed = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    summed = np.zeros((spot.max() + 1, 3))
    np.add.at(summed, spot[faces].reshape(-1), np.repeat(crossed, 3, axis=0))
    normals = summed[spot]
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-20)


def simplifier():
    """meshoptimizer's meshopt_simplifyWithAttributes with its C signature declared (the package's own wrapper passes
    its sizes and error untyped, and crashed)."""
    import ctypes
    from meshoptimizer._loader import lib
    pointer, size = ctypes.c_void_p, ctypes.c_size_t
    function = lib.meshopt_simplifyWithAttributes
    function.argtypes = [pointer, pointer, size, pointer, size, size, pointer, size, pointer, size, pointer, size,
                         ctypes.c_float, ctypes.c_uint, pointer]
    function.restype = size
    return function


def simplified(points, faces, bound):
    """The faces (k x 3, indices into `points`) of meshoptimizer's quadric-error cut of (points, faces) that moves the
    surface by `bound` (points' units) at most, a kept vertex's smooth normal moved by NORMAL_CHANGE counted as
    LEAST_ERROR (so the shading holds near and gives way with the bound far off), its open edges locked and, under
    SEAM_FREE, its UV seams' vertices (a position several vertices share) with every vertex of a face touching one;
    never more faces than given."""
    import meshoptimizer
    faces = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    flat = np.ascontiguousarray(faces.reshape(-1), dtype=np.uint32)
    kept = np.zeros(len(flat), dtype=np.uint32)
    corners = np.ascontiguousarray(points, dtype=np.float32)
    normals = np.ascontiguousarray(smooth_normals(np.asarray(points, dtype=np.float64), faces), dtype=np.float32)
    weights = np.full(3, LEAST_ERROR / NORMAL_CHANGE, dtype=np.float32)
    _, spot, shared = np.unique(np.asarray(points), axis=0, return_inverse=True, return_counts=True)
    locked = np.zeros(len(corners), dtype=np.uint8)
    if float(bound) < SEAM_FREE:
        locked[faces[(shared[spot.reshape(-1)] > 1)[faces].any(axis=1)].reshape(-1)] = 1
    options = meshoptimizer.SIMPLIFY_LOCK_BORDER | meshoptimizer.SIMPLIFY_ERROR_ABSOLUTE
    count = simplifier()(kept.ctypes.data, flat.ctypes.data, len(flat), corners.ctypes.data, len(corners), 12,
                         normals.ctypes.data, 12, weights.ctypes.data, 3, locked.ctypes.data, 0, float(bound),
                         options, None)
    if count > len(flat) or count % 3:
        raise RuntimeError(f"meshoptimizer gave {count} indices for {len(flat)}")
    return kept[:count].reshape(-1, 3).astype(np.int64)


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
    """The one indexed triangle primitive of a node's mesh, with no morph targets; refused for any other."""
    primitives = document["meshes"][document["nodes"][node]["mesh"]]["primitives"]
    if len(primitives) != 1 or primitives[0].get("mode", 4) != 4 or "indices" not in primitives[0] \
            or primitives[0].get("targets"):
        raise ValueError(f"node {document['nodes'][node].get('name')}: not one indexed triangle primitive")
    return primitives[0]


def faces_of(document):
    return sum(document["accessors"][primitive(document, node)["indices"]]["count"] // 3
               for node, _ in mesh_frames(document))


def copied_accessor(document, number):
    """A copy of accessor `number` on a new buffer view of its own (a writer may share one accessor between meshes:
    trimesh does identical arrays); the copy's number."""
    document["bufferViews"].append({"buffer": 0, "byteOffset": 0, "byteLength": 0})
    document["accessors"].append({**document["accessors"][number], "bufferView": len(document["bufferViews"]) - 1})
    return len(document["accessors"]) - 1


def with_cut(document, binary, bound):
    """(document, binary): every mesh's primitive cut within `bound` metres in its scene's frame (`simplified`), its
    kept vertices alone left with every attribute as it was; all else of the GLB as it was. A primitive the cut does not
    change is left untouched."""
    pieces, shared = {}, {}
    for node, _ in mesh_frames(document):
        found = primitive(document, node)
        for number in [found["indices"], *found["attributes"].values()]:
            shared[number] = shared.get(number, 0) + 1
    for node, frame in mesh_frames(document):
        found = primitive(document, node)
        points = repair.accessor_array(document, binary, found["attributes"]["POSITION"]).astype(np.float64)
        faces = repair.accessor_array(document, binary, found["indices"]).reshape(-1, 3).astype(np.int64)
        cut = simplified(points @ frame[:3, :3].T + frame[:3, 3], faces, bound)
        if len(cut) == len(faces):
            continue
        kept, cut = np.unique(cut, return_inverse=True)
        columns = {name: repair.accessor_array(document, binary, number)[kept]
                   for name, number in found["attributes"].items()}
        for attribute, values in [*columns.items(), ("indices", cut.reshape(-1))]:
            number = found["indices"] if attribute == "indices" else found["attributes"][attribute]
            if shared[number] > 1:  # another primitive still reads it: this one's cut goes on a copy
                shared[number] -= 1
                number = copied_accessor(document, number)
            found.update(indices=number) if attribute == "indices" else found["attributes"].update({attribute: number})
            pieces[document["accessors"][number]["bufferView"]] = repair.with_accessor(document, number, values)
    return document, glb.with_views(document, binary, pieces)


def budgeted(final, near):
    """The made GLB at `final` cut in place within error_bound(near) when that drops a face;
    {near_m, error_m, faces_before, faces}."""
    document, binary = glb.read(final)
    bound, before = error_bound(near), faces_of(document)
    document, binary = with_cut(document, binary, bound)
    counts = {"near_m": round(NEAREST if near is None else max(float(near), 0.0), 3), "error_m": round(bound, 6),
              "faces_before": int(before), "faces": int(faces_of(document))}
    if counts["faces"] < before:
        glb.write(final, document, binary)
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


def entry_version(folder, entry):
    """The version of `entry` the place lays (its newest under the place's assets), else the library's newest (a made
    entry no place lays yet, cut as seen from NEAREST)."""
    import os
    from score.stages import place_build
    laid = sorted((pathlib.Path(folder) / "assets" / "model" / entry).glob("*"), key=lambda path: int(path.name))
    if laid:
        return laid[-1].name
    held = pathlib.Path(os.environ.get("SCORE_LIB_ROOT") or ".") / "entries" / "model" / entry
    versions = sorted((path.name for path in held.glob("*") if path.name.isdigit()), key=int)
    if not versions:
        raise place_build.Refused(f"{entry}: neither laid in {folder} nor in the library")
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
    """The made `entry` (its version the place laid, else the library's newest; its files the library's, never the
    place's copies, which `put` converted: the pad's rocket laid only its USD, 2026-11-28) cut within error_bound(near)
    and taken into score_lib again as the same draft (take-in writes a changed draft over), its record's `budget` the
    counts; its hulls, physics and moving parts as made. Nothing taken in when the cut drops no face. The counts."""
    from score.stages import place_build
    from score.stages.place_build import maker
    version = entry_version(folder, entry)
    record = library_record(entry, version)
    if record.get("state") != "draft":
        raise place_build.Refused(f"{entry}@{version} is {record.get('state')}, not a draft: cut it as a new version")
    work = pathlib.Path(folder) / "made" / entry
    work.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in record["files"]:
        reference = place_build.library_files.reference(f"model/{entry}@{version}", name)
        found = place_build.library_files.resolve(reference)
        if found is None:
            raise place_build.Refused(f"{reference}: the library does not hold this file")
        files[name] = work / name
        files[name].write_bytes(pathlib.Path(found).read_bytes())
    counts = budgeted(work / f"{entry}-final.glb", near)
    if counts["faces"] == counts["faces_before"]:
        return {"entry": entry, **counts, "taken_in": None}
    record_of(work / f"{entry}.json", counts)
    made_with = [{"what": made["what"], "source": made["by"]} for made in record["provenance"]["made_with"]]
    address = maker.taken_in(entry, files, record["title"], made_with, work)
    return {"entry": entry, **counts, "taken_in": address}
