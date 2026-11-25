"""One whole person of the people line put together (#223): the SOMA body with its own face (`../face`, #226) as the
skin the clothes are sewn on and worn over (`../garments`, #225), its strand hair (`../hair`, #227) on that head, its
shoes and belt and jewellery (`../accessories`, #228), each from the library, drawn photoreal from every side.

The face's skin (`face.npz` `skin`: SOMA-X's mid body of the person's MHR identity joined to ICT-FaceKit's face) is in
the identity body's own rest frame and size; the clips every body plays are the clips rig's (people-clips rig.npz:
SOMA's mean body at the low level of detail, its bind and its weights) played on the person's build (rig.npz `bind`,
the bones fitted to the made person). The skin is carried there as one:

- `laid`: the identity's low body (body_face.py's `low_points`, the clips rig's own topology) put on the clips rig's
  mean body point for point, scaled by height (`SCALE_BY`) and moved by the points' mean off it, along the floor;
  `limb_turns`: each limb then turned onto the mean's (MHR's rest holds the arms otherwise than the mean's bind);
- `relaxed_hands`: the clips rig has one joint a hand and MHR's rest holds the fingers straight and spread (owner,
  2026-11-25: "stiff splayed fingers"), so each hand's fingers are bent towards its palm past the knuckles, a little
  more the further out (FINGER_CURL_DEGREES at the tips), and drawn a little together (FINGER_CLOSE), as a hand
  hangs at rest; its tones (`hand_tones`): a flush growing towards the fingers, the thin skin of the back of the hand
  and the inner wrist;
- `carried_skin`: every skin point given the clips rig's weights of its nearest low-body triangle (barycentric), then
  skinned from the mean's bind onto the build's: the body the garments are draped on, its shoes fitted on, drawn;
- `head_carried`: the face's other pieces (eyes, teeth, mouth, tears, brows, lashes) and the hair, moved by the Head
  joint alone, as the head's skin is (its weights all the Head's);
- the hair is combed on this head's own scalp at the build's bind (`hair.py`), then each drawn frame (`pushed_out`)
  every strand point is kept `HAIR_OFF_M` out of the skin and, over the brows, `BROW_CLEAR_M` past the brows' hair, so
  no strand runs through the skin or under a brow hair.

A fault fails the run (`faults`): skin points whose nearest low-body triangle is further than `BIND_LIMIT_M` (the skin
is not this body's); the hair's own (`hair.faults`) and the jewellery's (`jewellery.faults`).
"""
import numpy as np
import trimesh

CHUNK = 20000  # points a closest-point question holds at once
TRUNK = ("Root", "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "HeadEnd")
SEGMENT_WEIGHT = 0.9  # a low-body point carried this much by one joint is that joint's part
SCALE_BY = "height"  # the identity is scaled to the clips rig's mean height (the build's bones are fitted to that)
BIND_LIMIT_M = 0.03  # a skin point further than this from the low body is not the same body's
HAIR_OFF_M = 0.002  # a hair point is kept this far outside the skin
BROW_CLEAR_M = 0.002  # and this far past the brows' hair over the brows
# A relaxed hand hanging at rest: the fingers bent about 60 degrees in all from the knuckles to the tips (the knuckle,
# middle and end joints together, read off a hand at rest; a choice, not a measure) and drawn a fifth closer together.
FINGER_CURL_DEGREES = 60.0
FINGER_CLOSE = 0.2
KNUCKLES_OF_HAND = 0.5  # the knuckles' line this far from the wrist joint along the hand's length
HAND_FLUSH = 0.6  # the flush at the fingertips (none at the wrist)
HAND_THIN = 0.5  # the thin bluish skin of the back of the hand and the inner wrist
WRIST_REACH_M = 0.06  # the inner wrist: the forearm's palm side this near the wrist joint


def laid(low_points, mean_points, trunk=None):
    """The scale and the shift that lay the identity's low body on the clips rig's mean body (same topology):
    `SCALE_BY` the heights over the floor, then moved along the floor by the mean difference of the `trunk` points
    (all when not given; the limbs are posed otherwise, `limb_turns`)."""
    scale = float(np.ptp(mean_points[:, 1]) / np.ptp(low_points[:, 1]))
    trunk = np.ones(len(low_points), dtype=bool) if trunk is None else trunk
    shift = (mean_points[trunk] - low_points[trunk] * scale).mean(axis=0)
    shift[1] = float(mean_points[:, 1].min() - low_points[:, 1].min() * scale)
    return scale, shift


def limb_turns(low, mean_points, weights, names):
    """Each joint's rigid move (4 x 4) laying the low body's part it carries (its points over SEGMENT_WEIGHT) on the
    mean body's same points (Kabsch, no scale): MHR's rest holds the arms otherwise than SOMA's mean bind (her hands
    8 cm higher, 2026-11-24), so the low body is put in the mean's pose limb by limb before the clips rig's bind
    skins it. The trunk's joints (TRUNK) are left: their parts differ by shape, not pose (the Chest's seven points
    turned 9 degrees by her bust)."""
    found = np.tile(np.eye(4), (weights.shape[1], 1, 1))
    for joint, name in enumerate(names):
        mine = weights[:, joint] > SEGMENT_WEIGHT
        if str(name) in TRUNK or mine.sum() < 4:
            continue
        here, there = low[mine], mean_points[mine]
        here_middle, there_middle = here.mean(axis=0), there.mean(axis=0)
        left, _, right = np.linalg.svd((here - here_middle).T @ (there - there_middle))
        sign = np.sign(np.linalg.det(right.T @ left.T))
        turn = right.T @ np.diag([1.0, 1.0, sign]) @ left.T
        found[joint, :3, :3] = turn
        found[joint, :3, 3] = there_middle - turn @ here_middle
    return found


def posed_like_mean(points, weights, turns):
    """Points of the low body's frame moved by their joints' limb turns, blended by their weights."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    moved = np.einsum("jab,pb->pja", turns[:, :3], homogeneous)
    return np.einsum("pj,pja->pa", weights, moved) / weights.sum(axis=1, keepdims=True)


def trunk_points(clips_rig):
    """The clips rig's points its trunk's joints carry (SEGMENT_WEIGHT of them together)."""
    names = [str(name) for name in clips_rig["names"]]
    columns = [names.index(name) for name in TRUNK if name in names]
    return np.asarray(clips_rig["weights"], float)[:, columns].sum(axis=1) > SEGMENT_WEIGHT


def closest(mesh, points):
    """trimesh's closest points on `mesh` (nearest, distance, triangle), asked CHUNK points at a time: asked all at
    once for the groom's 1.85 million points it held 27 GB (2026-11-24)."""
    found = [trimesh.proximity.closest_point(mesh, points[start:start + CHUNK])
             for start in range(0, len(points), CHUNK)]
    return tuple(np.concatenate([part[index] for part in found]) for index in range(3))


def barycentric(points, mesh_points, mesh_faces):
    """Each point's nearest triangle on the mesh, its barycentric weights there and its distance off it."""
    mesh = trimesh.Trimesh(mesh_points, mesh_faces, process=False)
    nearest, distance, triangle = closest(mesh, points)
    weights = trimesh.triangles.points_to_barycentric(mesh_points[mesh_faces[triangle]], nearest)
    return triangle, np.clip(weights, 0.0, 1.0) / np.clip(weights, 0.0, 1.0).sum(axis=1, keepdims=True), distance


def skin_weights(points, low_points, low_faces, weights):
    """The clips rig's weights at each skin point, from its nearest low-body triangle; and each point's distance
    off the low body."""
    triangle, corner_weights, distance = barycentric(points, low_points, low_faces)
    return np.einsum("pc,pcj->pj", corner_weights, weights[low_faces[triangle]]), distance


def carried_skin(face, body, clips_rig, build_bind):
    """The face's skin as the person's body at the build's bind, its hands relaxed: {points, faces, weights, scale,
    shift, off, tones} (`off` each skin point's distance off the low body, m; `tones` the face's with the hands')."""
    from score.stages.people_cloth import skinned
    scale, shift = laid(np.asarray(body["low_points"], float), np.asarray(clips_rig["points"], float),
                        trunk_points(clips_rig))
    low = np.asarray(body["low_points"], float) * scale + shift
    points = np.asarray(face["skin.points"], float) * scale + shift
    weights, off = skin_weights(points, low, np.asarray(body["low_triangles"], np.int64),
                                np.asarray(clips_rig["weights"], float))
    turns = limb_turns(low, np.asarray(clips_rig["points"], float), np.asarray(clips_rig["weights"], float),
                       clips_rig["names"])
    points = posed_like_mean(points, weights, turns)
    points, hand_tones = relaxed_hands(points, weights, clips_rig["names"], np.asarray(clips_rig["bind"], float))
    tones = np.asarray(face["skin.tones"], float).copy() if "skin.tones" in face else np.zeros((len(points), 3))
    tones[:, :2] = np.maximum(tones[:, :2], hand_tones)
    joints = np.tile(np.arange(weights.shape[1]), (len(weights), 1))
    posed = skinned(points, joints, weights, np.asarray(build_bind, float)[None], np.asarray(clips_rig["bind"]))[0]
    return {"points": posed, "faces": np.asarray(face["skin.triangles"], np.int64), "weights": weights,
            "scale": scale, "shift": shift, "off": off, "turns": turns, "tones": tones}


def hand_frame(points, wrist):
    """A hand's frame from its points: the wrist, its long axis (towards the fingertips), its palm's direction (the
    flat hand's normal, turned to the side the thumb stands to) and its across axis; and the hand's length."""
    middle = points.mean(axis=0)
    _, _, axes = np.linalg.svd(points - middle, full_matrices=False)
    along = axes[0] * np.sign(axes[0] @ (middle - wrist))
    normal, across = axes[2], axes[1]
    reach = (points - wrist) @ along
    sideways = (points - wrist) @ across
    height = (points - wrist) @ normal
    span = (reach > 0.2 * reach.max()) & (reach < 0.6 * reach.max())
    thumb_ends = [span & (side * sideways > np.percentile(side * sideways[span], 95)) for side in (1.0, -1.0)]
    offsets = [height[end].mean() - height[span].mean() for end in thumb_ends]
    palm = normal * np.sign(offsets[int(np.argmax(np.abs(offsets)))])
    return along, palm, np.cross(palm, along), float(reach.max())


def relaxed_hands(points, weights, names, bind):
    """The skin's points with each hand's fingers bent towards its palm past the knuckles (a bend of constant
    curvature, FINGER_CURL_DEGREES at the tips) and drawn FINGER_CLOSE together: points of the mean's bind frame;
    and each point's hand tones (flush, thin)."""
    names = [str(name) for name in names]
    moved = points.copy()
    tones = np.zeros((len(points), 2))
    for side in ("Left", "Right"):
        wrist = bind[names.index(f"{side}Hand"), :3, 3]
        hand = weights[:, names.index(f"{side}Hand")] > 0.5
        along, palm, across, length = hand_frame(points[hand], wrist)
        offset = points - wrist
        reach, height, sideways = offset @ along, offset @ palm, offset @ across
        knuckles = KNUCKLES_OF_HAND * length
        fingers = hand & (reach > knuckles)
        out = reach[fingers] - knuckles
        bend = np.radians(FINGER_CURL_DEGREES) / (length - knuckles)
        radius = 1.0 / bend
        turned = out * bend
        new_reach = knuckles + (radius - height[fingers]) * np.sin(turned)
        new_height = radius - (radius - height[fingers]) * np.cos(turned)
        middle = np.median(sideways[fingers])
        new_side = middle + (sideways[fingers] - middle) * (1.0 - FINGER_CLOSE * out / (length - knuckles))
        moved[fingers] = wrist + np.outer(new_reach, along) + np.outer(new_height, palm) + np.outer(new_side, across)
        tones[hand, 0] = HAND_FLUSH * np.clip(reach[hand] / length, 0.0, 1.0)
        back = hand & (height < 0.0) & (reach < knuckles)
        inner_wrist = (weights[:, names.index(f"{side}ForeArm")] > 0.5) & (height > 0.0) & \
            (np.linalg.norm(offset, axis=1) < WRIST_REACH_M)
        tones[back | inner_wrist, 1] = HAND_THIN
    return moved, tones


def head_carried(points, moves):
    """Points of the mean's frame carried by the head's moves: frames x points x 3."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    return np.einsum("fij,pj->fpi", moves, homogeneous)[..., :3]


def pushed_out(points, skin_points, skin_faces, clear):
    """Each point kept at least `clear` (m, one a point) outside the skin along its nearest triangle's outward normal
    (the skin is open at the eyes and mouth, so inside is read off that normal, not a closed volume): the moved points,
    and the most any point was short of its clearance (m)."""
    mesh = trimesh.Trimesh(skin_points, skin_faces, process=False)
    nearest, _, triangle = closest(mesh, points)
    normals = mesh.face_normals[triangle]
    short = np.asarray(clear, float) - np.einsum("pi,pi->p", points - nearest, normals)
    moving = short > 0.0
    moved = points.copy()
    moved[moving] += normals[moving] * short[moving, None]
    return moved, float(max(0.0, short.max()))


def clips_bind():
    """The clips rig's own bind (SOMA's mean body's joints), the frame the face's pieces are laid in."""
    from tools.characters import garments
    return np.asarray(np.load(garments.CLIPS)["bind"], float)


def faults(skin):
    """The skin's fault, one line (none when the face's body is this person's)."""
    most = float(skin["off"].max())
    if most > BIND_LIMIT_M:
        return [f"skin not this body's: a point {most * 1000.0:.1f} mm off the low body (limit "
                f"{BIND_LIMIT_M * 1000.0:.0f})"]
    return []


def skin_bound(points, skin_points, skin_faces):
    """Each point bound to its nearest skin triangle: (triangle, barycentric weights, height along its normal)."""
    mesh = trimesh.Trimesh(skin_points, skin_faces, process=False)
    nearest, _, triangle = closest(mesh, points)
    weights = trimesh.triangles.points_to_barycentric(skin_points[skin_faces[triangle]], nearest)
    return triangle, weights, np.einsum("pi,pi->p", points - nearest, mesh.face_normals[triangle])


def skin_carried(binding, skin_frames, skin_faces):
    """Points bound by `skin_bound` carried by the skin every frame (frames x points x 3)."""
    triangle, weights, height = binding
    found = []
    for skin in skin_frames:
        corners = skin[skin_faces[triangle]]
        normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
        found.append(np.einsum("pc,pcd->pd", weights, corners) + normal * height[:, None])
    return np.asarray(found)
