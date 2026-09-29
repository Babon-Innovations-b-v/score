"""Dress the body: the crew's work suit and the space suit, after the owner's drawing of them (#100).

Both are made from parts built outside the repo by tools that stay there (`paths.LOOK`): cloth
GarmentCode draped on this body, boots and hair Hi3DGen made, the MakeHuman eyes. Here the parts
are assembled on the body (`work_suit.py`, `boots.py`, `face.py`, `space_suit.py`), weighted to
its skeleton (`skin.py`) and painted (`paint.py`), so every clip plays on both outfits with no
conversion of any kind.

An outfit is a list of `Part`s, one surface each in the body file, each carrying its own picture.
The game draws every one with the crew's own two-tone light (`game/people/person/`).

Three things the pictures showed and why the code is the shape it is:

**Some parts arrive wound inward.** The generated hair's triangles all face into the head, and a
mirrored brow can come out inside out; the engine then culls the outside and the head shows
through. They are turned by the sign of their volume.

**The collar is seen from inside.** Through the stand collar's front gap you see its far wall and
the inside of the cloth below it, which the engine would cull, showing the background. The collar
is drawn from both sides, and a navy lining is laid inside the upper body.

**A picture needs its own seams.** A painted part is unwrapped and its points split along the
texture seams; the normals are carried across the split from the whole part, or every seam shows
as a crease in the light.
"""
import blender
import face
import numpy as np
import paint
import skin
import space_suit
import texels
import trimesh
import work_suit
from paths import EYES, HAIR, SPACE_DRAPE, WORK_DRAPE

# The lining: the upper body's inside, above this height, is drawn facing in.
LINING_ABOVE = 1.25


class Part:
    """One surface of an outfit: its name, points, faces, weights, texture coordinates (v
    running up the picture), normals, and its picture as bytes (rows, columns, 3)."""

    def __init__(self, surface, points, faces, weights, uv, normals, picture):
        self.surface = surface
        self.points = points
        self.faces = faces
        self.weights = weights
        self.uv = uv
        self.normals = normals
        self.picture = picture


def split_part(name, points, faces, weights):
    """A part unwrapped and split along its texture seams, as a painter takes it: points, faces,
    weights, uv and normals (carried from the unsplit part), and each point's source point."""
    normals = texels.smooth_normals(points, faces)
    new_faces, source, uv = texels.split_on_seams(faces, blender.corner_uv(name, points, faces))
    return {"points": points[source], "faces": new_faces, "weights": weights[source], "uv": uv,
            "normals": normals[source], "source": source}


def painted(name, split, picture):
    return Part(name, split["points"], split["faces"], split["weights"], split["uv"],
                split["normals"], picture)


def flat(name, points, faces, weights, colour, both_sides=False):
    """A part in one colour. Drawn from both sides, it is doubled with the copy turned round."""
    normals = texels.smooth_normals(points, faces)
    if both_sides:
        faces = np.concatenate([faces, faces[:, ::-1] + len(points)])
        points = np.concatenate([points, points])
        weights = np.concatenate([weights, weights])
        normals = np.concatenate([normals, -normals])
    return Part(name, points, faces, weights, np.full((len(points), 2), 0.5), normals,
                texels.flat_picture(colour))


def wound_outward(points, faces):
    """Faces turned round where the mesh encloses a negative volume, piece by piece."""
    faces = np.asarray(faces, dtype=np.int64).copy()
    mesh = trimesh.Trimesh(points, faces, process=False)
    for piece in trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(faces))):
        if trimesh.Trimesh(points, faces[piece], process=False).volume < 0:
            faces[piece] = faces[piece][:, ::-1]
    return faces


def lining(cloth_points, cloth_faces, cloth_weights, panels):
    """The inside of the upper body, faces turned in, seen through the collar's front gap."""
    upper = (np.char.find(panels, "torso") >= 0) | (np.char.find(panels, "collar") >= 0)
    keep = upper[cloth_faces].all(axis=1) & (cloth_points[cloth_faces][:, :, 1].min(axis=1) > LINING_ABOVE)
    used = np.unique(cloth_faces[keep])
    index = np.full(len(cloth_points), -1)
    index[used] = np.arange(len(used))
    normals = -texels.smooth_normals(cloth_points, cloth_faces)[used]
    return Part("work_lining", cloth_points[used], index[cloth_faces[keep]][:, ::-1].copy(),
                cloth_weights[used], np.full((len(used), 2), 0.5), normals,
                texels.flat_picture(paint.NAVY))


def bare_parts(body):
    """The bare skin and what is on it: the body's own head and hands, the hair and the eyes from
    the look, and the brows and irises laid on them. {name: (points, faces, weights)}."""
    names = body.joint_names
    head_points, head_faces, head_weights = skin.head_and_neck(body)
    eyes = np.load(EYES)
    eye_points, eye_faces = eyes["points"], eyes["faces"].astype(np.int64)
    surface = face.the_head_surface(head_points, head_faces, eye_points, eye_faces)
    hair = np.load(HAIR)
    shaped = {"skin_head": (head_points, head_faces, head_weights),
              "skin_hands": skin.bare_hands(body),
              "hair": (hair["points"], wound_outward(hair["points"], hair["faces"]), None),
              "eyes": (eye_points, eye_faces, None),
              "irises": (*face.irises(surface), None),
              "eyebrows": (*face.brows(surface), None)}
    for name, (points, faces, weights) in shaped.items():
        if weights is None:
            shaped[name] = (points, faces, skin.on_one_joint(len(points), names, "Head"))
    return shaped


def work_suit_parts(body):
    """The work suit, every part painted."""
    shaped, panels, extra = work_suit.pieces(body, WORK_DRAPE)
    shaped.update(bare_parts(body))
    parts = []
    for name, (points, faces, weights) in shaped.items():
        if name in paint.WORK_FLAT:
            parts.append(flat(name, points, faces, weights, paint.WORK_FLAT[name],
                              both_sides=name == "work_collar"))
            continue
        split = split_part(name, points, faces, weights)
        if name == "work_cloth":
            picture = paint.work_cloth(split, panels, body.joints)
        elif name == "work_placket":
            picture = paint.work_placket(split, extra["placket_across"])
        elif name == "work_pocket":
            picture = paint.work_pocket(split, extra["flap_from"])
        elif name == "skin_head":
            picture = paint.skin_head(split)
        elif name == "hair":
            picture = paint.hair(split)
        else:
            raise ValueError(f"no painter for the work suit's {name}")
        parts.append(painted(name, split, picture))
    parts.append(lining(*shaped["work_cloth"], panels))
    return parts


def space_suit_parts(body):
    """The space suit, every part flat but the chest flag."""
    parts = []
    for name, (points, faces, weights) in space_suit.pieces(body, SPACE_DRAPE).items():
        if name == "flag":
            split = split_part("suit_flag", points, faces, weights)
            parts.append(painted(name, split, paint.suit_flag(split)))
        else:
            parts.append(flat(name, points, faces, weights, paint.suit_colour(name)))
    return parts


def outfits(body):
    """Both outfits, by the names the game knows them by: {"work": parts, "suit": parts}."""
    return {"work": work_suit_parts(body), "suit": space_suit_parts(body)}
