"""Dress the body: the crew's work suit and the space suit, as pieces hung on the body's skeleton.

A placeholder for the crew's final look, which is to be cleaner and in the game's own character
style (the owner's call, #36, 2026-09-27). What it gets right, and what any later look has to
keep: every piece is either a shell over the body or a rigid part on one joint, skinned with the
body's own weights, so every clip Kimodo writes plays on it with no conversion of any kind.

Each outfit is a list of pieces, `(surface, vertices, faces, weights)`. The surface is a name,
never a colour: the game paints each one from the design system (`game/people/person/`).

Four things that were wrong in the pictures and are why the code is the shape it is:

**A shell's edge is tucked onto the body.** A shell pushed out from the body and left open at
the neck, a wrist or an ankle shows a gap you can see through, the owner's note on the second
round. The edge vertices stay pinned just off the skin while the rest is pushed out and relaxed.

**A band is cut, not picked.** A belt made of whole triangles off a coarse mesh came out as a
saw blade. Bands are cut along their edge the way a polygon is clipped against a line, and the
cut corners are welded so the band stays one piece when it is lifted off the suit.

**A band is lifted off the suit, not the body.** Relaxing the suit pushes it further out than
it was asked for in places, and a collar built out from the body sat inside it, unseen.

**Spheres are wound outwards.** The first helmets were inside out, so from the front you saw the
inside of the back of the helmet and the visor only from behind.
"""
import numpy as np
import regions
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

# How far a shell's edge stays off the skin, in metres: enough not to flicker through it.
TUCKED = 0.002
# The work suit: how far it stands off the body, and how much it is relaxed, which is what hides
# the bare body's detail under it.
SUIT_OFF = 0.022
SUIT_RELAXING = 12
# The space suit: thicker everywhere and thicker again over the chest and shoulders, which on the
# AxEMU is a hard shell rather than cloth.
SPACE_SUIT_OFF = 0.055
SPACE_SUIT_CHEST_OFF = 0.085


class Body:
    """The body at its bind pose, and what the dressing needs to know about it."""

    def __init__(self, vertices, faces, weights, joint_names, bind_world, eyes):
        self.vertices = vertices
        self.faces = faces
        self.weights = weights
        self.joint_names = joint_names
        self.joint = {name: index for index, name in enumerate(joint_names)}
        self.bind_world = bind_world
        self.eyes = eyes
        self.normals = _smooth_normals(vertices, faces)
        self.around = _neighbours(faces, len(vertices))
        region = np.array(regions.regions_of(joint_names))[weights.argmax(axis=1)]
        self.hand = np.array(["Hand" in joint_names[joint] for joint in weights.argmax(axis=1)])
        self.skin = region == regions.SKIN
        self.clothes = region == regions.CLOTHES
        self.boots = region == regions.BOOTS
        self.head_only = self.skin & ~self.hand
        self.head = self.at("Head")
        self.from_head = vertices - self.head
        region_number = {regions.SKIN: 0, regions.CLOTHES: 1, regions.BOOTS: 2}
        numbered = np.array([region_number[name] for name in region])
        self.triangle_region = np.array([np.bincount(numbered[corners], minlength=3).argmax()
                                         for corners in faces])

    def at(self, joint_name):
        """Where a joint is at bind."""
        return self.bind_world[self.joint[joint_name]][:3, 3]

    def grown(self, mask, rings):
        """A vertex mask grown outwards by so many rings of neighbours."""
        for _ in range(rings):
            wider = mask.copy()
            for vertex in np.where(mask)[0]:
                wider[self.around[vertex]] = True
            mask = wider
        return mask

    def frontmost(self, across, up, mask, reach=0.012):
        """The frontmost point of the body near an across and a height, at bind."""
        pool = self.vertices[mask]
        close = np.hypot(pool[:, 0] - across, pool[:, 1] - up) < reach
        if not close.any():
            close = np.hypot(pool[:, 0] - across, pool[:, 1] - up) < reach * 3
        return pool[close][np.argmax(pool[close][:, 2])]


def work_suit(body, hair_style="full"):
    """The crew's work suit: a relaxed one-piece, collar, cuffs, belt, pockets, boots, a face."""
    pieces = [("skin", *_body_part(body, body.triangle_region == 0))]
    suit_mask = body.grown(body.clothes, 1) & ~(body.head_only & (body.from_head[:, 1] > -0.09))
    suit = _shell(body, suit_mask, SUIT_OFF, SUIT_RELAXING, weight_relaxing=4)
    pieces.append(("clothes", *suit))
    pieces += _work_suit_bands(body, suit)
    pieces += _work_suit_parts(body, suit_mask)
    pieces.append(("boots", *_shell(body, body.grown(body.boots, 3),
                                    np.where(body.boots, 0.016, 0.034), 3)))
    pieces += _hair(body, hair_style)
    pieces += _face(body)
    return pieces


def space_suit(body):
    """The space suit, after NASA's photos of the AxEMU: hood, dark visor, hard chest, tall pack."""
    pieces = []
    covered = ~body.head_only & ~body.boots & ~body.hand
    chest = body.grown(covered, 0) & (np.min([np.linalg.norm(body.vertices - body.at(name), axis=1)
                                              for name in ("Chest", "Spine2", "LeftShoulder",
                                                           "RightShoulder")], axis=0) < 0.26)
    suit = _shell(body, covered, np.where(chest, SPACE_SUIT_CHEST_OFF, SPACE_SUIT_OFF), 16,
                  weight_relaxing=6)
    pads = np.array([body.at(name) for name in ("LeftForeArm", "RightForeArm", "LeftShin",
                                                "RightShin")])
    on_a_pad = lambda points: np.linalg.norm(points[:, None, :] - pads[None], axis=2).min(axis=1) < 0.13
    pad, rest = _split_by_corners(suit, on_a_pad)
    pieces += [("suit", *rest), ("suit_pad", *pad)]
    pieces.append(("suit", *_shell(body, body.hand, 0.03, 6)))
    sole, upper = _split_by_corners(_shell(body, body.boots, 0.04, 6),
                                    lambda points: points[:, 1] < 0.035)
    pieces += [("suit", *upper), ("suit_sole", *sole)]
    pieces += _helmet(body)
    chest_at = body.at("Chest")
    pieces.append(("suit", *_rigid(body, *_box(chest_at + np.array([0.0, 0.15, 0.22]),
                                               (0.24, 0.16, 0.08)), "Chest")))
    pieces.append(("hardware", *_rigid(body, *_box(chest_at + np.array([0.0, 0.15, 0.265]),
                                                   (0.16, 0.04, 0.02)), "Chest")))
    ring, ring_faces = _sphere(body.at("Neck2") + np.array([0.0, -0.04, 0.0]), 0.15, rings=6,
                               segments=20, squash=(1.0, 0.3, 1.0))
    pieces.append(("hardware", *_rigid(body, ring, ring_faces, "Chest")))
    pack_middle = chest_at + np.array([0.0, 0.16, -0.40])
    pieces.append(("suit", *_rigid(body, *_box(pack_middle, (0.52, 0.82, 0.26)), "Chest")))
    pieces.append(("suit_stripe", *_rigid(body, *_box(pack_middle + np.array([0.0, 0.41, 0.0]),
                                                      (0.53, 0.02, 0.27)), "Chest")))
    return pieces


# --- the work suit's parts --------------------------------------------------------------

def _work_suit_bands(body, suit):
    """Collar, cuffs and belt, each cut cleanly out of the suit and lifted just off it."""
    hips = body.at("Hips")[1]
    neck = body.at("Neck1")
    wrists = [body.at(name) for name in ("LeftHand", "RightHand")]
    near_a_wrist = lambda points: np.min([np.linalg.norm(points - wrist, axis=1)
                                          for wrist in wrists], axis=0)
    return [
        ("overall_trim", *_band(body, suit, lambda points: np.linalg.norm(points - neck, axis=1) - 0.14,
                                0.012)),
        ("overall_trim", *_band(body, suit, lambda points: near_a_wrist(points) - 0.085, 0.01)),
        ("belt", *_band(body, suit, lambda points: np.maximum(hips + 0.035 - points[:, 1],
                                                        points[:, 1] - (hips + 0.085)), 0.01)),
    ]


def _work_suit_parts(body, suit_mask):
    """The chest pockets, the buckle and a patch on the shoulder, rigid on the joint under them."""
    pieces = []
    for side in (-1, 1):
        front = body.frontmost(0.095 * side, 1.33, suit_mask, 0.02)
        pocket = np.array([0.095 * side, 1.325, front[2] + 0.024])
        pieces.append(("overall_trim", *_rigid(body, *_box(pocket, (0.10, 0.085, 0.012)), "Chest")))
        pieces.append(("clothes", *_rigid(body, *_box(pocket + np.array([0.0, 0.036, 0.004]),
                                                      (0.105, 0.022, 0.012)), "Chest")))
    hips = body.at("Hips")[1]
    buckle = body.frontmost(0.0, hips + 0.057, suit_mask, 0.02)
    pieces.append(("hardware", *_rigid(body, *_box(np.array([0.0, hips + 0.057, buckle[2] + 0.028]),
                                                   (0.05, 0.04, 0.012)), "Hips")))
    shoulder = body.at("LeftArm")
    pieces.append(("patch", *_rigid(body, *_box(shoulder + np.array([0.02, -0.02, 0.075]),
                                                (0.06, 0.06, 0.012)), "LeftArm")))
    return pieces


def _hair(body, style):
    """Hair over the top, back and sides of the head, clear of the face."""
    above = body.from_head
    covered = body.head_only & (((above[:, 1] > 0.085) | ((above[:, 1] > 0.06) & (above[:, 2] < 0.07)))
                                | ((above[:, 2] < 0.0) & (above[:, 1] > -0.06))
                                | ((above[:, 1] > 0.02) & (np.abs(above[:, 0]) > 0.062))
                                | ((above[:, 1] > 0.025) & (above[:, 2] < 0.09)
                                   & (np.abs(above[:, 0]) > 0.045))
                                | ((above[:, 1] > 0.045) & (above[:, 2] < 0.085)))
    if style == "bun":
        knot, knot_faces = _sphere(body.head + np.array([0.0, 0.07, -0.12]), 0.055)
        return [("hair", *_shell(body, covered, 0.012, 4)),
                ("hair", *_rigid(body, knot, knot_faces, "Head"))]
    return [("hair", *_shell(body, covered, np.where(above[:, 1] > 0.05, 0.028, 0.018), 6))]


def _face(body):
    """Eyes, brows and lips, small shapes on the head so a face reads in flat colour."""
    pieces = []
    for side, eye in body.eyes.items():
        surface = body.frontmost(eye[0], eye[1], body.head_only)
        white, white_faces = _sphere(np.array([eye[0], eye[1], surface[2] - 0.005]), 0.012,
                                     rings=6, segments=12, squash=(1.35, 0.7, 0.6))
        pieces.append(("eye_white", *_rigid(body, white, white_faces, "Head")))
        iris, iris_faces = _sphere(np.array([eye[0], eye[1], surface[2] - 0.0015]), 0.0065,
                                   rings=6, segments=10, squash=(1.0, 1.0, 0.6))
        pieces.append(("iris", *_rigid(body, iris, iris_faces, "Head")))
        brow_at = body.frontmost(eye[0] + 0.004 * side, eye[1] + 0.024, body.head_only)
        brow, brow_faces = _box(brow_at + np.array([0.0, 0.0, -0.001]), (0.034, 0.0075, 0.008))
        tilt = Rotation.from_euler("z", -8 * side, degrees=True).as_matrix()
        pieces.append(("hair", *_rigid(body, brow_at + (brow - brow_at) @ tilt.T, brow_faces,
                                       "Head")))
    nose = body.vertices[body.head_only][np.argmax(body.vertices[body.head_only][:, 2])]
    mouth = nose[1] - 0.036
    lips = body.head_only & (np.abs(body.vertices[:, 1] - mouth) < 0.007) \
        & (np.abs(body.vertices[:, 0]) < 0.024) & (body.vertices[:, 2] > nose[2] - 0.04)
    pieces.append(("lips", *_shell(body, lips, 0.0015, 0, tuck=False)))
    return pieces


def _helmet(body):
    """A bubble with a dark visor across the front, a white hood over the rest, two lights."""
    middle = body.head + np.array([0.0, 0.03, 0.01])
    bubble, bubble_faces = _sphere(middle, 0.165, rings=16, segments=24, squash=(1.0, 1.1, 1.05))
    from_middle = bubble - middle
    visor = (from_middle[:, 2] > 0.02) & (from_middle[:, 1] > -0.10) & (from_middle[:, 1] < 0.12)
    helmet = _rigid(body, bubble, bubble_faces, "Head")
    pieces = [("visor", *_split(*helmet, visor[bubble_faces].all(axis=1)))]
    hood, hood_faces = _sphere(middle + np.array([0.0, 0.025, -0.015]), 0.18, rings=16,
                               segments=24, squash=(1.02, 1.15, 1.05))
    from_middle = hood - middle
    covering = ~((from_middle[:, 2] > 0.04) & (from_middle[:, 1] < 0.13)) & (from_middle[:, 1] > -0.11)
    stripe = covering & (np.abs(from_middle[:, 0]) < 0.022) & (from_middle[:, 1] > 0.05)
    hood_part = _rigid(body, hood, hood_faces, "Head")
    pieces.append(("suit", *_split(*hood_part, covering[hood_faces].all(axis=1))))
    pieces.append(("suit_stripe", *_split(*hood_part, stripe[hood_faces].all(axis=1))))
    for side in (-1, 1):
        light, light_faces = _sphere(middle + np.array([0.12 * side, 0.12, 0.12]), 0.025,
                                     rings=6, segments=8)
        pieces.append(("hardware", *_rigid(body, light, light_faces, "Head")))
    return pieces


# --- shapes -----------------------------------------------------------------------------

def _shell(body, mask, push, relaxing, weight_relaxing=0, tuck=True):
    """A shell over the triangles whose corners are all in the mask: pushed out, then relaxed.

    Its edge stays tucked just off the skin, so it never stands open on a gap.
    """
    triangles = body.faces[mask[body.faces].all(axis=1)]
    used = np.unique(triangles)
    renumber = -np.ones(len(body.vertices), dtype=np.int64)
    renumber[used] = np.arange(len(used))
    wanted = push[used] if np.ndim(push) else np.full(len(used), float(push))
    edge = np.array([not mask[body.around[vertex]].all() for vertex in used]) if tuck \
        else np.zeros(len(used), dtype=bool)
    wanted = np.where(edge, TUCKED, wanted)
    base, normals = body.vertices[used], body.normals[used]
    points = base + normals * wanted[:, None]
    weights = body.weights[used].copy()
    around = [renumber[body.around[vertex]][renumber[body.around[vertex]] >= 0] for vertex in used]
    for _ in range(relaxing):
        relaxed = np.array([points[ring].mean(axis=0) if len(ring) else points[index]
                            for index, ring in enumerate(around)])
        points = np.where(edge[:, None], points, 0.5 * points + 0.5 * relaxed)
    for _ in range(weight_relaxing):
        weights = 0.5 * weights + 0.5 * np.array([weights[ring].mean(axis=0) if len(ring)
                                                  else weights[index]
                                                  for index, ring in enumerate(around)])
    # Relaxing shrinks a shell; push it back out to at least the gap it was asked for.
    gap = ((points - base) * normals).sum(axis=1)
    points += normals * np.maximum(0.0, wanted - gap)[:, None]
    return points, renumber[triangles], weights


def _band(body, part, outside, lift):
    """The piece of a mesh where outside(point) <= 0, cut along its edge and lifted off it.

    Where the suit under it tucks in to the skin the band tucks in with it, or its edge stands
    a centimetre off the neck and shows a sliver of light.
    """
    points, faces, weights = _clip(part, outside)
    if not len(faces):
        return points, faces, weights
    off_the_body, _ = cKDTree(body.vertices).query(points)
    share = np.clip((off_the_body - TUCKED) / (SUIT_OFF - TUCKED), 0.0, 1.0)
    return points + _smooth_normals(points, faces) * (lift * share)[:, None], faces, weights


def _clip(part, outside):
    """The piece of a mesh where outside(point) <= 0, with triangles cut cleanly at the edge.

    Each triangle is cut against the edge the way a polygon is clipped against a line; a new
    corner on an edge takes its place and its skin weights part way between the two ends, and
    corners that land on the same spot are welded so the piece stays whole.
    """
    points, faces, weights = part
    distance = outside(points)
    kept_points, kept_weights, kept_faces = [], [], []
    for corners in faces:
        polygon = []
        for index in range(3):
            here, there = corners[index], corners[(index + 1) % 3]
            if distance[here] <= 0:
                polygon.append((points[here], weights[here]))
            if (distance[here] <= 0) != (distance[there] <= 0):
                part_way = distance[here] / (distance[here] - distance[there])
                polygon.append((points[here] + (points[there] - points[here]) * part_way,
                                weights[here] + (weights[there] - weights[here]) * part_way))
        if len(polygon) < 3:
            continue
        first = len(kept_points)
        for point, weight in polygon:
            kept_points.append(point)
            kept_weights.append(weight)
        for fan in range(1, len(polygon) - 1):
            kept_faces.append([first, first + fan, first + fan + 1])
    if not kept_faces:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64), np.zeros((0, weights.shape[1]))
    kept_points = np.array(kept_points)
    _, keep, renumber = np.unique(np.round(kept_points, 5), axis=0, return_index=True,
                                  return_inverse=True)
    faces_out = renumber.reshape(-1)[np.array(kept_faces, dtype=np.int64)]
    return kept_points[keep], faces_out, np.array(kept_weights)[keep]


def _body_part(body, triangle_mask):
    """The body's own triangles that a mask picks, as a piece of their own."""
    return _split(body.vertices, body.faces, body.weights, triangle_mask)


def _split(points, faces, weights, keep):
    """The triangles of a piece that `keep` says yes to, with only the corners they use."""
    triangles = faces[keep]
    used = np.unique(triangles)
    renumber = -np.ones(len(points), dtype=np.int64)
    renumber[used] = np.arange(len(used))
    return points[used], renumber[triangles], weights[used]


def _split_by_corners(part, test):
    """A piece split in two by whether all three corners of each triangle pass a test."""
    points, faces, weights = part
    keep = test(points)[faces].all(axis=1)
    return _split(points, faces, weights, keep), _split(points, faces, weights, ~keep)


def _rigid(body, points, faces, joint_name):
    """A shape that moves with one joint and nothing else."""
    weights = np.zeros((len(points), len(body.joint_names)))
    weights[:, body.joint[joint_name]] = 1.0
    return points, faces, weights


def _sphere(middle, radius, rings=14, segments=20, squash=(1.0, 1.0, 1.0)):
    """A sphere, squashed along each axis, with its triangles facing outwards."""
    points, faces = [], []
    for ring in range(rings + 1):
        down = np.pi * ring / rings
        for segment in range(segments):
            round_about = 2 * np.pi * segment / segments
            points.append([np.sin(down) * np.cos(round_about) * squash[0], np.cos(down) * squash[1],
                           np.sin(down) * np.sin(round_about) * squash[2]])
    for ring in range(rings):
        for segment in range(segments):
            corner = ring * segments + segment
            beside = ring * segments + (segment + 1) % segments
            faces += [[corner, beside, corner + segments],
                      [beside, beside + segments, corner + segments]]
    return np.array(points) * radius + middle, np.array(faces)


def _box(middle, size):
    """A box, its triangles facing outwards."""
    half_x, half_y, half_z = np.array(size) / 2
    corners = np.array([[-half_x, -half_y, -half_z], [half_x, -half_y, -half_z],
                        [half_x, half_y, -half_z], [-half_x, half_y, -half_z],
                        [-half_x, -half_y, half_z], [half_x, -half_y, half_z],
                        [half_x, half_y, half_z], [-half_x, half_y, half_z]]) + middle
    sides = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]]
    faces = [[side[0], side[1], side[2]] for side in sides] + \
        [[side[0], side[2], side[3]] for side in sides]
    return corners, np.array(faces)


def _neighbours(faces, count):
    """For every vertex, the vertices it shares a triangle edge with."""
    rows = [set() for _ in range(count)]
    for first, second, third in faces:
        rows[first].update((second, third))
        rows[second].update((first, third))
        rows[third].update((first, second))
    return [np.array(sorted(row), dtype=np.int64) for row in rows]


def _smooth_normals(points, faces):
    """One normal a vertex, from the triangles around it, weighted by how big each one is."""
    corners = points[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals = np.zeros_like(points)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.where(lengths > 0, lengths, 1.0)
