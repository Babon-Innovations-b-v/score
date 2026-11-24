"""The bench's measures pass a made model only where it matches its NVIDIA truth (#163): one table of made models
against one small truth (a 0.5 x 0.4 x 0.8 m box, its top one material and its sides another, 10 kg, its hull its
collider, static friction 0.5), each row the one bar a known fault must break, or a known-small error must keep.
The pictured rows (#159: a model with no NVIDIA truth, the 2099 cockpit cases) hold the same box made at its target
size to PICTURED_BARS: its close-up outline fit, its target, a closed one-piece mesh, the gate's least wall (3 mm at
its size), its labels ON and OFF as decals, its sides metal paint and its top its pick (the top is 0.2 of its 1.84 m2,
so a wrong top holds 0.89 of its area). The answers are worked by hand: a box laid on its side or leaning 8 degrees
is 90 or 8 degrees off up, 10% wider is a size error of 0.10, a cylinder in the box's place is nearer the kind's
cylinder, a 1 mm shell's wall is 1 mm, a hull grown 3 cm stands 3 cm out, and so on.

Breaks (each applied once, seen red, reverted), in tools/props/bench/measures/:
- _align.aligned keeping the first axis turn (none) and dropping ICP's: the box laid on its side passes up.
- _align.up_error returning 0: the box leaning 8 degrees passes up.
- _heading.turned not turning (every turn the model as laid), or _heading.heading reading the as-laid turn's own
  correlation as the best: the desk-like box laid a half or quarter turn off passes its heading (#192: tc4r's desk and
  fridge passed every shape measure, the 24 axis turns setting them back first); _heading.finish_weights weighting
  each point alike (by area): the half and quarter turns pass (the 6 cm cable hole is 0.2% of the area);
  __init__.BARS without its orientation.heading row: the half turn has no row to fail.
- _align.aligned registering every surface point, not the outside's alone (_mesh.outside): the cabinet made upright
  with its inner shelves where the truth's sit upside down is stood on its head (tc3's fridge, #178).
- __init__.size judging the boxes' proportions instead of their sizes: the box laid 20% too big all round passes.
- __init__.twin never finding one: the truth itself ranks second behind its recoloured twin.
- __init__.laid_like keeping the other at its own size: the box's double, another asset of the same shape at twice
  its size, no longer ranks level with it, so a model the shape cannot tell apart ranks first.
- _clean.cleanliness counting no open edge: the box missing a face passes its open length.
- _clean.CRUMB at 0: the box with a 1 cm floater passes its crumbs.
- _clean.thinnest taking the thickest wall: the 1 mm shell passes its wall.
- __init__.held holding the wall to the gate's 3 mm alone: the 1.5 mm shell made for NVIDIA's 2 mm one fails (NVIDIA's
  own walls run thinner than the gate's floor: crates 2.3 mm, cartons 0.1 mm; #163 calibration).
- __init__.by_finish keeping the material prims: the one side part reads as half of each of two finishes.
- __init__.by_finish reading a surface painted for one model as one finish: one part for its two names passes.
- _finish.finish_split counting every part, however small: the three slivers make five parts for two finishes.
- _finish.finish_split holding a finish whatever its parts' purity: one part for two materials passes.
- _edges.wander returning 0: the slant given triangle by triangle passes its wander.
- __init__.seen_finishes keeping the parts: the slant between two parts in one surface and look fails its wander
  (nothing shows where they meet).
- _edges.fitted keeping only the fit about each point: the square label cut cleanly fails its wander (its corners, as
  NVIDIA's labels and carton flaps have).
- _edges.wander measuring the whole distance, not across the edge within its faces: the slant cut cleanly fails (the
  bumps of the surface under it are no wander).
- _edges.islands counting an island that meets no other finish: the 6 cm sticker's model fails its speck share (its
  1 cm block modelled apart reads as a speck).
- _edges.finish_edges ignoring `face_seen` (#159: tc5r's surgical chair, 98 of its 112 specks where its clean look
  shows nothing): the twelve side specks its look, drawn from above, never shows fail its specks.
- _edges.finish_edges dropping SPECK_TRIANGLES: the 6 cm sticker on a model 6 m across (NVIDIA's rack composition:
  0.5 to 33 cm2 stickers on 4.3 m) fails its speck share.
- _edges.density counting every point as at an edge: a finish per triangle at random passes its density.
- _physics.overhang reading the distance from inside the hull: the hull grown 3 cm passes its overhang.
- _physics.overhang measuring off the drawn mesh instead of its outline (its convex hull): the open box under its
  own hull, as NVIDIA's crates are, fails its overhang.
- _physics.convex calling every piece convex: the ring-shaped mesh collider passes.
- __init__.held taking a mass ratio one way only: the box at half its mass passes.
- _finish.finish_likeness ignoring the family: a 30% part of the wrong family passes.
- _finish.part_look measuring the colour difference in a*b* alone (lightness free): the toaster's body in stainless
  #e0e0e0 passes its colour, and so does the #484848 body.
- _finish.carried returning each face's truth material instead of its triangle: every look row reads the wrong faces.
- _finish.part_look holding every metalness: the metal body passes.
- _finish.finish_look judging every roughness held: the body rough 0.9 passes.
- _finish.part_look judging every class the same: the steel body passes.
- _finish.see_through_held judging every part held (#186): the top drawn opaque and the body drawn see-through pass;
  _finish.true_through reading no truth as see-through: the opaque top is not judged.
- _finish.pattern_held judging the ratio one way only (`ratio <= PATTERN_REACH`): the humidifier's lost ribs pass;
  without PATTERN_FLOOR: the granite seat over NVIDIA's 0.0 divides by zero.
- __init__.step_change measuring after against itself: the step that flattened the box by 10% passes.
- _physics.rested comparing heights only: the drop that laid it on its side passes up.
- __init__.BARS without its look.holes row (#159) -> the printer box's holed look has no look.holes row to fail.
- _joints (#177, the hung cabinet: the box with a door slab hinged on its left edge; NVIDIA's hinge about -z, limits -90
  to 0): moving_bodies taking a joint's body0 (the carcass) -> the door cut as NVIDIA's fails its faces;
  count_gap never counting
  -> no moving part passes; line_angle as a signed angle -> NVIDIA's -z against the made +z fails its axis (180);
  off_line the distance between pivots (along the axis too) -> the door's pivot 0.4 m up its hinge line fails;
  range_gap on the upper limits alone -> the door opening 0 to 90 against -90 to 0 fails.
- __init__.pictured judging its size against the target's proportions: the pictured box 20% too big passes its size.
- __init__.held taking gate_wall's bound as 0: the pictured 1 mm shell passes its wall.
- __init__.label_words keeping case and spaces: the labels printed "on" and "OFF " miss two.
- __init__.picks reading the class alone: the rusted metal top passes its picks.
- __init__.picks counting every part held: the cloth top passes its picks.
- __init__.text_read counting every mark read (#185: tc4r's sign drew a garbled "C" for "03" and passed): the OFF label
  drawn garbled passes; label_words(mark["read"]) -> mark["read"]: the labels read "on" and "OFF " fail;
  ("look", "read") left out of PICTURED_BARS: the garbled label is not judged.
- PICTURED_BARS without the picture judge's rows (#159 round 7: the cockpit looks judged by no one) -> the look whose
  shape is off its close-up and the look worse than the previous round's pass; without ("look", "holes") -> the look
  holed through passes.
"""
import functools
import pathlib
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import measures  # noqa: E402

SIDES = (0.5, 0.4, 0.8)


def standing(mesh):
    """The mesh moved so its floor is z=0 and its box is centred on the Z axis."""
    low, high = mesh.bounds
    mesh.apply_translation((-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]))
    return mesh


def box(sides=SIDES):
    return standing(trimesh.creation.box(sides))


def turned(mesh, degrees, axis=(1, 0, 0)):
    mesh = mesh.copy()
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(degrees), axis, mesh.centroid))
    return standing(mesh)


def top_material(mesh):
    return (mesh.face_normals[:, 2] > 0.5).astype(int)


def side(mesh, material=None, mass=10.0, colliders="hull", friction=0.5):
    """A side dict as the bench reads it; colliders "hull" is the mesh's own points as one convex piece."""
    if isinstance(colliders, str):
        colliders = [{"vertices": mesh.vertices, "faces": None}]
    return {"vertices": mesh.vertices, "faces": mesh.faces, "face_material": material, "box": mesh.bounds,
            "mass": mass, "colliders": colliders, "friction": friction}


TRUTH = side(box(), top_material(box()))
OTHERS = [side(standing(trimesh.creation.cylinder(0.22, 0.8, sections=48)), None) | {"id": "cylinder"},
          side(box((0.6, 0.5, 0.05)), None) | {"id": "plate"}]


def two_prims_one_finish():
    """TRUTH with its sides bound as two material prims of one surface (as the pantry cabinet binds its wood)."""
    mesh = box()
    split = np.where(mesh.face_normals[:, 2] > 0.5, 1, np.where(mesh.triangles_center[:, 0] < 0, 0, 2))
    return {**TRUTH, "face_material": split,
            "materials": [{"name": "side_a", "surface": "wood"}, {"name": "top", "surface": "paint"},
                          {"name": "side_b", "surface": "wood"}]}


def one_model_finishes():
    """TRUTH with its top and sides two material names bound to one surface painted for one model (the toaster's
    plastic and metal, one picture)."""
    return {**TRUTH, "materials": [{"name": "plastic", "surface": "atlas", "one_model": True},
                                   {"name": "metal", "surface": "atlas", "one_model": True}]}


def with_slivers():
    """The box cut finer, three of its 192 faces (0.5% of its area each) parts of their own."""
    mesh = box().subdivide().subdivide()
    parts = top_material(mesh)
    parts[[0, 1, 2]] = [2, 3, 4]
    return mesh, parts


def made(mesh, whole=False, **given):
    """The made side's measures against TRUTH; with `whole` the kind's others ranked and its top a finish of its own
    (unless `material` says), else neither: the rank and the finish edges are the dearest measures, and a row that
    judges another one has no use for them."""
    material = given.pop("material", top_material(mesh) if whole else None)
    return measures.measured(TRUTH, side(mesh, material, **given), others=OTHERS if whole else ())


@functools.cache
def uneven():
    """The box cut into 12288 uneven triangles on a bumpy surface as TRELLIS.2 cuts a model (each corner inside a face
    moved up to a fifth of a step within it and a tenth of one out of it), standing as the truth."""
    mesh = trimesh.creation.box(SIDES)
    for _ in range(5):
        mesh = mesh.subdivide()
    mesh.merge_vertices()
    half = np.array(SIDES) / 2
    free = ~np.isclose(np.abs(mesh.vertices), half)
    inside = free.sum(1, keepdims=True) == 2
    shift = np.random.default_rng(5).uniform(-0.2, 0.2, mesh.vertices.shape) * np.array(SIDES) / 2 ** 5
    shift = np.where(free, shift, shift / 2)
    return standing(trimesh.Trimesh(mesh.vertices + np.where(inside, shift, 0), mesh.faces, process=False))


def cut_along(mesh, planes):
    """The mesh with its triangles cut along each plane (normal, point), so no face crosses one."""
    for normal, point in planes:
        halves = [trimesh.intersections.slice_faces_plane(mesh.vertices, mesh.faces, sign * np.asarray(normal, float),
                                                         point)[:2] for sign in (1, -1)]
        mesh = trimesh.util.concatenate([trimesh.Trimesh(*half, process=False) for half in halves])
        mesh.merge_vertices()
    return mesh


def slant(mesh):
    """Whether each face's middle is above the slanted plane z = 0.3 + 0.3 x."""
    middle = mesh.triangles_center
    return (middle[:, 2] > 0.3 + 0.3 * middle[:, 0]).astype(int)


@functools.cache
def cut_cleanly():
    """The uneven box cut along the slanted plane through its triangles (run 1's smooth line), each side its finish."""
    mesh = cut_along(uneven(), [((-0.3, 0, 1), (0, 0, 0.3))])
    return mesh, slant(mesh)


@functools.cache
def labelled():
    """The uneven box with an 8 x 8 cm label cut cleanly into its front, a finish of its own (square corners)."""
    mesh = cut_along(uneven(), [((1, 0, 0), (-0.04, 0, 0)), ((1, 0, 0), (0.04, 0, 0)), ((0, 0, 1), (0, 0, 0.36)),
                                ((0, 0, 1), (0, 0, 0.44))])
    middle = mesh.triangles_center
    label = (np.abs(middle[:, 0]) < 0.04) & (np.abs(middle[:, 2] - 0.4) < 0.04) & (middle[:, 1] < -0.15)
    return mesh, label.astype(int)


def specked():
    """The uneven box's top and sides, twelve lone side triangles given the top's finish."""
    mesh = uneven()
    parts = top_material(mesh)
    parts[np.random.default_rng(3).choice(np.flatnonzero(parts == 0), 12, replace=False)] = 1
    return mesh, parts


def with_sticker():
    """The uneven box with a 6 cm round sticker in a finish of its own on its front (its triangles), and a 1 cm block
    modelled apart in its sides' finish 6 m off: one model 6 m across."""
    mesh = uneven()
    parts = top_material(mesh)
    middle = mesh.triangles_center
    parts[(np.linalg.norm(middle[:, [0, 2]] - (0, 0.4), axis=1) < 0.03) & (middle[:, 1] < -0.15)] = 2
    block = trimesh.creation.box((0.01, 0.01, 0.01)).apply_translation((6, 0, 0.005))
    return trimesh.util.concatenate([mesh, block]), np.r_[parts, np.zeros(len(block.faces), int)]


def edged(mesh, material, seen=None):
    """How cleanly a made model's finishes meet (its parts its finishes; `seen` each face's pixels in its look),
    against TRUTH's own: the finish-edge measures alone, as measured adds them."""
    own = measures._edges.finish_edges(TRUTH["vertices"], TRUTH["faces"], TRUTH["face_material"])
    return {"finish": measures._edges.finish_edges(mesh.vertices, mesh.faces, material, seen), "truth_clean": own}


def looked_from(mesh, way):
    """Each face's pixels in a look drawn from straight `way` (a unit axis): one where the face turns towards it."""
    return (mesh.face_normals @ np.asarray(way, dtype=float) > 0.5).astype(int)


def with_floater():
    return trimesh.util.concatenate([box(), trimesh.creation.box((0.01, 0.01, 0.01)).apply_translation((0, 0, 1.2))])


def missing_face():
    mesh = box()
    return trimesh.Trimesh(mesh.vertices, mesh.faces[1:], process=False)


def open_top():
    """The box with no lid: an open crate, its hull still its collider as NVIDIA's are."""
    mesh = box()
    return trimesh.Trimesh(mesh.vertices, mesh.faces[mesh.face_normals[:, 2] < 0.5], process=False)


def shell(wall=0.001):
    inner = box(tuple(value - 2 * wall for value in SIDES)).apply_translation((0, 0, wall))
    inner.invert()
    return trimesh.util.concatenate([box(), inner])


def cabinet(shelves):
    """The box closed round three inner shelves at these heights (a fridge's liner and shelves, NVIDIA's inside)."""
    planks = [box((0.46, 0.36, 0.01)).apply_translation((0, 0, height)) for height in shelves]
    return trimesh.util.concatenate([box()] + planks)


def grown(mesh, reach):
    hull = mesh.copy()
    hull.vertices = hull.vertices + np.sign(hull.vertices - hull.centroid) * reach
    return [{"vertices": hull.vertices, "faces": None}]


def ring_collider():
    ring = trimesh.creation.annulus(r_min=0.1, r_max=0.2, height=0.3)
    return [{"vertices": ring.vertices, "faces": ring.faces}]


def looks(wrong_family_area, wrong_colour_area):
    """Matched parts' look-alike measures: a share of the area of the wrong family, a share too far in colour."""
    held = {"delta_e": 4.0, "lightness": 3.0, "highlight": 2.0, "detail": 1.0}
    far = {**held, "delta_e": 15.0}
    rows = [(1 - wrong_family_area - wrong_colour_area, held, "plastic"), (wrong_family_area, held, "metal"),
            (wrong_colour_area, far, "plastic")]
    return {"likeness": measures.finish_likeness([{"area": area, "views": {"overview": view, "close": view},
                                                   "family": family, "true_family": "plastic"}
                                                  for area, view, family in rows if area > 0])}


# NVIDIA's look on the truth (#172), as the owner's toaster: its sides and floor a dark grey plastic (linear albedo
# 0.013, sRGB #1d1d1d), its top an aluminium (0.33, metal 0.9). A part's look: linear colour, metal, roughness, class.
BODY = {"colour": [0.013] * 3, "metal": 0.0, "roughness": 0.24, "class": "plastic", "opacity": 1.0, "through": False}
TOP = {"colour": [0.33] * 3, "metal": 0.9, "roughness": 0.3, "class": "aluminium", "opacity": 0.3, "through": True}


def linear(token):
    """An sRGB hex token's linear grey."""
    value = int(token[1:3], 16) / 255
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4] * 3


@functools.cache
def looked_truth():
    """(TRUTH wearing NVIDIA's look, BODY sides and TOP top; each of its faces' nearest truth triangle: its own)."""
    faces = top_material(box())
    truth_look = {key: np.array([(TOP if face else BODY)[name] for face in faces], dtype=object if key == "class"
                                else float) for key, name in (("albedo", "colour"), ("metal", "metal"),
                                                              ("roughness", "roughness"), ("class", "class"),
                                                              ("see_through", "through"))}
    truth = {**measures.arrays(TRUTH), "face_look": truth_look}
    return truth, measures._finish.carried(truth, truth["vertices"], truth["faces"])


def worn(body, top=TOP):
    """The finish look of the box made with its two parts in these looks, laid as TRUTH, against looked_truth."""
    (truth, nearest), faces = looked_truth(), top_material(box())
    return {"finish": measures._finish.finish_look(truth, truth["vertices"], truth["faces"], faces, nearest,
                                                   {0: {**BODY, **body}, 1: {**TOP, **top}})}


HOLE = 0.06  # metres across the dark cable hole on the desk-like truth's top, near its front left corner


@functools.cache
def holed_truth():
    """The box with a dark 6 cm cable hole laid 1 mm over its top near its front left corner (0.2% of its area, as
    tc4r's desk's), NVIDIA's look on it: its sides BODY's dark plastic, its top TOP's aluminium, the hole black."""
    body = box()
    low, high = body.bounds
    corner = np.array([low[0] + 0.05, low[1] + 0.05, high[2] + 0.001])
    hole = trimesh.Trimesh(np.array([corner, corner + [HOLE, 0, 0], corner + [HOLE, HOLE, 0], corner + [0, HOLE, 0]]),
                           [[0, 1, 2], [0, 2, 3]])
    mesh = trimesh.util.concatenate([body, hole])
    finish = np.r_[top_material(body), [2, 2]]
    colours = {0: BODY["colour"], 1: TOP["colour"], 2: [0.002] * 3}
    look = {"albedo": np.array([colours[int(one)] for one in finish], dtype=float)}
    return {**measures.arrays(side(mesh, finish)), "face_look": look}, mesh, finish, colours


def headed(degrees):
    """The measures of the box laid turned `degrees` about up, painted as a made model is (`painted`: its own texture
    on its one surface, the hole painted into its top), against the holed truth."""
    truth, mesh, _, colours = holed_truth()
    body = box()
    points, faces = trimesh.sample.sample_surface(body, 20000, seed=3)
    low = mesh.vertices[-4]
    in_hole = (points[:, 2] > body.bounds[1][2] - 1e-6) \
        & np.all((points[:, :2] >= low[:2]) & (points[:, :2] <= low[:2] + HOLE), 1)
    colour = np.where(in_hole[:, None], colours[2], np.where(top_material(body)[faces][:, None] == 1, colours[1],
                                                               colours[0]))
    turn = trimesh.transformations.rotation_matrix(np.radians(degrees), (0, 0, 1), body.bounds.mean(0))
    laid = trimesh.Trimesh(trimesh.transformations.transform_points(body.vertices, turn), body.faces, process=False)
    painted = {"points": trimesh.transformations.transform_points(points, turn), "colour": colour}
    return measures.measured(truth, {**side(laid), "painted": painted})


def dropped(made_turn):
    """The two drops' rests: the truth stays as laid, the made one turned `made_turn` degrees about X."""
    motion = trimesh.transformations.rotation_matrix(np.radians(made_turn), (1, 0, 0))
    return {"drop": measures.rested(np.eye(4), TRUTH["vertices"], motion, TRUTH["vertices"])}


def flattened(share):
    after = box()
    after.vertices[:, 2] *= 1 - share
    return {"steps": measures.step_change(TRUTH, side(box()), side(after))}


@functools.cache
def hung_cabinet():
    """The box with a door slab 2 cm thick hung on its front (-y) face, hinged about the upright at its left edge, as
    NVIDIA's truth (its hinge about -z, -90 to 0 degrees); each of its faces' nearest truth triangle (itself)."""
    door = trimesh.creation.box((0.48, 0.02, 0.76))
    door.apply_translation((0.0, -0.21, 0.4))
    carcass = box()
    mesh = trimesh.util.concatenate([carcass, door])
    body = np.r_[np.zeros(len(carcass.faces), int), np.ones(len(door.faces), int)]
    truth = {**side(mesh), "face_body": body, "bodies": [{"prim": "carcass"}, {"prim": "door"}],
             "joints": [{"prim": "hinge", "type": "PhysicsRevoluteJoint", "body0": 0, "body1": 1,
                         "axis": [0.0, 0.0, -1.0], "pivot": [-0.24, -0.21, 0.0], "limits": [-90.0, 0.0]}]}
    truth = measures.arrays(truth)
    return mesh, body, truth, measures._finish.carried(truth, truth["vertices"], truth["faces"])


HINGE = {"type": "revolute", "axis": [0.0, 0.0, 1.0], "pivot": [-0.24, -0.2, 0.4], "limits": [0.0, 90.0]}


def hung(faces="door", whole=False, **joint):
    """The cabinet made as its truth, its door cut as `faces` ("door", "top" or "none") on `joint` (HINGE changed):
    every measure (`whole`), else its parts' alone, the made model standing on the truth as it is."""
    mesh, body, truth, nearest = hung_cabinet()
    part = {"door": body - 1, "top": np.where((mesh.face_normals[:, 2] > 0.5) & (body == 0), 0, -1),
            "none": np.full(len(body), -1)}[faces]
    made_side = {**side(mesh), "face_part": part, "joints": [] if faces == "none" else [{**HINGE, **joint}]}
    if whole:
        return measures.measured(truth, made_side)
    return {"parts": measures._joints.joints(truth, truth["vertices"], made_side, nearest, np.eye(4))}


def leaning(degrees):
    return (trimesh.transformations.rotation_matrix(np.radians(degrees), (1, 0, 0))[:3, :3] @ [0, 0, 1]).tolist()


PICTURE = {"labels": ["ON", "OFF"], "classes": ["metal", "plastic"], "never": ["cloth", "rusted_metal"]}


def pictured(mesh, fit=0.95, decals=("ON", "OFF"), top=("plastic", "paint"), material=None, read=None, seen=None):
    """(the made box's pictured measures against SIDES as its target and PICTURE, PICTURED_BARS): its sides part 0 in
    metal paint, its top part 1 of `top` (class, recipe), its decals' text `decals`, with `read` ((its words, what
    its look read there), ...) its look's text marks read back (#185), and with `seen` ({group: {measure: value}})
    its look's holes and the picture judge's group against its close-up (#159 round 7)."""
    parts = top_material(mesh) if material is None else material
    made = {**side(mesh, parts), "classes": {0: "metal", 1: top[0]}, "families": {0: "paint", 1: top[1]},
            "decals": list(decals)}
    found = measures.pictured(SIDES, made, fit, PICTURE)
    if read is not None:
        found["look"] = measures.text_read([{"text": text, "read": shown} for text, shown in read])
    for group, values in (seen or {}).items():
        found[group] = {**found.get(group, {}), **values}
    return found, measures.PICTURED_BARS


CASES = [
    ("the truth itself", lambda: made(box(), whole=True), None, True),
    ("the door cut and hung as NVIDIA's", lambda: hung(whole=True), None, True),
    ("no moving part cut", lambda: hung("none"), "parts.count_gap", False),
    ("the top cut as the door", lambda: hung("top"), "parts.faces_least", False),
    ("the door on a slide", lambda: hung(type="prismatic"), "parts.type_held", False),
    ("its hinge leaning 15 degrees", lambda: hung(axis=leaning(15)), "parts.axis_most", False),
    ("its hinge leaning 5 degrees", lambda: hung(axis=leaning(5)), "parts.axis_most", True),
    ("its hinge on the right edge", lambda: hung(pivot=[0.24, -0.2, 0.4]), "parts.pivot_most", False),
    ("opening 30 degrees for 90", lambda: hung(limits=[0.0, 30.0]), "parts.range_most", False),
    ("opening 120 degrees for 90", lambda: hung(limits=[0.0, 120.0]), "parts.range_most", True),
    ("laid on its side", lambda: made(turned(box(), 90)), "alignment.up_error", False),
    ("its cable hole where NVIDIA's is", lambda: headed(0), "orientation.heading", True),
    ("laid a half turn off, its cable hole in the far corner (tc4r's desk)", lambda: headed(180),
     "orientation.heading", False),
    ("laid a quarter turn off (tc4r's fridge, its door on its side)", lambda: headed(90), "orientation.heading", False),
    ("leaning 8 degrees", lambda: made(turned(box(), 8)), "alignment.up_error", False),
    ("leaning 3 degrees", lambda: made(turned(box(), 3)), "alignment.up_error", True),
    ("upright, its inner shelves where the truth's sit upside down", lambda: measures.measured(
        side(cabinet((0.1, 0.18, 0.26)), None), side(cabinet((0.53, 0.61, 0.69)), None)), "alignment.up_error", True),
    ("10% wider", lambda: made(box((0.55, 0.4, 0.8))), "size.size", False),
    ("4% wider", lambda: made(box((0.52, 0.4, 0.8))), "size.size", True),
    ("20% too big all round", lambda: made(box((0.6, 0.48, 0.96))), "size.size", False),
    ("the truth with its recoloured twin among the kind", lambda: measures.measured(
        TRUTH, side(box(), top_material(box())), others=OTHERS + [{**TRUTH, "id": "twin"}]), "shape.rank", True),
    ("the truth beside its double at twice the size", lambda: measures.measured(
        TRUTH, side(box(), top_material(box())), others=[side(box(tuple(2 * value for value in SIDES)), None)]),
     "shape.rank", False),
    ("a cylinder in the box's place", lambda: made(standing(trimesh.creation.cylinder(0.22, 0.8)), whole=True,
                                                   material=None), "shape.rank", False),
    ("the box missing a face", lambda: made(missing_face(), material=None), "clean.open_length", False),
    ("a 1 cm floater", lambda: made(with_floater(), material=None), "clean.crumbs", False),
    ("a 1 mm shell", lambda: made(shell(), material=None), "clean.thinnest", False),
    ("a 1.5 mm shell for a 2 mm one", lambda: measures.measured(side(shell(0.002), None), side(shell(0.0015), None)),
     "clean.thinnest", True),
    ("a 0.5 mm shell for a 2 mm one", lambda: measures.measured(side(shell(0.002), None), side(shell(0.0005), None)),
     "clean.thinnest", False),
    ("cut 16 times finer", lambda: made(box().subdivide().subdivide()), "clean.triangles_per_m2", False),
    ("its sides bound as two prims of one finish", lambda: measures.measured(
        two_prims_one_finish(), side(box(), top_material(box()))), "finish.held_least", True),
    ("one part for two names of one picture", lambda: measures.measured(
        one_model_finishes(), side(box(), np.zeros(12, int))), "finish.held_least", False),
    ("three sliver parts beside its two", lambda: made(with_slivers()[0], material=with_slivers()[1]),
     "finish.parts_per_material", True),
    ("one part for two materials", lambda: made(box(), material=np.zeros(12, int)), "finish.held_least", False),
    ("the top cut along the box's rim", lambda: edged(uneven(), top_material(uneven())), "finish.edge_wander", True),
    ("a slant cut cleanly through its triangles", lambda: edged(*cut_cleanly()), "finish.edge_wander", True),
    ("a square label cut cleanly into its front", lambda: edged(*labelled()), "finish.edge_wander", True),
    ("the slant given triangle by triangle", lambda: edged(uneven(), slant(uneven())), "finish.edge_wander", False),
    ("the slant between two parts in one surface and look", lambda: measures.measured(TRUTH, {
        **side(uneven(), slant(uneven())), "surfaces": {0: "surface/paint", 1: "surface/paint"},
        "looks": {0: BODY, 1: BODY}}), "finish.edge_wander", True),
    ("twelve lone triangles of the top's finish", lambda: edged(*specked()), "finish.specks", False),
    ("twelve lone side triangles its look, drawn from above, never shows",
     lambda: edged(*specked(), looked_from(specked()[0], (0, 0, 1))), "finish.specks", True),
    ("twelve lone side triangles its look, drawn all round, shows", lambda: edged(*specked(), np.ones(
        len(specked()[0].faces), int)), "finish.specks", False),
    ("a 6 cm sticker on a model 6 m across", lambda: edged(*with_sticker()), "finish.speck_share", True),
    ("the box's own finishes cut finely", lambda: edged(uneven(), top_material(uneven())), "finish.edge_density", True),
    ("a finish per triangle at random", lambda: edged(uneven(), np.random.default_rng(3).integers(
        0, 2, len(uneven().faces))), "finish.edge_density", False),
    ("half its mass", lambda: made(box(), mass=5.0), "physics.mass_ratio", False),
    ("1.4 times its mass", lambda: made(box(), mass=14.0), "physics.mass_ratio", True),
    ("its hull grown 3 cm", lambda: made(box(), colliders=grown(box(), 0.03)), "physics.overhang", False),
    ("its hull grown 3 mm", lambda: made(box(), colliders=grown(box(), 0.003)), "physics.overhang", True),
    ("an open box under its hull", lambda: made(open_top(), material=None), "physics.overhang", True),
    ("no collider", lambda: made(box(), colliders=[]), "physics.colliders", False),
    ("a ring-shaped mesh collider", lambda: made(box(), colliders=ring_collider()), "physics.convex", False),
    ("friction 0.7 for 0.5", lambda: made(box(), friction=0.7), "physics.friction_gap", False),
    ("a 30% part of the wrong family", lambda: looks(0.3, 0.0), "likeness.alike", False),
    ("a 10% part too far in colour", lambda: looks(0.0, 0.1), "likeness.alike", True),
    ("each part in its matching surface", lambda: worn({}), "finish.colour", True),
    ("the toaster's body in stainless #e0e0e0", lambda: worn({"colour": linear("#e0e0e0"), "metal": 1.0,
                                                              "roughness": 0.16, "class": "metal"}),
     "finish.colour", False),
    ("its body a #282828 plastic for #1d1d1d", lambda: worn({"colour": linear("#282828")}), "finish.colour", True),
    ("its body a #484848 plastic for #1d1d1d", lambda: worn({"colour": linear("#484848")}), "finish.colour", False),
    ("its body metal", lambda: worn({"metal": 1.0}), "finish.metal", False),
    ("its body rough 0.9 for 0.24", lambda: worn({"roughness": 0.9}), "finish.roughness", False),
    ("its body steel for plastic", lambda: worn({"class": "metal"}), "finish.class", False),
    ("its see-through top see-through, its body not", lambda: worn({}), "finish.see_through", True),
    ("its see-through top drawn opaque (the tc4r fridge's door)", lambda: worn({}, {**TOP, "opacity": 1.0}),
     "finish.see_through", False),
    ("its opaque body drawn see-through", lambda: worn({"opacity": 0.3}), "finish.see_through", False),
    ("its body's grain a little over NVIDIA's (the tire rack's tube, 1.63 for 1.17)",
     lambda: worn({"pattern": 1.63, "true_pattern": 1.17}), "finish.pattern", True),
    ("its smooth body drawn speckled granite (the surgical chair's seat, 4.96 for 0.0)",
     lambda: worn({"pattern": 4.96, "true_pattern": 0.0}), "finish.pattern", False),
    ("its ribbed body drawn smooth (the humidifier's column, 0.2 for 12.9)",
     lambda: worn({"pattern": 0.2, "true_pattern": 12.9}), "finish.pattern", False),
    ("a step that flattened it by 10%", lambda: flattened(0.1), "steps.chamfer_change", False),
    ("the drop that laid it on its side", lambda: dropped(90), "drop.rest_up", False),
    ("the drop that left it as the truth's", lambda: dropped(0), "drop.rest_up", True),
    ("its look holed through its front (tc4's printer box)", lambda: {"look": {"holes": 0.0047}}, "look.holes", False),
    ("its look with a humidifier's few dark vents", lambda: {"look": {"holes": 0.00012}}, "look.holes", True),
    ("pictured: the box as its close-up shows it", lambda: pictured(box()), None, True),
    ("pictured: its outline off the close-up", lambda: pictured(box(), fit=0.8), "shape.closeup", False),
    ("pictured: 20% too big all round", lambda: pictured(box((0.6, 0.48, 0.96))), "size.size", False),
    ("pictured: 4% wider", lambda: pictured(box((0.52, 0.4, 0.8))), "size.size", True),
    ("pictured: the box missing a face", lambda: pictured(missing_face()), "clean.open_length", False),
    ("pictured: a 1 cm floater", lambda: pictured(with_floater()), "clean.crumbs", False),
    ("pictured: a 1 mm shell", lambda: pictured(shell(), material=np.zeros(len(shell().faces), int)),
     "clean.thinnest", False),
    ("pictured: the slant given triangle by triangle", lambda: pictured(uneven(), material=slant(uneven())),
     "finish.edge_wander", False),
    ("pictured: its OFF label not printed", lambda: pictured(box(), decals=("ON",)), "labels.held", False),
    ("pictured: its labels printed on and OFF", lambda: pictured(box(), decals=("on", "OFF ")), "labels.held",
     True),
    ("pictured: its labels read back where its look drew them", lambda: pictured(
        box(), read=(("ON", "on"), ("OFF", "OFF "))), "look.read", True),
    ("pictured: its OFF label drawn garbled", lambda: pictured(box(), read=(("ON", "ON"), ("OFF", "?F?"))),
     "look.read", False),
    ("pictured: its look's reading unanswered", lambda: pictured(box(), read=(("ON", "ON"), ("OFF", None))),
     "look.read", False),
    ("pictured: a cloth top", lambda: pictured(box(), top=("fabric", "cloth")), "finish.picks", False),
    ("pictured: a rusted metal top", lambda: pictured(box(), top=("metal", "rusted_metal")), "finish.picks", False),
    ("pictured: its look seen as its close-up", lambda: pictured(box(), seen={"picture": {
        "drawn": 1, "shape": 0, "regressed": 0}, "look": {"holes": 0.00005}}), None, True),
    ("pictured: its look's shape off its close-up by eye", lambda: pictured(box(), seen={"picture": {
        "drawn": 1, "shape": 1}}), "picture.shape", False),
    ("pictured: its look worse than the previous round's", lambda: pictured(box(), seen={"picture": {
        "drawn": 1, "regressed": 1}}), "picture.regressed", False),
    ("pictured: its look holed through", lambda: pictured(box(), seen={"look": {"holes": 0.0047}}), "look.holes",
     False),
]


@pytest.mark.parametrize("name, found, measure, holds", CASES, ids=[case[0] for case in CASES])
def test_a_made_model_passes_only_where_it_matches_its_truth(name, found, measure, holds):
    found = found()
    verdict = measures.judged(*found) if isinstance(found, tuple) else measures.judged(found)
    if measure is None:
        assert verdict["pass"] is holds, (name, verdict["failed"])
        return
    rows = {row["measure"]: row for row in verdict["rows"]}
    assert rows[measure]["pass"] is holds, (name, rows[measure])
