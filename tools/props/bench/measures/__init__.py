"""The prop benchmark's measures (#163, design on #162): one step's model of the prop route held to the NVIDIA SimReady
asset it was made from, every measure a plain number, each judged at its bar.

    measured(truth, made, others=(), input_view=None) -> {"alignment", "size", "shape", "clean", "truth_clean",
                                                          "finish", "physics"}
    laid_like(other, truth)                           -> another asset scaled to the truth's longest side
    by_finish(truth)                                  -> its face_material by finish (surface), not material prim
    twin(other, truth)                                -> whether another asset is the truth's geometry recoloured
    finish_likeness(looks)                            -> {"alike", "within_bounds", "same_family"}
    rested(truth_motion, truth_vertices, made_motion, made_vertices) -> {"rest_up", "rest_height"}
    step_change(truth, before, after)                 -> {"chamfer_change"}
    judged(found)                                     -> {"rows": [{measure, value, bar, pass}], "pass", "failed"}

`truth` and `made` are plain dicts, metres, Z up: {"vertices" (N, 3), "faces" (T, 3), "face_material" (T,) material
or part per face, "box" (low, high), "mass" kg, "colliders" [{"vertices", "faces" or None}], "friction" static}; a
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

from . import _align, _clean, _finish, _mesh, _physics, _shape

finish_likeness = _finish.finish_likeness
rested = _physics.rested

# (group, measure, test, bound): "least" value >= bound, "most" value <= bound, "true", "ratio" max(v, 1/v) <= bound,
# "near_one" |v - 1| <= bound, "times_truth_most" / "times_truth_least" against bound times the truth's own value
# (its "truth_clean"), "least_or_truth" value >= the bound or the truth's own when lower, "plus_truth_most" value <=
# the truth's own plus bound, "wall" value >= the model gate's least wall for the truth's size or bound times the
# truth's own thinnest wall, whichever is less.
BARS = (
    ("shape", "ring", "least", 0.75),
    ("shape", "input", "least", 0.90),
    ("shape", "f_score", "least", 0.80),
    ("shape", "rank", "most", 1),
    ("alignment", "up_error", "most", 5.0),
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
    ("likeness", "alike", "least", 0.80),
    ("physics", "mass_ratio", "ratio", 1.5),
    ("physics", "colliders", "least", 1),
    ("physics", "convex", "true", None),
    ("physics", "collider_volume_ratio", "near_one", 0.20),
    ("physics", "overhang", "most", 0.01),
    ("physics", "friction_gap", "most", 0.15),
    ("drop", "rest_up", "most", 10.0),
    ("drop", "rest_height", "most", 0.02),
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
    if made.get("face_material") is not None:
        found["finish"] = _finish.finish_split(truth, placed, made["faces"], made["face_material"])
    if truth.get("colliders"):
        found["physics"] = _physics.physics(truth, made)
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
    if test == "true":
        return bool(value), True
    if test == "ratio":
        return max(value, 1 / value) <= bound if value > 0 else False, bound
    if test == "near_one":
        return abs(value - 1) <= bound, bound
    if test in ("least", "least_or_truth", "times_truth_least", "wall"):
        return value >= bound, bound
    return value <= bound, bound


def judged(found):
    """Each measure present in `found` (measured's, with any "likeness", "drop" and "steps" groups the runner adds)
    against its bar: {"rows": [{"measure", "value", "bar", "pass"}], "pass": every row held, "failed": names}."""
    rows = []
    for group, measure, test, bound in BARS:
        if measure not in found.get(group, {}):
            continue
        value = found[group][measure]
        truth_value = found.get("truth_clean", {}).get(measure)
        passed, bar = held(test, value, bound, truth_value, found.get("truth_sides"))
        rows.append({"measure": f"{group}.{measure}", "value": value, "bar": bar, "pass": bool(passed)})
    failed = [row["measure"] for row in rows if not row["pass"]]
    return {"rows": rows, "pass": not failed, "failed": failed}
