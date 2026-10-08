"""The crew kit (#112): one file per build holding every part a seed can mix onto that build.

    MOTION_PERSON=kit_<build> python body.py      (run.sh builds every kit build)

A kit file is a person file (`body.py`) whose outfits are the kit's parts, one node each, so the
game shows the nodes a mix names and hides the rest:

- `work_<scheme>`: the work suit in one of the colour schemes (`paint.SCHEMES`), with bare hands;
- `suit`: the space suit;
- `head_<face>`: one of the faces on this build's neck (skin, eyes, irises, brows);
- `hair_<style>_<face>`: one of the hairstyles, fitted to that face's head;
- `plain_<outfit>`: the crowd's plain clothes (`prologue.PLAIN`), with bare hands.

What a build holds is its look's `person.json` (`kit`: faces, hair, schemes, plain): a build
carries only its own sex's faces and hairstyles, because a mix never puts a woman's face on a
man's build. The drapes are GarmentCode's on this build, in its look; the faces are SAM 3D Body's
reads of the kit's face sheet, set on this build's neck (`faces.py`); the hairstyles were made on
take C's head and are carried onto each face. Every place measured on take C goes through
`fit.py`, with this build's joints and torso.
"""
import numpy as np

import dress
import face
import faces
import paint
import skin
import space_suit
import work_suit
from paths import HOME, KIT, SPACE_DRAPE, WORK_DRAPE
from person import WHO

# Take C's eyes, seated on the head every kit face is carried from.
TAKE_C_EYES = HOME / "look" / "take_c" / "eyes.npz"
# The six faces of the kit's face sheet (takes/kit_faces_101.png), left to right, top row first:
# who they are, and their colours. Hair and brows follow the drawing; skin is take C's.
FACES = {
    "f1": {"who": "young man", "hair": (30, 24, 22), "shine": (62, 52, 48), "brow": (28, 22, 20), "brow_scale": 0.9},
    "f2": {"who": "young woman, bob", "hair": (34, 24, 22), "shine": (68, 52, 46), "brow": (40, 30, 26), "brow_scale": 0.65},
    "f3": {"who": "man in his forties", "hair": (24, 22, 24), "shine": (52, 50, 56), "brow": (22, 20, 20), "brow_scale": 1.0},
    "f4": {"who": "young woman, long hair", "hair": (40, 28, 24), "shine": (74, 56, 48), "brow": (44, 32, 28), "brow_scale": 0.6},
    "f5": {"who": "older man, grey", "hair": (178, 176, 172), "shine": (214, 212, 208), "brow": (150, 146, 140), "brow_scale": 0.95},
    "f6": {"who": "heavier woman", "hair": (38, 26, 22), "shine": (72, 54, 46), "brow": (42, 30, 26), "brow_scale": 0.65},
    # The leader's own face, on his own build (not one of the kit's).
    "leader": {"who": "old man", "hair": (192, 192, 190), "shine": (226, 226, 224), "brow": (132, 130, 126), "brow_scale": 1.1},
}


def face_body(name):
    """A face's whole body as SAM read it, at its bind pose, as a skin.Body."""
    data = np.load(KIT / "face_bodies" / f"{name}.npz")
    return skin.Body(data["points"], data["faces"], data["weights"], list(data["joint_names"]),
                     data["bind_world"][:, :3, 3])


def with_points(body, points):
    """The same body with its points moved."""
    return skin.Body(points, body.faces, body.weights, body.joint_names,
                     [body.joints[name] for name in body.joint_names])


class TemplateHead:
    """Take C's head as the look's parts were fitted on it: the template's skin head and eyes,
    and where the brows' strips and the irises' middles sit on it, all in take C's own measures."""

    def __init__(self, template):
        self.template = template
        head_points, head_faces, _ = skin.head_and_neck(template, skin.TAKE_C_NECK_CUT)
        eyes = np.load(TAKE_C_EYES)
        self.eye_points, self.eye_faces = eyes["points"], eyes["faces"].astype(np.int64)
        self.surface = face.the_head_surface(head_points, head_faces, self.eye_points, self.eye_faces)
        self.brows = []
        for side in (1.0, -1.0):
            grid, rows, columns = face.brow_grid(side, face.TAKE_C_BROW)
            hits, _ = face.cast_front(self.surface, grid)
            self.brows.append((hits, grid, rows, columns))
        self.irises = [face.cast_front(self.surface, np.array([centre]))[0][0]
                       for centre in face.TAKE_C_EYE_CENTRES]


def brow_strip(grid, rows, columns, scale):
    """A brow grid made thinner or thicker about its own centre line."""
    shaped = grid.reshape(rows, columns, 2).copy()
    middle = shaped[:, :, 1].mean(axis=0, keepdims=True)
    shaped[:, :, 1] = middle + (shaped[:, :, 1] - middle) * scale
    return shaped.reshape(-1, 2)


def head_parts(build, face_name, reference):
    """One face on this build: {name: (points, faces, weights)} for its skin, eyes, irises and
    brows, the build with the face's head on it, and what carries take C's head onto it."""
    template = reference.template
    points = faces.transplanted(build, face_body(face_name), template)
    worn = with_points(build, points)
    head_points, head_faces, head_weights = skin.head_and_neck(worn)
    carry = faces.Carrier(template.points, points, template)
    eye_points = carry(reference.eye_points)
    surface = face.the_head_surface(head_points, head_faces, eye_points, reference.eye_faces)
    scale = FACES[face_name]["brow_scale"]
    brows = []
    for hits, grid, rows, columns in reference.brows:
        moved = carry(hits)
        shaped = brow_strip(moved[:, :2], rows, columns, scale)
        brows.append(face.slab(surface, shaped, rows, columns))
    irises = [face.disc(surface, carry(centre[None])[0][:2]) for centre in reference.irises]
    names = build.joint_names
    shaped = {"skin_head": (head_points, head_faces, head_weights),
              "eyes": (eye_points, reference.eye_faces, skin.on_one_joint(len(eye_points), names, "Head")),
              "irises": (*face.joined(irises), None), "eyebrows": (*face.joined(brows), None)}
    for key, (part_points, part_faces, weights) in shaped.items():
        if weights is None:
            shaped[key] = (part_points, part_faces, skin.on_one_joint(len(part_points), names, "Head"))
    return shaped, worn, carry


def hair_part(style, worn, carry, names):
    """A hairstyle made on take C's head, carried onto a face on this build and kept out of its
    skull: (points, faces, weights, how many points were pushed out)."""
    data = np.load(KIT / "hair" / f"{style}.npz")
    points = carry(data["points"])
    head_points, head_faces, _ = skin.head_and_neck(worn)
    hair_faces = dress.wound_outward(points, data["faces"])
    points, pushed = faces.kept_outside(points, hair_faces, head_points, head_faces)
    return points, hair_faces, skin.on_one_joint(len(points), names, "Head"), pushed


def wear_the_face(face_name):
    """The head's colours from here on: this kit face's skin (take C's), hair and brows."""
    colours = FACES[face_name]
    paint.FACE_COLOURS.update({"hair": colours["hair"], "shine": colours["shine"],
                               "brow": colours["brow"]})


def paint_head(shaped, face_name, build, prefix):
    """The head's parts painted in the face's colours: a list of Parts."""
    wear_the_face(face_name)
    parts = []
    for name, (points, part_faces, weights) in shaped.items():
        if name == "skin_head":
            split = dress.split_part(f"{prefix}skin_head", points, part_faces, weights)
            picture = paint.skin_head(split, KIT / "faces" / face_name, faces.head_joint_shift(build))
            parts.append(dress.painted("skin_head", split, picture))
        elif name == "eyebrows":
            parts.append(dress.flat(name, points, part_faces, weights, FACES[face_name]["brow"]))
        else:
            parts.append(dress.flat(name, points, part_faces, weights, paint.WORK_FLAT[name]))
    return parts


def paint_hair(style, face_name, points, part_faces, weights, prefix):
    """One hairstyle painted in the face's hair colours: a Part."""
    wear_the_face(face_name)
    split = dress.split_part(f"{prefix}hair_{style}", points, part_faces, weights)
    return dress.painted("hair", split, paint.hair(split))


def work_suits(body, schemes):
    """The work suit's shapes once, painted in each scheme: {f"work_{scheme}": parts}. A scheme
    may be a dict of its own (`paint.wear`)."""
    shaped, panels, extra = work_suit.pieces(body, WORK_DRAPE)
    shaped["skin_hands"] = skin.bare_hands(body)
    splits = {name: dress.split_part(f"kit_{name}", *shape) for name, shape in shaped.items()
              if name not in paint.WORK_FLAT}
    suits = {}
    for scheme in schemes:
        paint.wear(scheme)
        parts = []
        for name, (points, part_faces, weights) in shaped.items():
            if name in paint.WORK_FLAT:
                parts.append(dress.flat(name, points, part_faces, weights, paint.WORK_FLAT[name],
                                        both_sides=name == "work_collar"))
            elif name == "work_cloth":
                parts.append(dress.painted(name, splits[name], paint.work_cloth(splits[name], panels, body.joints)))
            elif name == "work_placket":
                parts.append(dress.painted(name, splits[name], paint.work_placket(splits[name], extra["placket_across"])))
            elif name == "work_pocket":
                parts.append(dress.painted(name, splits[name], paint.work_pocket(splits[name], extra["flap_from"])))
        parts.append(dress.lining(*shaped["work_cloth"], panels, paint.SCHEME["cloth"]))
        suits[f"work_{scheme if isinstance(scheme, str) else 'own'}"] = parts
        print(f"work_{scheme}: {sum(len(part.faces) for part in parts)} triangles", flush=True)
    paint.wear("navy")
    return suits


def space_suit_parts(body):
    """The crew's space suit on this build, every part flat but the flag."""
    parts = []
    for name, (points, part_faces, weights) in space_suit.pieces(body, SPACE_DRAPE).items():
        if name == "flag":
            split = dress.split_part("kit_suit_flag", points, part_faces, weights)
            parts.append(dress.painted(name, split, paint.suit_flag(split)))
        else:
            parts.append(dress.flat(name, points, part_faces, weights, paint.suit_colour(name)))
    print(f"suit: {sum(len(part.faces) for part in parts)} triangles", flush=True)
    return parts


def heads(body, reference, face_names, hair_styles):
    """Every face on this build and every hairstyle on each: {node: parts}."""
    nodes = {}
    for face_name in face_names:
        shaped, worn, carry = head_parts(body, face_name, reference)
        nodes[f"head_{face_name}"] = paint_head(shaped, face_name, body, f"kit_{face_name}_")
        for style in hair_styles:
            points, part_faces, weights, pushed = hair_part(style, worn, carry, body.joint_names)
            print(f"hair {style} on {face_name}: {pushed} points pushed out of the skull", flush=True)
            nodes[f"hair_{style}_{face_name}"] = [
                paint_hair(style, face_name, points, part_faces, weights, f"kit_{face_name}_")]
    return nodes


def outfits(body):
    """The kit's nodes for this build, by the names the game knows them by."""
    import prologue
    holds = WHO["kit"]
    reference = TemplateHead(faces.template_body())
    nodes = work_suits(body, holds["schemes"])
    nodes["suit"] = space_suit_parts(body)
    for name in holds["plain"]:
        nodes[f"plain_{name}"] = prologue.plain_outfit(body, name)
    nodes.update(heads(body, reference, holds["faces"], holds["hair"]))
    return nodes
