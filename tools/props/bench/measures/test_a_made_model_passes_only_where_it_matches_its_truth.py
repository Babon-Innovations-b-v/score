"""The bench's measures pass a made model only where it matches its NVIDIA truth (#163): one table of made models
against one small truth (a 0.5 x 0.4 x 0.8 m box, its top one material and its sides another, 10 kg, its hull its
collider, static friction 0.5), each row the one bar a known fault must break, or a known-small error must keep.
The answers are worked by hand: a box laid on its side or leaning 8 degrees is 90 or 8 degrees off up, 10% wider is
a size error of 0.10, a cylinder in the box's place is nearer the kind's cylinder, a 1 mm shell's wall is 1 mm, a
hull grown 3 cm stands 3 cm out, and so on.

Breaks (each applied once, seen red, reverted), in tools/props/bench/measures/:
- _align.aligned keeping the first axis turn (none) and dropping ICP's: the box laid on its side passes up.
- _align.up_error returning 0: the box leaning 8 degrees passes up.
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
- _finish.finish_split counting every part, however small: the three slivers make five parts for two finishes.
- _finish.finish_split holding a finish whatever its parts' purity: one part for two materials passes.
- _physics.overhang reading the distance from inside the hull: the hull grown 3 cm passes its overhang.
- _physics.overhang measuring off the drawn mesh instead of its outline (its convex hull): the open box under its
  own hull, as NVIDIA's crates are, fails its overhang.
- _physics.convex calling every piece convex: the ring-shaped mesh collider passes.
- __init__.held taking a mass ratio one way only: the box at half its mass passes.
- _finish.finish_likeness ignoring the family: a 30% part of the wrong family passes.
- __init__.step_change measuring after against itself: the step that flattened the box by 10% passes.
- _physics.rested comparing heights only: the drop that laid it on its side passes up.
"""
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


def with_slivers():
    """The box cut finer, three of its 192 faces (0.5% of its area each) parts of their own."""
    mesh = box().subdivide().subdivide()
    parts = top_material(mesh)
    parts[[0, 1, 2]] = [2, 3, 4]
    return mesh, parts


def made(mesh, **given):
    """The made side's measures against TRUTH, the kind's others ranked."""
    return measures.measured(TRUTH, side(mesh, given.pop("material", top_material(mesh)), **given), others=OTHERS)


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


def dropped(made_turn):
    """The two drops' rests: the truth stays as laid, the made one turned `made_turn` degrees about X."""
    motion = trimesh.transformations.rotation_matrix(np.radians(made_turn), (1, 0, 0))
    return {"drop": measures.rested(np.eye(4), TRUTH["vertices"], motion, TRUTH["vertices"])}


def flattened(share):
    after = box()
    after.vertices[:, 2] *= 1 - share
    return {"steps": measures.step_change(TRUTH, side(box()), side(after))}


CASES = [
    ("the truth itself", lambda: made(box()), None, True),
    ("laid on its side", lambda: made(turned(box(), 90)), "alignment.up_error", False),
    ("leaning 8 degrees", lambda: made(turned(box(), 8)), "alignment.up_error", False),
    ("leaning 3 degrees", lambda: made(turned(box(), 3)), "alignment.up_error", True),
    ("10% wider", lambda: made(box((0.55, 0.4, 0.8))), "size.size", False),
    ("4% wider", lambda: made(box((0.52, 0.4, 0.8))), "size.size", True),
    ("20% too big all round", lambda: made(box((0.6, 0.48, 0.96))), "size.size", False),
    ("the truth with its recoloured twin among the kind", lambda: measures.measured(
        TRUTH, side(box(), top_material(box())), others=OTHERS + [{**TRUTH, "id": "twin"}]), "shape.rank", True),
    ("the truth beside its double at twice the size", lambda: measures.measured(
        TRUTH, side(box(), top_material(box())), others=[side(box(tuple(2 * value for value in SIDES)), None)]),
     "shape.rank", False),
    ("a cylinder in the box's place", lambda: made(standing(trimesh.creation.cylinder(0.22, 0.8)), material=None),
     "shape.rank", False),
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
    ("three sliver parts beside its two", lambda: made(with_slivers()[0], material=with_slivers()[1]),
     "finish.parts_per_material", True),
    ("one part for two materials", lambda: made(box(), material=np.zeros(12, int)), "finish.held_least", False),
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
    ("a step that flattened it by 10%", lambda: flattened(0.1), "steps.chamfer_change", False),
    ("the drop that laid it on its side", lambda: dropped(90), "drop.rest_up", False),
    ("the drop that left it as the truth's", lambda: dropped(0), "drop.rest_up", True),
]


@pytest.mark.parametrize("name, found, measure, holds", CASES, ids=[case[0] for case in CASES])
def test_a_made_model_passes_only_where_it_matches_its_truth(name, found, measure, holds):
    verdict = measures.judged(found())
    if measure is None:
        assert verdict["pass"] is holds, (name, verdict["failed"])
        return
    rows = {row["measure"]: row for row in verdict["rows"]}
    assert rows[measure]["pass"] is holds, (name, rows[measure])
