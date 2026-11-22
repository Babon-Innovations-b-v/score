"""The cigarette the 2099 prologue's player smokes on the balcony (#152), built in code as a score_lib model: one closed
round solid at a king size cigarette's measures, its parts (GeomSubsets) the filter, the paper and the lit end, each
for a library surface laid on it at the place (`surface --part`, the lit end a glowing palette variant), each bound to
a placeholder material named after it so any USD reader splits them; no colour of its own.

    .venv/bin/python tools/props/smoke_beat/cigarette.py <out folder>

Writes <out>/cigarette.usdc (y up, metres, its default prim /cigarette: the mouth end at the origin, the lit end
LENGTH along +z, its middle on the z axis) and <out>/cigarette.json (its measures and their sources).

The measures (eastern-tobacco.com's cigarette sizes guide, read 2026-11-20: "the standard king size cigarette length
mm sits at 84 millimetres", "approximately 7.8 to 8 millimetres" across, "the filter length typically accounts for 20
to 27 millimetres"): 84 mm long, 7.9 mm across (the middle of 7.8 to 8), the filter 23.5 mm (the middle of 20 to 27).
The lit end's 2 mm is this builder's own choice: no source here measures a burning coal's depth.
"""
import argparse
import json
import math
import pathlib

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdShade, Vt

LENGTH = 0.084
DIAMETER = 0.0079
FILTER = 0.0235
EMBER = 0.002
SIDES = 32  # round to within 0.02 mm of a true circle at this diameter
SOURCE = "https://eastern-tobacco.com/cigarette-sizes-and-dimensions-complete-format-guide/ (read 2026-11-20)"


def rings():
    """The heights along z where the side's rings stand: the mouth end, the filter's end, the lit end's start, the tip."""
    return [0.0, FILTER, LENGTH - EMBER, LENGTH]


def solid():
    """The closed round solid: (points (n x 3), triangles (m x 3), each triangle's part name)."""
    radius = DIAMETER / 2.0
    turns = np.linspace(0.0, 2.0 * math.pi, SIDES, endpoint=False)
    circle = np.column_stack([np.cos(turns) * radius, np.sin(turns) * radius])
    heights = rings()
    points = [np.column_stack([circle, np.full(SIDES, height)]) for height in heights]
    points.append([[0.0, 0.0, 0.0], [0.0, 0.0, LENGTH]])
    points = np.vstack(points)
    mouth, tip = len(heights) * SIDES, len(heights) * SIDES + 1
    triangles, parts = [], []
    side_parts = ("filter", "paper", "ember")
    for ring, part in enumerate(side_parts):
        for side in range(SIDES):
            here, there = ring * SIDES + side, ring * SIDES + (side + 1) % SIDES
            triangles += [[here, there, there + SIDES], [here, there + SIDES, here + SIDES]]
            parts += [part, part]
    last = (len(heights) - 1) * SIDES
    for side in range(SIDES):
        triangles.append([mouth, (side + 1) % SIDES, side])
        parts.append("filter")
        triangles.append([tip, last + side, last + (side + 1) % SIDES])
        parts.append("ember")
    return points, np.array(triangles), parts


def written(out):
    """The cigarette's USD and record written into `out`; the USD's path."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    points, triangles, parts = solid()
    stage = Usd.Stage.CreateNew(str(out / "cigarette.usdc"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/cigarette")
    stage.SetDefaultPrim(root.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, "/cigarette/cigarette")
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, point)) for point in points]))
    mesh.CreateFaceVertexCountsAttr([3] * len(triangles))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray([int(index) for index in triangles.ravel()]))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr(UsdGeom.Boundable.ComputeExtentFromPlugins(mesh, Usd.TimeCode.Default()))
    names = np.array(parts)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    for part in ("filter", "paper", "ember"):
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, part, UsdGeom.Tokens.face,
                                                 Vt.IntArray([int(face) for face in np.flatnonzero(names == part)]),
                                                 "materialBind", UsdGeom.Tokens.nonOverlapping)
        # A placeholder material named after the part (no shader, no colour), so any USD reader splits the parts
        # (score #156); the place lays its library surface over it.
        placeholder = UsdShade.Material.Define(stage, f"/cigarette/Looks/{part}")
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(placeholder)
    stage.Save()
    record = {"length_m": LENGTH, "diameter_m": DIAMETER, "filter_m": FILTER, "ember_m": EMBER, "source": SOURCE,
              "frame": "y up, metres: the mouth end at the origin, the lit end along +z",
              "parts": {"filter": "the filter's tipping paper", "paper": "the white paper over the tobacco",
                        "ember": "the lit end (a glowing palette variant)"},
              "ember_source": "this builder's own choice: no source here measures a burning coal's depth"}
    (out / "cigarette.json").write_text(json.dumps(record, indent=1) + "\n")
    return out / "cigarette.usdc"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out")
    print(json.dumps({"usd": str(written(parser.parse_args().out))}))


if __name__ == "__main__":
    main()
