"""The people cloth stage (score/stages/people_cloth): a garment's loose points are the ones the shell gate calls loose,
its seam-split points one cloth, the person's skeleton plays the sim body's turns on its own bones, the skin carries a
point by its weights, the body surface is cut one piece a segment in its segment's frame, the cloth values come from
the table by plane stress, and each gate fails its break.

On one toy person and its garment, made here: a 1 cm square of two triangles with one corner given twice (welded to
four points, the face that lost a corner dropped), its fitted shell four rig points beside its corners with offsets
0.01, 0.01, 0.06 and 0.2 m (OFFSET_MOST 0.05: the two corners by the last two loose; a point beside the last that
no face draws, as a primitive sharing another's points holds, loose and not free; a lone loose triangle beside it
and a loose flap on one riding corner, hung by no edge, not free), its cloth the cotton row (E 30.54
N/m, nu 0.3058: lambda 10.3026 N/m, worked by hand), a loose edge pulled 20% past its built and skin length while one
the skin itself draws long, or one at its built length where the skin draws it short, is not stretched; a two-joint
skeleton (Hips at 1 m, Shin 0.5 m under it) whose sim poses are its bind (it stays at its bind), then both turned 90
degrees about up (the shin's foot, 0.5 m under, stays under and turns no further than the Hips), then the Hips alone
turned (the Shin unturned in the world); a point 0.1 m along x off the Hips goes to -0.1 m along z on the Hips, half
of that on Hips and Shin halved. On runs written here (no engine): a good run passes every gate, a loose point 1 cm
inside the body fails `through`, an edge 20% stretched fails `stretch`, cloth still sliding 0.05 m/s on a standing
body fails `rests`. The make with no dressed body names each person left out and writes an empty layer. Newton itself
is not run here (its kernels compile for a minute); the real run's numbers are on its commit.

Breaks that turn the one test red (each applied once and seen red, reverted, 2026-11-13):
- loose_of's `> limit` made `>= 0.0` (the loose corners).
- free_points' `& drawn` dropped (the loose point no face of the part draws taken as free).
- free_points' `>= 2` made `>= 1` (the flap on one riding point taken as free), and its `& hung` dropped (the lone
  triangle and the flap taken as free), each seen red on its own.
- welded's `index[faces]` made `faces` (the welded faces).
- person_worlds' `np.swapaxes(turns[:, segment[parent]], 1, 2) @` dropped (a segment's world turn taken as its turn
  against its parent: the shin turns past the Hips).
- skinned's `@ np.linalg.inv(np.asarray(bind, dtype=float))[None]` dropped (row "all on the Hips").
- pieces' `points[used] @ frame[:3, :3].T + frame[:3, 3]` made `points[used]`.
- material_of's `/ (1.0 - poisson ** 2)` dropped (lambda).
- judge_through's `> limit` made `> 1.0`; judge_stretch's `> STRETCH_MOST` made `> 1.0`; judge_rests' `> REST_MOST`
  made `> 1.0` (each its gate's row of the written runs).
- stretches' `np.maximum(built[None], riding)` made `riding` (row "at built where the skin draws it short"), and made
  `built[None]` (row "long where the skin draws it long"), each seen red on its own.
- make's `left_out.append(...)` dropped (the make's left out).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/people_cloth/test_loose_cloth_rides_its_sim_body_and_is_judged_by_measure.py
"""
import json

import numpy as np
from pxr import Usd
from scipy.spatial.transform import Rotation

from score import checks
from score.stages import people_cloth
from score.stages.people_bodies import bodies

QUARTER = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])  # 90 degrees about up
SIDE = 0.01  # the garment square's side, metres


def person():
    """One toy person: Root at the floor, Hips 1 m over it, Shin 0.5 m under the Hips (kept: Hips, Shin), and its
    fitted shell beside the garment square: two rig points 1 cm off it, one 6 cm, one 20 cm (the last two loose)."""
    bind = np.repeat(np.eye(4)[None], 3, axis=0)
    bind[1, 1, 3], bind[2, 1, 3] = 1.0, 0.5
    return {"names": np.array(["Root", "Hips", "Shin"]), "parents": np.array([-1, 0, 1]), "bind": bind,
            "points": np.array([[-0.001, 0.0, 0.0], [0.0, 0.011, 0.0], [0.011, 0.0, 0.0], [0.011, 0.011, 0.0]]),
            "shell_offsets": np.array([0.01, 0.01, 0.06, 0.2])}


def garment():
    """The square of two triangles as the glTF gives it: corner (SIDE, 0) given twice (a seam split), and a face
    that loses a corner once the two are one."""
    points = np.array([[0.0, 0.0, 0.0], [SIDE, 0.0, 0.0], [0.0, SIDE, 0.0], [SIDE, SIDE, 0.0], [SIDE, 0.0, 0.0]])
    return points, np.array([[0, 1, 2], [4, 3, 2], [1, 4, 2]])


def sim_poses(rig):
    """The sim body's segment poses (frames x [Hips, Shin] x 7): at the bind; both turned a quarter at the Hips;
    the Hips turned a quarter with the Shin left unturned in the world."""
    def frame(hips, shin):
        return [[*rig["bind"][joint][:3, 3], *Rotation.from_matrix(turn).as_quat()]
                for joint, turn in ((1, hips), (2, shin))]
    return [frame(np.eye(3), np.eye(3)), frame(QUARTER, QUARTER), frame(QUARTER, np.eye(3))]


def written_run(folder, deep=0.0, stretch=0.02, restless=0.001):
    """A people_cloth.json as the make writes it, one standing and one walking person."""
    def part(clip):
        found = {"deepest m": deep, "frames deeper than thickness": int(deep > 0.003), "largest stretch": stretch,
                 "largest drift off skin m": 0.01}
        if clip in people_cloth.STILL:
            found["restless m/s"] = restless
        return {"cloth_5": {"node": "made", "points": 10, "loose": 3, "measures": found}}
    folder.mkdir()
    record = {"place": "toy", "engine": "written", "seconds": 0.0, "left out": [],
              "people": {"stander": {"clip": "standing", "parts": part("standing"), "left out": []},
                         "walker": {"clip": "walking", "parts": part("walking"), "left out": []}}}
    (folder / people_cloth.RECORD).write_text(json.dumps(record))
    return folder


def failed_gates(folder):
    return {check.name for check in people_cloth.CHECKS if check.judge(folder, {}, {}).answer == checks.FAIL}


def left_out_run(tmp_path):
    """The make on a cast whose one person has no dressed and built body: its out folder."""
    tmp_path.mkdir()
    sim, cast, out = tmp_path / "sim", tmp_path / "cast", tmp_path / "out"
    for folder in (sim, cast, out):
        folder.mkdir()
    (sim / "sim_bodies.json").write_text(json.dumps({"rate": 30.0, "gravity": 9.81, "bodies": {
        "nev": {"clip": "standing", "measures": {}}}}))
    (cast / "cast.json").write_text(json.dumps({"place": "toy", "characters": [
        {"name": "nev", "look": "astronaut/made", "doing": "standing"}], "crowd": None}))
    np.savez(tmp_path / "rig.npz", weights=np.zeros((1, 1)))
    inputs = {"sim-body": str(sim), "cast": str(cast), "people-clips-made": str(tmp_path),
              "cloth materials": str(people_cloth.REPO / "data/physics/cloth.json")}
    people_cloth.make(inputs, out, 0, {})
    return out


def moved(points, corner, to):
    found = points.copy()
    found[corner] = to
    return found[None]


def test_loose_cloth_rides_its_sim_body_and_is_judged_by_measure(tmp_path):
    rig = person()
    glb_points, glb_faces = garment()

    # the garment as one cloth: the seam-split corner welded, the face that lost a corner dropped
    points, faces, index = people_cloth.welded(glb_points, glb_faces)
    assert len(points) == 4 and index[1] == index[4]
    assert len(faces) == 2 and np.allclose(points[faces[1]], glb_points[[4, 3, 2]])

    # its free points are the shell gate's loose cloth its faces draw: near the 6 cm and 20 cm offsets, not the 1 cm
    # ones; a loose point another primitive sharing its points draws, and this part's faces do not, is not free
    loose = people_cloth.loose_of(glb_points, rig, bodies.OFFSET_MOST)
    free = people_cloth.free_points(points, faces, index, loose)
    assert {tuple(point) for point in points[free]} == {(SIDE, 0.0, 0.0), (SIDE, SIDE, 0.0)}
    assert free.sum() == 2
    shared = np.vstack([glb_points, [[2 * SIDE, 2 * SIDE, 0.0]]])  # by the 20 cm offset: loose, drawn by no face here
    shared_points, shared_faces, shared_index = people_cloth.welded(shared, glb_faces)
    shared_loose = people_cloth.loose_of(shared, rig, bodies.OFFSET_MOST)
    assert shared_loose[-1]
    shared_free = people_cloth.free_points(shared_points, shared_faces, shared_index, shared_loose)
    assert shared_free.sum() == 2 and not shared_free[shared_index[-1]]
    only_undrawn = np.zeros(len(shared), dtype=bool)
    only_undrawn[-1] = True
    assert not people_cloth.free_points(shared_points, shared_faces, shared_index, only_undrawn).any()
    # a piece hung on the body by no edge rides the skin: a lone triangle all loose (by the 20 cm offset) and a flap
    # of two loose points on the square's riding corner (0, 0) alone; the square's loose corners stay free
    corner = 2 * SIDE
    hung = np.vstack([glb_points, [[corner, corner, 0.0], [corner + 0.001, corner, 0.0], [corner, corner + 0.001, 0.0],
                                   [corner, corner, 0.001], [corner + 0.001, corner, 0.001]]])
    hung_faces = np.vstack([glb_faces, [[5, 6, 7], [0, 8, 9]]])
    hung_points, hung_welded, hung_index = people_cloth.welded(hung, hung_faces)
    hung_loose = people_cloth.loose_of(hung, rig, bodies.OFFSET_MOST)
    assert hung_loose[5:].all() and not hung_loose[0]
    hung_free = people_cloth.free_points(hung_points, hung_welded, hung_index, hung_loose)
    assert hung_free.sum() == 2 and not hung_free[hung_index[5:]].any()

    # its cloth values from the cotton row by plane stress, the bending over the welded cloth's mean edge
    row = json.loads((people_cloth.REPO / "data/physics/cloth.json").read_text())["recipes"]["cloth"]
    material = people_cloth.material_of(row, points, faces, 0.003)
    assert material["mu"] == row["shear"] == 4.971
    assert round(material["lambda"], 4) == 10.3026
    assert np.isclose(material["bending"], row["bending"] / ((2 * SIDE + SIDE * 2 ** 0.5) / 3))
    assert material["radius"] == 0.0015 and material["density"] == 0.224

    # a loose edge's stretch is its length over the longer of its built and its skin's length (cloth, skin, stretch)
    corner, rest = index[1], points
    for case, cloth, skin, stretch in (
            ("pulled 20% past built and skin", moved(rest, corner, (0.012, 0.0, 0.0)), rest[None], 0.2),
            ("long where the skin draws it long", moved(rest, corner, (0.02, 0.0, 0.0)),
             moved(rest, corner, (0.02, 0.0, 0.0)), 0.0),
            ("at built where the skin draws it short", rest[None], moved(rest, corner, (0.008, 0.0, 0.0)), 0.0)):
        assert np.isclose(people_cloth.stretches(cloth, rest, skin, faces, free)[0], stretch, atol=1e-9), case

    # the skeleton plays the sim's turns on its own bones
    worlds = people_cloth.person_worlds(rig, [1, 2], sim_poses(rig))
    assert np.allclose(worlds[0], rig["bind"])
    assert np.allclose(worlds[1, 2, :3, 3], (0.0, 0.5, 0.0)) and np.allclose(worlds[1, 2, :3, :3], QUARTER)
    assert np.allclose(worlds[1, 1, :3, :3].T @ worlds[1, 2, :3, :3], np.eye(3)), "the shin turns past its parent"
    assert np.allclose(worlds[2, 2, :3, 3], (0.0, 0.5, 0.0)) and np.allclose(worlds[2, 2, :3, :3], np.eye(3))

    # the skin carries a point 0.1 m along x off the Hips by its weights through those worlds, frame by frame
    point = np.array([[0.1, 1.0, 0.0]])
    for case, joints, weights, expected in (
            ("all on the Hips", [[1, 2]], [[1.0, 0.0]], [(0.1, 1.0, 0.0), (0.0, 1.0, -0.1), (0.0, 1.0, -0.1)]),
            ("half Hips, half Shin", [[1, 2]], [[0.5, 0.5]],
             [(0.1, 1.0, 0.0), (0.0, 1.0, -0.1), (0.05, 1.0, -0.05)])):
        found = people_cloth.skinned(point, np.array(joints), np.array(weights), worlds, rig["bind"])
        assert np.allclose(found[:, 0], expected), case

    # the body surface cut one piece a segment, in its segment's bind frame
    body = np.array([[0.0, 1.0, 0.0], [0.1, 1.0, 0.0], [0.0, 1.1, 0.0], [0.0, 0.5, 0.0], [0.1, 0.5, 0.0],
                     [0.0, 0.4, 0.0]])
    weights = np.zeros((6, 3))
    weights[:3, 1], weights[3:, 2] = 1.0, 1.0
    cut = people_cloth.pieces(body, np.array([[0, 1, 2], [3, 4, 5]]), weights, [1, 2], [1, 1, 2], rig["bind"])
    assert [len(piece["faces"]) for piece in cut] == [1, 1]
    assert np.allclose(sorted(map(tuple, cut[0]["points"])), sorted([(0, 0, 0), (0.1, 0, 0), (0, 0.1, 0)]))
    assert np.allclose(sorted(map(tuple, cut[1]["points"])), sorted([(0, 0, 0), (0.1, 0, 0), (0, -0.1, 0)]))

    # a good written run passes every gate and each break fails its own gate alone
    for gate, made in (("", {}), ("through", {"deep": 0.01}), ("stretch", {"stretch": 0.2}),
                       ("rests", {"restless": 0.05})):
        assert failed_gates(written_run(tmp_path / (gate or "good"), **made)) == ({gate} - {""}), gate or "good"

    # the make with no dressed body names the person left out and writes an empty layer
    out = left_out_run(tmp_path / "make")
    assert json.loads((out / people_cloth.RECORD).read_text())["left out"] == [
        "nev: no usable dressed and built body of its look (people-dress-astronaut-made, people-body-astronaut-made)"]
    assert people_cloth.output_faults(out) == []
    assert not list(Usd.Stage.Open(str(out / people_cloth.LAYER)).Traverse())
