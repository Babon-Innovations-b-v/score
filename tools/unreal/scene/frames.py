"""The place's frame in Unreal's (#221): a scene package's points, ways and copies (scene.json, glTF: right-handed,
+y up, -z ahead, metres) as Unreal places them (left-handed, +z up, +x ahead, +y right, centimetres).

How the glTF import turns a mesh is measured, not assumed: the editor imports a box from the origin to (1, 2, 3)
metres (calibration_gltf) and reads its bounds (basis_from_bounds), every turn then made with that BASIS. BASIS here is
the expected one, what a plan written outside Unreal uses: Interchange's glTF import as UE 5.8 measured it (#222, run
8: the box read 1 m along Unreal's x, 3 m along its y, 2 m along its z), glTF's +x Unreal's +x, its +z Unreal's +y,
its up, +y, Unreal's +z (a mirror, as a right-handed frame into a left-handed one must be; glTF's ahead, -z, is then
Unreal's -y). Plain Python with no numpy: Unreal's own Python runs it.
"""
import base64
import json
import math
import struct

CENTIMETRES = 100.0  # Unreal's units a metre
BASIS = ((1, 0, 0), (0, 0, 1), (0, 1, 0))  # row i: Unreal's axis i from a glTF point's (x, y, z)
CALIBRATION = (1.0, 2.0, 3.0)  # metres: the calibration box's far corner, each axis its own length


def turned(basis, way):
    """A glTF way in Unreal's axes (no scale)."""
    return [sum(row[column] * way[column] for column in range(3)) for row in basis]


def point(basis, spot):
    """A glTF point (metres) where Unreal places it (centimetres)."""
    return [value * CENTIMETRES for value in turned(basis, spot)]


def basis_from_bounds(low, high):
    """The import's BASIS read from the calibration box's bounds in Unreal (centimetres): each Unreal axis is the glTF
    axis whose length it spans (CALIBRATION), signed by which side of the origin the box lies on. Refused (ValueError)
    when the bounds are no such box."""
    basis = []
    for axis in range(3):
        span = high[axis] - low[axis]
        found = [index for index, length in enumerate(CALIBRATION) if abs(span - length * CENTIMETRES) < 0.5]
        side = 1 if abs(low[axis]) < 0.5 else -1 if abs(high[axis]) < 0.5 else 0
        if len(found) != 1 or not side:
            raise ValueError(f"the calibration box's bounds {low} .. {high} are not a box of {CALIBRATION} m")
        basis.append(tuple(side if index == found[0] else 0 for index in range(3)))
    if sorted(row.index(next(value for value in row if value)) for row in basis) != [0, 1, 2]:
        raise ValueError(f"the calibration box's bounds {low} .. {high} take one glTF axis twice")
    return tuple(basis)


def column_matrix(matrix):
    """scene.json's `matrix` (16 numbers, column by column, as glTF writes a node's) as rows of the matrix that turns
    a column point."""
    return [[matrix[column * 4 + row] for column in range(4)] for row in range(4)]


def quaternion(rotation):
    """A 3 x 3 turn (rows, turning a column way) as the unit quaternion [x, y, z, w] that turns a way the same, as
    Unreal's FQuat turns one."""
    trace = rotation[0][0] + rotation[1][1] + rotation[2][2]
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2
        found = [(rotation[2][1] - rotation[1][2]) / scale, (rotation[0][2] - rotation[2][0]) / scale,
                 (rotation[1][0] - rotation[0][1]) / scale, 0.25 * scale]
    else:
        axis = max(range(3), key=lambda index: rotation[index][index])
        nxt, last = (axis + 1) % 3, (axis + 2) % 3
        scale = math.sqrt(1.0 + rotation[axis][axis] - rotation[nxt][nxt] - rotation[last][last]) * 2
        found = [0.0, 0.0, 0.0, (rotation[last][nxt] - rotation[nxt][last]) / scale]
        found[axis] = 0.25 * scale
        found[nxt] = (rotation[nxt][axis] + rotation[axis][nxt]) / scale
        found[last] = (rotation[last][axis] + rotation[axis][last]) / scale
    if found[3] < 0:
        found = [-value for value in found]
    return [round(value, 9) + 0.0 for value in found]


def copy_transform(basis, matrix):
    """A copy's scene.json `matrix` (a turn and an even scale, scene_package.copy_frame) as Unreal's transform:
    {location (cm), rotation [x, y, z, w], scale}; the turn B R B^T, so the copy's object, imported through the same
    basis, stands where it was laid."""
    rows = column_matrix(matrix)
    linear = [row[:3] for row in rows[:3]]
    determinant = (linear[0][0] * (linear[1][1] * linear[2][2] - linear[1][2] * linear[2][1])
                   - linear[0][1] * (linear[1][0] * linear[2][2] - linear[1][2] * linear[2][0])
                   + linear[0][2] * (linear[1][0] * linear[2][1] - linear[1][1] * linear[2][0]))
    if determinant <= 0:
        raise ValueError("a copy's matrix is mirrored or flat: scene_package bakes those into their own object")
    scale = determinant ** (1.0 / 3.0)
    rotation = [[value / scale for value in row] for row in linear]
    in_unreal = [[sum(basis[row][inner] * rotation[inner][outer] * basis[column][outer]
                      for inner in range(3) for outer in range(3)) for column in range(3)] for row in range(3)]
    return {"location": [round(value, 6) + 0.0 for value in point(basis, [row[3] for row in rows[:3]])],
            "rotation": quaternion(in_unreal), "scale": round(scale, 9)}


def rotator(ahead, up):
    """Unreal's rotator {roll, pitch, yaw} (degrees) of a thing looking along `ahead` with `up` its top (Unreal's
    axes), as FMatrix::Rotator reads one: yaw and pitch from ahead, roll from where up lies about it."""
    length = math.sqrt(sum(value * value for value in ahead))
    ahead = [value / length for value in ahead]
    yaw = math.atan2(ahead[1], ahead[0])
    pitch = math.atan2(ahead[2], math.hypot(ahead[0], ahead[1]))
    side = [up[1] * ahead[2] - up[2] * ahead[1], up[2] * ahead[0] - up[0] * ahead[2],
            up[0] * ahead[1] - up[1] * ahead[0]]  # Unreal's +y: up x ahead
    top = [ahead[1] * side[2] - ahead[2] * side[1], ahead[2] * side[0] - ahead[0] * side[2],
           ahead[0] * side[1] - ahead[1] * side[0]]  # up made square to ahead: ahead x side
    across = [-math.sin(yaw), math.cos(yaw), 0.0]  # the unrolled rotator's +y
    roll = math.atan2(sum(top[index] * across[index] for index in range(3)),
                      sum(side[index] * across[index] for index in range(3)))
    return {"roll": math.degrees(roll), "pitch": math.degrees(pitch), "yaw": math.degrees(yaw)}


def calibration_gltf():
    """The calibration box as a glTF document (its buffer inline): one mesh, a box from the origin to CALIBRATION
    metres, no material."""
    far = CALIBRATION
    corners = [(x, y, z) for x in (0.0, far[0]) for y in (0.0, far[1]) for z in (0.0, far[2])]
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6),
             (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    data = b"".join(struct.pack("<3f", *corner) for corner in corners) + \
        b"".join(struct.pack("<3H", *face) for face in faces)
    return {"asset": {"version": "2.0", "generator": "SCORE tools/unreal/scene/frames.py"},
            "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "calibration"}],
            "meshes": [{"name": "calibration", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3",
                           "min": [0.0, 0.0, 0.0], "max": list(far)},
                          {"bufferView": 1, "componentType": 5123, "count": 36, "type": "SCALAR"}],
            "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 96},
                            {"buffer": 0, "byteOffset": 96, "byteLength": 72}],
            "buffers": [{"byteLength": len(data),
                         "uri": "data:application/octet-stream;base64," + base64.b64encode(data).decode()}]}


def written_calibration(path):
    """The calibration box's glTF written at `path`; the path."""
    path.write_text(json.dumps(calibration_gltf()))
    return path
