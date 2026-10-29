"""The sim body stage's layer (layers/sim_bodies.usda): each body's segments, bones and muscles, every frame."""
import numpy as np

from score.stages.sim_body._body import RATE

MUSCLE_WIDTH = 0.006  # metres: a muscle's drawn line
DRAWN = 3  # decimals a drawn muscle point keeps (a millimetre): the layer is text
RESTING, ACTIVE = (0.25, 0.35, 0.85), (0.9, 0.1, 0.1)  # a muscle's colour at activation 0 and 1


def write_layer(path, place, runs, arrays, records):
    """layers/sim_bodies.usda: each body under its character's prim, a guide in the Turned frame: an Xform a SOMA
    segment (its pose every frame) holding the bones of the body it rides, every other bone under Bones (its pose
    every frame), each bone a Mesh; and Muscles, every muscle a line along its path every frame, coloured from RESTING
    to ACTIVE by its activation."""
    from pxr import Gf, Sdf, Usd, UsdGeom, Vt
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    layer.timeCodesPerSecond = layer.framesPerSecond = RATE
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for name, entry in runs.items():
        frames = entry["frames"]
        root = f"/{place}/Characters/{name}/SimBody"
        for prim in (f"/{place}", f"/{place}/Characters", f"/{place}/Characters/{name}"):
            stage.OverridePrim(prim)
        body = UsdGeom.Xform.Define(stage, root)
        UsdGeom.Imageable(body).CreatePurposeAttr(UsdGeom.Tokens.guide)
        body.GetPrim().SetCustomDataByKey("score:mass", records[name]["mass"])
        segments = list(entry["rides"])
        bones, riders = arrays[f"{name}/bones"], arrays[f"{name}/segments"]
        held = {}
        for index, segment in enumerate(segments):
            part = UsdGeom.Xform.Define(stage, f"{root}/{segment}")
            timed(part, riders[:, index])
            held.setdefault(entry["rides"][segment], (f"{root}/{segment}", index))
        UsdGeom.Scope.Define(stage, f"{root}/Bones")
        for number, bone in enumerate(entry["bones"]):
            points = arrays[f"{name}/mesh/{bone}/points"].astype(float)
            if bone in held:  # drawn in the segment riding it, which carries it rigidly
                where, index = held[bone]
                carried = np.linalg.inv(pose_matrix(riders[0, index])) @ pose_matrix(bones[0, number])
                points = points @ carried[:3, :3].T + carried[:3, 3]
            else:
                where = f"{root}/Bones/bone_{bone}"
                timed(UsdGeom.Xform.Define(stage, where), bones[:, number])
            mesh = UsdGeom.Mesh.Define(stage, f"{where}/bone_{bone}")
            mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.round(points, DRAWN + 1).astype(np.float32)))
            faces = arrays[f"{name}/mesh/{bone}/faces"]
            mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(faces)))
            mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(faces.reshape(-1).astype(np.int32)))
            mesh.CreateDisplayColorAttr([Gf.Vec3f(0.89, 0.85, 0.79)])
        muscles = UsdGeom.BasisCurves.Define(stage, f"{root}/Muscles")
        muscles.CreateTypeAttr(UsdGeom.Tokens.linear)
        colours = UsdGeom.PrimvarsAPI(muscles).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray,
                                                             UsdGeom.Tokens.uniform)
        muscles.CreateWidthsAttr(Vt.FloatArray([MUSCLE_WIDTH]))
        muscles.SetWidthsInterpolation(UsdGeom.Tokens.constant)
        counts = arrays[f"{name}/counts"]
        muscles.CreateCurveVertexCountsAttr(Vt.IntArray.FromNumpy(counts.max(axis=0).astype(np.int32)))
        placed = muscles.CreatePointsAttr()
        for code, (frame, points) in enumerate(zip(frames, padded(arrays[f"{name}/paths"], counts))):
            placed.Set(Vt.Vec3fArray.FromNumpy(np.round(points, DRAWN).astype(np.float32)), code)
            shade = np.clip(np.asarray(frame["activations"]), 0.0, 1.0)[:, None]
            colours.Set(Vt.Vec3fArray.FromNumpy(np.round(np.asarray(RESTING) * (1 - shade) + np.asarray(ACTIVE) * shade,
                                                         DRAWN).astype(np.float32)), code)
    layer.Save()


def padded(paths, counts):
    """Each frame's muscle path points (the frames' paths end to end, `counts` frames x muscles), each muscle padded
    to its most points over the frames by repeating its last one, so the drawn lines keep one topology."""
    most, start = counts.max(axis=0), 0
    for row in counts:
        pieces = []
        for count, room in zip(row, most):
            mine = paths[start:start + count]
            pieces.append(np.concatenate([mine, np.repeat(mine[-1:], room - count, axis=0)]))
            start += count
        yield np.concatenate(pieces)


def pose_matrix(pose):
    """A pose [x, y, z, qx, qy, qz, qw] as a 4 x 4."""
    from scipy.spatial.transform import Rotation
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = Rotation.from_quat(np.asarray(pose[3:], dtype=float)).as_matrix(), pose[:3]
    return found


def timed(xform, poses):
    """An Xform's transform set at every frame's pose."""
    from pxr import Gf
    moved = xform.AddTransformOp()
    for code, pose in enumerate(poses):
        moved.Set(Gf.Matrix4d(np.round(pose_matrix(pose).T, 6).tolist()), code)
