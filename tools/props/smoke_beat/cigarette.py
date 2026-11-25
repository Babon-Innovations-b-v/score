"""The cigarette the 2099 prologue's player smokes on the balcony (#152), built in code as a score_lib model: one closed
round solid at a king size cigarette's measures, its parts (GeomSubsets) the filter, the paper, the ember (the
glowing burn line) and the ash (the grey cap of the lit end), each finished by a library surface (FINISHES: a recipe
entry of score_lib in a colour, its roughness and glow the recipe's own from data/library/materials.json), bound to a
look named after the part and marked with the surface's address (`score:surface`, `score:surface:colour`).

    .venv/bin/python tools/props/smoke_beat/cigarette.py <out folder>

Writes <out>/cigarette.usdc (y up, metres, its default prim /cigarette: the mouth end at the origin, the lit end
LENGTH along +z, its middle on the z axis), <out>/cigarette.glb (the same solid for a game engine, one mesh and
material per part, each named after the part, its factors the finish's, smooth round sides) and <out>/cigarette.json
(its measures, finishes and their sources).

The measures (eastern-tobacco.com's cigarette sizes guide, read 2026-11-20: "the standard king size cigarette length
mm sits at 84 millimetres", "approximately 7.8 to 8 millimetres" across, "the filter length typically accounts for 20
to 27 millimetres"): 84 mm long, 7.9 mm across (the middle of 7.8 to 8), the filter 23.5 mm (the middle of 20 to 27).
The lit end's 4 mm (a 1.5 mm glowing burn line under a 2.5 mm ash cap) and the finishes' colours are this builder's
own choices: no source here measures a burning coal's depth or a cigarette's colours.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

REPO = pathlib.Path(__file__).resolve().parents[3]

LENGTH = 0.084
DIAMETER = 0.0079
FILTER = 0.0235
EMBER = 0.0015
ASH = 0.0025
PARTS = ("filter", "paper", "ember", "ash")
# Each part's library surface and colour (the builder's own reading of a lit king size cigarette): the filter's cork
# tipping paper, the white paper, the burn line's glowing coal, the grey ash.
FINISHES = {"filter": ("surface/printed", "#c48a52"), "paper": ("surface/printed", "#f1efe8"),
            "ember": ("surface/glowing", "#ff5a1a"), "ash": ("surface/printed", "#8e8b86")}
SIDES = 32  # round to within 0.02 mm of a true circle at this diameter
SOURCE = "https://eastern-tobacco.com/cigarette-sizes-and-dimensions-complete-format-guide/ (read 2026-11-20)"


def rings():
    """The heights along z where the side's rings stand: the mouth end, the filter's end, the burn line, the ash's
    start, the tip."""
    return [0.0, FILTER, LENGTH - ASH - EMBER, LENGTH - ASH, LENGTH]


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
    for ring, part in enumerate(PARTS):
        for side in range(SIDES):
            here, there = ring * SIDES + side, ring * SIDES + (side + 1) % SIDES
            triangles += [[here, there, there + SIDES], [here, there + SIDES, here + SIDES]]
            parts += [part, part]
    last = (len(heights) - 1) * SIDES
    for side in range(SIDES):
        triangles.append([mouth, (side + 1) % SIDES, side])
        parts.append("filter")
        triangles.append([tip, last + side, last + (side + 1) % SIDES])
        parts.append("ash")
    return points, np.array(triangles), parts


def linear(hex_colour):
    """'#rrggbb' as linear RGB (a look's colour is linear)."""
    srgb = [int(hex_colour[index:index + 2], 16) / 255.0 for index in (1, 3, 5)]
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in srgb]


def finish(part):
    """A part's finish: {surface, colour (hex), linear, roughness, glow (linear, given off)}, its roughness and glow its
    recipe's own (data/library/materials.json), its colour FINISHES'."""
    address, colour = FINISHES[part]
    recipe = json.loads((REPO / "data/library/materials.json").read_text())["recipes"][address.split("/", 1)[1]]
    shade = linear(colour)
    glow = [value * float(recipe.get("glow", 0.0)) for value in shade]
    return {"surface": address, "colour": colour, "linear": shade, "roughness": float(recipe["roughness"]),
            "glow": glow}


def look(stage, part):
    """The part's look at /cigarette/Looks/<part>: a UsdPreviewSurface in its finish, marked with its surface."""
    found = finish(part)
    material = UsdShade.Material.Define(stage, f"/cigarette/Looks/{part}")
    material.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(found["surface"])
    material.GetPrim().CreateAttribute("score:surface:colour", Sdf.ValueTypeNames.String).Set(found["colour"])
    shader = UsdShade.Shader.Define(stage, f"/cigarette/Looks/{part}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*found["linear"]))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(found["roughness"])
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*found["glow"]))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def usd_written(path):
    """The solid as USD at `path`: one mesh, a GeomSubset a part, each bound to its look."""
    points, triangles, parts = solid()
    stage = Usd.Stage.CreateNew(str(path))
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
    for part in PARTS:
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, part, UsdGeom.Tokens.face,
                                                 Vt.IntArray([int(face) for face in np.flatnonzero(names == part)]),
                                                 "materialBind", UsdGeom.Tokens.nonOverlapping)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(look(stage, part))
    stage.Save()


def part_mesh(points, triangles, part):
    """One side band or end cap of a part as its own trimesh in the part's finish, its vertices its own: a band's
    normals run out from the axis (a smooth round side), a cap's along it (out of the end it closes)."""
    import trimesh
    used = np.unique(triangles)
    remap = np.full(len(points), -1)
    remap[used] = np.arange(len(used))
    corners = points[used]
    if np.ptp(corners[:, 2]) < 1e-12:
        normals = np.tile([0.0, 0.0, -1.0 if corners[0, 2] < LENGTH / 2.0 else 1.0], (len(corners), 1))
    else:
        normals = np.column_stack([corners[:, 0], corners[:, 1], np.zeros(len(corners))])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
    found = finish(part)
    glow = max(found["glow"] + [0.0])
    material = trimesh.visual.material.PBRMaterial(
        name=part, baseColorFactor=[*found["linear"], 1.0], roughnessFactor=found["roughness"], metallicFactor=0.0,
        emissiveFactor=[value / glow for value in found["glow"]] if glow > 0 else None)
    return trimesh.Trimesh(corners, remap[triangles], vertex_normals=normals, process=False,
                           visual=trimesh.visual.TextureVisuals(material=material))


def glb_written(path):
    """The solid as a GLB at `path`: a mesh and material a part, each named after it. A part's caps and sides keep
    vertices of their own (a cap meets no side within one part but the filter's mouth and the ash's tip)."""
    import trimesh
    points, triangles, parts = solid()
    names = np.array(parts)
    scene = trimesh.Scene()
    for part in PARTS:
        chosen = triangles[names == part]
        pieces = [part_mesh(points, chosen[mask], part) for mask in band_and_cap(points, chosen)]
        scene.add_geometry(trimesh.util.concatenate(pieces) if len(pieces) > 1 else pieces[0], node_name=part,
                           geom_name=part)
    path.write_bytes(scene.export(file_type="glb", include_normals=True))


def band_and_cap(points, triangles):
    """A part's triangles split into its side band and its end cap (a cap's triangles lie level): the masks of each
    that holds any."""
    heights = points[triangles][:, :, 2]
    level = np.ptp(heights, axis=1) < 1e-12
    return [mask for mask in (~level, level) if mask.any()]


def written(out):
    """The cigarette's USD, GLB and record written into `out`; the USD's path."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    usd_written(out / "cigarette.usdc")
    glb_written(out / "cigarette.glb")
    record = {"length_m": LENGTH, "diameter_m": DIAMETER, "filter_m": FILTER, "ember_m": EMBER, "ash_m": ASH,
              "source": SOURCE, "frame": "y up, metres: the mouth end at the origin, the lit end along +z",
              "parts": {"filter": "the filter's cork tipping paper", "paper": "the white paper over the tobacco",
                        "ember": "the glowing burn line", "ash": "the grey ash capping the lit end"},
              "finishes": {part: {key: finish(part)[key] for key in ("surface", "colour", "roughness")}
                           for part in PARTS},
              "lit_end_source": "this builder's own choice: no source here measures a burning coal's depth",
              "colour_source": "this builder's own reading of a lit king size cigarette"}
    (out / "cigarette.json").write_text(json.dumps(record, indent=1) + "\n")
    return out / "cigarette.usdc"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out")
    print(json.dumps({"usd": str(written(parser.parse_args().out))}))


if __name__ == "__main__":
    main()
