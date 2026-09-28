"""Edit a finished model file in place: stand it upright, pad its texture maps, and cut triangles out.

All three work on the file's own bytes rather than through a 3D package, because a round trip through
trimesh or Blender drops maps or smooth normals from these files. numpy, scipy, trimesh and Pillow only.

A Pixal3D model comes out in the tilted camera of the picture it was built from. `upright_turn`
finds the turn that stands it up; `turned` applies it to the positions and normals.

The bake leaves black between the UV pieces and almost no margin. As the game draws the model
further away it reads smaller copies of each picture, and that black bleeds into the pieces'
edges; thin parts are nearly all edge and go patchy. `padded` gives every texel outside the pieces
the colour of the nearest texel inside one, in every map.
"""
import io
import json
import struct

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt

# Texels at each piece's edge, already darkened by the bake, that get refilled too.
EDGE_RING = 1
# How far from straight down the face a model settles on may point once it is stood up.
RESTING_DEGREES = 35
# A round body's axis is read from this many slices of it, from this share of its height up.
TUBE_SLICES, TUBE_FROM = 6, 0.45

FLOAT = 5126
INDEX_KINDS = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}


def read(path):
    """The file as (document, list of each buffer view's bytes)."""
    data = open(path, "rb").read()
    length = struct.unpack("<I", data[12:16])[0]
    document = json.loads(data[20:20 + length])
    rest = data[20 + length:]
    binary = rest[8:8 + struct.unpack("<I", rest[:4])[0]]
    views = [binary[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
             for view in document["bufferViews"]]
    return document, views


def write(document, views, path):
    """Rebuild the one binary buffer from `views`, each aligned to four bytes, and write the file."""
    chunks, offset = [], 0
    for view, blob in zip(document["bufferViews"], views):
        view["byteOffset"], view["byteLength"], view["buffer"] = offset, len(blob), 0
        chunks.append(blob + b"\0" * (-len(blob) % 4))
        offset += len(chunks[-1])
    binary = b"".join(chunks)
    document["buffers"] = [{"byteLength": len(binary)}]
    text = json.dumps(document, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    with open(path, "wb") as out:
        out.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(binary)))
        out.write(struct.pack("<I", len(text)) + b"JSON" + text)
        out.write(struct.pack("<I", len(binary)) + b"BIN\0" + binary)


def accessor_array(document, views, index):
    """An accessor's values as a numpy array, one row per element."""
    accessor = document["accessors"][index]
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
    kind = np.float32 if accessor["componentType"] == FLOAT else INDEX_KINDS[accessor["componentType"]]
    view = document["bufferViews"][accessor["bufferView"]]
    if view.get("byteStride"):
        raise ValueError("interleaved buffer views are not handled")
    values = np.frombuffer(views[accessor["bufferView"]], dtype=kind, count=accessor["count"] * width,
                           offset=accessor.get("byteOffset", 0))
    return values.reshape(-1, width) if width > 1 else values


def put_accessor(document, views, index, values):
    """Write `values` back over an accessor's bytes, keeping its place in its buffer view."""
    accessor = document["accessors"][index]
    start = accessor.get("byteOffset", 0)
    blob = np.ascontiguousarray(values, dtype=np.float32).tobytes()
    old = views[accessor["bufferView"]]
    views[accessor["bufferView"]] = old[:start] + blob + old[start + len(blob):]
    if "min" in accessor:
        accessor["min"], accessor["max"] = values.min(0).tolist(), values.max(0).tolist()


def replace_accessor(document, views, index, values):
    """Put `values` in place of an accessor's elements, however many there now are, in the buffer
    view it has to itself; min and max follow when the accessor keeps them."""
    accessor = document["accessors"][index]
    view = accessor["bufferView"]
    sharing = [number for number, other in enumerate(document["accessors"]) if other["bufferView"] == view]
    if sharing != [index]:
        raise ValueError("an accessor that shares its buffer view cannot change its length")
    views[view] = np.ascontiguousarray(values).tobytes()
    accessor["byteOffset"], accessor["count"] = 0, len(values)
    if "min" in accessor:
        rows = values.reshape(len(values), -1)
        accessor["min"], accessor["max"] = rows.min(0).tolist(), rows.max(0).tolist()


def without_triangles(document, views, dropped):
    """Take the triangles `dropped` marks out of the first primitive, and the corners only they
    used. Every kept corner keeps its normal and UVs and the maps are untouched: for cutting a scrap
    the generator left beside a model, or a doorway, out of a finished file."""
    primitive = document["meshes"][0]["primitives"][0]
    kind = INDEX_KINDS[document["accessors"][primitive["indices"]]["componentType"]]
    triangles = accessor_array(document, views, primitive["indices"]).reshape(-1, 3)[~np.asarray(dropped)]
    used, renumbered = np.unique(triangles, return_inverse=True)
    for index in set(primitive["attributes"].values()):
        replace_accessor(document, views, index, accessor_array(document, views, index)[used])
    replace_accessor(document, views, primitive["indices"], renumbered.reshape(-1).astype(kind))


def positions(document, views):
    """Every primitive's positions, stacked: the model's shape for choosing its turn."""
    return np.vstack([accessor_array(document, views, primitive["attributes"]["POSITION"])
                      for mesh in document["meshes"] for primitive in mesh["primitives"]])


def turned(document, views, turn):
    """Apply a 3x3 turn to every position, normal and tangent."""
    done = set()
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            for name in ("POSITION", "NORMAL", "TANGENT"):
                index = primitive["attributes"].get(name)
                if index is None or index in done:
                    continue
                values = accessor_array(document, views, index).astype(np.float64)
                values[:, :3] = values[:, :3] @ turn.T
                put_accessor(document, views, index, values)
                done.add(index)


def rotation_between(start, end):
    """The shortest 3x3 turn taking direction `start` onto direction `end`."""
    start, end = start / np.linalg.norm(start), end / np.linalg.norm(end)
    axis = np.cross(start, end)
    sine, cosine = np.linalg.norm(axis), float(start @ end)
    if sine < 1e-9:
        if cosine > 0:
            return np.eye(3)
        other = np.array([1.0, 0.0, 0.0]) if abs(start[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        axis = np.cross(start, other)
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    axis /= sine
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + sine * skew + (1 - cosine) * skew @ skew


def box_sides(points):
    """The three sides of the points' tightest-fitting box, longest first."""
    to_box, extents = trimesh.bounds.oriented_bounds(points)
    sides = np.linalg.inv(to_box)[:3, :3].T
    return sides[np.argsort(-np.asarray(extents))]


def upright_turn(points, long=False, feet=False, tube=False):
    """The turn that stands a model up.

    By default the box side pointing nearest to up becomes straight up. `long` stands it on its
    longest side instead (a tall rocket, whose splayed legs can make another side look more
    upright). `feet` then sets it down on the face it would settle on (`resting_face`), so a model
    on legs stands on its footpads. `tube` then stands a round body's own axis straight up
    (`tube_axis`), for a rocket section, whose fins and side boxes fool the other two. Last, it is
    squared to the ground (`squared`).
    """
    sides = box_sides(points)
    side = sides[0] if long else sides[np.argmax(np.abs(sides[:, 1]))]
    turn = rotation_between(side * np.sign(side[1]), np.array([0.0, 1.0, 0.0]))
    if feet:
        turn = rotation_between(-resting_face(points @ turn.T), np.array([0.0, 1.0, 0.0])) @ turn
    if tube:
        turn = rotation_between(tube_axis(points @ turn.T), np.array([0.0, 1.0, 0.0])) @ turn
    return squared(points @ turn.T) @ turn


def resting_face(points):
    """The outward direction of the biggest face on the underside of the points' outer hull,
    within RESTING_DEGREES of straight down: the face spanning a model's feet, which it settles on
    when set down. Its lowest points alone would often be two feet and an engine bell."""
    hull = trimesh.convex.convex_hull(points)
    downward = hull.face_normals @ np.array([0.0, -1.0, 0.0]) > np.cos(np.radians(RESTING_DEGREES))
    if not downward.any():
        return np.array([0.0, -1.0, 0.0])
    candidates = np.where(downward)[0]
    return hull.face_normals[candidates[np.argmax(hull.area_faces[candidates])]]


def circle_centre(across):
    """The centre of the circle that best fits points given as (x, z) pairs."""
    matrix = np.c_[across, np.ones(len(across))]
    first, second, _ = np.linalg.lstsq(matrix, -(across ** 2).sum(1), rcond=None)[0]
    return np.array([-first / 2, -second / 2])


def tube_axis(points):
    """The direction of a round body's axis, pointing up: circles fitted to TUBE_SLICES slices of
    its upper part, where fins and legs do not reach, and the line through their centres."""
    height = points[:, 1]
    low, span = height.min(), np.ptp(height)
    centres = []
    for index in range(TUBE_SLICES):
        start = low + span * (TUBE_FROM + (1 - TUBE_FROM) * index / TUBE_SLICES)
        band = points[(height >= start) & (height < start + span * (1 - TUBE_FROM) / TUBE_SLICES)]
        centre = circle_centre(band[:, [0, 2]])
        centres.append([centre[0], start, centre[1]])
    centres = np.array(centres)
    direction = np.linalg.svd(centres - centres.mean(0))[2][0]
    return direction * np.sign(direction[1])


def squared(points):
    """The turn about up that lays the model's longest side across the ground along Z, so it
    faces along an axis rather than at whatever angle the picture's camera left it."""
    ground = points[:, [0, 2]] - points[:, [0, 2]].mean(0)
    along = np.linalg.svd(ground, full_matrices=False)[2][0]
    angle = np.arctan2(along[0], along[1])
    cosine, sine = np.cos(angle), np.sin(angle)
    return np.array([[cosine, 0.0, -sine], [0.0, 1.0, 0.0], [sine, 0.0, cosine]])


def uv_corners(document, views):
    """The first primitive's UVs, one row per face corner."""
    primitive = document["meshes"][0]["primitives"][0]
    uv = accessor_array(document, views, primitive["attributes"]["TEXCOORD_0"])
    if "indices" not in primitive:
        return uv
    return uv[accessor_array(document, views, primitive["indices"])]


def covered(corners, size):
    """Which texels some UV triangle covers."""
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    for triangle in corners.reshape(-1, 3, 2):
        draw.polygon([(float(u) * size, float(v) * size) for u, v in triangle], fill=255)
    return np.asarray(image) > 0


def nearest_inside(inside):
    """For every texel, the (row, column) of the nearest texel of `inside` after its outer ring
    of EDGE_RING texels is dropped; the ring stays when dropping it would leave nothing."""
    kept = binary_erosion(inside, iterations=EDGE_RING) if EDGE_RING else inside
    kept = kept if kept.any() else inside
    _, (rows, columns) = distance_transform_edt(~kept, return_indices=True)
    return rows, columns


def padded(document, views):
    """Every map with the space outside the UV pieces filled from the nearest piece."""
    corners = uv_corners(document, views)
    sources = {}
    for image in document["images"]:
        picture = Image.open(io.BytesIO(views[image["bufferView"]]))
        size = picture.size[0]
        if size not in sources:
            sources[size] = nearest_inside(covered(corners, size))
        rows, columns = sources[size]
        pixels = np.asarray(picture.convert("RGB"))[rows, columns]
        buffer = io.BytesIO()
        Image.fromarray(pixels).save(buffer, "JPEG", quality=95)
        views[image["bufferView"]] = buffer.getvalue()
        image["mimeType"] = "image/jpeg"
