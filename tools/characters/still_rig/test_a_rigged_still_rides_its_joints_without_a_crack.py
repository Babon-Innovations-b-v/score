"""A rigged still's hard parts ride their joints and the cloth between them bends instead of cracking.

The fixture is a strip of points 1 cm apart up a body's back: suit cloth, a backpack on the chest, a helmet on the head
above it touching the backpack, and a stray backpack face inside the cloth. Each break below turns it red:

- a hard part's point far from any other hard part does not ride its joint wholly (`rigid`), or a weight row stops
  summing to one;
- the cloth next to a hard part keeps its own joint up to the rim, so neighbouring points 1 cm apart differ by more
  than a third of their weight (the cliff prop_build's eased_to_hard left on one surface: edges 8 times their length);
- the helmet and the backpack meet as two rigid parts on different joints (no `seamed` sharing), so a 10 degree nod
  stretches an edge at their seam more than 1.5 times its length;
- a loose strip of cloth 2 cm beside the backpack, joined to it by no face, is eased onto the chest (the ease measured
  straight across the gap, not over the surface: the upper arm beside the backpack torn at every swing);
- the cloth's weights jump from the hips to the chest between two points and `eased_cliffs` leaves a step of more than
  a fifth between neighbours, moves a fixed point, or lets a row stop summing to one;
- a cube with one side cut away is not closed by `closed` (an open edge left, or a fan face turned against the face
  it borders, so the patch shows its back: the black tears at the shoulders and boots);
- a lone face of another part inside a part is kept as that other part (`kept_pieces`);
- a second, smaller visor piece apart from the visor (a dark seam round the helmet's rim) stays visor, or the largest
  piece is not kept whole (`one_visor`);
- the sphere's sight lines are not spread over both halves of every axis (`directions`);
- a box painted red on its left side and blue elsewhere, stood (halved and lifted) and laid on a new map, reads
  back at each face's middle a colour other than its own (`own_maps` not taking the point back into the still's frame
  with `taken_back`, or reading the wrong texture place: the seams and panels of the still's own paint lost), the
  unwrap changes a face, or a texel outside every chart stays black (`bled`).
- a person's still (`parts_of(..., person=True)`) has a helmet, visor or backpack face (a dark face read as a visor
  and held rigid), or its head's faces are not all its head, or its head is held rigid (eased over hair resting on the
  shoulders, it hung the stairwell woman's sleeves from her head).
- a person's flat shoes 3 cm longer than the body's feet and 1 cm aside (`feet_fitted`) are not laid heel to toe on
  the body's foot skin, centred on it and pitched onto its rising sole, or a point above the ankle's blend moves (the stairwell woman's shoes stood
  2 cm in every tread and 18 cm under the next step).
- a trouser point 30 cm above its ankle keeps a weight on its foot or toes, a point under the ankle loses its foot, or
  a row stops summing to one (`off_the_feet`: the generated stairwell woman's wide jeans, inpainted from the hem,
  swung back from the calf in a fin at every push-off); a point 20 cm over its knee keeps a weight on its shin, or a
  point under the knee loses its shin (`off_the_shins`: the same jeans' thigh points hung from the shin and spiked
  18 cm off the thigh at every stride).
- a person whose arms (columns of 5 cm at 20 cm either side) touch its trunk (15 cm) all the way down is refused
  (`landmarks_of` not falling back to `fused_landmarks`), its arm's axis is read more than 2 cm off the sleeve's middle
  (the band reaching into the trunk), or a sleeve point is not its arm's or a trunk point is (the hoodie man and the
  older woman refused before the split, 2026-11-27); a hand hanging under the crotch's height against a strut to the
  thigh (each slice cutting hand and thigh as one piece) is not its arm's to the fingertips, or the thigh is
  (`HAND_TIP_UNDER_WRIST`, `HAND_HALF`; break applied once, seen red, reverted, 2026-11-27: the old band ending at
  the crotch).
- a body's file grown by the place clips (`clips_added`) reads its rest offsets other than its bind's (a clip then
  played on the wrong bones), takes a clips rig's joints in the rig's order rather than the skin's, loses a byte of the
  numbers it had (the clips it was built with changed), or a climb keeps its height's run over the loop, gives a rise
  other than its own, or a climb going the wrong way is kept (`level_climb`).
- a person's clip bringing an arm 5 degrees off its trunk while the still's arm hangs 15 out keeps it nearer than 15
  (`arms_kept_out` not raising it: the hands into the older woman's coat, 2026-11-27), an arm swung out to 30 or
  brought across the trunk to -20 (a hand on the far knee) is moved, the hand's bone changes its length, or the
  written local turn and its parent's world miss the arm's world. Breaks applied once, seen red, reverted
  (2026-11-27): the floor's turn left at zero; `ARM_ACROSS_DEGREES` 1000 (the arm across pushed out).
- a person's hands (round 2, 2026-11-27; each break applied once, seen red, reverted): open stick hands laid again by
  `hands.curled` keep a finger bent under nine tenths of CURL_DEGREES, two fingers spread more than 6 degrees, the
  thumb's tip 2 cm or more off the index finger, or the fingertips where they were (the curl skipped; the spread
  left at whole's fan); `hands.nails` marks points off the back of the end bones (the back's sign flipped); a trouser
  point a fused arm's labels hung from the hand keeps the hand (`off_the_hands`'s cloth weights skipped: the hoodie
  man's dark wings at the hips), a cuff point stays on the hand rather than the forearm, or any other weight moves,
  or a point is taken off the arm where the sleeve and the cloth beside it are one colour (the older woman's coat:
  her cuffs left on her hips), a hand that never meets the clothes keeps its arm at the still's 15 degrees rather
  than its clip's own 5 (`hands_cleared` letting no floor down: the older woman's arms stiff 21 degrees out all her
  walk, 2026-11-28),
  or a tear's sides are not each closed by their own fan (`tears_closed`: the hollow showed black), a fan spans the
  tear, or a face still spans the sleeve and the thigh after `torn` (eased instead, his walk stretched edges by 15 cm or his
  hands stood 5 cm beside his cuffs), or a torn face moves or a copy loses its point's other values;
  a jagged rim keeps its jags or shrinks (`smoothed_rims` with no rounds); a skin speck on the sleeve by the cut
  keeps the lump's skin paint (`lump_patches` skipped); a nail is painted as the skin or as rough; the hands' skin is
  not the stats file's photo CIELAB (`photo_skin`).
"""
import pathlib
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import clips_added  # noqa: E402
from tools.characters import posture  # noqa: E402
import hands as relaxed_hands  # noqa: E402
import still_rig  # noqa: E402

NAMES = ["Root", "Hips", "Chest", "Head"]


def strip():
    """Two columns of points 1 cm apart from 0.8 m to 1.9 m, faces between them, each face's part by its height:
    suit under 1.3 m, backpack to 1.6 m, helmet over it; and every point's own weights on the hips."""
    heights = np.round(np.arange(0.8, 1.9001, 0.01), 3)
    points = np.array([[side, height, -0.15] for height in heights for side in (0.0, 0.01)])
    faces = []
    for row in range(len(heights) - 1):
        low, high = 2 * row, 2 * row + 2
        faces += [[low, low + 1, high + 1], [low, high + 1, high]]
    faces = np.array(faces)
    middles = points[faces].mean(1)[:, 1]
    part_of = np.where(middles < 1.3, 0, np.where(middles < 1.6, 3, 1))
    weights = np.zeros((len(points), len(NAMES)))
    weights[:, NAMES.index("Hips")] = 1.0
    return points, faces, part_of, weights, heights


def open_hands():
    """Two open stick hands at a toy bind, back up (+y), fingers along +x, each finger 4 bones fanned 12 degrees apart
    and its thumb 45 degrees out (the left's on +z, the right's mirrored), points on rings 4 mm round every bone, all
    on their Hand joint: (names, joints, points, weights)."""
    joints, rings = {}, []
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        joints[f"{side}Hand"] = np.zeros(3)
        for number, finger in enumerate(posture.FINGERS):
            turn = np.radians(12.0 * (1.5 - number))
            line = np.array([np.cos(turn), 0.0, sign * np.sin(turn)])
            knuckle = np.array([0.08, 0.0, sign * (0.0225 - 0.015 * number)])
            chain = posture.finger_chain(side, finger)
            joints[chain[1]] = 0.4 * knuckle
            for joint, reach in zip(chain[2:], (0.0, 0.04, 0.065, 0.085)):
                joints[joint] = knuckle + reach * line
        thumb = np.array([np.cos(np.radians(45.0)), 0.0, sign * np.sin(np.radians(45.0))])
        for joint, reach in zip(posture.finger_chain(side, "Thumb")[1:], (0.0, 0.025, 0.045, 0.065)):
            joints[joint] = np.array([0.02, 0.0, sign * 0.02]) + reach * thumb
    names = ["Root", "LeftHand", "RightHand"]
    weights = []
    for side in ("Left", "Right"):
        for finger in posture.FINGERS + ("Thumb",):
            chain = posture.finger_chain(side, finger)
            for start, end in zip(chain[1:], chain[2:]):
                span = joints[end] - joints[start]
                across = np.cross(span, [0.0, 1.0, 0.0])
                across /= np.linalg.norm(across)
                for share in np.linspace(0.0, 1.0, 6):
                    for angle in np.linspace(0, 2 * np.pi, 12, endpoint=False):
                        rings.append(joints[start] + share * span + 0.004 * (np.cos(angle) * across +
                                                                             np.sin(angle) * np.array([0, 1.0, 0])))
                        weights.append([0.0, 1.0, 0.0] if side == "Left" else [0.0, 0.0, 1.0])
    return names, joints, np.array(rings), np.array(weights)


def test_a_rigged_still_rides_its_joints_without_a_crack():
    points, faces, part_of, weights, heights = strip()
    out = still_rig.rigid(points, faces, part_of, weights, NAMES)
    assert np.allclose(out.sum(1), 1.0)
    height = points[:, 1]
    head, chest = out[:, NAMES.index("Head")], out[:, NAMES.index("Chest")]
    assert np.allclose(head[height > 1.6 + still_rig.SEAM + 0.01], 1.0)
    assert np.allclose(chest[(height > 1.3 + 0.01) & (height < 1.6 - still_rig.SEAM - 0.01)], 1.0)
    seam = np.argmin(np.abs(height - 1.6))
    assert 0.3 < head[seam] < 0.7 and 0.3 < chest[seam] < 0.7
    column = out[0::2]
    assert np.abs(np.diff(column, axis=0)).max() < 1 / 3
    assert chest[np.argmin(np.abs(height - 1.29))] > 0.9 and chest[height < 1.3 - still_rig.EASE_REACH].max() == 0.0

    nod = np.repeat(np.eye(4)[None, None], len(NAMES), axis=1)
    pivot = np.array([0.0, 1.6, 0.0])
    nod[0, NAMES.index("Head"), :3, :3] = Rotation.from_euler("x", 10, degrees=True).as_matrix()
    nod[0, NAMES.index("Head"), :3, 3] = pivot - nod[0, NAMES.index("Head"), :3, :3] @ pivot
    order, kept = still_rig.strongest(out)
    most, _, _ = still_rig.stretch(points, faces, order, kept, nod)
    assert max(most) < 1.5
    cracked = weights.copy()
    cracked[height > 1.6] = np.eye(len(NAMES))[NAMES.index("Head")]
    cracked[(height >= 1.3) & (height <= 1.6)] = np.eye(len(NAMES))[NAMES.index("Chest")]
    order, kept = still_rig.strongest(cracked)
    assert max(still_rig.stretch(points, faces, order, kept, nod)[0]) > 1.5

    beside = points[(height > 1.35) & (height < 1.55)] + [0.0, 0.0, 0.02]
    loose = np.r_[points, beside]
    start = len(points)
    loose_faces = [faces] + [[[start + 2 * row, start + 2 * row + 1, start + 2 * row + 3],
                              [start + 2 * row, start + 2 * row + 3, start + 2 * row + 2]]
                             for row in range(len(beside) // 2 - 1)]
    loose_faces = np.concatenate([np.asarray(rows).reshape(-1, 3) for rows in loose_faces])
    loose_weights = np.r_[weights, weights[:len(beside)]]
    eased = still_rig.rigid(loose, loose_faces, np.r_[part_of, np.zeros(len(loose_faces) - len(faces), int)],
                            loose_weights, NAMES)
    assert np.allclose(eased[start:, NAMES.index("Hips")], 1.0)

    stepped = weights.copy()
    stepped[height >= 1.0] = np.eye(len(NAMES))[NAMES.index("Chest")]
    fixed = height > 1.5
    smooth = still_rig.eased_cliffs(points, faces, stepped, fixed)
    assert np.allclose(smooth.sum(1), 1.0) and np.allclose(smooth[fixed], stepped[fixed])
    assert np.abs(np.diff(smooth[0::2], axis=0)).max() < 0.2

    box = trimesh.creation.box()
    cut = trimesh.Trimesh(box.vertices, box.faces[2:], process=False)
    shut = still_rig.closed(cut)
    assert still_rig.open_edges(cut) > 0 and still_rig.open_edges(shut) == 0 and shut.is_winding_consistent

    mesh = trimesh.Trimesh(points, faces, process=False)
    stray = part_of.copy()
    stray[10] = still_rig.PARTS.index("backpack")
    assert still_rig.kept_pieces(mesh, stray)[10] == part_of[10]
    visor, helmet = still_rig.PARTS.index("visor"), still_rig.PARTS.index("helmet")
    two = np.where(part_of == still_rig.PARTS.index("suit"), part_of, helmet)
    two[-40:-10], two[-60:-56] = visor, visor
    one = still_rig.one_visor(mesh, two)
    assert (one[-40:-10] == visor).all() and (one[-60:-56] == helmet).all()

    sights = still_rig.directions(still_rig.SIGHTS)
    assert np.allclose(np.linalg.norm(sights, axis=1), 1.0)
    assert (sights.max(0) > 0.9).all() and (sights.min(0) < -0.9).all()

    painted = trimesh.creation.box()
    painted.vertices[:, 1] *= 2.0
    left = painted.face_normals[:, 0] < -0.5
    picture = np.zeros((8, 8, 3), np.uint8)
    picture[:, :4] = [200, 40, 40]
    picture[:, 4:] = [40, 40, 200]
    from PIL import Image
    places = np.where(left[:, None, None], [0.25, 0.5], [0.75, 0.5]) * np.ones((1, 3, 1))
    split = trimesh.Trimesh(painted.vertices[painted.faces].reshape(-1, 3), np.arange(36).reshape(-1, 3),
                            process=False)
    split.visual = trimesh.visual.TextureVisuals(uv=places.reshape(-1, 2), image=Image.fromarray(picture))
    split.visual.material = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.fromarray(picture))
    source = still_rig.Source(split, split.faces)
    stood = painted.vertices * 0.5 + [0.0, 1.0, 0.0]
    mapping, faces_on, laid = still_rig.unwrapped(stood, painted.faces, painted.vertex_normals, size=64)
    assert np.allclose(stood[mapping][faces_on], stood[painted.faces])
    maps, report = still_rig.own_maps(stood[mapping], faces_on, laid, still_rig.taken_back(painted.vertices, stood),
                                      source, {"red": "#c83030", "blue": "#3030c8"}, size=64)
    texture = maps["base_color"].astype(float)
    for side, colour in ((left, (200, 40, 40)), (~left, (40, 40, 200))):
        middle = laid[faces_on[side]].mean(1)
        read = still_rig.bilinear(texture / 255.0, middle) * 255.0
        assert np.abs(read - colour).max() < 20
    assert (maps["base_color"].reshape(-1, 3).sum(1) > 0).all() and len(report) == 2

    person = trimesh.creation.icosphere(subdivisions=3, radius=0.1)
    person.vertices += [0.0, 1.65, 0.0]
    person = trimesh.util.concatenate([person, trimesh.creation.box((0.4, 0.6, 0.2), trimesh.transformations
                                                                    .translation_matrix([0.0, 1.1, 0.0]))])
    joints = ["Hips", "Chest", "Neck1", "Head", "HeadEnd"]
    bind = np.repeat(np.eye(4)[None], len(joints), axis=0)
    bind[:, 1, 3] = [1.0, 1.3, 1.5, 1.6, 1.75]
    dark = np.full((len(person.vertices), 3), 0.8)
    dark[person.vertices[:, 2] > 0.05] = 0.1  # the face's front as dark as a visor
    found = still_rig.parts_of(person, dark, None, joints, bind, person=True)
    on_head = person.triangles_center[:, 1] > 1.52
    assert (found[on_head] == still_rig.PARTS.index("head")).all()
    assert set(found[~on_head]) == {still_rig.PARTS.index("suit")} and "head" not in still_rig.RIGID
    head_ball = trimesh.creation.icosphere(subdivisions=5, radius=0.1)
    head_ball.vertices += [0.0, 1.65, 0.0]
    ball_parts = np.full(len(head_ball.faces), still_rig.PARTS.index("head"))
    face_colours = np.tile([0.3, 0.2, 0.1], (len(head_ball.vertices), 1))  # hair
    face_strip = (np.abs(head_ball.vertices[:, 0]) < 0.03) & (head_ball.vertices[:, 2] > 0.05)
    face_colours[face_strip] = [0.8, 0.6, 0.5]
    face_colours[face_strip & (head_ball.vertices[:, 1] > 1.67)] = [0.1, 0.1, 0.1]  # a dark brow, under half the strip
    bind_head = bind.copy()
    bind_head[joints.index("Head"), :3, 3] = [0.0, 1.65, 0.0]
    assert np.allclose(still_rig.face_skin(head_ball.vertices, head_ball.faces, ball_parts, face_colours, joints,
                                           bind_head),
                       [0.8, 0.6, 0.5])

    feet = {}
    for side, x in (("Left", 0.1), ("Right", -0.1)):
        skin = np.array([[x, y + 0.1 * (z + 0.08), z] for z in np.linspace(-0.08, 0.18, 14)
                         for y in (0.0, 0.04, 0.08)])  # the sole rises 2.6 cm heel to toe, as SOMA's
        feet[side] = (skin, float(skin[skin[:, 2] < 0.08, 1].max()))
    shoe = np.array([[side * 0.1 + 0.012, y, z] for side in (1, -1) for z in np.linspace(-0.065, 0.213, 15)
                     for y in (0.0, 0.05)] + [[side * 0.1, y, 0.0] for side in (1, -1) for y in (0.3, 0.45)])
    laid = still_rig.feet_fitted(trimesh.Trimesh(shoe, np.zeros((0, 3), int), process=False), feet).vertices
    for side in (1, -1):
        sole = laid[(np.sign(laid[:, 0]) == side) & (shoe[:, 1] == 0.0)]
        assert np.allclose([sole[:, 2].min(), sole[:, 2].max()], [-0.08, 0.18], atol=1e-6)
        assert np.allclose(sole[:, 0].mean(), side * 0.1, atol=1e-6)
        assert np.allclose(sole[:, 1], 0.1 * (sole[:, 2] + 0.08), atol=1e-3)
    above = shoe[:, 1] > feet["Left"][1] + still_rig.ANKLE_BLEND
    assert np.allclose(laid[above], shoe[above])

    leg_names = ["LeftShin", "LeftFoot", "LeftToeBase", "RightShin", "RightFoot", "RightToeBase"]
    leg_bind = np.repeat(np.eye(4)[None], len(leg_names), axis=0)
    leg_bind[:, 1, 3] = [0.45, 0.08, 0.02, 0.45, 0.08, 0.02]
    hem = np.array([[0.1, 0.38, 0.0], [0.1, 0.02, 0.0], [-0.1, 0.12, 0.0]])
    hung = np.array([[0.2, 0.5, 0.3, 0, 0, 0], [0, 0.7, 0.3, 0, 0, 0], [0, 0, 0, 0.5, 0.5, 0]])
    freed = still_rig.off_the_feet(hem, hung, leg_names, leg_bind)
    assert np.allclose(freed.sum(1), 1.0) and np.allclose(freed[0], [1, 0, 0, 0, 0, 0])
    assert np.allclose(freed[1], hung[1]) and np.allclose(freed[2], [0, 0, 0, 0.75, 0.25, 0])
    knee_names = ["LeftLeg", "LeftShin", "RightLeg", "RightShin"]
    knee_bind = np.repeat(np.eye(4)[None], 4, axis=0)
    knee_bind[:, 1, 3] = [0.9, 0.48, 0.9, 0.48]
    thigh = np.array([[0.1, 0.68, 0.0], [0.1, 0.3, 0.0], [-0.1, 0.51, 0.0]])
    shin_hung = np.array([[0.0, 1.0, 0, 0], [0.2, 0.8, 0, 0], [0, 0, 0.0, 1.0]])
    unhung = still_rig.off_the_shins(thigh, shin_hung, knee_names, knee_bind)
    assert np.allclose(unhung.sum(1), 1.0) and np.allclose(unhung[0], [1, 0, 0, 0])
    assert np.allclose(unhung[1], shin_hung[1]) and np.allclose(unhung[2], [0, 0, 0.5, 0.5])

    rest = np.repeat(np.eye(4)[None], 3, axis=0)
    rest[:, 1, 3] = [0.0, 1.0, 1.4]
    rest[2, 0, 3] = 0.1
    skin_glb = {"nodes": [{"name": "Root", "children": [1]}, {"name": "Hips", "children": [2]}, {"name": "Chest"}],
                "skins": [{"joints": [0, 1, 2], "inverseBindMatrices": 0}]}
    inverse = np.linalg.inv(rest).transpose(0, 2, 1).astype(np.float32)
    skin_glb["accessors"] = [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "MAT4"}]
    skin_glb["bufferViews"] = [{"buffer": 0, "byteOffset": 0, "byteLength": inverse.nbytes}]
    names, parents, bind, offsets = clips_added.skeleton(skin_glb, inverse.tobytes())
    assert names == ["Root", "Hips", "Chest"] and list(parents) == [-1, 0, 1]
    assert np.allclose(offsets, [[0, 0, 0], [0, 1.0, 0], [0.1, 0.4, 0]], atol=1e-6)
    rig = {"names": np.array(["Chest", "Root", "Hips"]), "bind": np.arange(3)[:, None, None] * np.ones((3, 4, 4)),
           "clips": np.array(["talking"]), "clip_talking": np.arange(3)[None, :, None, None] * np.ones((2, 3, 4, 4))}
    ordered = clips_added.in_rig_order(type("Held", (), {"files": list(rig), "__getitem__": lambda self, key:
                                                         rig[key]})(), names)
    assert list(ordered["bind"][:, 0, 0]) == [1, 2, 0] and list(ordered["clip_talking"][0, :, 0, 0]) == [1, 2, 0]
    grown = clips_added.contents_of(skin_glb, inverse.tobytes())
    grown.reading([1.0, 2.0], "SCALAR", 5126)
    assert grown.blob()[:inverse.nbytes] == inverse.tobytes() and len(grown.accessors) == 2

    climb = np.repeat(np.eye(4)[None, None], 31, axis=0).repeat(2, axis=1)
    climb[:, 1, 1, 3] = 1.0 + np.linspace(0.0, 0.6, 31) + 0.02 * np.sin(np.linspace(0, 4 * np.pi, 31))
    level, rise = clips_added.level_climb(climb, 1, 30.0)
    assert abs(level[-1, 1, 1, 3] - level[0, 1, 1, 3]) < 1e-9 and abs(rise - 0.6) < 1e-9
    assert np.allclose(np.diff(level[:, 1, 1, 3]) - np.diff(climb[:, 1, 1, 3]), -0.02)
    try:
        clips_added.level_climb(climb, -1, 30.0)
        raise AssertionError("a climb up kept as a climb down")
    except ValueError:
        pass

    def column(x, radius, low, high):
        return trimesh.creation.cylinder(radius=radius, segment=[[x, low, 0.0], [x, high, 0.0]], sections=32)

    fused = trimesh.util.concatenate([column(0.0, 0.15, 0.8, 1.5), column(0.2, 0.05, 0.76, 1.45),
                                      column(-0.2, 0.05, 0.76, 1.45), column(0.1, 0.05, 0.0, 0.82),
                                      column(-0.1, 0.05, 0.0, 0.82), column(0.15, 0.025, 0.765, 0.795),
                                      column(-0.15, 0.025, 0.765, 0.795)])
    samples = still_rig.prop_rig.sampled(fused, 60000)
    arm_names = ["LeftArm", "RightArm", "LeftHand", "RightHand"]
    arm_bind = np.repeat(np.eye(4)[None], len(arm_names), axis=0)
    arm_bind[:, 1, 3] = [1.45, 1.45, 0.95, 0.95]
    fit = still_rig.landmarks_of(samples, arm_bind, arm_names)
    for side, x in (("Left", 0.2), ("Right", -0.2)):
        assert abs(fit[side + "Arm"]["start"][0] - x) < 0.02
        sleeve = (np.abs(samples[:, 0] - x) < 0.045) & (samples[:, 1] > 0.9) & (samples[:, 1] < 1.3)
        assert (fit["limbs"][sleeve] == side + "Arm").all()
    assert (fit["limbs"][(np.abs(samples[:, 0]) < 0.1) & (samples[:, 1] > 0.9)] == "").all()
    for side, x in (("Left", 0.2), ("Right", -0.2)):
        hand = (np.abs(samples[:, 0] - x) < 0.02) & (samples[:, 1] < 0.79) & (samples[:, 1] > 0.765)
        thigh = (np.abs(samples[:, 0] - x / 2) < 0.03) & (samples[:, 1] < 0.79)
        assert (fit["limbs"][hand] == side + "Arm").all() and not (fit["limbs"][thigh] == side + "Arm").any()

    kept_names = ["Root", "Chest", "LeftArm", "LeftHand", "RightArm", "RightHand"]
    kept_parents = np.array([-1, 0, 1, 2, 1, 4])

    def arm_worlds(left, right):
        """Worlds with each arm (0.2 m out at 1.4 m) hanging `left` and `right` degrees out from straight down."""
        worlds = np.repeat(np.eye(4)[None], 6, axis=0)
        worlds[1, 1, 3] = 1.3
        for side, sign, angle in (("Left", 1.0, left), ("Right", -1.0, right)):
            turn = Rotation.from_euler("z", sign * angle, degrees=True).as_matrix()
            arm, hand = kept_names.index(side + "Arm"), kept_names.index(side + "Hand")
            worlds[arm, :3, :3], worlds[arm, :3, 3] = turn, [sign * 0.2, 1.4, 0.0]
            worlds[hand, :3, :3], worlds[hand, :3, 3] = turn, worlds[arm, :3, 3] + turn @ [0.0, -0.5, 0.0]
        return worlds

    kept_bind = arm_worlds(15.0, 15.0)
    swung = np.stack([arm_worlds(5.0, 30.0), arm_worlds(-20.0, 15.0)])
    out, turned = still_rig.arms_kept_out(swung, kept_bind, kept_names, kept_parents)
    left_angle = still_rig.abduction(out, kept_bind, kept_names, "Left")[0]
    right_angle = still_rig.abduction(out, kept_bind, kept_names, "Right")[0]
    assert left_angle[0] >= 15.0 - 1e-6 and abs(left_angle[1] + 20.0) < 1e-6 and abs(right_angle[0] - 30.0) < 0.01
    lengths = np.linalg.norm(out[:, 3, :3, 3] - out[:, 2, :3, 3], axis=1)
    assert np.allclose(lengths, 0.5)
    for arm in (2, 4):
        local = Rotation.from_quat(turned[arm]).as_matrix()
        assert np.allclose(out[:, 1, :3, :3] @ local, out[:, arm, :3, :3])

    hand_names = ["Root", "LeftForeArm", "LeftHand", "RightForeArm", "RightHand", "LeftLeg"]
    hand_bind = np.repeat(np.eye(4)[None], len(hand_names), axis=0)
    for side, x in (("Left", 0.3), ("Right", -0.3)):
        hand_bind[hand_names.index(side + "ForeArm"), :3, 3] = [x, 1.05, 0.0]
        hand_bind[hand_names.index(side + "Hand"), :3, 3] = [x, 0.8, 0.0]
    hand_bind[hand_names.index("LeftLeg"), :3, 3] = [0.1, 0.9, 0.0]
    def tube(x, radius, low, high, step=0.005, around=16):
        """An open tube up the y axis at `x`, a ring of `around` points every `step`."""
        heights = np.arange(low, high + 1e-9, step)
        angles = np.linspace(0, 2 * np.pi, around, endpoint=False)
        ring = np.c_[x + radius * np.cos(angles), np.zeros(around), radius * np.sin(angles)]
        points = np.concatenate([ring + [0.0, height, 0.0] for height in heights])
        faces = [[row * around + k, row * around + (k + 1) % around, (row + 1) * around + k] for row in
                 range(len(heights) - 1) for k in range(around)]
        faces += [[row * around + (k + 1) % around, (row + 1) * around + (k + 1) % around, (row + 1) * around + k]
                  for row in range(len(heights) - 1) for k in range(around)]
        return trimesh.Trimesh(points, np.array(faces), process=False)

    arm_skin = trimesh.util.concatenate([tube(0.3, 0.04, 0.6, 1.05), tube(-0.3, 0.04, 0.6, 1.05),
                                         tube(0.12, 0.05, 0.4, 0.9)])
    skin_points, skin_faces = arm_skin.vertices, arm_skin.faces
    on = np.zeros((len(skin_points), len(hand_names)))
    for side, x in (("Left", 0.3), ("Right", -0.3)):
        mine = np.abs(skin_points[:, 0] - x) < 0.05
        on[mine, hand_names.index(side + "Hand")] = (skin_points[mine, 1] < 0.8)
        on[mine, hand_names.index(side + "ForeArm")] = skin_points[mine, 1] >= 0.8
    on[np.abs(skin_points[:, 0] - 0.12) < 0.06, hand_names.index("LeftLeg")] = 1.0
    tones = np.zeros((len(skin_points), 3))
    tones[:, 0] = np.clip(0.8 - skin_points[:, 1], 0, 1)
    cut_out = relaxed_hands.cut(skin_points, skin_faces, on, tones, hand_names, hand_bind)
    for side, x in (("Left", 0.3), ("Right", -0.3)):
        kept = cut_out[f"{side}.points"]
        assert (np.abs(kept[:, 0] - x) < 0.05).all() and kept[:, 1].max() <= 0.8 + relaxed_hands.STUB + 1e-9
        assert kept[:, 1].min() < 0.61 and len(cut_out[f"{side}.tones"][0]) == 3
        assert cut_out[f"{side}.faces"].max() == len(kept) - 1

    toy_names, toy_joints, toy_points, toy_weights = open_hands()
    curled, curled_joints = relaxed_hands.curled(toy_points, toy_weights, toy_names, toy_joints)
    for side in ("Left", "Right"):
        measured = posture.hand_measured(curled_joints, side)
        assert all(bend >= 0.9 * relaxed_hands.CURL_DEGREES[finger] for finger, bend in measured["bend degrees"].items())
        assert max(measured["spread degrees"]) <= 6.0 and measured["thumb gap m"] < 0.02  # together, the thumb in
    tips = toy_points[:, 0] > 0.15
    assert curled[tips, 1].mean() < toy_points[tips, 1].mean() - 0.02  # the fingertips curled towards the palm (-y)
    nailed = relaxed_hands.nails(curled, toy_weights, toy_names, curled_joints).astype(bool)
    assert 10 < nailed.sum() < 0.2 * len(toy_points)
    open_nails = relaxed_hands.nails(toy_points, toy_weights, toy_names, toy_joints).astype(bool)
    assert (toy_points[open_nails, 1] > 0.0019).all() and abs(open_nails.sum() - nailed.sum()) < 0.2 * nailed.sum()
    fingertip = np.linalg.norm(toy_points[:, [0, 2]], axis=1) > 0.08 + 0.065 - 0.04  # past the fingers' last joints
    thumb_tip = np.linalg.norm(np.abs(toy_points[:, [0, 2]]) - [0.02 + 0.055 * 0.707] * 2, axis=1) < 0.03
    assert (fingertip | thumb_tip)[open_nails].all()  # on the back (+y) of the end bones only

    cloth_colour, skin_colour = np.array([0.6, 0.45, 0.3]), np.array([0.85, 0.65, 0.55])
    colours = np.tile(cloth_colour, (len(skin_points), 1))
    under = skin_points[:, 1] < 0.8 - 0.01  # the hand's skin from a centimetre under the wrist
    colours[under] = skin_colour
    patch = (skin_points[:, 1] < 0.8) & (skin_points[:, 1] > 0.7) & (skin_points[:, 2] > 0.03)
    colours[patch] = cloth_colour  # a cuff's flap hanging from the sleeve over the hand: cloth, kept
    crevice = (skin_points[:, 1] > 0.66) & (skin_points[:, 1] < 0.676) & (skin_points[:, 2] < -0.035)
    colours[crevice] = [0.3, 0.2, 0.15]  # a shaded crevice of the lump: cut with it
    speck = (skin_points[:, 1] > 0.801) & (skin_points[:, 1] < 0.818) & (skin_points[:, 2] < -0.025)
    colours[speck] = skin_colour  # a speck of skin paint on the sleeve: kept
    colours[np.abs(skin_points[:, 0] - 0.12) < 0.06] = skin_colour  # a bare thigh beside the hand: no cloth
    cut_faces = still_rig.hand_cut(skin_points, skin_faces, colours, on, hand_names, hand_bind, skin_colour)
    arm_faces = (np.abs(skin_points[skin_faces, 0] - 0.3) < 0.05).all(1) | (
        np.abs(skin_points[skin_faces, 0] + 0.3) < 0.05).all(1)
    painted_skin = (np.abs(colours[skin_faces] - skin_colour).max(2) < 1e-9).all(1)
    assert cut_faces[arm_faces & painted_skin & (skin_points[skin_faces, 1].max(1) < 0.785)].all()
    assert cut_faces[arm_faces & crevice[skin_faces].all(1)].all()
    assert not cut_faces[arm_faces & patch[skin_faces].all(1)].any()
    assert not cut_faces[arm_faces & speck[skin_faces].any(1)].any()
    assert not cut_faces[arm_faces & (skin_points[skin_faces, 1].max(1) > 0.8 + still_rig.HAND_CUFF_OVER)].any()
    assert not cut_faces[~arm_faces].any()

    outward = hand_bind.copy()
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        outward[hand_names.index(side + "Hand"), 0, 3] += sign * 0.04  # the joint 4 cm out beside its sleeve
    round_cut = arm_faces & (skin_points[skin_faces, 1].max(1) < 0.79)  # a cut all round the arm
    offsets = still_rig.sleeve_offsets(skin_points, skin_faces, round_cut, on, hand_names, outward)
    assert np.allclose(offsets["Left"], [-0.04, 0.0, 0.0], atol=0.01)
    assert np.allclose(offsets["Right"], [0.04, 0.0, 0.0], atol=0.01)
    store = {"names": np.array(hand_names), **cut_out}
    moved_bind = hand_bind.copy()
    turn = Rotation.from_euler("z", 30, degrees=True).as_matrix()
    for side in ("Left", "Right"):
        fore, hand = hand_names.index(side + "ForeArm"), hand_names.index(side + "Hand")
        elbow = hand_bind[fore, :3, 3] + [0.0, 0.1, 0.0]
        moved_bind[fore, :3, 3] = elbow
        moved_bind[hand, :3, :3] = turn
        moved_bind[hand, :3, 3] = elbow + turn @ [0.0, -0.5, 0.0]
    laid_hands = still_rig.hands_laid(store, hand_names, hand_bind, moved_bind)
    for side in ("Left", "Right"):
        points_laid, _, weights_laid, _ = laid_hands[side]
        hand = hand_names.index(side + "Hand")
        tip = cut_out[f"{side}.points"][cut_out[f"{side}.points"][:, 1].argmin()]
        expected = moved_bind[hand, :3, 3] + turn @ ((tip - hand_bind[hand, :3, 3]) * 2.0)
        assert np.allclose(points_laid[cut_out[f"{side}.points"][:, 1].argmin()], expected, atol=1e-9)
        assert np.allclose(weights_laid.sum(1), 1.0)

    part_with = np.zeros(len(skin_faces), int)
    joined = still_rig.with_hands(skin_points, skin_faces, part_with, on, colours, cut_faces, laid_hands, skin_colour)
    joined_points, joined_faces, joined_parts, joined_weights, joined_paint, joined_rough = joined
    joined_hand = np.isfinite(joined_rough).all(1)
    hand_count = sum(len(laid_hands[side][1]) for side in ("Left", "Right"))
    still_faces = joined_faces[joined_parts != still_rig.PARTS.index("hand")]
    assert (joined_parts == still_rig.PARTS.index("hand")).sum() == hand_count
    assert len(still_faces) > (~cut_faces).sum() and still_rig.open_edges(
        trimesh.Trimesh(joined_points, still_faces, process=False)) == 0  # the cut's holes (and the tubes' ends) shut
    assert joined_faces.max() == len(joined_points) - 1 and len(np.unique(joined_faces)) == len(joined_points)
    assert joined_hand.sum() == sum(len(laid_hands[side][0]) for side in ("Left", "Right"))
    assert np.allclose(joined_paint[joined_hand].min(0), skin_colour, atol=0.05)
    assert np.allclose(joined_weights.sum(1), 1.0)
    new_points = ~joined_hand & (np.arange(len(joined_points)) >= len(np.unique(skin_faces[~cut_faces])))  # fans' middles
    cuffs = new_points & (np.abs(np.abs(joined_points[:, 0]) - 0.3) < 0.05) & (joined_points[:, 1] < 0.83) & (
        joined_points[:, 1] > 0.6)
    assert cuffs.sum() == 2 and np.allclose(joined_paint[cuffs], cloth_colour)  # the cuff's fan in the cloth's paint
    kept_points = np.zeros(len(skin_points), bool)
    kept_points[np.unique(skin_faces[~cut_faces])] = True
    at_still = np.zeros(len(skin_points), int)
    at_still[kept_points] = np.arange(kept_points.sum())  # the kept points come first, in their order
    on_arms = np.abs(np.abs(skin_points[:, 0]) - 0.3) < 0.05
    assert np.allclose(joined_paint[at_still[speck & kept_points & on_arms]], cloth_colour)  # the lump's speck repainted
    thigh = np.abs(skin_points[:, 0] - 0.12) < 0.06
    assert np.isnan(joined_paint[at_still[thigh]]).all()  # a bare thigh 9 cm off the cut keeps its own paint
    tones_nail = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    nail_paint = still_rig.hand_paint(skin_colour, tones_nail)
    assert np.allclose(nail_paint[0], skin_colour) and (nail_paint[1] > skin_colour).all()  # a nail paler
    assert still_rig.hand_roughness(tones_nail)[1, 1] < still_rig.hand_roughness(tones_nail)[0, 1]  # and glossier
    assert np.allclose(still_rig.hand_roughness(tones_nail[:, :2])[:, 1], still_rig.HAND_METAL_ROUGHNESS[1])
    stats_file = pathlib.Path(__import__("tempfile").mkdtemp()) / "stats.json"
    stats_file.write_text('{"paint_toned": {"photo_lab": [68.2, 15.5, 18.2]}}')
    assert np.allclose(still_rig.photo_skin(stats_file), [0.80, 0.61, 0.53], atol=0.01)  # the older woman's photo

    angles = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    jagged = np.r_[np.c_[np.cos(angles), np.zeros(16), np.sin(angles)] * (0.04 + 0.005 * (-1) ** np.arange(16))[:, None],
                   [[0.0, 0.0, 0.0]]]
    rim_fans = np.c_[np.arange(16), (np.arange(16) + 1) % 16, np.full(16, 16)]
    smooth = np.linalg.norm(still_rig.smoothed_rims(jagged, rim_fans)[:16], axis=1)
    assert smooth.std() < 0.001 and abs(smooth.mean() - 0.04) < 0.002  # the jags gone, the opening its size

    sleeve_weights = on.copy()  # a cuff ring kept on the hand, the thigh beside it hung from the hand (fused labels)
    left_arm = np.abs(skin_points[:, 0] - 0.3) < 0.05
    cuff = (np.abs(np.abs(skin_points[:, 0]) - 0.3) < 0.05) & (skin_points[:, 1] < 0.8) & (skin_points[:, 1] > 0.784)
    hung = thigh & (skin_points[:, 1] < 0.75) & (skin_points[:, 1] > 0.6)
    sleeve_weights[hung] = 0.0
    sleeve_weights[hung, hand_names.index("LeftHand")] = 1.0
    fused_cut = (left_arm[skin_faces].all(1) & (skin_points[skin_faces, 1].max(1) < 0.79)) | (
        np.abs(skin_points[skin_faces, 0] + 0.3) < 0.05).all(1) & (skin_points[skin_faces, 1].max(1) < 0.79)
    garments = np.tile(cloth_colour, (len(skin_points), 1))  # a camel sleeve, dark trousers on the thigh
    garments[thigh] = [0.1, 0.1, 0.15]
    taken_off, off_points = still_rig.off_the_hands(skin_points, skin_faces, fused_cut, sleeve_weights, garments,
                                                    hand_names, hand_bind)
    assert off_points[hung].all() and not off_points[~hung].any()
    camel = np.tile(cloth_colour, (len(skin_points), 1))
    camel[thigh] -= 0.05  # the coat's flank a shade darker than its sleeve: still one garment
    one_coat, none_off = still_rig.off_the_hands(skin_points, skin_faces, fused_cut, sleeve_weights, camel,
                                                 hand_names, hand_bind)
    assert not none_off.any() and np.allclose(one_coat[hung, hand_names.index("LeftForeArm")], 1.0)  # one garment
    assert np.allclose(taken_off[hung, hand_names.index("LeftLeg")], 1.0)  # the thigh back on its leg
    assert np.allclose(taken_off[cuff & left_arm, hand_names.index("LeftForeArm")], 1.0)  # the cuff on the forearm
    assert np.allclose(taken_off[cuff & ~left_arm, hand_names.index("RightForeArm")], 1.0)
    strip_points = np.array([[x, y, 0.0] for y in (0.0, 0.01) for x in (0.0, 0.01, 0.02, 0.03)])
    strip_faces = np.array([[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6]])
    strip_weights = np.zeros((8, len(hand_names)))
    strip_weights[[0, 1, 4, 5], hand_names.index("LeftForeArm")] = 1.0  # a sleeve beside a thigh, fused
    strip_weights[[2, 3, 6, 7], hand_names.index("LeftLeg")] = 1.0
    strip_weights[6] = 0.0
    strip_weights[6, [hand_names.index("LeftForeArm"), hand_names.index("LeftLeg")]] = 0.3, 0.7
    split, split_faces, split_weights, (split_tag,) = still_rig.torn(strip_points, strip_faces, strip_weights,
                                                                     hand_names, np.ones(6, bool), np.arange(8.0))
    share = still_rig.arm_share(split_weights, hand_names)[split_faces]
    assert (share.max(1) - share.min(1) < still_rig.TEAR).all() and len(split) > 8  # nothing spans the tear
    assert np.allclose(split[split_faces], strip_points[strip_faces]) and np.allclose(strip_points[split_tag.astype(int)], split)
    assert np.allclose(split_weights[:8], strip_weights) and np.allclose(split_weights.sum(1), 1.0)
    grid = np.array([[x, y, 0.0] for y in (0.0, 0.01, 0.02, 0.03) for x in (0.0, 0.01, 0.02, 0.03)])  # a slit's sides
    grid_faces = np.array([[row * 4 + column, row * 4 + column + 1, row * 4 + column + 5] for row in range(3)
                           for column in range(3)] + [[row * 4 + column, row * 4 + column + 5, row * 4 + column + 4]
                                                      for row in range(3) for column in range(3)])
    grid_weights = np.zeros((16, len(hand_names)))
    grid_weights[grid[:, 0] < 0.015, hand_names.index("LeftForeArm")] = 1.0
    grid_weights[grid[:, 0] > 0.015, hand_names.index("LeftLeg")] = 1.0
    slit, slit_faces, slit_weights, (slit_from,) = still_rig.torn(grid, grid_faces, grid_weights, hand_names,
                                                                  np.ones(18, bool), np.arange(16))
    shut_points, shut_faces, shut_parts, shut_weights, (shut_tag,) = still_rig.tears_closed(
        slit, slit_faces, np.zeros(len(slit_faces), int), slit_weights, hand_names, slit_from, slit[:, :1])
    shut_share = still_rig.arm_share(shut_weights, hand_names)[shut_faces]
    assert len(shut_faces) > len(slit_faces) and len(shut_points) == len(slit) + 2  # each side's run fanned
    assert (shut_share.max(1) - shut_share.min(1) < still_rig.TEAR).all()  # no fan across the tear
    assert len(shut_parts) == len(shut_faces) and np.allclose(shut_weights.sum(1), 1.0) and len(shut_tag) == len(
        shut_points)
    assert np.allclose(taken_off[~hung & ~cuff], sleeve_weights[~hung & ~cuff]) and np.allclose(taken_off.sum(1), 1.0)

    laid_paint = np.full((len(stood), 3), np.nan)
    laid_paint[painted.vertices[:, 0] > 0] = [0.9, 0.6, 0.5]
    box_map, box_faces, box_places = still_rig.unwrapped(stood, painted.faces, painted.vertex_normals, size=64)
    hand_maps, _ = still_rig.own_maps(stood[box_map], box_faces, box_places,
                                      still_rig.taken_back(painted.vertices, stood), source, {}, size=64,
                                      laid_paint=laid_paint[box_map])
    right_faces = (painted.vertices[painted.faces][:, :, 0] > 0).all(1)
    read = still_rig.bilinear(hand_maps["base_color"] / 255.0, box_places[box_faces[right_faces]].mean(1))
    assert np.abs(read - [0.9, 0.6, 0.5]).max() < 0.05
    read = still_rig.bilinear(hand_maps["base_color"] / 255.0, box_places[box_faces[left]].mean(1))
    assert np.abs(read * 255 - (200, 40, 40)).max() < 20

    plate = trimesh.creation.box((0.3, 0.3, 0.02)).subdivide_to_size(0.005)
    finger = trimesh.creation.box((0.02, 0.02, 0.02), trimesh.transformations.translation_matrix([0.05, 0.0, 0.005]))
    depth_points = np.r_[plate.vertices, finger.vertices]
    depth_faces = np.r_[plate.faces, finger.faces + len(plate.vertices)]
    depth_parts = np.r_[np.zeros(len(plate.faces), int), np.full(len(finger.faces), still_rig.PARTS.index("hand"))]
    depth_names = ["Root", "LeftHand"]
    depth_weights = np.zeros((len(depth_points), 2))
    depth_weights[:len(plate.vertices), 0] = depth_weights[len(plate.vertices):, 1] = 1.0
    order, kept = still_rig.strongest(depth_weights, 2)
    still = np.repeat(np.eye(4)[None, None], 2, axis=1)
    depth = still_rig.hands_depth(depth_points, depth_faces, depth_parts, order, kept, depth_names)
    assert depth(still)["Left"] > 0.0
    out_move = still.copy()
    out_move[0, 1, 2, 3] = 0.05
    assert depth(out_move)["Left"] == 0.0

    def fake_depth(moves):
        """The left hand 'in the clothes' while it is nearer than 0.36 m to the middle, 3 cm in on a plateau out to
        0.345 m (a degree more out brings it no nearer out: the hoodie man's left hand); the right always 2 cm in."""
        reach = (moves @ kept_bind)[:, 3, 0, 3].min()
        return {"Left": 0.03 if reach < 0.345 else float(max(0.0, 0.36 - reach)), "Right": 0.02}

    straight = np.stack([arm_worlds(15.0, 15.0)] * 2)
    cleared_worlds, _, cleared = still_rig.hands_cleared(straight, kept_bind, kept_names, kept_parents, fake_depth)
    assert cleared["Left"][1] <= still_rig.HAND_CLEAR and 0.0 < cleared["Left"][0] <= 6.0
    assert cleared["Right"][0] == 0.0 and cleared["Right"][1] == 0.02
    assert cleared_worlds[:, 3, 0, 3].min() >= 0.36 - still_rig.HAND_CLEAR
    hanging, _, free = still_rig.hands_cleared(np.stack([arm_worlds(5.0, 5.0)] * 2), kept_bind, kept_names,
                                               kept_parents, lambda moves: {"Left": 0.0, "Right": 0.0})
    assert free["Left"][0] == free["Right"][0] == -still_rig.HAND_LOWER_MOST
    assert abs(still_rig.abduction(hanging, kept_bind, kept_names, "Left")[0] - 5.0).max() < 0.1
