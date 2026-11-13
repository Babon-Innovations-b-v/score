"""A finished model file edited on its own bytes (glb_file.py) is stood up the way its shape says, and keeps everything
else: its shape, its normals turned with it, its kept triangles' corners and UVs, its maps padded from the nearest
piece and shrunk only as far as each map's role allows.

The one test reads a table of shapes whose right answer is plain (a crate 0.6 tall stands 0.6 tall; a 7 degree lean is
taken out; a 20 degree one is not trusted), built here as points or normals, each turned by the stand its row names and
judged by the measures its row expects; then one one-square model file is cut, turned, padded, shrunk, written and read
back once, and every thing it must keep is asserted on what comes back.

Breaks that turn the test red (each applied once and seen red; the rows named are the ones that fail):
- row "leaning building": level_turn's wall `up = np.linalg.eigh(spread)[1][:, 0]` made `[:, 2]`.
- row "tilted pad": level_turn's flat branch `if floor_share >= FLOOR_SHARE and ...` made `if False:`.
- row "steep lean": level_turn's `> most:` made `> 90:`.
- row "tilted crate": upright_turn's default `sides[np.argmax(np.abs(sides[:, 1]))]` made `sides[0]`.
- row "tall rocket": upright_turn's `sides[0] if long` made `sides[2] if long`.
- row "flat take": upright_turn's `sides[2] if flat` made `sides[1] if flat`.
- row "sheet square to the picture": upright_turn's `up = -np.sign(side[2]) if flat else np.sign(side[1])` made
  `up = np.sign(side[1])` and `(up or 1.0)` made `up` (the code before f47fd1ca: a zero pick and a NaN turn,
  2026-10-26), and, apart, `-np.sign(side[2])` made `np.sign(side[2])` (laid picture side down).
- row "model on legs": upright_turn's `if feet:` made `if False:`.
- row "long model": upright_turn's `return squared(points @ turn.T) @ turn` made `return turn`.
- row "square sheet": squared's `if max(sides) >= SQUARE_ASPECT * min(sides):` made `if True:` (the long-side way
  only, as before 2026-10-26: the sheet stays about 45 degrees off).
- row "long plank": squared's `>= SQUARE_ASPECT * min(sides)` made `>= 1e9 * min(sides)` (the tightest rectangle's
  way only: a plank 60 degrees off is squared the short way, its long side along X).
- row "round footprint": squared's `angle = 0.0` made `pass`.
- row "rocket section": upright_turn's `if tube:` made `if False:`.
- the file's normals: turned's `("POSITION", "NORMAL", "TANGENT")` made `("POSITION", "TANGENT")`.
- the file's kept triangle: without_triangles' `[~np.asarray(dropped)]` made `[np.asarray(dropped)]`.
- the file's maps without black: padded's `[rows, columns]` lookup made the picture as it is
  (`pixels = np.asarray(picture.convert("RGB"))`).
- the file's map sizes: shrunk's `wanted = side if number in base_images else ...` made `wanted = side`.
"""
import io
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import glb_file  # noqa: E402


def tilted(points, degrees, axis=(1.0, 0.0, 0.0)):
    """The points turned `degrees` about `axis`, the way a picture's camera leaves a model."""
    axis = np.array(axis) / np.linalg.norm(axis)
    angle = np.radians(degrees)
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    turn = np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew
    return points @ turn.T


def box(width, height, depth, count=4000, seed=0):
    """Points filling a box standing on the ground, centred over the origin."""
    return (np.random.default_rng(seed).random((count, 3)) - [0.5, 0.0, 0.5]) * [width, height, depth]


def square_picture(size, left_colour):
    """A PNG `size` texels a side, `left_colour` on its left half and black elsewhere, as a bake leaves it."""
    pixels = np.zeros((size, size, 3), dtype=np.uint8)
    pixels[:, : size // 2] = left_colour
    picture = io.BytesIO()
    Image.fromarray(pixels).save(picture, "PNG")
    return picture.getvalue()


def one_quad_file(size=16):
    """A model file holding one square facing up, whose UVs cover the left half of a picture that is red there and
    black elsewhere."""
    positions = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], dtype=np.float32)
    normals = np.tile(np.array([0, 1, 0], dtype=np.float32), (4, 1))
    uv = np.array([[0, 0], [0.5, 0], [0.5, 1], [0, 1]], dtype=np.float32)
    indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint16)
    picture = square_picture(size, [200, 30, 30])
    views = [positions.tobytes(), normals.tobytes(), uv.tobytes(), indices.tobytes(), picture]
    document = {
        "asset": {"version": "2.0"},
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 4,
             "min": positions.min(0).tolist(), "max": positions.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "type": "VEC3", "count": 4},
            {"bufferView": 2, "componentType": 5126, "type": "VEC2", "count": 4},
            {"bufferView": 3, "componentType": 5123, "type": "SCALAR", "count": 6},
        ],
        "bufferViews": [{"buffer": 0, "byteLength": len(view)} for view in views],
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
    }
    return document, views


BOX_NORMALS = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
BOX_AREAS = np.array([6.0, 6.0, 4.0, 4.0, 6.0, 6.0])  # a 2 x 3 x 2 box's six sides
SHEET_TOLERANCE = 0.002 + 1e-5 * 0.08  # np.allclose's atol plus its rtol of the 8 cm side


def picture_faced_sheet():
    """A sheet whose faces are exact planes square to Z (the finish's remesh of a rug standing in the picture's
    plane), its first four points on the face toward the picture's camera (-Z)."""
    points = box(0.13, 0.28, 0.002)
    points[:, 2] = np.where(points[:, 2] < 0, -0.001, 0.001)
    points[:, 2][:4] = -0.001
    return points


def on_legs():
    """Four thin legs under a tall body leaning 25 degrees over them, all tilted 20 degrees, and where each foot's
    points lie in it."""
    rng = np.random.default_rng(1)
    body = tilted(box(1.0, 2.5, 1.0, 3000), 25, (0.0, 0.0, 1.0)) + [0.0, 0.4, 0.0]
    feet = [rng.normal([x, 0.0, z], 0.005, (200, 3)) for x in (-0.8, 0.8) for z in (-0.8, 0.8)]
    return tilted(np.vstack([body, *feet]), 20), [slice(3000 + 200 * foot, 3200 + 200 * foot) for foot in range(4)]


def round_footprint():
    rng = np.random.default_rng(1)
    angle, radius = rng.random(4000) * 2 * np.pi, 0.5 * np.sqrt(rng.random(4000))
    return np.c_[radius * np.cos(angle), rng.random(4000) * 0.4, radius * np.sin(angle)]


def rocket_section():
    """A tube with fins at its foot and a box on its side, tilted: fins and box fool the other ways of standing it up,
    the tube's axis does not."""
    rng = np.random.default_rng(2)
    angle = rng.random(6000) * 2 * np.pi
    tube = np.c_[0.3 * np.cos(angle), rng.random(6000) * 2.0, 0.3 * np.sin(angle)]
    fins = np.vstack([box(0.05, 0.5, 1.4, 800, seed) for seed in (3, 4)])
    fins[800:] = fins[800:, [2, 1, 0]]
    side_box = box(0.3, 0.4, 0.3, 600, 5) + [0.4, 1.2, 0.0]
    return tilted(np.vstack([tube, fins, side_box]), 12, (1.0, 0.0, 0.5))


def shapes():
    """Every shape, the stand that turns it (level_turn on its faces, upright_turn with the row's flags, or squared
    alone) and what the turned shape must show:
    extent: per axis (0 x, 1 y, 2 z), the open range its span lies in;
    still: no turn at all;
    lean: the most nearly vertical face normal is within these degrees of straight up or down;
    top: the first face normal's height after the turn is above this;
    marked_on_top: the first point ends above the mean;
    feet: the spread of the feet's mean heights is under this;
    tube: the tube's own axis is within these degrees of up."""
    legs, feet = on_legs()
    return [
        {"name": "leaning building", "stand": "level", "faces": (tilted(BOX_NORMALS, 7.0), BOX_AREAS), "lean": 0.01},
        {"name": "tilted pad", "stand": "level",
         "faces": (tilted(np.array([[0, 1, 0], [0, -1, 0], [1, 0, 0], [0, 0, 1]], float), 8.0),
                   np.array([100.0, 100.0, 1.0, 1.0])), "top": 0.9999},
        # 20 degrees: its sides still read as walls (sin 20 = 0.34, under WALL_SLOPE), so a lean is found, and it is
        # past the 15 degrees a generated model's crookedness is trusted to
        {"name": "steep lean", "stand": "level", "faces": (tilted(BOX_NORMALS, 20.0), BOX_AREAS), "still": True},
        {"name": "tilted crate", "stand": "upright", "points": tilted(box(1.0, 0.6, 0.8), 35),
         "extent": {1: (0.57, 0.63)}},
        {"name": "tall rocket", "stand": "upright", "flags": {"long": True},
         "points": tilted(box(0.5, 2.0, 0.5), 50, (1.0, 0.0, 1.0)), "extent": {1: (1.9, 2.1)}},
        # a rug drawn from straight above comes out standing in the picture's plane; `flat` lays it, thin side up
        {"name": "flat take", "stand": "upright", "flags": {"flat": True}, "points": tilted(box(2.0, 3.0, 0.02), 10),
         "extent": {1: (0.01, 0.03)}},
        # its side had no up at all (2026-10-26); laid, the face toward the picture's camera is on top
        {"name": "sheet square to the picture", "stand": "upright", "flags": {"flat": True},
         "points": picture_faced_sheet(), "extent": {1: (0.001, 0.003)}, "marked_on_top": True},
        # the body's box would stand it on the lean; the feet decide level
        {"name": "model on legs", "stand": "upright", "flags": {"feet": True}, "points": legs, "feet": (feet, 0.02)},
        {"name": "long model", "stand": "upright", "points": tilted(box(0.4, 0.3, 2.0), 40, (0.0, 1.0, 0.0)),
         "extent": {2: (1.9, np.inf)}},
        # an 8 cm square note lying flat, turned 45 degrees about up: squared, 8 cm along X and Z (11.3 cm turned)
        {"name": "square sheet", "stand": "upright", "flags": {"flat": True},
         "points": tilted(box(0.08, 0.001, 0.08), 45, (0.0, 1.0, 0.0)),
         "extent": {axis: (0.08 - SHEET_TOLERANCE, 0.08 + SHEET_TOLERANCE) for axis in (0, 2)}},
        {"name": "long plank", "stand": "squared", "points": tilted(box(0.2, 0.05, 2.0), 60, (0.0, 1.0, 0.0)),
         "extent": {2: (1.98, np.inf), 0: (-np.inf, 0.22)}},
        {"name": "round footprint", "stand": "squared", "points": round_footprint(), "still": True},
        {"name": "rocket section", "stand": "upright", "flags": {"long": True, "tube": True},
         "points": rocket_section(), "tube": 1.5},
    ]


def stand_turn(shape):
    """The turn the row's stand gives its shape."""
    if shape["stand"] == "level":
        return glb_file.level_turn(*shape["faces"])
    if shape["stand"] == "squared":
        return glb_file.squared(shape["points"])
    return glb_file.upright_turn(shape["points"], **shape.get("flags", {}))


def shape_failures(shape):
    """What the turned shape shows that its row does not expect, each named."""
    turn = stand_turn(shape)
    if not np.isfinite(turn).all():
        return [f"no turn: {turn}"]
    failures = []
    if shape.get("still") and not np.allclose(turn, np.eye(3)):
        failures.append(f"turned when it should be left as it is: {turn}")
    if "faces" in shape:
        stood = shape["faces"][0] @ turn.T
        worst = np.degrees(np.arccos(np.clip(np.abs(stood[:, 1]).max(), -1, 1)))
        if "lean" in shape and not worst < shape["lean"]:
            failures.append(f"a side still leans {worst:.3f} degrees off vertical or level")
        if "top" in shape and not stood[0, 1] > shape["top"]:
            failures.append(f"its top is not laid level: {stood[0]}")
        return failures
    turned = shape["points"] @ turn.T
    extents = np.ptp(turned, axis=0)
    for axis, (low, high) in shape.get("extent", {}).items():
        if not low < extents[axis] < high:
            failures.append(f"spans {extents[axis]:.4f} along axis {axis}, not within ({low}, {high}): {extents}")
    if shape.get("marked_on_top") and not turned[0, 1] > turned[:, 1].mean():
        failures.append("laid picture side down")
    if "feet" in shape:
        feet, most = shape["feet"]
        heights = [float(turned[foot, 1].mean()) for foot in feet]
        if not max(heights) - min(heights) < most:
            failures.append(f"not level on its feet: {heights}")
    if "tube" in shape:
        axis = glb_file.tube_axis(turned)
        lean = np.degrees(np.arccos(min(1.0, axis[1])))
        if not lean < shape["tube"]:
            failures.append(f"its tube leans {lean:.2f} degrees")
    return failures


def test_a_model_is_stood_up_by_its_shape_and_keeps_the_rest(tmp_path):
    failures = {shape["name"]: shape_failures(shape) for shape in shapes()}
    assert not any(failures.values()), {name: found for name, found in failures.items() if found}

    # one file through every edit: its second triangle cut, up turned onto x, its maps padded and shrunk (a room of
    # hundreds of pieces cannot carry 2K maps on each, the hub kit 2026-10-06: the base colour to the side asked for,
    # every other map to half of it), then written and read back
    document, views = one_quad_file(size=256)
    views.append(square_picture(256, [90, 90, 90]))
    document["bufferViews"].append({"buffer": 0, "byteLength": len(views[5])})
    document["images"].append({"bufferView": 5, "mimeType": "image/png"})
    document["materials"] = [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0},
                                                        "metallicRoughnessTexture": {"index": 1}}}]
    document["textures"] = [{"source": 0}, {"source": 1}]
    turn = glb_file.rotation_between(np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    glb_file.without_triangles(document, views, [False, True])
    glb_file.turned(document, views, turn)
    glb_file.padded(document, views)
    glb_file.shrunk(document, views, 128)
    glb_file.write(document, views, tmp_path / "quad.glb")
    document, views = glb_file.read(tmp_path / "quad.glb")

    order = glb_file.accessor_array(document, views, 3)
    kept = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 1]], float)
    assert document["accessors"][0]["count"] == 3
    assert np.allclose(glb_file.accessor_array(document, views, 0)[order], kept @ turn.T, atol=1e-5)
    assert np.allclose(glb_file.accessor_array(document, views, 2)[order], [[0, 0], [0.5, 0], [0.5, 1]])
    assert np.allclose(glb_file.accessor_array(document, views, 1), [1, 0, 0], atol=1e-5), "normals not turned"
    # up turned onto x: the square's corners, all at height 0, now all sit at x 0
    assert np.allclose(document["accessors"][0]["max"][0], 0.0, atol=1e-5)
    assert np.allclose(glb_file.accessor_array(document, views, 0)[:, 0], 0.0, atol=1e-5)
    pictures = [Image.open(io.BytesIO(views[image["bufferView"]])).convert("RGB") for image in document["images"]]
    assert [picture.size for picture in pictures] == [(128, 128), (64, 64)]
    darkest = min(np.asarray(picture).astype(int).sum(-1).min() for picture in pictures)
    assert darkest > 150, f"a texel is still near black after padding: {darkest}"
