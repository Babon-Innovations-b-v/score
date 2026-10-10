"""Check drape_measure's plain pieces on cloth whose numbers are known: a flat sheet bends 0 degrees, a sheet folded
along one edge bends by the fold, and each leg's hem is its own lowest trouser point; the silhouette on a made-up body
of tubes (a torso narrowest at its waist, arms held down and out, legs) dressed in slightly wider tubes reads the gap
it was given and finds the waist where the body is narrowest, and its verdict fails a wider or sagging cloth and a
sleeve missing where the reference has one, and leaves a cut neither drape reads unknown; the gate is over the torso
and arm regions only, and over the dense cuts, which find a bulge between the named cuts and a puffed sleeve cap
between the armpit and the shoulder; a dense cut past both drapes' sleeves is absent and passes; the belt band reads
unknown where the torso cloth does not reach it, and the verdict lets only pass through; cloth through cloth is
counted.

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
# Above ARMPIT_HEIGHT the torso widens by SHOULDER_FLARE (cm), out past the upper arms' bones (20 cm from the spine
# at the shoulders, a centimetre further out for each centimetre down): where a real body's cut round the spine takes
# in the arms. It is past them from 130 cm up (26.8 cm against 25 cm there; 25.6 against 26 at 129).
ARMPIT_HEIGHT, SHOULDER_FLARE = 128.0, 12.0
# The arm tubes start ARM_INSET (cm) inside the shoulder joint, so their open ends sit in the torso above the
# shoulder band (a real body is closed there); `sleeve_cap` widens the sleeve to CAP_CM past the shoulder joint, short
# of the first upper-arm cut (UPPER_ARM_FROM of the 28 cm upper arm: 8.4 cm).
ARM_INSET, CAP_CM = 8.0, 7.0


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


def tube(start, end, radius, shift=(0.0, 0.0, 0.0), rings=40, around=48, closed=False):
    """A tube's points and triangles from start to end (cm), its axis moved by `shift`, open or `closed` at its ends
    (a body is closed: a cut across an open end leaves a chain that does not close); `radius` is one number or one a
    ring."""
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
    faces = np.concatenate([np.stack([here, right, here + around], -1),
                            np.stack([right, right + around, here + around], -1)]).reshape(-1, 3)
    points = points.reshape(-1, 3)
    if closed:
        step = np.arange(around)
        last = (rings - 1) * around
        caps = [np.stack([np.full(around, len(points)), (step + 1) % around, step], -1),
                np.stack([np.full(around, len(points) + 1), last + step, last + (step + 1) % around], -1)]
        points, faces = np.concatenate([points, [start, end]]), np.concatenate([faces, *caps])
    return points, faces


def person(torso=0.0, sleeve=0.0, leg=0.0, sleeve_shift=(0.0, 0.0, 0.0), sleeves=True, low_belly=0.0,
           bulge_at=LOW_BELLY_HEIGHT, sleeve_cap=0.0, closed=False):
    """(points, faces, part of each face) of tubes (`closed` for a body) round the body's bones, each wider by its
    extra (cm), the torso also by `low_belly` round `bulge_at` only, the sleeves by `sleeve_cap` up to CAP_CM past
    the shoulder; the body's own when all extras are 0. Parts: 0 torso, 1 sleeve, 2 trousers."""
    places = joints()
    heights = np.linspace(80.0, 150.0, 141)
    waisted = TORSO_RADIUS + torso - WAIST_DIP * np.exp(-((heights - WAIST_HEIGHT) / 6.0) ** 2) + \
        low_belly * np.exp(-((heights - bulge_at) / 2.0) ** 2) + \
        SHOULDER_FLARE / (1.0 + np.exp(-(heights - ARMPIT_HEIGHT) / 0.5))
    pieces = [(tube([0, 80, 0], [0, 150, 0], waisted, rings=len(heights), closed=closed), 0)]
    for prefix in ("Left", "Right"):
        start, end = places[prefix + "Arm"], places[prefix + "Hand"]
        start = start - ARM_INSET * (end - start) / np.linalg.norm(end - start)
        along = np.linspace(0.0, np.linalg.norm(end - start), 40)
        if sleeves:
            pieces.append((tube(start, end, ARM_RADIUS + sleeve + sleeve_cap * (along < ARM_INSET + CAP_CM),
                                sleeve_shift, closed=closed), 1))
        pieces.append((tube(places[prefix + "Leg"], places[prefix + "Foot"], LEG_RADIUS + leg, closed=closed), 2))
    points, faces, parts, count = [], [], [], 0
    for (piece_points, piece_faces), part in pieces:
        points.append(piece_points)
        faces.append(piece_faces + count)
        parts.append(np.full(len(piece_faces), part))
        count += len(piece_points)
    return np.concatenate(points), np.concatenate(faces), np.concatenate(parts)


def body():
    points, faces, _ = person(closed=True)
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
        assert drape_measure.judge(cloth[region], cloth[region], drape_measure.limb_of(region))["verdict"] == "pass"


def test_wider_torso_fails_and_names_why():
    reference = drape_measure.silhouette(person(torso=1.0, sleeve=1.0), body(), joints())
    wider = drape_measure.silhouette(person(torso=3.0, sleeve=1.0), body(), joints())
    verdict = drape_measure.judge(wider["waist"], reference["waist"], "torso")
    assert verdict["verdict"] == "fail" and set(verdict["over"]) == {"cloth_width", "standoff_median", "standoff_p90"}
    assert drape_measure.judge(wider["forearm"], reference["forearm"], "arm")["verdict"] == "pass"


def test_sagging_sleeve_fails():
    reference = drape_measure.silhouette(person(sleeve=1.0), body(), joints())
    sagging = drape_measure.silhouette(person(sleeve=1.0, sleeve_shift=(0.0, -2.0, 0.0)), body(), joints())
    assert drape_measure.judge(sagging["forearm"], reference["forearm"], "arm")["verdict"] == "fail"


def test_missing_sleeve_fails_where_the_reference_has_one():
    reference = drape_measure.silhouette(person(sleeve=1.0), body(), joints())
    bare = drape_measure.silhouette(person(sleeves=False), body(), joints())
    assert bare["cuff"] is None
    assert drape_measure.judge(bare["cuff"], reference["cuff"], "arm")["over"] == ["unread"]
    assert drape_measure.judge(bare["cuff"], reference["cuff"], "arm")["verdict"] == "fail"
    assert drape_measure.judge(bare["cuff"], None, "arm")["verdict"] == "unknown"


def test_gate_is_over_the_torso_and_arms():
    reference = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0), body(), joints())
    wide_legs = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=4.0), body(), joints())
    verdicts = named_verdicts(wide_legs, reference)
    assert verdicts["shin"]["verdict"] == "fail" and drape_measure.gate(verdicts, {}) == "pass"
    verdicts["elbow"] = {"verdict": "unknown", "over": []}
    assert drape_measure.gate(verdicts, {}) == "unknown"
    verdicts["belly"] = {"verdict": "fail", "over": ["cloth_width"]}
    assert drape_measure.gate(verdicts, {}) == "fail"


def test_a_puffy_low_belly_fails_the_gate():
    reference = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0), body(), joints())
    puffy = drape_measure.silhouette(person(torso=1.0, sleeve=1.0, leg=1.0, low_belly=3.0), body(), joints())
    verdicts = named_verdicts(puffy, reference)
    assert verdicts["low_belly"]["verdict"] == "fail", verdicts["low_belly"]
    assert all(verdicts[region]["verdict"] == "pass" for region in ("chest", "underbust", "waist", "belly", "hip"))
    assert drape_measure.gate(verdicts, {}) == "fail"


def named_verdicts(mine, reference):
    """Every named region's verdict of one silhouette against another."""
    return {region: drape_measure.judge(mine[region], reference[region], drape_measure.limb_of(region))
            for region in drape_measure.REGIONS}


def dense_verdicts(mine, reference):
    """Every dense cut's verdict of one person() against another, on the made-up body."""
    found = drape_measure.dense_silhouette(mine, body(), joints())
    theirs = drape_measure.dense_silhouette(reference, body(), joints())
    return {name: {"band": row[0], **drape_measure.judge_dense(row, theirs[name], row[0])}
            for name, row in found.items()}


def test_armpit_is_where_the_body_takes_in_the_arms():
    assert drape_measure.armpit_height(body(), joints()) == 130.0


def test_dense_cuts_step_through_every_band():
    found = drape_measure.dense_cuts(joints(), body())
    names = [name for name, band, *_ in found if band == "torso"]
    assert names[0] == "torso_85" and names[-1] == "torso_134" and len(names) == 50
    shoulder = [name for name, band, *_ in found if band == "shoulder"]
    assert shoulder == [f"shoulder_{height}" for height in range(130, 135)]
    arm = [name for name, band, *_ in found if band == "arm"]
    assert len(arm) == 2 * (14 + 1 + 18) and "upper_arm_30" in arm and "forearm_95" in arm and "elbow" in arm


def test_a_bulge_between_the_named_cuts_fails_the_dense_gate():
    reference = person(torso=1.0, sleeve=1.0, leg=1.0)
    bulged = person(torso=1.0, sleeve=1.0, leg=1.0, low_belly=2.0, bulge_at=89.0)
    named = named_verdicts(drape_measure.silhouette(bulged, body(), joints()),
                           drape_measure.silhouette(reference, body(), joints()))
    assert drape_measure.gate(named, {}) == "pass"
    dense = dense_verdicts(bulged, reference)
    assert dense["torso_89"]["verdict"] == "fail" and drape_measure.gate(named, dense) == "fail"
    summary = drape_measure.band_summary(dense)
    assert summary["torso"]["worst_cut"] in ("torso_88", "torso_89", "torso_90") and not summary["arm"]["fail"]


def test_a_puffed_sleeve_cap_fails_only_the_shoulder():
    dense = dense_verdicts(person(torso=1.0, sleeve=1.0, sleeve_cap=2.0), person(torso=1.0, sleeve=1.0))
    summary = drape_measure.band_summary(dense)
    assert summary["shoulder"]["fail"], summary["shoulder"]
    assert not summary["torso"]["fail"] and not summary["arm"]["fail"], summary


def test_the_same_drape_passes_every_dense_cut_and_cuts_past_both_sleeves_are_absent():
    cloth = person(torso=1.0, sleeve=1.0, leg=1.0)
    assert {row["verdict"] for row in dense_verdicts(cloth, cloth).values()} == {"pass"}
    bare = person(torso=1.0, sleeves=False)
    dense = dense_verdicts(bare, bare)
    assert dense["forearm_50"]["verdict"] == "absent"
    assert drape_measure.worst(row["verdict"] for row in dense.values()) == "pass"
    assert dense_verdicts(bare, cloth)["forearm_50"] == {"band": "arm", "verdict": "fail", "over": ["unread"],
                                                          "margin_cm": None}


def test_no_belt_band_to_read_is_unknown_and_blocks():
    assert drape_measure.belt_cover(1.10, 1.00, 1.06) is None
    assert drape_measure.belt_cover(1.03, 1.00, 1.06) == 3.0
    assert drape_measure.judge_belt(None, None) == "unknown"
    assert drape_measure.judge_belt(None, 2.0) == "fail"
    assert drape_measure.judge_belt(1.5, 2.0) == "fail" and drape_measure.judge_belt(1.7, 2.0) == "pass"
    assert drape_measure.worst(["pass", drape_measure.judge_belt(None, None)]) == "unknown"


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
