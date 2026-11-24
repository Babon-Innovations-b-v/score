"""A groom written as USD BasisCurves by our own code (#227, PRD #223): Blender's own USD exporter of hair was not
trusted to carry widths and colour (the deep dive on #56), so the strands groom.py saved are written here.

    python basis_curves.py <groom out folder> <groom.usda> [--frames bind,0,7,14,21] [--fps 30]

- One `BasisCurves` prim, `/Groom/Hair`, linear (each strand a polyline, as Unreal's groom reads it), Z up, metres:
  its `curveVertexCounts`, `points`, `widths` (per point, twice the radius), `displayColor` (the hair's colour,
  constant: the library surface's linear colour) and two primvars per strand named as Unreal's groom Alembic schema
  names them, so the Alembic writer of the next slice maps them one to one: `groom_root_uv` (the root's place in the
  body's UV map, by which Unreal binds a groom to its skeletal mesh as Deform Curves on Surface does in Blender) and
  `groom_guide` (1 for a combed guide, 0 for a grown child). The rest of that schema (`groom_group_id`,
  `groom_closest_guides`, `groom_guide_weights`, `groom_id`) and Unreal's centimetre, Y-up import settings are the
  next slice's.
- The bind is `points`' default value (the groom as it is bound); each clip frame named is a time sample at its
  frame number (`timeCodesPerSecond` the clip's fps), so the file shows the strands following the clip.
- Every frame must hold the same strands: a count, guide flag or root UV that differs refuses the file by name.
"""
import argparse
import json
import pathlib

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt


def checked(frames):
    """The frames' strands, refused when one frame's strands are not the first's or a frame's arrays disagree."""
    first = frames[0][1]
    for name, strands in frames:
        counts, points = strands["counts"], strands["points"]
        if int(counts.sum()) != len(points) or len(strands["radius"]) != len(points):
            raise ValueError(f"frame {name}: {int(counts.sum())} points by count, {len(points)} points, "
                             f"{len(strands['radius'])} radii")
        if len(strands["root_uv"]) != len(counts) or len(strands["guide"]) != len(counts):
            raise ValueError(f"frame {name}: {len(counts)} strands, {len(strands['root_uv'])} root uvs, "
                             f"{len(strands['guide'])} guide flags")
        for key in ("counts", "guide", "root_uv"):
            if not np.array_equal(strands[key], first[key]):
                raise ValueError(f"frame {name}: its {key} is not the first frame's: not the same strands")
    return frames


def written(path, frames, colour, fps):
    """The groom at `path`: `frames` [(name, time or None, strands)], the first one's arrays the prim's own."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.SetTimeCodesPerSecond(fps)
    root = UsdGeom.Xform.Define(stage, "/Groom")
    stage.SetDefaultPrim(root.GetPrim())
    hair = UsdGeom.BasisCurves.Define(stage, "/Groom/Hair")
    hair.CreateTypeAttr(UsdGeom.Tokens.linear)
    first = frames[0][2]
    hair.CreateCurveVertexCountsAttr(Vt.IntArray.FromNumpy(first["counts"].astype(np.int32)))
    hair.CreateWidthsAttr(Vt.FloatArray.FromNumpy((2 * first["radius"]).astype(np.float32)))
    hair.SetWidthsInterpolation(UsdGeom.Tokens.vertex)
    hair.CreateDisplayColorPrimvar(UsdGeom.Tokens.constant).Set(Vt.Vec3fArray([Gf.Vec3f(*map(float, colour))]))
    api = UsdGeom.PrimvarsAPI(hair)
    api.CreatePrimvar("groom_root_uv", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.uniform).Set(
        Vt.Vec2fArray.FromNumpy(first["root_uv"].astype(np.float32)))
    api.CreatePrimvar("groom_guide", Sdf.ValueTypeNames.IntArray, UsdGeom.Tokens.uniform).Set(
        Vt.IntArray.FromNumpy(first["guide"].astype(np.int32)))
    points = hair.CreatePointsAttr()
    extent = hair.CreateExtentAttr()
    for _, time, strands in frames:
        at = Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)
        place = strands["points"].astype(np.float32)
        points.Set(Vt.Vec3fArray.FromNumpy(place), at)
        extent.Set(Vt.Vec3fArray.FromNumpy(np.stack([place.min(0), place.max(0)])), at)
    stage.GetRootLayer().Save()
    return path


def timed(names):
    """Each frame name with its time code: the bind the default (untimed) value, a clip frame its number."""
    return [(name, None if name == "bind" else float(name)) for name in names]


def frame_file(groom, name):
    return groom / "frames" / ("bind.npz" if name == "bind" else f"{int(name):03d}.npz")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("groom", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--frames", default="bind")
    parser.add_argument("--fps", type=float, default=30.0)
    given = parser.parse_args()
    colour = json.loads((given.groom / "measures.json").read_text())["colour_linear"]
    names = given.frames.split(",")
    loaded = checked([(name, dict(np.load(frame_file(given.groom, name)))) for name in names])
    frames = [(name, time, strands) for (name, time), (_, strands) in zip(timed(names), loaded)]
    written(given.out, frames, colour, given.fps)
    print(f"basis curves: {len(frames[0][2]['counts'])} strands, {len(frames[0][2]['points'])} points, "
          f"{len(frames)} frames -> {given.out}")


if __name__ == "__main__":
    main()
