"""The finish against NVIDIA's: the made model's parts held to the truth's material faces (each made face takes the
material of the nearest truth surface point, the made model set on the truth), by split_compare's ownership rule;
what each part got held to NVIDIA's look on the same faces (#172: its surface's colour, metal or not, roughness and
class against the truth's maps there); and each matched part's surface held to the truth's by the look-alike check's
bounds."""
import numpy as np
from scipy.spatial import cKDTree

import score.stages.props.prop_data as prop_data

from . import _mesh

CARRY_POINTS = 200000  # truth surface points a made face's material is read from
CANDIDATES = 8  # truth triangles measured exactly per made face (those of its nearest truth points)
CARRY_CHUNK = 100000  # made faces carried at a time
# A part's look held (#172, set by the calibration pass, tools/props/bench/calibrate): its colour within COLOUR_REACH
# (CIE76 delta E of its surface's base colour from NVIDIA's albedo mean on its faces), its roughness within
# ROUGHNESS_REACH of NVIDIA's mean there, its metalness within METAL_REACH of NVIDIA's mean there: metal or not, a
# metallic paint (NVIDIA's mean 0.4 to 0.6, the tire rack's 0.53 under a library 0.47) either.
COLOUR_REACH = 10.0
ROUGHNESS_REACH = 0.25
METAL_REACH = 0.5
# A part's drawn pattern held (#186): its look's lightness detail (bench/run finish.drawn_patterns: the median of the
# high-pass, L units) within PATTERN_REACH times NVIDIA's close-up's on the same part either way, each side taken as at
# least PATTERN_FLOOR (under it, a surface is smooth). tc4r's 48 parts over 1% of their models' area: the surgical
# chair's granite seat 4.96 against NVIDIA's smooth 0.0 (4.96 times), the humidifier's column 0.2 against its ribs'
# 12.9 (12.5 times under: "ribs lost") and its diffuser 4.7 times under fail; the owner's clean ones held: the locker's
# wooden bench 2.9 times under NVIDIA's grain, the gas stove's grates 2.5 times, the tire rack's steel tube 1.4 over.
PATTERN_REACH = 3.0
PATTERN_FLOOR = 1.0
# A part's drawn colour held (#198): its look's median CIELAB (bench/run finish.drawn_patterns, the look drawn under the
# close-up's own light) against the input close-up's on the same part and view: its hue and colour strength (the a*b*
# distance) within DRAWN_AB, its lightness within DRAWN_L. On tc5r's seven colour objects relit (r9c-light) the greys
# the eye holds right lay 0 to 1.7 apart in a*b* (drill b01's cool light grey 3.8), the faults the owner named over it:
# the heat gun's body drawn navy 5.0, the coffee station's orange wood 7.4 and 8.3, drill b01's red 9.9 and 10.0, the
# hospital chair's royal seat 16.7, the fridge's handle 26.6. Lightness wanders more with TRELLIS.2's lumps and bare
# metal's reflections (the held parts lay within 13 L*); the chair's seat drawn 18 to 21 L* lighter fails it.
DRAWN_AB = 4.5
DRAWN_L = 15.0
# A part's whites held (#159): the share of its pixels its look draws clipped white (bench/run finish.drawn_patterns,
# under the close-up's own light) at most CLIPPED_REACH over the input close-up's on the same part and view. Its median
# colour is white on both sides, so `drawn` held tc6's blown-out locker (its body 0.88 clipped against NVIDIA's 0.03, a
# #c8c8c8 token for NVIDIA's 0.32 albedo) and anesthesia machine (0.22 more over 56% of it, its drawers and panels
# lost). Over tc6's 33 looks at the bar's 0.90 of the area, five fail: those two, the humidifier's white shade (0.25
# over), the fridge's body drawn chrome (0.25) and the hospital chair's white frame drawn flatter than NVIDIA's (0.18);
# the 28 others hold (the sign, the tire rack, the grinder, the ladder, the ratchet whole). A part that gives off light
# (finish part_looks' `lit`) is drawn at its light's strength and is not judged.
CLIPPED_REACH = 0.15
# A part's shading held (#206, owner 2026-11-24 on tc6w2's anesthesia machine: "this one got a bit worse, and u
# overlit the others aswell"; its mean lightness the input's, 0.819 for 0.819, its whites one flat white where NVIDIA's
# shade into every seam, drawer line and corner): its look's lightness spread (L* of its 90th less its 10th percentile,
# bench/run finish.drawn_patterns) at least the input close-up's on the same part over SPREAD_REACH, and how deep its
# creases fall (the 5th percentile of its lightness less its local mean, likeness measure.high_pass, as a depth) at
# least the input's over CREASE_REACH, each side taken as at least its floor (under it, a part is plain). Never judged
# the other way: a part shaded more than the input is `pattern`'s and the picture judge's. Calibrated on tc6's 26 looks
# with an r206 light step, their 132 parts over 1% of the close-up: NVIDIA's own model drawn by the look (r206's light
# step, laid on the close-up by its outline) holds 0.958 of the area at least (the tire rack), 1.0 on the 25 others;
# today's made looks fail 18 of 26 at the bar's 0.90: the anesthesia machine 0.22 (its white body's creases 1.0 deep
# for the input's 5.1, its drawer front 1.9 for 13.0, its arm 1.3 for 23.9), the stove, the printer box, both chairs,
# the drills, the grinder, the heat gun, the ratchet, the hammer, the humidifier, the vending machine; the locker
# (0.98: NVIDIA's flat painted body 0.4 deep), the toaster (0.98) and the desk (1.0) hold.
SPREAD_REACH = 2.5
SPREAD_FLOOR = 2.0
CREASE_REACH = 2.0
CREASE_FLOOR = 1.0


def split_rule():
    """tools/props/library/split_compare.py: finishes_owned, OWN_PURITY, FINISH_LEAST."""
    with prop_data.tools("props/library", "props"):
        import split_compare
    return split_compare


def look_bounds():
    """tools/props/library/likeness/measure.py: passes (one view's measures within every bound)."""
    with prop_data.tools("props/library/likeness", "props/library", "props"):
        import measure
    return measure


def carried(truth, placed, made_faces):
    """Each made face's truth triangle: the truth triangle nearest its middle (its material the face's truth
    material, its look the face's truth look), found exactly among the triangles of the CANDIDATES truth points
    (drawn by area, and every triangle's middle) nearest it. NVIDIA lays tape, decals and labels as a thin layer
    just over a box's own surface (box_flat_a10's tape 0.4 mm over its card); the nearest drawn point read either
    layer and blurred a strip's edges by the points' spacing (5 mm there), so an exact copy of box_flat_a10 held
    none of its tape (#163 calibration). A point nudged out along the normal read the tape's hidden underside as
    card, so none is."""
    import trimesh
    points, picked = _mesh.sampled(truth["vertices"], truth["faces"], CARRY_POINTS, seed=6)
    triangles = truth["vertices"][truth["faces"]]
    points = np.concatenate([points, triangles.mean(1)])
    picked = np.concatenate([picked, np.arange(len(triangles))])
    tree = cKDTree(points)
    asked = placed[made_faces].mean(1)
    found = np.empty(len(made_faces), dtype=np.int64)
    for start in range(0, len(asked), CARRY_CHUNK):
        point = asked[start:start + CARRY_CHUNK]
        _, index = tree.query(point, k=CANDIDATES)
        candidate = picked[index]
        nearest = trimesh.triangles.closest_point(triangles[candidate].reshape(-1, 3, 3),
                                                  np.repeat(point, CANDIDATES, axis=0))
        distance = np.linalg.norm(nearest - np.repeat(point, CANDIDATES, axis=0), axis=1).reshape(-1, CANDIDATES)
        found[start:start + CARRY_CHUNK] = candidate[np.arange(len(point)), distance.argmin(1)]
    return found


def finish_split(truth, placed, made_faces, made_parts, nearest):
    """{"owned": finishes owned of those counted, "held_mean", "held_least": each counted finish's share held in
    parts pure in it, "purity": area-weighted share of each made part in its main finish, "parts", "materials",
    "pairs": [{"part", "material", "area"}] each made part with its main truth material and its area share};
    `nearest` each made face's truth triangle (carried). Faces bound to no material (-1) are one part of their own: tc6's
    withdrawn polyhaven_metal_office_desk binds none, and its -1s, read as an index, made no part at all."""
    rule = split_rule()
    area = _mesh.areas(placed, made_faces)
    finish = np.asarray(truth["face_material"])[nearest]
    part_of = np.asarray(made_parts)
    part_of = np.where(part_of < 0, part_of.max() + 1, part_of)
    table = np.zeros((int(part_of.max()) + 1, int(finish.max()) + 1))
    np.add.at(table, (part_of, finish), area)
    pure = table / np.maximum(table.sum(1, keepdims=True), 1e-12)
    counted = np.nonzero(table.sum(0) >= rule.FINISH_LEAST * area.sum())[0]
    held = [table[pure[:, number] >= rule.OWN_PURITY, number].sum() / table[:, number].sum() for number in counted]
    owned, _ = rule.finishes_owned(area, finish, part_of)
    truth_area = _mesh.areas(truth["vertices"], truth["faces"])
    materials = np.bincount(np.asarray(truth["face_material"]), weights=truth_area)
    parts = np.nonzero(table.sum(1) >= rule.FINISH_LEAST * area.sum())[0]  # a part as a finish is counted: 1% up
    counted_materials = int((materials >= rule.FINISH_LEAST * materials.sum()).sum())
    return {"owned": round(len(owned) / max(len(counted), 1), 4),
            "held_mean": round(float(np.mean(held)), 4), "held_least": round(float(np.min(held)), 4),
            "purity": round(float((table.max(1)).sum() / table.sum()), 4),
            "parts": int(len(parts)), "materials": counted_materials,
            "parts_per_material": round(len(parts) / max(counted_materials, 1), 3),
            "pairs": [{"part": int(part), "material": int(table[part].argmax()),
                       "area": round(float(table[part].sum() / table.sum()), 5)} for part in parts]}


def colour_lab(linear):
    """Linear RGB as CIE Lab (tools/props/library/likeness/colour.py)."""
    with prop_data.tools("props/library/likeness", "props/library", "props"):
        import colour
    return colour.lab(linear)


def true_look(look, triangles, weights):
    """NVIDIA's look over some truth triangles, area-weighted: (albedo, metal, roughness, class), each None where
    none of them has it."""
    def mean(values):
        values = np.asarray(values, dtype=float).reshape(len(triangles), -1)
        kept = ~np.isnan(values).any(1)
        return np.average(values[kept], axis=0, weights=weights[kept]) if weights[kept].sum() > 0 else None
    albedo, metal, roughness = (mean(look[name][triangles]) for name in ("albedo", "metal", "roughness"))
    classes = np.asarray(look["class"], dtype=object)[triangles]
    named = [name for name in dict.fromkeys(classes) if name is not None]
    held = {name: float(weights[classes == name].sum()) for name in named}
    return (albedo, None if metal is None else float(metal[0]), None if roughness is None else float(roughness[0]),
            max(held, key=held.get) if held else None)


def true_through(look, triangles, weights):
    """The area share of some truth triangles whose NVIDIA material lets light through (face_look's `see_through`),
    None for a truth that does not say or no area."""
    if look.get("see_through") is None or weights.sum() <= 0:
        return None
    return float(weights[np.asarray(look["see_through"], dtype=bool)[triangles]].sum() / weights.sum())


def see_through_held(made, through):
    """Whether a part lets light through as NVIDIA's faces under it do (#186: the tc4r fridge's glass door drawn an
    opaque panel): None where neither side is see-through (its made `opacity` under 1, over half its faces' area
    NVIDIA's glass) or either side does not say."""
    if through is None or made.get("opacity") is None:
        return None
    made_through, true_through_ = made["opacity"] < 1.0, through > 0.5
    return None if not (made_through or true_through_) else made_through == true_through_


def pattern_held(made):
    """Whether a part's drawn pattern is NVIDIA's on its faces (PATTERN_REACH, PATTERN_FLOOR), None where either side
    has none measured (`made` {pattern, true_pattern})."""
    if made.get("pattern") is None or made.get("true_pattern") is None:
        return None
    ratio = max(made["pattern"], PATTERN_FLOOR) / max(made["true_pattern"], PATTERN_FLOOR)
    return bool(1.0 / PATTERN_REACH <= ratio <= PATTERN_REACH)


def drawn_held(made):
    """Whether a part's drawn colour is the input close-up's on it (DRAWN_AB, DRAWN_L), None where either side has none
    measured (`made` {drawn, true_drawn}: CIELAB)."""
    if made.get("drawn") is None or made.get("true_drawn") is None:
        return None
    gap = np.asarray(made["drawn"], dtype=float) - np.asarray(made["true_drawn"], dtype=float)
    return bool(np.hypot(gap[1], gap[2]) <= DRAWN_AB and abs(gap[0]) <= DRAWN_L)


def clipped_held(made):
    """Whether a part's look draws no more of it clipped white than the input close-up does, within CLIPPED_REACH;
    None where either side has none measured or the part gives off light (`made` {clipped, true_clipped, lit})."""
    if made.get("clipped") is None or made.get("true_clipped") is None or made.get("lit"):
        return None
    return bool(made["clipped"] - made["true_clipped"] <= CLIPPED_REACH)


def shade_held(made):
    """Whether a part's look shades it as the input close-up does on it (SPREAD_REACH, CREASE_REACH): no flatter, its
    creases no shallower; None where either side has none measured or the part gives off light (`made` {shade,
    true_shade: {spread, crease}, lit}). A side with no crease measured (no pixel whose whole reach lies on the part)
    is held by its spread alone."""
    if made.get("shade") is None or made.get("true_shade") is None or made.get("lit"):
        return None
    drawn, given = made["shade"], made["true_shade"]
    held = max(drawn["spread"], SPREAD_FLOOR) >= max(given["spread"], SPREAD_FLOOR) / SPREAD_REACH
    if drawn.get("crease") is not None and given.get("crease") is not None:
        held = held and max(drawn["crease"], CREASE_FLOOR) >= max(given["crease"], CREASE_FLOOR) / CREASE_REACH
    return bool(held)


def part_look(made, truth, through=None):
    """One part's look held to NVIDIA's on its faces: {"delta_e", "metal", "roughness_gap", "class", "see_through"},
    each None where either side lacks it (`made` {colour, metal, roughness, class, opacity}; `truth` true_look's;
    `through` true_through's)."""
    albedo, metal, roughness, name = truth
    return {"see_through": see_through_held(made, through), "pattern": pattern_held(made), "drawn": drawn_held(made),
            "clipped": clipped_held(made), "shade": shade_held(made),
            "delta_e": None if albedo is None or made.get("colour") is None else
            round(float(np.linalg.norm(colour_lab(np.asarray(made["colour"], dtype=float)) - colour_lab(albedo))), 2),
            "metal": None if metal is None or made.get("metal") is None else
            bool(abs(made["metal"] - metal) < METAL_REACH),
            "roughness_gap": None if roughness is None or made.get("roughness") is None else
            round(abs(float(made["roughness"]) - roughness), 3),
            "class": None if name is None or made.get("class") is None else bool(made["class"] == name),
            "made": {key: made.get(key) for key in ("colour", "metal", "roughness", "class", "opacity", "pattern",
                                                    "true_pattern", "drawn", "true_drawn", "clipped",
                                                    "true_clipped", "shade", "true_shade", "lit")},
            "true": {"albedo": None if albedo is None else [round(float(value), 4) for value in albedo],
                     "metal": None if metal is None else round(metal, 3),
                     "roughness": None if roughness is None else round(roughness, 3), "class": name,
                     "see_through": None if through is None else round(through, 3)}}


def finish_look(truth, placed, made_faces, made_parts, nearest, looks):
    """{"colour", "metal", "roughness", "class", "see_through": the area share of the counted parts (split_compare's
    FINISH_LEAST) whose look holds (part_look: delta E within COLOUR_REACH, metal or not as NVIDIA's (METAL_REACH),
    roughness within ROUGHNESS_REACH, the same class, see-through where NVIDIA's is and only there, its drawn pattern
    NVIDIA's: pattern_held, its drawn colour the input's: drawn_held, its whites no more clipped: clipped_held, its shading no flatter: shade_held), of
    those both sides name; "parts": each part's look}. `looks` {part: {colour
    linear RGB, metal, roughness, class}} what each made part got; `nearest` each made face's truth triangle."""
    rule = split_rule()
    area = _mesh.areas(placed, made_faces)
    part_of = np.asarray(made_parts)
    truth_area = _mesh.areas(truth["vertices"], truth["faces"])
    rows = []
    for part in np.unique(part_of):
        held = part_of == part
        if area[held].sum() < rule.FINISH_LEAST * area.sum() or looks.get(int(part)) is None:
            continue
        triangles = nearest[held]
        weights = area[held] * (truth_area[triangles] > 0)
        found = part_look(looks[int(part)], true_look(truth["face_look"], triangles, weights),
                          true_through(truth["face_look"], triangles, weights))
        rows.append({"part": int(part), "area": round(float(area[held].sum() / area.sum()), 5), **found})
    tests = {"colour": lambda row: row["delta_e"] <= COLOUR_REACH, "metal": lambda row: row["metal"],
             "roughness": lambda row: row["roughness_gap"] <= ROUGHNESS_REACH, "class": lambda row: row["class"],
             "see_through": lambda row: row["see_through"], "pattern": lambda row: row["pattern"],
             "drawn": lambda row: row["drawn"], "clipped": lambda row: row["clipped"],
             "shade": lambda row: row["shade"]}
    keys = {"colour": "delta_e", "metal": "metal", "roughness": "roughness_gap", "class": "class",
            "see_through": "see_through", "pattern": "pattern", "drawn": "drawn", "clipped": "clipped",
            "shade": "shade"}
    found = {}
    for name, test in tests.items():
        judged = [row for row in rows if row[keys[name]] is not None]
        total = sum(row["area"] for row in judged)
        if total > 0:
            found[name] = round(sum(row["area"] for row in judged if test(row)) / total, 4)
    return {**found, "parts": rows}


def finish_likeness(looks):
    """{"alike": the area share whose surface holds every bound in every view and is of the truth's family,
    "within_bounds", "same_family"}; `looks` is [{"area", "views": {view: look-alike measures}, "family",
    "true_family"}], one a matched part (finish_split's pairs, drawn by tools/props/library/likeness)."""
    bounds = look_bounds()
    total = sum(look["area"] for look in looks)
    within = [all(bounds.passes(measured) for measured in look["views"].values()) for look in looks]
    family = [look["family"] == look["true_family"] for look in looks]
    def share(kept):
        return round(sum(look["area"] for look, keep in zip(looks, kept) if keep) / total, 4)
    return {"alike": share([one and other for one, other in zip(within, family)]),
            "within_bounds": share(within), "same_family": share(family)}
