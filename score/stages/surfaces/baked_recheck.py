"""finish-route-recheck made on what the bake made (#100, owner's choice of 2026-11-25, option 1): each take's views
are drawn in the bake's own base colour map, so the recheck sees a worn recipe's bare (the hub's consoles: the token
hull-grey drawn flat passed while the bake laid rust over half of each), and its question says the pictures show the
baked colour, wear and pattern. surfaces-bake is a declared input of the row (stages.baked_rechecked).

The mapping: the views row's model is the raw take welded and normalised, its faces in the raw take's order; the
bake's labelled take (`labelled/<take>/`, one .ply a surface, faces.npz each raw face's surface) holds the same faces
laid on the finished model, levelled and cut to its box, then laid into the kit frame its made model stands in
(laid_take, as bake_check.laid_parts lays it: turned, refitted and stood square by its baked.json entry). A surface
whose .ply keeps every raw face of that surface pairs its faces with the raw take's one to one; the affine frame from
the views' frame into the kit frame is fitted on those pairs (least squares, again without the pairs over
FIT_OUTLIER times the median miss until none drops: the levelled feet). Each face of the views is then drawn in the
baked colour of the made model's triangle nearest it in the kit frame (each triangle's texel at its middle,
baked_gltf.base_colours); a face further than FAR_SHARE of the model's largest side from every baked triangle (a
detail the cut-down copy did not keep) keeps its flat library colour. bake_check.py is not imported, so an edit of
the check moves no recheck. A take of several models is drawn from its first by name. A take the bake made no model for,
with no base colour map, no surface to pair or a fit missing over FIT_MISS of its laid size is drawn flat as before
and asked the flat question, the reason kept in drawn.json.

Set on the row in the table, as bake_fitted is on the bake, so no row reading route_recheck.py (finish-route-picks
asks its question of the drafted parts before any bake, flat) moves. Output: route_recheck's, with drawn.json
({take: how its views were drawn}).
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import route_recheck  # noqa: E402

CALLER = route_recheck.CALLER
FLAT_DRAWN, FLAT_BODY = route_recheck.drawn, route_recheck.recheck_body  # route_recheck's own, the flat way
FILE = "drawn.json"
FIT_OUTLIER = 3.0
FIT_ROUNDS = 5  # fits at most, each without the pairs the one before it missed by over FIT_OUTLIER medians
FIT_MISS = 0.02  # a fit whose median pair lies over 2% of the laid model's largest side off is no frame
FIT_PAIRS = 20000  # pairs fitted at most, spread over the take
FAR_SHARE = 0.05  # a face over 5% of the laid model's largest side from every baked triangle keeps its flat colour
QUESTION = route_recheck.QUESTION.replace(
    "each part\ndrawn flat in its library surface's colour, shaded only by angle: no shine, wear or pattern is drawn, so "
    "judge\nroughness and metal from the words below, colour from the pictures.",
    "each part\ndrawn in the colours the bake gave it (its base colour map: the wear, rust, dirt and pattern it laid), "
    "shaded only by\nangle: no shine is drawn, so judge roughness and metal from the words below, colour and wear from "
    "the pictures.")
if QUESTION == route_recheck.QUESTION:
    raise RuntimeError("route_recheck.QUESTION no longer says the views are drawn flat: word the baked question again")


def ask(bodies):
    """The row's one batch, as route_recheck asks it (the table's claude_asks sets this module's `ask`)."""
    return route_recheck.route_ask.asked(bodies, CALLER)


def raw_pairs(names, surface, plys):
    """(raw face indices, laid face indices) of every surface whose .ply kept all of its raw faces: `names` and
    `surface` the labelled take's faces.npz (each raw face's surface by index into names), `plys` each .ply's face
    count by surface name, in laid_take's order (its faces concatenated)."""
    named = np.asarray(names)[surface]
    raw, laid, start = [], [], 0
    for name, count in plys:
        faces = np.flatnonzero(named == name)
        if len(faces) == count:
            raw.append(faces)
            laid.append(start + np.arange(count))
        start += count
    return ((np.concatenate(raw), np.concatenate(laid)) if raw else
            (np.zeros(0, dtype=int), np.zeros(0, dtype=int)))


def fitted_frame(source, target):
    """The affine frame (4 x 3: points with a 1 appended, times it) taking `source` points onto `target`, least squares,
    fitted again without the pairs over FIT_OUTLIER times the kept pairs' median miss until none drops (at most
    FIT_ROUNDS fits); and the median miss of the pairs kept."""
    lifted = np.hstack([source, np.ones((len(source), 1))])
    kept = np.ones(len(source), dtype=bool)
    for _ in range(FIT_ROUNDS):
        frame = np.linalg.lstsq(lifted[kept], target[kept], rcond=None)[0]
        miss = np.linalg.norm(lifted @ frame - target, axis=1)
        within = miss <= max(FIT_OUTLIER * float(np.median(miss[kept])), 1e-9)
        if within.sum() < 4 or (within == kept).all():
            break
        kept = within
    return frame, float(np.median(miss[kept]))


def face_colours(points, baked_points, baked_colours, far):
    """Each point's baked colour (sRGB 0-255): its nearest baked triangle's; and which points lie within `far` of one."""
    from scipy.spatial import cKDTree
    distance, nearest = cKDTree(baked_points).query(points)
    colours = np.clip(np.asarray(baked_colours)[nearest] * 255, 0, 255).astype(np.uint8)
    return colours, distance <= far


def baked_model(gltf):
    """A baked .gltf's mesh over all its maps and each map's pictures by role (baked_gltf, as bake_check.gltf_model
    reads it; its own here, so no edit of the check moves this row)."""
    import baked_gltf
    document, views = baked_gltf.read(gltf)
    return baked_gltf.geometry(document, views), baked_gltf.maps(document, gltf)


def laid_take(labelled, entry):
    """A labelled take's surfaces (one .ply each, by name) as one mesh laid into the kit frame its made model stands
    in (stored_parts.kit_frame, as bake_check.laid_parts lays them): (surface names, the mesh, each face's surface)."""
    import trimesh
    import stored_parts
    paths = sorted(labelled.glob("*.ply"))
    meshes = [trimesh.load(path, process=False) for path in paths]
    joined = trimesh.util.concatenate(meshes)
    laid = stored_parts.kit_frame(np.asarray(joined.vertices), np.array(entry["base"]).reshape(3, 3), entry["size"])
    codes = np.concatenate([np.full(len(mesh.faces), code) for code, mesh in enumerate(meshes)])
    return [path.stem for path in paths], trimesh.Trimesh(laid, joined.faces, process=False), codes


def baked_faces(views, bake, take):
    """The views model's faces in the bake's colours: (each face's sRGB 0-255, which faces it reached, the note), or
    (None, None, why not)."""
    import baked_gltf
    import route_split
    baked = json.loads((bake / "baked.json").read_text()) if (bake / "baked.json").exists() else {}
    models = sorted(model for model, entry in baked.items() if entry.get("parts") == take)
    if not models:
        return None, None, {"drawn": "flat", "why": "the bake made no model of this take"}
    model, entry = models[0], baked[models[0]]
    labelled = bake / "labelled" / take
    if not (labelled / "faces.npz").exists():
        return None, None, {"drawn": "flat", "why": f"no labelled faces of {take} in the bake"}
    geometry, maps = baked_model(bake / "made" / f"{model}.gltf")
    if not maps or any("base_color" not in pictures for pictures in maps):
        return None, None, {"drawn": "flat", "why": f"{model}: no base_color map"}
    colours = baked_gltf.base_colours(geometry, maps)[0]
    names, laid, codes = laid_take(labelled, entry)
    faces = np.load(labelled / "faces.npz")
    raw, paired = raw_pairs(faces["names"], faces["surface"],
                            [(name, int((codes == code).sum())) for code, name in enumerate(names)])
    if len(raw) < 4:
        return None, None, {"drawn": "flat", "why": f"{model}: no surface of the labelled take keeps its raw faces"}
    mesh = route_split.model_of(views)
    centres = mesh.triangles_center
    spread = np.linspace(0, len(raw) - 1, min(len(raw), FIT_PAIRS)).astype(int)
    frame, miss = fitted_frame(centres[raw[spread]], laid.triangles_center[paired[spread]])
    size = float(np.max(entry["size"]))
    if miss > FIT_MISS * size:
        return None, None, {"drawn": "flat", "why": f"{model}: the fit misses by {miss:.4f} m of {size:.3f} m"}
    corners = geometry["positions"][geometry["triangles"]]
    far = FAR_SHARE * size
    drawn, reached = face_colours(np.hstack([centres, np.ones((len(centres), 1))]) @ frame, corners.mean(axis=1),
                                  colours, far)
    return drawn, reached, {"drawn": "baked", "model": model, "pairs": int(len(raw)), "miss_m": round(miss, 5),
                            "reached": round(float(reached.mean()), 4)}


def drawn_baked(folders, every, record, tokens, bake, notes):
    """route_recheck.drawn with each face in the bake's colour where the bake reached it (baked_faces), else flat in
    its library colour as route_recheck draws it; the note kept in `notes` by take, the pictures marked `baked`."""
    from PIL import Image
    import finish_parts
    import route_cast as cast
    import route_split
    take = folders["views"].name
    colours, reached, note = baked_faces(folders["views"], bake, take)
    notes[take] = note
    if colours is None:
        return {**FLAT_DRAWN(folders, every, record, tokens), "baked": False}
    mesh = route_split.model_of(folders["views"])
    part_of = np.load(folders["parts"] / "parts.npy").astype(int)
    flat = finish_parts.surface_colours(every, {row["judge"] for row in record["parts"]})
    by_part = np.array([route_recheck.token_colour(row["settings"]["token"], tokens) if row.get("settings")
                        else flat[row["judge"]] for row in record["parts"]], dtype=np.uint8)
    by_face = np.where(reached[:, None], colours, by_part[part_of])
    angles = json.loads((folders["views"].parent / "views.json").read_text())[folders["views"].name]["views"]
    faces = np.load(folders["views"] / "faces.npz")
    folders["out"].mkdir(parents=True)
    for view in faces.files:
        cast.picture(cast.face_painted(by_face, faces[view]), faces[view],
                     cast.shading(mesh, faces[view], angles[view])).save(folders["out"] / f"checked-{view}.png")
    return {"views": list(faces.files), "close_up": Image.open(folders["views"] / "close-up.png"),
            "drawn": [Image.open(folders["out"] / f"checked-{view}.png") for view in faces.files], "baked": True}


def body_baked(pictures, entry, finishes, context):
    """route_recheck.recheck_body, asked the baked question (QUESTION) where the views were drawn baked."""
    if not pictures.get("baked"):
        return FLAT_BODY(pictures, entry, finishes, context)
    flat = route_recheck.QUESTION
    route_recheck.QUESTION = QUESTION
    try:
        return FLAT_BODY(pictures, entry, finishes, context)
    finally:
        route_recheck.QUESTION = flat


def make_recheck(inputs, out, seed, params):
    """route_recheck.make_recheck with every take's views drawn from the bake (inputs["surfaces-bake"]) and asked so,
    its asks through this module's `ask`; drawn.json."""
    bake, notes = pathlib.Path(inputs["surfaces-bake"]), {}
    held = route_recheck.drawn, route_recheck.recheck_body, route_recheck.ask
    route_recheck.drawn = lambda folders, every, record, tokens: drawn_baked(folders, every, record, tokens, bake,
                                                                             notes)
    route_recheck.recheck_body = body_baked
    route_recheck.ask = lambda bodies: ask(bodies)
    try:
        route_recheck.make_recheck(inputs, out, seed, params)
    finally:
        route_recheck.drawn, route_recheck.recheck_body, route_recheck.ask = held
    (out / FILE).write_text(json.dumps(notes, indent=1))
