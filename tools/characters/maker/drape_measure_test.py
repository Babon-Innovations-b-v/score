"""Check drape_measure's plain pieces on cloth whose numbers are known: a flat sheet bends 0 degrees, a sheet folded
along one edge bends by the fold, and each leg's hem is its own lowest trouser point; the silhouette on a made-up body
of tubes (a torso narrowest at its waist, arms held down and out, legs) dressed in slightly wider tubes reads the gap
it was given and finds the waist where the body is narrowest, and its verdict fails a wider or sagging cloth and a
sleeve missing where the reference has one, and leaves a cut neither drape reads unknown; the gate is over the torso
and arm regions only; cloth through cloth is counted.

Run: .venv/bin/python tools/characters/maker/drape_measure_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drape_measure  # noqa: E402

# Two triangles sharing the edge from point 0 to point 1.
POINTS = np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
FACES = np.array([[0, 2, 1], [0, 1, 3]])


def test_flat_sheet_bends_nothing():
    bends, heights = drape_measure.edge_bends(POINTS, FACES)
    assert len(bends) == 1 and abs(bends[0]) < 1e-9 and abs(heights[0] - 0.5) < 1e-9


def test_fold_bends_by_its_angle():
    folded = POINTS.copy()
    folded[3] = [0.0, 0.0, 1.0]  # the right triangle turned 90 degrees about the shared edge
    bends, _ = drape_measure.edge_bends(folded, FACES)
    assert abs(bends[0] - 90.0) < 1e-6


def test_hem_is_each_legs_lowest_point():
    points = np.array([[0.1, 0.30, 0.0], [0.1, 0.20, 0.0], [-0.1, 0.25, 0.0], [0.0, 1.0, 0.0]])
    labels = np.array(["pant_f_l", "pant_l_cuff_b", "pant_b_r", "left_ftorso"])
    assert abs(drape_measure.hem_height(points, labels, 0.05) - 0.175) < 1e-9


def test_flat_sheet_crosses_nothing():
    assert drape_measure.self_crossings(POINTS, FACES) == 0


def test_a_sheet_through_another_is_counted():
    lying = np.array([[-1.0, 0.0, -1.0], [1.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
    standing = np.array([[0.0, -1.0, 0.0], [0.0, 1.0, 0.2], [0.0, 1.0, -0.2]])
    points = np.concatenate([lying, standing])
    assert drape_measure.self_crossings(points, np.array([[0, 1, 2], [3, 4, 5]])) == 2


# A body 170 cm tall in an A pose (cm): arms straight, 45 degrees down from the shoulders.
TORSO_RADIUS, ARM_RADIUS, LEG_RADIUS = 15.0, 4.0, 7.0
# The torso narrows by WAIST_DIP (cm) round WAIST_HEIGHT (between the Spine2 and Chest joints, as on a real body).
WAIST_DIP, WAIST_HEIGHT = 3.0, 109.0
# Halfway from the belly cut (between Spine1 and Spine2, 102 cm) to the hip joints (85 cm).
LOW_BELLY_HEIGHT = 93.5


def joints():
    down_out = np.array([1.0, -1.0, 0.0]) / np.sqrt(2.0)
    places = {"Hips": [0, 90, 0], "Spine1": [0, 98, 0], "Spine2": [0, 106, 0], "Chest": [0, 114, 0],
              "Neck1": [0, 140, 0]}
    for side, prefix in ((1, "Left"), (-1, "Right")):
        shoulder = np.array([20.0 * side, 135.0, 0.0])
        mirrored = down_out * np.array([side, 1.0, 1.0])
        places.update({prefix + "Arm": shoulder, prefix + "ForeArm": shoulder + 28.0 * mirrored,
                       prefix + "Hand": shoulder + 52.0 * mirrored, prefix + "Leg": [9.0 * side, 85.0, 0.0],
                       prefix + "Shin": [9.0 * side, 47.0, 0.0], prefix + "Foot": [9.0 * side, 8.0, 0.0]})
    return {name: np.asarray(value, dtype=float) for name, value in places.items()}


def tube(start, end, radius, shift=(0.0, 0.0, 0.0), rings=40, around=48):
    """An open tube's points and triangles from start to end (cm), its axis moved by `shift`; `radius` is one number
    or one a ring."""
    start, end = np.asarray(start, dtype=float) + shift, np.asarray(end, dtype=float) + shift
    axis = (end - start) / np.linalg.norm(end - start)
    side = np.cross(axis, [0.0, 0.0, 1.0])
    side = side / np.linalg.norm(side) if np.linalg.norm(side) > 1e-9 else np.array([1.0, 0.0, 0.0])
    other = np.cross(axis, side)
    turns = np.linspace(0.0, 2 * np.pi, around, endpoint=False)
    along = np.linspace(0.0, 1.0, rings)
    radius = np.broadcast_to(np.asarray(radius, dtype=float), (rings,))[:, None, None]
    points = (start + along[:, None, None] * (end - start)
              + radius * (np.cos(turns)[None, :, None] * side + np.sin(turns)[None, :, None] * other))
    ring, step = np.meshgrid(np.arange(rings - 1), np.arange(around), indexing="ij")
    here, right = ring * around + step, ring * around + (step + 1) % around
    faces = np.concatenate([np.stack([here, right, here + around], -1), np.stack([right, right + around, here + around], -1)])
    return points.reshape(-1, 3), faces.reshape(-1, 3)


def person(torso=0.0, sleeve=0.0, leg=0.0, sleeve_shift=(0.0, 0.0, 0.0), sleeves=True, low_belly=0.0):
    """(points, faces, part of each face) of tubes round the body's bones, each wider by its extra (cm), the torso
    also by `low_belly` round LOW_BELLY_HEIGHT only; the body's own when all extras are 0. Parts: 0 torso, 1 sleeve,
    2 trousers."""
    places = joints()
    heights = np.linspace(80.0, 150.0, 141)
    waisted = TORSO_RADIUS + torso - WAIST_DIP * np.exp(-((heights - WAIST_HEIGHT) / 6.0) ** 2) + \
        low_belly * np.exp(-((heights - LOW_BELLY_HEIGHT) / 2.0) ** 2)
    pieces = [(tube([0, 80, 0], [0, 150, 0], waisted, rings=len(heights)), 0)]
    for prefix in ("Left", "Right"):
        if sleeves:
            pieces.append((tube(places[prefix + "Arm"], places[prefix + "Hand"], ARM_RADIUS + sleeve, sleeve_shift), 1))
        pieces.append((tube(places[prefix + "Leg"], places[prefix + "Foot"], LEG_RADIUS + leg), 2))
    points, faces, parts, count = [], [], [], 0
    for (piece_points, piece_faces), part in pieces:
        points.append(piece_points)
        faces.append(piece_faces + count)
        parts.append(np.full(len(piece_faces), part))
        count += len(piece_points)
    return np.concatenate(points), np.concatenate(faces), np.concatenate(parts)


def body():
    points, faces, _ = person()
    return points, faces


def test_section_of_one_triangle():
    points = np.array([[0.0, -1.0, 0.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0]])
    segments, keys = drape_measure.plane_section(points, np.array([[0, 1, 2]]), np.zeros(3), np.array([0.0, 1.0, 0.0]))
    assert segments.shape == (1, 2, 3) and np.allclose(np.sort(segments[0, :, 0]), [-0.5, 0.5])
    assert len(set(keys[0])) == 2


def test_silhouette_reads_the_gap_it_was_given():
    found = drape_measure.silhouette(person(torso=2.0, sleeve=1.0, leg=1.5), body(), joints())
    for region, gap in (("waist", 2.0), ("chest", 2.0), ("forearm", 1.0), ("upper_arm", 1.0), ("shin", 1.5)):
        assert abs(found[region]["standoff_median"] - gap) < 0.1, (region, found[region])
        assert abs(found[region]["cloth_width"] - found[region]["body_width"] - 2 * gap) < 0.2, (region, found[region])
    assert abs(found["hip"]["body_width"] - 2 * TORSO_RADIUS) < 0.1


def test_waist_is_where_the_body_is_narrowest():
    assert abs(drape_measure.natural_waist(body(), joints()) - WAIST_HEIGHT) <= drape_measure.WAIST_STEP_CM
    found = drape_measure.silhouette(person(torso=2.0), body(), joints())
    assert abs(found["waist"]["body_width"] - 2 * (TORSO_RADIUS - WAIST_DIP)) < 0.2, found["waist"]
    assert found["belly"]["body_width"] > found["waist"]["body_width"] + 1.0


def test_same_cloth_passes():
    cloth = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0), body(), joints())
    for region in drape_measure.REGIONS:
        assert drape_measure.judge(cloth[region], cloth[region], region)["verdict"] == "pass", region


def test_wider_torso_fails_and_names_why():
    reference = drape_measure.silhouette(person(torso=1.0, sleeve=1.0), body(), joints())
    wider = drape_measure.silhouette(person(torso=3.0, sleeve=1.0), body(), joints())
    verdict = drape_measure.judge(wider["waist"], reference["waist"], "waist")
    assert verdict["verdict"] == "fail" and set(verdict["over"]) == {"cloth_width", "standoff_median", "standoff_p90"}
    assert drape_measure.judge(wider["forearm"], reference["forearm"], "forearm")["verdict"] == "pass"


def test_sagging_sleeve_fails():
    reference = drape_measure.silhouette(person(sleeve=1.0), body(), joints())
    sagging = drape_measure.silhouette(person(sleeve=1.0, sleeve_shift=(0.0, -2.0, 0.0)), body(), joints())
    assert drape_measure.judge(sagging["forearm"], reference["forearm"], "forearm")["verdict"] == "fail"


def test_missing_sleeve_fails_where_the_reference_has_one():
    reference = drape_measure.silhouette(person(sleeve=1.0), body(), joints())
    bare = drape_measure.silhouette(person(sleeves=False), body(), joints())
    assert bare["cuff"] is None
    assert drape_measure.judge(bare["cuff"], reference["cuff"], "cuff") == {"verdict": "fail", "over": ["unread"]}
    assert drape_measure.judge(bare["cuff"], None, "cuff")["verdict"] == "unknown"


def test_gate_is_over_the_torso_and_arms():
    reference = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0), body(), joints())
    wide_legs = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=4.0), body(), joints())
    verdicts = {region: drape_measure.judge(wide_legs[region], reference[region], region)
                for region in drape_measure.REGIONS}
    assert verdicts["shin"]["verdict"] == "fail" and drape_measure.gate(verdicts) == "pass"
    verdicts["elbow"] = {"verdict": "unknown", "over": []}
    assert drape_measure.gate(verdicts) == "unknown"
    verdicts["belly"] = {"verdict": "fail", "over": ["cloth_width"]}
    assert drape_measure.gate(verdicts) == "fail"


def test_a_puffy_low_belly_fails_the_gate():
    reference = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0), body(), joints())
    puffy = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0, low_belly=3.0), body(), joints())
    verdicts = {region: drape_measure.judge(puffy[region], reference[region], region)
                for region in drape_measure.REGIONS}
    assert verdicts["low_belly"]["verdict"] == "fail", verdicts["low_belly"]
    assert all(verdicts[region]["verdict"] == "pass" for region in ("chest", "underbust", "waist", "belly", "hip"))
    assert drape_measure.gate(verdicts) == "fail"


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
