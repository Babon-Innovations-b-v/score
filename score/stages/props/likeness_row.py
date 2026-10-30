"""likeness@<place>: every object of the place's prop data, made by either route, held to its close-up and to the
model checks as they exist; the row that decides each object's route.

A prop object's model is its take's bake (surfaces-bake, after the surface line's split, library paint and the bake
that makes it solid; it runs only once surfaces-check, the paint's check, passed); a code object's, or a prop object
moved to `fallback` after failing, is its code build. Each is scored against its close-up (closeup@<place>) and its
checks written to likeness.json; an object that fails any goes to code (prop route), or to a new builder (code).

The gates, each failing an object by name:
- `outline`: likeness.OUTLINE_LEAST on the best of eight ways round (likeness.py, set on the hub's accepted models).
- `likeness`: DINOv2 on the best way's silhouette, at the least likeness likeness-calibration@<place> set on the
  place's accepted models; its evidence, the pairs' scores, is gathered on a rented machine (similar.py, paid). A
  designed place (its hand-in an approved design's, prepare/handin.py) names no accepted models, so no calibration
  applies to it: it is judged on the model in its finishes against the close-up in its colours (write_textured_pair)
  at DESIGNED_LEAST, so an object passes only when both `outline` and this pass (owner, 2026-10-30).
- `close-up parts present`: a prop model's parts (surfaces-parts) own every finish its close-up's list names, but a
  code-built light's lit finishes, its lamp the light layer's (`finishes_missing`); a code object's is unknown
  (nothing measures its parts: the fittings' parts check went with the code fallback, 2026-10-22).
- `thin and in proportion`: tools/props/gates/model.py's check (thinnest wall, spread against the row's size).
- `lean`: tools/props/library/straight.py on a generated model of a kind that stands square, as it exists: code
  builds are not held to it. No rule names such a kind since the old kinds' details (data/library/details.json)
  retired with the old models (owner, 2026-10-21), so no model is held to it until one does.
Whether a model is closed is written as a measure only: 3 of the hub's 9 accepted generated models and 27 of its 83
accepted code builds are not (2026-10-12), so no gate as it exists fails an open model.
An object a batch gap names (score/stages/batch_gaps.py: a paid step of its take failed in the batch) still fails each
gate by name; the table moves those faults to complete, which lists the gaps from this output's batch-gaps.json (the
gaps of every row it read, each with its hand-in object and inventory rows). A take the thin straight route built in
code (thin_straight.py) is held to its concept crop, cut out (its take's input.png), in place of a close-up; its
close-up's gap is carried only while a free check fails it (its faults then move to complete with the gap).
"""
import dataclasses
import json
import pathlib

import numpy as np
from PIL import Image

import score.stages.batch_gaps as batch_gaps
import score.stages.props.calibration_row as calibration_row
import score.stages.props.flat_sheet as flat_sheet
import score.stages.props.likeness as likeness
import score.stages.props.prop_data as prop_data
import score.stages.props.thin_straight as thin_straight
from score.stages.surfaces.prop_env import PROPS_HOME
from score.stages.surfaces.surface_gates import guarded, unknown, verdict

# DINOv2 on a processor machine for a few hundred pairs (similar.py), rounded up.
LIKENESS_EUROS = 1.0
# The library families a lamp's lit faces take (score/stages/surfaces/finish_parts.py SEEN_THROUGH_FAMILIES: glass,
# screen and light, judged by their own colour), which a code-built light leaves to the light layer (finishes_missing).
LIT_FAMILIES = ("glass", "screen", "light")
# A sheet's words (`sheet`): a paper, a note, a card, a poster, a label.
SHEET_WORDS = ("paper", "note", "card", "poster", "label")
# The pose rules the bake's guard list reads (score/stages/surfaces/tumble.py rules_of), so drawn_size lays a model
# as the bake laid it.
POSE_RULES = {"stance rules": "{data}/checks/stance.json", "resting rules": "{data}/checks/resting.json"}
# A designed place's DINOv2 judge (owner, 2026-10-30: likeness needs both the outline and textured DINOv2): the model
# in its baked finishes against the close-up in its colours (textured study, #36: among outline-passing pairs AUC 0.92
# against the silhouettes' 0.84), scored from the outline's best way and from the way facing it (BACK; an outline is
# its back's mirror, so it cannot tell a slab's face from its back: walkway's keypad read 0.07 from its blank back,
# 0.48 from its keys), the higher kept. Its least is the house rule's (calibration_row.py's MARGIN under the least of
# the alike controls), measured on this cast (#36, 2026-10-30): of the DINOv2 study's 13 hand-checked controls the
# textured view shows 3 not alike (galley's sink and workshop's desk_front_right lie tipped on their backs, storage's
# cable_bundle is a straight rod for a curved bundle); the other 10 least walkway's handrail_left_1, 0.191. On the
# study's 280 right and 331 wrong outline-passing pairs it passes 267 and 114 (the outline alone 280 and 331).
DESIGNED_LEAST = 0.14
TEXTURED_SIDE = 256
BACK = "@back"


def files(place):
    """prop_data.likeness_files with each prop object's take's Pixal3D input (its close-up as Pixal3D cut it out,
    object_record) that is there: a take the batch made no model of has none, and its gate names the object (a batch
    gap the table moves). Here, not in prop_data.py, whose edits move the paid prop rows' code versions."""
    record = prop_data.record_at(prop_data.path_of(place)) if prop_data.applies(place) else {"objects": {}}
    return {**prop_data.likeness_files(place), **POSE_RULES,
            **{f"pixal input {row}": "{home}/work/pixal/" + f"{entry['take']}.svviews/input.png"
               for row, entry in record["objects"].items() if entry["route"] == "prop"
               and (PROPS_HOME / "work/pixal" / f"{entry['take']}.svviews/input.png").exists()},
            **{f"code take {row}": "{home}/work/pixal/" + f"{entry['take']}.svviews/{thin_straight.MARK}"
               for row, entry in record["objects"].items() if entry["route"] == "prop"
               and thin_straight.code_built(entry["take"], PROPS_HOME / "work/pixal")}}


def route_of(row, record):
    """Where an object's model comes from: "code" for a code object or a prop object moved to the fallback."""
    return "code" if record["objects"][row]["route"] == "code" or row in record.get("fallback", {}) else "prop"


def baked_models(bake):
    """{take: baked .gltf} from a surfaces-bake output (the first model baked of each take)."""
    found = {}
    for model, entry in sorted(json.loads((bake / "baked.json").read_text()).items()):
        found.setdefault(entry["parts"], bake / "made" / f"{model}.gltf")
    return found


def model_of(row, record, inputs, baked):
    """An object's model file, or None when its route made none."""
    if route_of(row, record) == "code":
        return inputs.get(f"code build {row}")
    return baked.get(record["objects"][row]["take"])


def finishes_missing(take, parts, lit=False):
    """The finishes a take's close-up lists that no part of its model owns. A code-built light's (`lit`: its row's kind
    glows, thin_straight.slender_light) finishes of a lit family (LIT_FAMILIES) are its light's: the route builds its
    post or body and leaves its lamp to the library's lamp the light layer lays, so its build never misses them (the
    square's floodlight tower, outline 0.748, failed only on "bright white glowing lamp face", 2026-10-28)."""
    entry = parts["takes"].get(take)
    if entry is None:
        return None
    owned = {row["words"] for row in entry["parts"]}
    return [finish["finish"] for finish in entry["finishes"]
            if finish["finish"] not in owned and not (lit and finish.get("family") in LIT_FAMILIES)]


def model_checks(path, size, kind, square):
    """model.py's check at the row's size (y tall; its wide and deep sides on x and z as the model's own ground sides
    lie, longer to longer: the finish's stand lays a long model's longest ground side along z, glb_file.squared, and
    model.py fits the mesh to the laid size axis by axis, so a 4 m wall pipe's elbow laid crosswise read 0.6 mm thick),
    straight.py's for a square generated kind, and whether the mesh is closed. A slender row (model.py's own rule:
    thin_straight.slender) is laid as one scale, its longest side the row's, never fitted side by side: its box's two
    short sides are its thickness, not its reach, so a sagging string's 1 m sag fitted to its 8 by 0.01 by 0.01 box
    read its 1 cm tube 0.0 m thick (2026-10-26); its proportions are the outline's to hold."""
    import trimesh
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
        import straight
    points, triangles = likeness.gltf_mesh(path)
    mesh = trimesh.Trimesh(points, triangles, process=True)
    wide, deep, tall = (float(value) for value in size)
    ground = sorted((wide, deep), reverse=mesh.extents[0] >= mesh.extents[2])
    laid = [ground[0], tall, ground[1]]
    if thin_straight.slender(size):
        laid = (mesh.extents * max(laid) / mesh.extents.max()).tolist()
    found = {"model_check": model_gate.check(kind, mesh, laid), "closed": bool(mesh.is_watertight)}
    if sheet(kind, laid):
        wall = round(through(mesh, laid, model_gate.SAMPLES), 4)
        found["model_check"].update(thinnest=wall, sheet=True,
                                    **{"pass": found["model_check"]["spread"] <= model_gate.SPREAD_LIMIT
                                       and wall >= model_gate.least_wall(laid)})
    if square:
        found["straight"] = straight.straightness(mesh)
    return found


def sheet(kind, laid):
    """Whether a kind is a sheet (SHEET_WORDS in its name, laid thinner than flat_sheet.SHEET_SHARE of its longest side),
    its wall read `through` its face rather than along its faces' normals: a sheet's warp and rounded rim tilt those
    (quarters' paper 0.6 mm and sticky note 0.3 mm, habitat's paper note 1.4 mm, each a solid sheet, round 25)."""
    return any(word in kind.lower() for word in SHEET_WORDS) and min(laid) < flat_sheet.SHEET_SHARE * max(laid)


def through(mesh, laid, samples):
    """A sheet's 5th-percentile wall once fitted to `laid` (model.py's `thinnest` fit), inside its rim: rays straight
    down its thinnest side from above it, each its first stretch inside the mesh (a ray that enters and never leaves,
    a one-sided plane, reads 0; a hollow shell reads its outer wall), none within its model's own thickness of its edge
    (the finish's voxel remesh rounds a sheet's rim over that band: quarters' sticky note, 6 mm as baked, 1 mm laid)."""
    fitted = mesh.copy()
    fitted.vertices = (fitted.vertices - fitted.bounds[0]) / np.maximum(fitted.extents, 1e-6) * np.array(laid)
    across = int(np.argmin(laid))
    rim = min(float(mesh.extents[across]), 0.25 * min(laid[side] for side in range(3) if side != across))
    starts = rim + np.random.default_rng(0).uniform(0, 1, (samples, 3)) * (np.array(laid) - 2 * rim)
    starts[:, across] = laid[across] + 0.01
    down = np.zeros((samples, 3))
    down[:, across] = -1
    where, index, _ = fitted.ray.intersects_location(starts, down, multiple_hits=True)
    heights = [np.sort(where[index == ray, across])[::-1] for ray in np.unique(index)]
    walls = [found[0] - found[1] if len(found) > 1 else 0.0 for found in heights]
    return float(np.percentile(walls, 5)) if walls else 0.0


def drawn_size(row, model, rows, inputs):
    """A Pixal3D take's row size (wide, deep, tall) as the bake lays it: its width against its height its baked
    `model`'s own (x wide, y tall) where both its SAM 3 box and that model disagree with the row, or for a person; a
    row the guard list keeps as the row says (score/stages/surfaces/bake_job.py boxed, loaded by its path, with
    tumble.keeps_pose over the pose rules among `inputs` and its inventory's `rows`)."""
    import score.stages.surfaces.tumble as tumble
    import importlib.util
    with prop_data.tools("props/library", "props"):
        spec = importlib.util.spec_from_file_location(
            "bake_job", prop_data.REPO / "score/stages/surfaces/bake_job.py")
        bake_job = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bake_job)
    points, _ = likeness.gltf_mesh(model)
    extents = points.max(0) - points.min(0)
    wide, deep, tall = row["size"]
    wide, tall, deep = bake_job.boxed([wide, tall, deep], row.get("box"), extents[0] / max(extents[1], 1e-9),
                                      tumble.keeps_pose(row, tumble.rules_of(inputs), rows), tumble.person(row))
    return [wide, deep, tall]


def pixal_cut(path, folder, row):
    """A prop object's close-up as its take's Pixal3D input cut it out, its object made one piece with its holes filled
    as compare.closeup_mask makes every other cut (a rack's open frame stays one silhouette: storage's cargo rack, cut
    so, passed at 0.68; its open lattice measured 0.43 on bars a pixel apart)."""
    from scipy import ndimage
    picture = np.asarray(Image.open(path).convert("RGBA"))
    labels, count = ndimage.label(picture[..., 3] > 127)
    if count == 0:
        raise ValueError(f"{path}: Pixal3D's cut-out holds no object")
    largest = np.argmax(ndimage.sum(np.ones_like(labels), labels, index=range(1, count + 1))) + 1
    mask = ndimage.binary_fill_holes(labels == largest)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{row}.png"
    Image.fromarray(np.dstack([picture[..., :3], np.where(mask, 255, 0).astype(np.uint8)])).save(out)
    return out


def straight_cut(path, folder, row):
    """A thin straight code build's concept crop cut by its mask as it is (thin_straight.pieces: specks dropped, no
    hole filled, so a ladder stays posts and rails and a bundle its lines), unturned: the build follows its mask's
    centreline in the picture's frame and keeps the pose it was made in (thin_straight.write_take). A crop turned
    upright or level by its mask's long axis held a straight sweep of the box to it (2026-10-26); along its
    centreline, the build is the picture's own slant (#36, 2026-10-30)."""
    picture = np.asarray(Image.open(path).convert("RGBA"))
    folder.mkdir(parents=True, exist_ok=True)
    kept = np.where(thin_straight.pieces(picture[..., 3] > 127), 255, 0).astype(np.uint8)
    out = folder / f"{row}.png"
    Image.fromarray(np.dstack([picture[..., :3], kept])).save(out)
    return out


def shown_look_down(target, size):
    """The look-down a close-up of a row of `size` shows, read off its object `target`'s height:width on the close-up
    check's own view (tools/props/closeup/check.py expected_proportion, turned TURN_DEGREES), to the half degree."""
    with prop_data.tools("props/closeup", "props"):
        import check
    rows, columns = np.where(target)
    seen = (rows.max() - rows.min() + 1) / (columns.max() - columns.min() + 1)
    downs = np.arange(0.0, check.TOP_DOWN_DEGREES + 0.5, 0.5)
    return float(downs[np.argmin([abs(np.log(check.expected_proportion(size, down) / seen)) for down in downs])])


def whole_best_way(model, closeup, size):
    """likeness.best_way with both outlines whole, holes filled, as pixal_cut fills the close-up's: an open frame's
    model is otherwise held by its bars to its close-up's filled outline (engineroom's railing 0.339, filled 0.864).
    A row that lies flat is held at the better of its stated look-down (straight above) and the one its close-up shows
    (shown_look_down): the picture model draws some from three quarters anyway (wreck's open metal ring, a circle from
    above against its close-up's ellipse, 0.128), and that angle is read off the close-up, never searched per model.
    Here, not in likeness.best_way: likeness.py is in the code of the paid body rows (#36 outline study)."""
    from scipy import ndimage
    with prop_data.tools("props/closeup", "props"):
        import check
    points, triangles = likeness.gltf_mesh(model)
    target = ndimage.binary_fill_holes(likeness.closeup_object(closeup))
    ring, stated = likeness.candidate(), likeness.look_down(size)
    downs = [stated, shown_look_down(target, size)] if size and check.lies_flat(size) else [stated]
    ways = {down: [round(ring.outline(ndimage.binary_fill_holes(likeness.silhouette(points, triangles, step, down)),
                                      target), 4) for step in range(ring.YAWS)] for down in downs}
    down = max(downs, key=lambda angle: max(ways[angle]))
    best = int(np.argmax(ways[down]))
    return {"way": best, "look_down": down, "outline": ways[down][best], "ways": ways[down]}


def textured_view(path, way, down):
    """(sRGB picture on white, mask) of a model with its own finishes (route_cast's texture colours and angle shade,
    on the processor, no Blender), seen from `way` of YAWS at `down` degrees as likeness.silhouette frames it: its
    right is set by its yaw, so straight above is defined."""
    import math
    import score.stages.surfaces.route_cast as cast
    model = cast.loaded(path)
    yaw, pitch = math.radians(360.0 * way / likeness.candidate().YAWS), math.radians(down)
    eye = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    right = np.array([math.cos(yaw), 0.0, -math.sin(yaw)])
    up = np.cross(eye, right)
    reach = float(np.linalg.norm(model.mesh.vertices, axis=1).max()) * cast.MARGIN
    steps = (np.arange(likeness.SIDE) + 0.5) / likeness.SIDE * 2 - 1
    across, down_steps = np.meshgrid(steps, -steps)
    origins = (eye * reach * 2) + across[..., None] * right * reach + down_steps[..., None] * up * reach
    hit, rays, points = model.mesh.ray.intersects_id(origins.reshape(-1, 3), np.tile(-eye, (steps.size ** 2, 1)),
                                                     multiple_hits=False, return_locations=True)
    faces = np.full(steps.size ** 2, -1)
    met = np.full((steps.size ** 2, 3), np.nan)
    faces[rays], met[rays] = hit, points
    faces, met = faces.reshape(steps.size, steps.size), met.reshape(steps.size, steps.size, 3)
    seen = faces >= 0
    shade = np.zeros(faces.shape)
    shade[seen] = cast.SHADE_LEAST + (1 - cast.SHADE_LEAST) * np.abs(model.mesh.face_normals[faces[seen]] @ eye)
    colours = cast.texture_colours(model, faces, met) * shade[..., None]
    return np.where(seen[..., None], np.clip(colours, 0, 255), 255).astype(np.uint8), seen


def boxed_colour(picture, mask):
    """A picture's object (inside `mask`) cut to its box, on white in a TEXTURED_SIDE square, proportions kept."""
    rows, columns = np.where(mask)
    top, bottom, left, right = rows.min(), rows.max() + 1, columns.min(), columns.max() + 1
    cut = np.where(mask[..., None], picture, 255)[top:bottom, left:right].astype(np.uint8)
    scale = TEXTURED_SIDE / max(bottom - top, right - left)
    size = (max(1, round((right - left) * scale)), max(1, round((bottom - top) * scale)))
    square = Image.new("RGB", (TEXTURED_SIDE, TEXTURED_SIDE), (255, 255, 255))
    square.paste(Image.fromarray(cut).resize(size, Image.LANCZOS),
                 ((TEXTURED_SIDE - size[0]) // 2, (TEXTURED_SIDE - size[1]) // 2))
    return square


def write_textured_pair(entry, folder, row):
    """A designed place's DINOv2 pairs (DESIGNED_LEAST): the model in its finishes from the outline's best way and
    from the way facing it (BACK), each against the close-up's object in its colours, all boxed on white."""
    folder.mkdir(parents=True, exist_ok=True)
    drawn = folder / f"{row}-closeup.png"
    closeup = np.asarray(Image.open(entry["closeup"]).convert("RGB"))
    boxed_colour(closeup, likeness.closeup_object(entry["closeup"])).save(drawn)
    pairs = {}
    for name, way in ((row, entry["way"]), (row + BACK, (entry["way"] + likeness.candidate().YAWS // 2)
                                            % likeness.candidate().YAWS)):
        made = folder / f"{name}-model.png"
        boxed_colour(*textured_view(entry["model"], way, entry["look_down"])).save(made)
        pairs[name] = [str(made), str(drawn)]
    return pairs


def thin_built(inputs, row):
    """Whether the object's take is the thin straight route's code build (its code.json not a flat sheet's)."""
    mark = inputs.get(f"code take {row}")
    return mark is not None and json.loads(pathlib.Path(mark).read_text()).get("rule") != flat_sheet.RULE


def object_record(row, record, inputs, baked, parts, rows, square, cuts):
    """One object's route, model, outline (at the look-down its close-up was drawn at, for the size it was drawn at:
    tools/props/closeup/stage.py object_size), checks and missing parts; `rows`: the inventory's rows by id."""
    route = route_of(row, record)
    place = record["place"]
    found = {"route": route, "model": None}
    model = model_of(row, record, inputs, baked)
    closeup = inputs["closeup"] / "closeups" / f"{row}.png"
    if f"code take {row}" in inputs:  # built in code from its concept crop (thin_straight.py): held to the crop
        found["made"] = "code"
        closeup = pathlib.Path(inputs[f"pixal input {row}"])
    if model is None or not pathlib.Path(model).exists() or not closeup.exists():
        return {**found, "missing": "no model" if closeup.exists() else "no close-up"}
    cut = inputs.get(f"pixal input {row}") if route == "prop" else None
    if cut is None or not pathlib.Path(cut).exists():
        closeup = thin_straight.cut_out(closeup, cuts)
    else:
        closeup = straight_cut(cut, cuts, row) if thin_built(inputs, row) else pixal_cut(cut, cuts, row)
    kind = f"{place}_{row}"
    drawn = rows[row].get("read_size") or rows[row]["size"]
    found.update(model=str(model), closeup=str(closeup), **whole_best_way(model, closeup, drawn),
                 **model_checks(model, rows[row]["size"] if "made" in found
                                else drawn_size(rows[row], model, list(rows.values()), inputs), kind,
                                route == "prop" and kind in square))
    # a code build's parts: None, unknown (nothing measures them since the code fallback's parts check went)
    lit = thin_built(inputs, row) and thin_straight.slender_light(rows[row])
    found["parts_missing"] = finishes_missing(record["objects"][row]["take"], parts, lit) if route == "prop" else None
    return found


def make_likeness(inputs, out, seed, params):
    """likeness.json (every object's record) and pairs.json (each best way's silhouette pair, for DINOv2)."""
    record = prop_data.record_at(inputs["props"])
    rows = {row["id"]: row for row in json.loads(inputs["inventory"].read_text())["rows"]}
    square = set()  # no rule names a kind that stands square since the old kinds' details retired (2026-10-21)
    prop = "surfaces-bake" in inputs
    baked = baked_models(inputs["surfaces-bake"]) if prop else {}
    parts = json.loads((inputs["surfaces-parts"] / "parts.json").read_text()) if prop else {"takes": {}}
    found = {row: object_record(row, record, inputs, baked, parts, rows, square, out / "cut")
             for row in sorted(prop_data.kept(record["objects"], params))}
    pairs = {}
    for row, entry in found.items():
        if "way" not in entry:
            continue
        if record.get("approved"):  # a designed place: judged textured at DESIGNED_LEAST
            pairs.update(write_textured_pair(entry, out / "pairs", row))
        else:  # a calibrated place: its least was set on silhouettes (calibration_row.py)
            pairs[row] = likeness.write_pair(entry["model"], entry["closeup"], entry["way"], out / "pairs", row,
                                             entry["look_down"])
    (out / "likeness.json").write_text(json.dumps({"objects": found}, indent=1))
    (out / "pairs.json").write_text(json.dumps(pairs, indent=1))
    built = [row for row in found if f"code take {row}" in inputs and free_passed(found, row)]
    batch_gaps.write(out, [with_rows(entry, record)
                           for entry in thin_straight.without_closeup_gaps(batch_gaps.of(inputs), built)])


def free_passed(found, row):
    """Whether an object passed every free check (FREE), so a code build's close-up gap is closed by it."""
    return all(object_faults({row: found[row]}, faults_of)[row] == [] for faults_of in FREE.values())


def with_rows(entry, record):
    """A batch gap carried on with every object of the hand-in record its takes or rows name, and the inventory rows
    that object stands for, so the gates that name rows (this one's, complete's) find it."""
    named = set(entry["objects"])
    rows = [(row, *item.get("rows", ())) for row, item in record["objects"].items()
            if row in named or item.get("take") in named]
    return {**entry, "objects": sorted(named.union(*rows))}


def likeness_faults(folder):
    return [] if (folder / "likeness.json").exists() else ["no likeness.json"]


def objects(output):
    return json.loads((output / "likeness.json").read_text())["objects"]


# --- each object's faults by check: None when the check cannot tell ------------------------------------------------

def outline_faults(row, entry):
    if entry["outline"] < likeness.OUTLINE_LEAST:
        return [f"outline {entry['outline']:.3f} under {likeness.OUTLINE_LEAST}"]
    return []


def parts_faults(row, entry):
    missing = entry["parts_missing"]
    return None if missing is None else [f"misses {', '.join(missing)}"] if missing else []


def model_faults(row, entry):
    found = entry["model_check"]
    return [] if found["pass"] else [f"thinnest {found['thinnest']} m, spread {found['spread']}"]


def lean_faults(row, entry):
    return [] if "straight" not in entry or entry["straight"]["pass"] else ["leans or warps"]


def scored(scores, least):
    """DINOv2's faults on each object from its scores ({row: likeness}) at `least`; None for one not scored or no
    least."""
    def faults(row, entry):
        if least is None or row not in scores:
            return None
        return [f"likeness {scores[row]:.3f} under {least}"] if scores[row] < least else []
    return faults


FREE = {"outline": outline_faults, "close-up parts present": parts_faults, "thin and in proportion": model_faults,
        "lean": lean_faults}


def object_faults(found, faults_of):
    """{row: faults, or None when the check cannot tell}; an object with no model faults on every check."""
    return {row: ([entry["missing"]] if "missing" in entry else faults_of(row, entry)) for row, entry in found.items()}


def judged(name, found, faults):
    """The check's verdict: fail naming each object's faults, else unknown naming what it could not tell, else pass."""
    failing = [f"{row}: {fault} ({found[row]['route']} route)" for row, listed in sorted(faults.items()) if listed
               for fault in listed]
    untold = sorted(row for row, listed in faults.items() if listed is None)
    if untold and not failing:
        return unknown(name, f"cannot tell for {', '.join(untold)}")
    return verdict(name, failing + [f"{row}: cannot tell" for row in untold], len(found), "faults")


def free_judge(name):
    """The judge of one free check (FREE)."""
    def judge(output, inputs, evidence):
        found = objects(output)
        return judged(name, found, object_faults(found, FREE[name]))
    return judge


def judge_likeness(output, inputs, evidence):
    """Each best way's DINOv2 likeness ({row: score}, the gathered evidence) at least the calibration's least."""
    least = calibration_row.least(inputs.get("likeness-calibration"))
    if least is None and designed(inputs):
        least = DESIGNED_LEAST
    if least is None:
        return unknown("likeness", "DINOv2's least likeness is not set: no accepted calibration of the place's "
                                   "accepted models (likeness-calibration)")
    found = objects(output)
    return judged("likeness", found,
                  object_faults(found, scored(facing(json.loads(pathlib.Path(evidence).read_text())), least)))


def designed(inputs):
    """Whether the row's prop data is an approved design's hand-in (prepare/handin.py), which names no accepted
    models to calibrate on."""
    return "props" in inputs and bool(prop_data.record_at(inputs["props"]).get("approved"))


def facing(scores):
    """{row: likeness} from DINOv2's pair scores: a textured pair's best way or the way facing it (BACK), the
    higher."""
    found = {}
    for name, score in scores.items():
        row = name.removesuffix(BACK)
        found[row] = max(score, found.get(row, score))
    return found


def stored_pairs(output):
    """pairs.json's pairs, each picture read from the output's own pairs/ folder: the paths it holds point into the
    folder the make ran in, removed once the output was stored (likeness@campgrounds, 2026-10-15: no likeness came
    back, the cairn's model picture missing)."""
    pairs = json.loads((output / "pairs.json").read_text())
    return {row: [str(output / "pairs" / pathlib.Path(picture).name) for picture in pair]
            for row, pair in pairs.items()}


def gather_likeness(output, inputs, folder):
    """DINOv2's score of every pair on a rented machine (similar.py): the evidence file."""
    with prop_data.tools("cloud", "props"):
        import similar
        similar.likeness(stored_pairs(output), folder / "likeness.json", "score likeness")
    return folder / "likeness.json"


def routes(output, scores=None, least=None):
    """{row: "prop" | "code" | "builder" | "unknown"}: where each object stands after its checks (DINOv2's scores at
    `least` included). A prop object that passed every check stays prop; one that failed any goes to code; a code
    object that failed needs a new builder; one a check could not tell for is unknown."""
    found = objects(output)
    per_check = [object_faults(found, faults_of)
                 for faults_of in (*FREE.values(), scored(facing(scores or {}), least))]
    found_routes = {}
    for row, entry in found.items():
        told = [faults[row] for faults in per_check]
        if any(told):
            found_routes[row] = {"prop": "code", "code": "builder"}[entry["route"]]
        else:
            found_routes[row] = "unknown" if None in told else entry["route"]
    return found_routes


CHECKS = (*(guarded(name, free_judge(name)) for name in FREE),
          dataclasses.replace(guarded("likeness", judge_likeness), evidence="DINOv2 scores (similar.py)"))
GATHERERS = {"likeness": (gather_likeness, LIKENESS_EUROS)}


