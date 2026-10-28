"""records: the record's pieces come out as worked by hand: a pose as place and quaternion, a segment's turn against
its parent in degrees, a mesh's near vertices merged with its flat faces dropped, RRA's `adjusted` record's pelvis
centimetres, least share and mass percent, and the arrays named for the person. It runs in Newton's own Python
(MuJoCo pinned there; score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with none
built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- merged's flat-face filter `faces = faces[(faces[:, 0] != faces[:, 1]) & ...]` dropped: a face merged flat stays.
- adjustment_record's `pelvis = 100 * np.linalg.norm(moved_by, axis=1)` made `np.linalg.norm(moved_by, axis=1)`: the
  pelvis' move in metres, not centimetres.
- local_turns' `worlds[parent][:3, :3].T @ worlds[index][:3, :3]` made `worlds[index][:3, :3]`: a turn not against
  its parent.

Run: .venv/bin/python score/stages/sim_body/inside/records/test_a_record_keeps_poses_meshes_and_moves_as_worked_by_hand.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"


def placed(turn, place):
    """A turn and a place as a 4 x 4."""
    import numpy as np
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = turn, place
    return found


def a_pose_and_a_turn_read_as_worked_by_hand():
    """A 90 degree turn about z at (1, 2, 3) is [1, 2, 3, 0, 0, sin 45, cos 45]; a child turned 30 degrees about x under
    a parent turned 90 about z is [30, 0, 0] against it; the root has no turn of its own."""
    import numpy as np
    import records
    from scipy.spatial.transform import Rotation
    parent = placed(Rotation.from_euler("z", 90, degrees=True).as_matrix(), [1.0, 2.0, 3.0])
    child = parent @ placed(Rotation.from_euler("x", 30, degrees=True).as_matrix(), [0.0, 0.0, 0.0])
    pose = records.segment_pose(parent)
    half = np.sqrt(0.5)
    problems = [] if np.allclose(pose, [1.0, 2.0, 3.0, 0.0, 0.0, half, half]) else [f"pose {pose}"]
    turns = records.local_turns([parent, child], [-1, 0])
    return problems + ([] if len(turns) == 1 and np.allclose(turns[0], [30.0, 0.0, 0.0]) else [f"turns {turns}"])


def near_vertices_merge_and_flat_faces_go():
    """Two vertices 1 mm apart (within BONE_CELL, 5 mm) become one; the face between them falls flat and goes; the
    other face stays on the three vertices left."""
    import numpy as np
    import records
    points = np.array([[0.0, 0.0, 0.0], [0.001, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    kept, faces = records.merged(points, np.array([[0, 1, 2], [0, 2, 3]]))
    return [] if len(kept) == 3 and len(faces) == 1 and sorted(faces[0]) == [0, 1, 2] else [
        f"{len(kept)} vertices, faces {faces.tolist()}"]


def the_adjusted_record_reads_in_its_units():
    """The pelvis moved 1 and 3 cm on two frames: median 2 cm and most 3 cm; frame shares 1 and 0.5: least 0.5; a
    mass share of 0.02: 2 %, RRA's recommended -0.5 and -0.25: -50 and -25 %; no segment turned."""
    import numpy as np
    import records
    still = np.tile(np.eye(4), (2, 1, 1, 1))
    found = records.adjustment_record(np.array([[0.01, 0.0, 0.0], [0.03, 0.0, 0.0]]), 1.0, np.array([1.0, 0.5]),
                                      {"mass": 0.02, "mass recommended": [-0.5, -0.25], "torso": np.zeros(3)}, still, still, ["Hips"], [1.0, 2.0])
    wanted = {"pelvis cm": [2.0, 3.0], "least frame share": 0.5, "mass %": 2.0, "largest turn deg": 0.0,
              "kept share": 1.0, "mass % recommended": [-50.0, -25.0]}
    return [f"{key}: {found[key]}, not {value}" for key, value in wanted.items() if found[key] != value]


def the_arrays_are_named_for_the_person():
    """Two frames of one body and one muscle path of two points: `<name>/bones` 2 x 1 x 7, `/paths` 4 x 3, `/counts`
    2 x 1, and each bone's mesh points and faces."""
    import numpy as np
    import records
    found = records.arrays("walker", [[[0.0] * 7]] * 2, [[[0.0] * 7]] * 2, [np.zeros((2, 3))] * 2, [[2], [2]],
                           {"femur_l": (np.zeros((3, 3)), np.array([[0, 1, 2]]))})
    shapes = {name: array.shape for name, array in found.items()}
    wanted = {"walker/bones": (2, 1, 7), "walker/segments": (2, 1, 7), "walker/paths": (4, 3),
              "walker/counts": (2, 1), "walker/mesh/femur_l/points": (3, 3), "walker/mesh/femur_l/faces": (1, 3)}
    return [] if shapes == wanted else [f"arrays {shapes}"]


CHECKS = (a_pose_and_a_turn_read_as_worked_by_hand, near_vertices_merge_and_flat_faces_go,
          the_adjusted_record_reads_in_its_units, the_arrays_are_named_for_the_person)


def in_newton():
    """The checks, in Newton's own Python."""
    sys.path.insert(0, str(INSIDE))
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    if os.environ.get(IN_ENV):
        sys.exit(in_newton())
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        sys.exit(0)
    sys.exit(subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"}).returncode)
