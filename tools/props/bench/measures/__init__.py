"""The prop benchmark's measures (#163, design on #162): one step's model of the prop route held to the NVIDIA SimReady
asset it was made from, every measure a plain number, each judged at its bar.

    measured(truth, made, others=(), input_view=None) -> {"alignment", "size", "shape", "clean", "truth_clean",
                                                          "finish", "parts", "physics"}
                                                          ("parts": the moving parts and their joints against
                                                          NVIDIA's, _joints, #177, where the made side has
                                                          `face_part` and `joints` and the truth `face_body`)
                                                          ("finish" also how cleanly the finishes meet, _edges:
                                                          edge_density, edge_wander, specks, speck_share)
    laid_like(other, truth)                           -> another asset scaled to the truth's longest side
    by_finish(truth)                                  -> its face_material by finish (surface), not material prim
    twin(other, truth)                                -> whether another asset is the truth's geometry recoloured
    finish_likeness(looks)                            -> {"alike", "within_bounds", "same_family"}
    rested(truth_motion, truth_vertices, made_motion, made_vertices) -> {"rest_up", "rest_height"}
    step_change(truth, before, after)                 -> {"chamfer_change"}
    judged(found, bars=BARS)                          -> {"rows": [{measure, value, bar, pass}], "pass", "failed"}
    pictured(target, made, fit=None, picture=None)    -> {"size", "shape", "clean", "finish", "labels"}: a model
                                                          with no NVIDIA truth held to its close-up and target size
                                                          alone (the 2099 cockpit cases, #159), at PICTURED_BARS
    text_read(marks)                                  -> {"read", "misread"}: the share of the close-up's words
                                                          read back where its look drew them (#185)

`truth` and `made` are plain dicts, metres, Z up: {"vertices" (N, 3), "faces" (T, 3), "face_material" (T,) material
or part per face, "face_seen" (T,) the made face's pixels in its look (its specks only those drawn, _edges),
"box" (low, high), "mass" kg, "colliders" [{"vertices", "faces" or None}], "friction" static; the
made side's "painted" {"points", "colour" linear RGB}, its own paint, gives "orientation", its heading as laid}; a
key the made side lacks (a raw model has no parts, mass or colliders) leaves its measures out, never failed.
`others` are the kind's other truths, for the rank. `input_view` is (yaw, pitch) of the input render, by default
the close-up's (tools/props/closeup/check.py TURN_DEGREES and look_down for the truth's size).

The made model is measured as its route laid it: its size first, then set on the truth by the best of the cube's 24
axis turns and ICP (turn and move, never scale), whose turn of up is the up-axis error. The Newton drop itself runs in
the runner (tools/usd/drop.py on the convex colliders); `rested` compares its two rests. Finish likeness needs each
matched pair drawn by tools/props/library/likeness; `finish_likeness` judges those measures.

BARS are #162's design bars, before the calibration pass confirms or resets each with its numbers.
"""
import numpy as np

import score.stages.props.prop_data as prop_data

from . import _align, _clean, _edges, _finish, _heading, _joints, _mesh, _physics, _shape
from tools.props.bench.judge import KINDS as PICTURE_KINDS

finish_likeness = _finish.finish_likeness
rested = _physics.rested

# (group, measure, test, bound): "least" value >= bound, "most" value <= bound, "true", "ratio" max(v, 1/v) <= bound,
# "near_one" |v - 1| <= bound, "times_truth_most" / "times_truth_least" against bound times the truth's own value
# (its "truth_clean"), "least_or_truth" value >= the bound or the truth's own when lower, "plus_truth_most" value <=
# the truth's own plus bound, "wall" value >= the model gate's least wall for the truth's size or bound times the
# truth's own thinnest wall, whichever is less, "gate_wall" value >= the model gate's least wall for the target's size.
BARS = (
    ("shape", "ring", "least", 0.75),
    ("shape", "input", "least", 0.90),
    ("shape", "f_score", "least", 0.80),
    ("shape", "rank", "most", 1),
    ("alignment", "up_error", "most", 5.0),
    # The heading as laid, held by its own paint against NVIDIA's look (_heading, #159 round 7): the 24 axis turns
    # above turn a model laid round back before anything is held (tc4r's desk a half turn off, its fridge's glass
    # door on its side, both passing every shape measure while the picture judge saw them turned).
    ("orientation", "heading", "most", 0),
    ("size", "size", "most", 0.05),
    ("steps", "chamfer_change", "most", 0.005),
    ("clean", "open_length", "times_truth_most", 1.0),
    ("clean", "largest_share", "least_or_truth", 0.99),
    ("clean", "crumbs", "times_truth_most", 1.0),
    ("clean", "non_manifold_edges", "times_truth_most", 1.0),
    ("clean", "wound_against", "times_truth_most", 1.0),
    ("clean", "degenerate_faces", "times_truth_most", 1.0),
    ("clean", "repeated_faces", "times_truth_most", 1.0),
    ("clean", "thinnest", "wall", 0.5),
    ("clean", "triangles_per_m2", "times_truth_most", 2.0),
    ("clean", "flat_share", "times_truth_least", 0.8),
    ("clean", "swell", "plus_truth_most", 0.05),
    ("finish", "held_mean", "least", 0.80),
    ("finish", "held_least", "least", 0.50),
    ("finish", "purity", "least", 0.85),
    ("finish", "parts_per_material", "most", 2.0),
    # How cleanly the finishes meet (_edges, #179; owner 2026-11-23: tc3s's "table and toaster mesh became messy
    # compared to run 1"). The tune split's 54 truths (read by finish): 9 share a finish edge at all, their wander
    # 0.00063 at most (rack_composition_l08), 0 specks on every one. tc3s's six made models: wander 0.00072 (printer
    # box) to 0.0093 (desk, rack), toaster 0.0014; specks 0 to 870 (desk), toaster 21 (share 0.00052). The same six
    # cut cleanly along a plane instead (run 1's smooth line): wander 0.00087 at most (the rack: a plane grazing its
    # wires), 0 to 4 specks, share 0.00008 at most. Density: the six made 0.08 to 1.1 times their truths', the test box
    # given a finish per triangle at random 50 times.
    ("finish", "edge_density", "times_truth_most", 2.0),
    ("finish", "edge_wander", "most", 0.001),
    ("finish", "specks", "most", 8),
    ("finish", "speck_share", "most", 0.0002),
    ("finish", "colour", "least", 0.90),
    ("finish", "metal", "least", 0.90),
    ("finish", "roughness", "least", 0.90),
    ("finish", "class", "least", 0.90),
    # A part over NVIDIA's glass drawn see-through and a see-through part only over it (#186: the tc4r fridge's glass
    # door drawn an opaque grey panel): no part may miss, so the bar is every one.
    ("finish", "see_through", "least", 1.0),
    # Each part's drawn pattern as NVIDIA's on it (#186: the surgical chair's seat drawn speckled granite, 26% of it;
    # the humidifier's ribbed column drawn smooth, 58%), at the look bars' 0.90; its reach is beside _finish's.
    ("finish", "pattern", "least", 0.90),
    # Each part's colour as the look draws it under the close-up's light, held to the input's on the same view (#198:
    # tc5r's hospital chair seat drawn royal blue, drill b01's red too strong, both inside NVIDIA's albedo reach on
    # some parts), at the look bars' 0.90; its reaches are beside _finish's.
    ("finish", "drawn", "least", 0.90),
    # Each part drawn no more clipped white than the input shows it (#159: tc6's locker and anesthesia machine blown
    # out, their drawers, panels and vents lost), at the look bars' 0.90; its reach is beside _finish's.
    ("finish", "clipped", "least", 0.90),
    # Each part shaded as the input shows it, no flatter and its creases no shallower (#206: tc6w2's anesthesia
    # machine one flat white, its seams and drawer lines lost), at the look bars' 0.90; its reaches are beside _finish's.
    ("finish", "shade", "least", 0.90),
    # Each wood part's grain run as NVIDIA's (#159: the coffee station's walnut veneer drawn a stipple, no grain, its
    # boards merged): no wood part may miss, so the bar is every one; its reaches are beside _finish's.
    ("finish", "grain", "least", 1.0),
    # Moving parts and joints (#177, #161 rules 1 and 11), #162-style design bars until the calibration pass sets
    # them on the tune split's jointed truths: as many moving parts as NVIDIA's; each truth part's faces at least
    # half its made part's (area in common over area together); every joint of its type; its axis within 10 degrees
    # (a door's hinge leaning 10 degrees swings visibly off); a hinge's pivot within 5% of the diagonal of its line;
    # its open span within half of NVIDIA's (a door opening 90 against 135 degrees holds, one opening 45 does not).
    ("parts", "count_gap", "most", 0),
    ("parts", "faces_least", "least", 0.5),
    ("parts", "type_held", "least", 1.0),
    ("parts", "axis_most", "most", 10.0),
    ("parts", "pivot_most", "most", 0.05),
    ("parts", "range_most", "most", 0.5),
    # Every text mark of the close-up reads its words where the look drew it (#185, owner's rule: tc4r's sign drew a
    # garbled "C" for tc3's clean "03" and every measure passed). A word read wrong, or a ? for a glyph not clean, fails.
    ("look", "read", "least", 1.0),
    ("likeness", "alike", "least", 0.80),
    ("physics", "mass_ratio", "ratio", 1.5),
    ("physics", "colliders", "least", 1),
    ("physics", "convex", "true", None),
    ("physics", "collider_volume_ratio", "near_one", 0.20),
    ("physics", "overhang", "most", 0.01),
    ("physics", "friction_gap", "most", 0.15),
    ("drop", "rest_up", "most", 10.0),
    ("drop", "rest_height", "most", 0.02),
    # The picture judge (tools/props/bench/judge, #184): the made look held by eye to NVIDIA's render and the previous
    # round's look. Each kind of fault at `fault` fails; a `slight` passes. Calibration (2026-11-24, tc4r's renders):
    # NVIDIA's input against itself 15 of 15 every kind clean; against a re-render (1080 px, 32 samples) 5 of 5 pass,
    # two kinds slight (the box's specks, the rack's colour); the input with the re-render as previous 5 of 5 not
    # regressed. tc4r's 15 looks: 0 of 15 pass, every fault tc4/looked.json names found.
    ("picture", "drawn", "true", None),
    *(("picture", kind, "most", 0) for kind in PICTURE_KINDS),
    ("picture", "regressed", "most", 0),
    # The look's holes (bench/run look_holes, #159: the printer box's normals turned into its body drew black holes
    # through its front): the share of its silhouette the look shows as background or the mesh alone black. tc4r's 15
    # made models (1080, 16 and 32 samples): 0.00001 at most on ten, the humidifier's dark vents 0.00007 to 0.00012;
    # the printer box 0.0047 (0.00008 with its turned normals set to their faces'), the locker's garbled door labels
    # 0.0029, the fridge's specked door 0.00096 (0.0004 with its normals set).
    ("look", "holes", "most", 0.0002),
    # How far closing its hardware cuts stretched the mesh round them (bench/run look.py `stretched`, #212: the most
    # an edge within 1.5 cut radii grew). r13's locker, its lock blobs closed to their points: 4.2 to 9.2 at its four
    # locks, drawn as white cracks and starbursts round two; pressed onto their plate (r14l) 1.05 to 1.09.
    ("look", "stretched", "most", 1.5),
)


# A model with no NVIDIA truth (`pictured`, #159: the 2099 cockpit cases) is held to its close-up and its target size
# alone, so a bar never reads a truth's own value: its silhouette at the input view's bar (the close-up fitted outline,
# not yet calibrated for a fitted camera), its size at the truth's bar, a made mesh with no open edge, crumb or bad face
# and its largest piece at the truth path's own floor (0.99), none lowered by a truth's own value (NVIDIA's open,
# many-pieced assets are why the truth's bars are relative), its wall the gate's least for its size, its finish edges
# at the truth's absolute bars, every label of the close-up printed as a decal, and its finishes of the classes the
# close-up shows and of no recipe it does not show (the 2099 palette's cloth on a toggle lever, rust on screen bezels).
# The truth's relative bars (triangle density, flat share, swell, finish edge density) and its physics are not judged:
# there is nothing to hold them to. Its look is held by eye to the close-up itself.
PICTURED_BARS = (
    ("shape", "closeup", "least", 0.90),
    ("size", "size", "most", 0.05),
    ("clean", "open_length", "most", 0.0),
    ("clean", "largest_share", "least", 0.99),
    ("clean", "crumbs", "most", 0),
    ("clean", "non_manifold_edges", "most", 0),
    ("clean", "wound_against", "most", 0),
    ("clean", "degenerate_faces", "most", 0),
    ("clean", "repeated_faces", "most", 0),
    ("clean", "thinnest", "gate_wall", None),
    ("finish", "edge_wander", "most", 0.001),
    ("finish", "specks", "most", 8),
    ("finish", "speck_share", "most", 0.0002),
    ("finish", "picks", "least", 0.95),
    ("labels", "held", "least", 1.0),
    ("look", "read", "least", 1.0),
    # Its look by eye against its close-up and the previous round's look (the picture judge, #159 round 7: the cockpit
    # looks were drawn by no step and judged by no one), and its look's holes: the truth path's own bars, none of which
    # reads a truth's value.
    ("picture", "drawn", "true", None),
    *(("picture", kind, "most", 0) for kind in PICTURE_KINDS),
    ("picture", "regressed", "most", 0),
    # The close-up's own cut-out (#159: tc5r's torn cockpit cut-outs): its fault the input's, booked apart from the make.
    ("picture", "cutout", "most", 0),
    ("look", "holes", "most", 0.0002),
    ("look", "stretched", "most", 1.5),
)

TWIN_REACH = 0.001  # metres two assets' boxes may differ by and still be one geometry (twin)


def closeup_check():
    """tools/props/closeup/check.py: the close-up's turn and look-down."""
    with prop_data.tools("props/closeup", "props"):
        import check
    return check


def model_gate():
    """tools/props/gates/model.py: the least wall a size may have."""
    with prop_data.tools("props/gates", "props"):
        import model
    return model


def arrays(side):
    """The side with its vertices and faces as numpy arrays."""
    return {**side, "vertices": np.asarray(side["vertices"], dtype=float), "faces": np.asarray(side["faces"])}


def size(truth, made):
    """{"size": the largest per-axis ratio of the made box as laid to the true box, either way, less one;
    "proportion": the same of the boxes' proportions (each over its longest side); "ratios"}."""
    true_sides = np.asarray(truth["box"][1], dtype=float) - np.asarray(truth["box"][0], dtype=float)
    made_sides = made["vertices"].max(0) - made["vertices"].min(0)
    ratios = made_sides / true_sides
    shaped = (made_sides / made_sides.max()) / (true_sides / true_sides.max())
    return {"size": round(float(np.maximum(ratios, 1 / ratios).max() - 1), 4),
            "proportion": round(float(np.maximum(shaped, 1 / shaped).max() - 1), 4),
            "ratios": [round(float(value), 4) for value in ratios]}


def laid_like(other, truth):
    """Another asset laid as the route lays a model for `truth`: scaled whole until its longest side is the truth's,
    its mass by the scale cubed and its colliders with it (a wrong object at the right size, so a rank or a floor
    is never won on size alone)."""
    other = arrays(other)
    true_sides = np.asarray(truth["box"][1], dtype=float) - np.asarray(truth["box"][0], dtype=float)
    scale = float(true_sides.max() / (other["vertices"].max(0) - other["vertices"].min(0)).max())
    middle = (other["vertices"].min(0) + other["vertices"].max(0)) / 2
    laid = {**other, "vertices": (other["vertices"] - middle) * scale + middle,
            "box": [((np.asarray(corner, dtype=float) - middle) * scale + middle).tolist() for corner in other["box"]]}
    if other.get("mass") is not None:
        laid["mass"] = other["mass"] * scale ** 3
    if other.get("colliders") is not None:
        laid["colliders"] = [{**piece, "vertices": (np.asarray(piece["vertices"], dtype=float) - middle) * scale
                              + middle} for piece in other["colliders"]]
    return laid


def by_finish(truth):
    """The truth with each face's material its finish: a truth that names its `materials` (the truth reader's) has
    one finish a library surface (else a material name), however many material prims bind it (the pantry cabinet
    binds its dark wood as four prims, so a made part holding all that wood read as holding a quarter of it). Its
    `materials` become the finishes, so a truth read by finish reads the same again. A surface painted for one model
    (`one_model`: its maps cover the whole model's UVs once, the toaster's plastic and its metal one picture) names no
    finish: its material prims are NVIDIA's finish groups, one finish a material name (#168: read by surface the
    toaster was one finish, and four made parts failed parts_per_material against it)."""
    if not truth.get("materials") or truth.get("face_material") is None:
        return truth
    names = [item.get("name") if item.get("one_model") else item.get("surface") or item.get("name")
             for item in truth["materials"]]
    finish = {name: index for index, name in enumerate(dict.fromkeys(names))}
    lookup = np.array([finish[name] for name in names] + [-1])
    return {**truth, "face_material": lookup[np.asarray(truth["face_material"])],
            "materials": [{"name": name, "surface": name} for name in finish]}


def twin(other, truth):
    """Whether another asset is the truth's own geometry in another finish (NVIDIA's colour variants: the same
    triangles at the same size, crate_blue_a01 and crate_yellow_a01): no other object, so never ranked against."""
    sides = [np.asarray(side["box"][1], dtype=float) - np.asarray(side["box"][0], dtype=float) for side in (other, truth)]
    return len(other["faces"]) == len(truth["faces"]) and bool(np.allclose(sides[0], sides[1], atol=TWIN_REACH))


def seen_finishes(made):
    """Each made face's finish as it is seen: its part, parts given one library surface in one look (`surfaces` and
    `looks`, the route's, where the side has them) one finish, since nothing shows where they meet."""
    parts = np.asarray(made["face_material"])
    if made.get("surfaces") is None:
        return parts
    seen = {}
    named = {part: seen.setdefault((made["surfaces"].get(part), repr((made.get("looks") or {}).get(part))), len(seen))
             for part in np.unique(parts).tolist()}
    return np.array([named[part] for part in parts.tolist()])


def measured(truth, made, others=(), input_view=None):
    """Every measure of one made model against its truth (the module docstring); the kind's `others` are laid like
    the truth (laid_like) before the rank, its twins (twin) left out."""
    truth, made = by_finish(arrays(truth)), arrays(made)
    others = [laid_like(other, truth) for other in others if not twin(other, truth)]
    if input_view is None:
        check = closeup_check()
        sides = np.asarray(truth["box"][1], dtype=float) - np.asarray(truth["box"][0], dtype=float)
        input_view = (check.TURN_DEGREES, check.look_down(list(sides)))
    matrix, alignment = _align.aligned(truth, made)
    placed = _mesh.moved(made["vertices"], matrix)
    shape = {**_shape.silhouettes(truth, placed, made["faces"], input_view),
             **_shape.distances(truth["vertices"], truth["faces"], placed, made["faces"])}
    if others:
        shape["rank"], shape["others"] = _shape.rank(made, shape["f_score"], others)
    found = {"alignment": {**alignment, "matrix": matrix.round(6).tolist()}, "size": size(truth, made),
             "shape": shape, "clean": _clean.cleanliness(made["vertices"], made["faces"]),
             "truth_clean": _clean.cleanliness(truth["vertices"], truth["faces"]),
             "truth_sides": (truth["vertices"].max(0) - truth["vertices"].min(0)).tolist()}
    turned = _heading.heading(truth, made)
    if turned is not None:
        found["orientation"] = turned
    if made.get("face_material") is not None:
        nearest = _finish.carried(truth, placed, made["faces"])
        found["finish"] = _finish.finish_split(truth, placed, made["faces"], made["face_material"], nearest)
        found["finish"].update(_edges.finish_edges(placed, made["faces"], seen_finishes(made),
                                                       made.get("face_seen")))
        found["truth_clean"].update(_edges.finish_edges(truth["vertices"], truth["faces"], truth["face_material"]))
        if made.get("looks") is not None and truth.get("face_look") is not None:
            found["finish"].update(_finish.finish_look(truth, placed, made["faces"], made["face_material"], nearest,
                                                       made["looks"]))
    if made.get("joints") is not None and truth.get("face_body") is not None:
        found["parts"] = _joints.joints(truth, placed, made, _finish.carried(truth, placed, made["faces"]), matrix)
    if truth.get("colliders"):
        found["physics"] = _physics.physics(truth, made)
    return found


def label_words(text):
    """A label as compared: upper case, its runs of spaces one."""
    return " ".join(str(text or "").upper().split())


def labels(named, placed):
    """{"held": the share of the close-up's `named` labels the made model prints as a decal (`placed`: its decals'
    text), "missing", "placed"}."""
    printed = {label_words(text) for text in placed}
    missing = [label for label in named if label_words(label) not in printed]
    return {"held": round(1 - len(missing) / len(named), 4), "missing": missing, "placed": sorted(printed)}


def text_read(marks):
    """{"read": the share of `marks` ([{"text": the close-up's words, "read": what was read where the look drew them,
    None unanswered}], bench/run finish.marks_read) whose words were read back (label_words alike), "misread": each
    one not}, or None when there is no mark to read."""
    if not marks:
        return None
    misread = [{"text": mark["text"], "read": mark["read"]} for mark in marks
               if label_words(mark["read"]) != label_words(mark["text"])]
    return {"read": round(1 - len(misread) / len(marks), 4), "misread": misread}


def picks(made, classes, never):
    """{"picks": the area share of the made faces whose part's class (`made["classes"]`) is one the close-up shows
    (`classes`) and whose surface's recipe (`made["families"]`) is none it does not show (`never`), "wrong": each
    part not held, its class, recipe and area share}."""
    area = _mesh.areas(made["vertices"], made["faces"])
    parts = np.asarray(made["face_material"])
    held, wrong = 0.0, []
    for part in np.unique(parts).tolist():
        share = float(area[parts == part].sum() / area.sum())
        kind, family = made["classes"].get(part), made["families"].get(part)
        if kind in classes and family not in never:
            held += share
        else:
            wrong.append({"part": part, "class": kind, "family": family, "share": round(share, 4)})
    return {"picks": round(held, 4), "wrong": wrong}


def pictured(target, made, fit=None, picture=None):
    """Every measure of a made model with no NVIDIA truth (PICTURED_BARS): its box as laid against `target` (wide,
    deep, tall metres: x, y, z), the close-up's silhouette `fit` (the IoU of its outline through the camera fitted on
    the close-up, close_up_fit), its mesh's cleanliness, and where it has finish parts their edges and, given the case's
    `picture` ({labels, classes, never}), its labels as decals (`made["decals"]`, their text) and its finish picks
    (`made["classes"]`, `made["families"]`). A key the made side lacks leaves its measures out."""
    made = arrays(made)
    box = [[0.0, 0.0, 0.0], [float(side) for side in target]]
    found = {"size": size({"box": box}, made), "shape": {} if fit is None else {"closeup": round(float(fit), 4)},
             "clean": _clean.cleanliness(made["vertices"], made["faces"]), "truth_sides": list(box[1])}
    if made.get("face_material") is not None:
        found["finish"] = _edges.finish_edges(made["vertices"], made["faces"], seen_finishes(made),
                                              made.get("face_seen"))
        if picture and made.get("classes") is not None:
            found["finish"].update(picks(made, picture["classes"], picture["never"]))
    if picture and picture["labels"] and made.get("decals") is not None:
        found["labels"] = labels(picture["labels"], made["decals"])
    return found


def step_change(truth, before, after):
    """{"chamfer_change"}: the two-way mean distance between one step's model and the step's before it, both as
    laid, over the truth's diagonal (closing and cutting must not move the shape)."""
    before, after = arrays(before), arrays(after)
    apart = _shape.distances(before["vertices"], before["faces"], after["vertices"], after["faces"])
    reach = _mesh.diagonal(before["vertices"]) / _mesh.diagonal(np.asarray(truth["vertices"], dtype=float))
    return {"chamfer_change": round(apart["chamfer"] * reach, 5)}


def held(test, value, bound, truth_value, sides):
    """(whether one measure holds its bar, the bar as judged)."""
    if test == "least_or_truth":
        bound = min(bound, truth_value)
    elif test == "times_truth_most" or test == "times_truth_least":
        bound = bound * truth_value
    elif test == "plus_truth_most":
        bound = truth_value + bound
    elif test == "wall":
        bound = min(model_gate().least_wall(sides), bound * truth_value)
    elif test == "gate_wall":
        bound = model_gate().least_wall(sides)
    if test == "true":
        return bool(value), True
    if test == "ratio":
        return max(value, 1 / value) <= bound if value > 0 else False, bound
    if test == "near_one":
        return abs(value - 1) <= bound, bound
    if test in ("least", "least_or_truth", "times_truth_least", "wall", "gate_wall"):
        return value >= bound, bound
    return value <= bound, bound


def judged(found, bars=BARS):
    """Each measure present in `found` (measured's, with any "likeness", "drop" and "steps" groups the runner adds;
    or pictured's at PICTURED_BARS) against its bar: {"rows": [{"measure", "value", "bar", "pass"}], "pass": every row
    held, "failed": names}."""
    rows = []
    for group, measure, test, bound in bars:
        if measure not in found.get(group, {}):
            continue
        value = found[group][measure]
        truth_value = found.get("truth_clean", {}).get(measure)
        passed, bar = held(test, value, bound, truth_value, found.get("truth_sides"))
        rows.append({"measure": f"{group}.{measure}", "value": value, "bar": bar, "pass": bool(passed)})
    failed = [row["measure"] for row in rows if not row["pass"]]
    return {"rows": rows, "pass": not failed, "failed": failed}
