"""Check the plain pieces of the Blender drape: GarmentCode's measurements carried to a body by the measured ratios, the
seams of panels cut apart and put back in the box mesh's order (so GarmentCode's segmentation, a line per box mesh
point, still lines up), fine panels carried onto a sewn coarse cloth, and the cloth file read back by people/drape.py
exactly as it read GarmentCode's own.

Run: .venv/bin/python tools/characters/maker/sewing_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "people"))
import drape  # noqa: E402
import sewing  # noqa: E402

BASE = {"height": 170.0, "bust": 90.0, "underbust": 80.0, "waist": 70.0, "hips": 95.0, "arm_length": 50.0,
        "arm_pose_angle": 45.0, "shoulder_incl": 20.0, "head_l": 25.0, "back_width": 40.0}
MEASURED = {"height": 1.70, "bust": 0.90, "waist": 0.70, "hips": 0.95, "leg_circ": 0.55, "arm_pose_angle": 44.0,
            "arm_length": 0.70, "wrist": 0.15, "shoulder_w": 0.33}

# Two panels, a square each of two triangles, side by side with a gap; their shared side is one seam of two points.
# Box mesh points: 0 and 1 the seam's (shared), 2 and 3 the left panel's outer side, 4 and 5 the right panel's.
LEFT = [[0.0, 0.0, 0.0], [0.0, 10.0, 0.0], [-10.0, 0.0, 0.0], [-10.0, 10.0, 0.0]]
RIGHT = [[4.0, 0.0, 0.0], [4.0, 10.0, 0.0], [14.0, 0.0, 0.0], [14.0, 10.0, 0.0]]
BOX_INDEX = [0, 1, 2, 3, 0, 1, 4, 5]
FACES = [[0, 2, 1], [1, 2, 3], [4, 5, 6], [5, 7, 6]]
BOX_OBJ = "\n".join(["mtllib work_0_material.mtl", "v 2.0 0.0 0.0", "v 2.0 10.0 0.0", "v -10.0 0.0 0.0",
                     "v -10.0 10.0 0.0", "v 14.0 0.0 0.0", "v 14.0 10.0 0.0", "vt 0 0", "vt 1 0", "vt 0 1",
                     "f 1/1 3/2 2/3", "f 2/1 3/2 4/3", "f 1/1 2/2 5/3", "f 2/1 6/2 5/3"]) + "\n"
LABELS = ["stitch_0", "stitch_0", "left", "left", "right", "right"]


def measurements_unchanged_on_the_same_body():
    sized = sewing.sized_measurements(BASE, MEASURED, MEASURED)
    assert sized == {key: round(value, 4) for key, value in BASE.items()}, sized


def measurements_follow_their_own_ratio():
    ours = dict(MEASURED, height=1.53, bust=0.81, waist=0.63, arm_length=0.63, arm_pose_angle=41.0)
    sized = sewing.sized_measurements(BASE, MEASURED, ours)
    assert sized["height"] == 153.0 and sized["head_l"] == 22.5, sized  # lengths follow the height
    assert sized["bust"] == 81.0 and sized["underbust"] == 72.0 and sized["back_width"] == 36.0, sized
    assert sized["waist"] == 63.0 and sized["hips"] == 95.0 and sized["arm_length"] == 45.0, sized
    assert sized["arm_pose_angle"] == 42.0 and sized["shoulder_incl"] == 20.0, sized  # angles move or stay


def threads_tie_every_copy_to_its_first():
    assert sewing.seams(BOX_INDEX).tolist() == [[0, 4], [1, 5]]
    gaps = sewing.seam_gaps(np.array(LEFT + RIGHT), BOX_INDEX)
    assert np.allclose(gaps, [4.0, 4.0]), gaps


def sewn_points_come_back_in_box_order():
    sewn = np.array(LEFT + RIGHT)
    sewn[4:6, 0] = 0.2  # the right panel's seam pulled almost shut
    merged = sewing.merged(sewn, BOX_INDEX, 6)
    assert np.allclose(merged[:2, 0], 0.1) and np.allclose(merged[2:4], LEFT[2:]) and np.allclose(merged[4:], RIGHT[2:])
    try:
        sewing.merged(sewn, BOX_INDEX, 7)
    except ValueError:
        pass
    else:
        raise AssertionError("a box point with no panel point must be refused")


def drape_reads_the_cloth_file():
    positions = sewing.merged(np.array(LEFT + RIGHT), BOX_INDEX, sewing.box_point_count(BOX_OBJ))
    text = sewing.sim_obj(BOX_OBJ, positions)
    assert text.count("\nvt ") == 3 and "mtllib" in text and text.count("\nf ") == 4
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "work_0_sim.obj").write_text(text)
        (folder / "work_0_sim_segmentation.txt").write_text("\n".join(LABELS) + "\n")
        points, faces, labels = drape.read_cloth(folder)
    assert np.allclose(points, positions * drape.CENTIMETRES), points
    assert faces.tolist() == [[0, 2, 1], [1, 2, 3], [0, 1, 4], [1, 5, 4]] and labels == LABELS
    try:
        sewing.sim_obj(BOX_OBJ, positions[:5])
    except ValueError:
        pass
    else:
        raise AssertionError("a point count that does not match the box mesh must be refused")


def fine_points_ride_on_the_sewn_coarse_cloth():
    coarse = {"points": np.array(LEFT, dtype=float), "faces": np.array(FACES[:2]), "panel": np.zeros(4, dtype=int)}
    fine = {"points": np.array([[-5.0, 5.0, 0.0], [0.0, 0.0, 0.0], [-10.0, 10.0, 0.0], [0.5, 5.0, 0.0]]),
            "panel": np.zeros(4, dtype=int)}
    assert np.allclose(sewing.carried(fine, coarse, coarse["points"]), fine["points"])  # unsewn, nothing moves
    folded = coarse["points"].copy()
    folded[:, 2] = -folded[:, 0]  # the square turned a quarter round its seam side
    folded[:, 0] = 0.0
    carried = sewing.carried(fine, coarse, folded)
    assert np.allclose(carried[:3], [[0.0, 5.0, 5.0], [0.0, 0.0, 0.0], [0.0, 10.0, 10.0]]), carried
    assert np.allclose(carried[3], [0.0, 5.0, -0.5]), carried  # just past the panel's edge, carried on in line


def a_sleeve_must_reach_down_the_upper_arm():
    assert sewing.arm_of("left_sleeve_f") == "left_arm" and sewing.arm_of("sl_right_cuff_b") == "right_arm"
    assert sewing.arm_of("pant_l_cuff_f") is None and sewing.arm_of("left_ftorso") is None
    # A strip of two triangles along x from 0.1 to 0.5, an arm from x = 0 to x = 1.
    points = np.array([[0.1, 0, 0], [0.5, 0, 0], [0.1, 1, 0], [0.5, 1, 0], [0.9, 0, 0]])
    faces = np.array([[0, 1, 2], [1, 3, 2], [1, 4, 3]])
    on_limb = np.array([True, True, True, True, False])
    gaps = sewing.uncovered(points, faces, on_limb, [0, 0, 0], [1, 0, 0], (0.3, 0.75), step=0.05)
    # the third triangle has a corner on the limb, so it counts, reaching to 0.9
    assert gaps == [], gaps
    gaps = sewing.uncovered(points, faces[:2], on_limb, [0, 0, 0], [1, 0, 0], (0.3, 0.75), step=0.05)
    assert gaps == [0.55, 0.6, 0.65, 0.7, 0.75], gaps


if __name__ == "__main__":
    for check in (measurements_unchanged_on_the_same_body, measurements_follow_their_own_ratio,
                  threads_tie_every_copy_to_its_first, sewn_points_come_back_in_box_order,
                  drape_reads_the_cloth_file, fine_points_ride_on_the_sewn_coarse_cloth,
                  a_sleeve_must_reach_down_the_upper_arm):
        check()
        print("ok", check.__name__)
