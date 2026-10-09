"""The far city as a place of its own: its towers, the land they stand on, the mountains behind and the harbour
water out to its shore, as one OpenUSD stage that the flat, the street, the square and the launch view each reference
where they stand (their scene record's `places` entry for `far_city`; tools/usd/scene.py write_places).

The owner on the demo (2026-10-09): a picture on the skyline is "cheating"; the far city is made by the framework, in
3D, from its own made towers. Its layout is far_city.py's plan (the same seed lays the same city: hundreds of towers
rows deep along a far shore, the business districts taller, code-built mountains behind); this module stands it up:

    /far_city/Towers      one point instancer: a prototype per tower kind (the kind's made model, converted once by
                          glb_asset.py), an instance per tower of the plan, standing on the land at its spot, turned to
                          face the ring's middle as the plan turns it and scaled to the height the plan deals it
    /far_city/Land        the waterfront's flat land, from the shore back to the mountains' foot
    /far_city/Mountains   the plan's mountain heights on its polar grid
    /far_city/Harbour     the water from the places' own harbour (radius HARBOUR_FROM) out to the shore, so no gap
                          of sky shows under the city; named Harbour, not Water, so a place that shows the city keeps it

    .venv/bin/python tools/usd/far_city_stage.py --seed 7 --out <stages folder> [--models <folder of made towers>]

writes <out>/far_city/far_city.usda (and its assets/), beside the places that reference it as ../../far_city/.
A tower kind's model is <models>/<row>.gltf or .glb (far_city.MODELS by default); a kind with no model yet stops the
stage, since a city of stand-ins would be a placeholder. Frame: EarthSite's metres, the water at height 0, bearings
clockwise from north (-z), as far_city.py.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, Vt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import far_city  # noqa: E402
import glb_asset  # noqa: E402
import scene  # noqa: E402

PLACE = "far_city"
# The place whose library surfaces the city is painted from: the launch view, the harbour it stands across.
STYLE = "prologue_launch"
LAND_SURFACE = "concrete_dark"
MOUNTAIN_SURFACE = "foliage_leaf"
WATER_SURFACE = "harbour_water"
# The places' own harbour reaches 320 m (data/scene/launch.json `harbour`); the city's water starts a little inside it.
HARBOUR_FROM = 300.0
# The land's height over the water, and how far in front of the first row the waterfront starts.
LAND_HIGH = 2.0
LAND_FRONT = 20.0
WATER_HIGH = -0.02


def bearing_point(bearing, reach, height):
    """A point at a bearing (degrees clockwise from north, -z) and a reach from the ring's middle, at a height."""
    turn = math.radians(bearing)
    return (reach * math.sin(turn), height, -reach * math.cos(turn))


def polar_mesh(bearings, reaches, heights, surface):
    """A grid over bearings (columns) and reaches (rows, each row's reach per bearing) as a builders-style mesh."""
    points = np.array([bearing_point(bearing, reaches[row][column], heights[row][column])
                       for row in range(len(reaches)) for column, bearing in enumerate(bearings)], dtype=float)
    columns = len(bearings)
    triangles = []
    for row in range(len(reaches) - 1):
        for column in range(columns - 1):
            here = row * columns + column
            triangles += [[here, here + columns, here + 1], [here + 1, here + columns, here + columns + 1]]
    uvs = points[:, [0, 2]]
    return {"points": points, "triangles": np.array(triangles, dtype=np.int64), "uvs": uvs, "surface": surface}


def land_mesh(city):
    """The waterfront's land: from just in front of the shore back to where the mountains rise, flat at LAND_HIGH."""
    hills = city["mountains"]
    shore = hills["shore"]
    back = hills["reaches"][0]
    reaches = [[edge - LAND_FRONT for edge in shore], [edge + back for edge in shore]]
    heights = [[LAND_HIGH] * len(shore)] * 2
    return polar_mesh(hills["bearings"], reaches, heights, LAND_SURFACE)


def mountain_mesh(city):
    """The plan's mountains: its heights on its polar grid, each row's reach behind that bearing's shore."""
    hills = city["mountains"]
    reaches = [[edge + reach for edge in hills["shore"]] for reach in hills["reaches"]]
    heights = [[max(LAND_HIGH, height) for height in row] for row in hills["heights"]]
    return polar_mesh(hills["bearings"], reaches, heights, MOUNTAIN_SURFACE)


def harbour_mesh(city):
    """The water from HARBOUR_FROM out to under the land's front edge, over the city's bearings."""
    hills = city["mountains"]
    reaches = [[HARBOUR_FROM] * len(hills["shore"]), [edge - LAND_FRONT + 5.0 for edge in hills["shore"]]]
    heights = [[WATER_HIGH] * len(hills["shore"])] * 2
    return polar_mesh(hills["bearings"], reaches, heights, WATER_SURFACE)


def model_file(models, row):
    """A tower kind's made model in the models folder."""
    for suffix in (".gltf", ".glb"):
        found = pathlib.Path(models) / f"{row}{suffix}"
        if found.exists():
            return found
    raise SystemExit(f"{row}: no made model in {models}; the far city waits for its tower kinds' models")


def tower_turn(facing):
    """A tower's turn about up so its front (+z, the kit frame's) looks along the plan's bearing `facing`."""
    angle = math.radians(180.0 - facing)
    return Gf.Quath(math.cos(angle / 2.0), Gf.Vec3h(0.0, math.sin(angle / 2.0), 0.0))


def write_towers(stage, city, models, out):
    """The towers as one point instancer, a prototype per kind; {kind: count}."""
    instancer = UsdGeom.PointInstancer.Define(stage, f"/{PLACE}/Towers")
    kinds = sorted({tower["kind"] for tower in city["towers"]})
    boxes = {}
    for kind in kinds:
        prototype = UsdGeom.Xform.Define(stage, f"/{PLACE}/Towers/Prototypes/{kind}")
        boxes[kind] = glb_asset.asset(model_file(models, kind), out / "assets" / f"{kind}.usdc", out / "assets/textures")
        prototype.GetPrim().GetReferences().AddReference(f"./assets/{kind}.usdc")
        instancer.GetPrototypesRel().AddTarget(prototype.GetPath())
    indices, positions, turns, scales = [], [], [], []
    for tower in city["towers"]:
        low, high = (np.asarray(corner, dtype=float) for corner in boxes[tower["kind"]])
        scale = float(tower["height"]) / float(high[1] - low[1])
        x, z = tower["at"]
        indices.append(kinds.index(tower["kind"]))
        positions.append(Gf.Vec3f(float(x), float(LAND_HIGH - low[1] * scale), float(z)))
        turns.append(tower_turn(float(tower["facing"])))
        scales.append(Gf.Vec3f(scale, scale, scale))
    instancer.CreateProtoIndicesAttr(Vt.IntArray(indices))
    instancer.CreatePositionsAttr(Vt.Vec3fArray(positions))
    instancer.CreateOrientationsAttr(Vt.QuathArray(turns))
    instancer.CreateScalesAttr(Vt.Vec3fArray(scales))
    return {kind: indices.count(number) for number, kind in enumerate(kinds)}


def write_ground(stage, city):
    """The land, the mountains and the harbour, each a mesh painted with its library surface."""
    for name, built, kind in (("Land", land_mesh(city), "ground"), ("Mountains", mountain_mesh(city), "ground"),
                              ("Harbour", harbour_mesh(city), "water")):
        prim = scene.mesh_prim(stage, f"/{PLACE}/{name}", built)
        scene.bind_surface(stage, prim, PLACE, built["surface"])
        for key, value in (("score:kind", kind), ("score:plain", kind),
                           ("score:from", "tools/usd/far_city.py's plan of the far shore and its mountains")):
            prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def write_stage(city, models, out):
    """The far city's stage at <out>/far_city/far_city.usda; its path and the towers laid of each kind."""
    folder = pathlib.Path(out) / PLACE
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{PLACE}.usda"
    layer = Sdf.Layer.FindOrOpen(str(path)) or Sdf.Layer.CreateNew(str(path))
    layer.Clear()
    stage = Usd.Stage.Open(layer)
    root = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    Usd.ModelAPI(root).SetKind(Kind.Tokens.assembly)
    UsdGeom.Scope.Define(stage, f"/{PLACE}/Library")
    export.library_materials(stage, STYLE, f"/{PLACE}")
    counts = write_towers(stage, city, models, folder)
    write_ground(stage, city)
    for key, value in (("score:kind", "place"), ("score:seed", str(city["seed"])),
                       ("score:from", "tools/usd/far_city.py plan (seeded), tools/usd/far_city_stage.py")):
        root.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    layer.defaultPrim = PLACE
    layer.pseudoRoot.SetInfo("upAxis", UsdGeom.Tokens.y)
    layer.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    layer.Save()
    return path, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--models", type=pathlib.Path, default=far_city.MODELS)
    arguments = parser.parse_args()
    path, counts = write_stage(far_city.plan(arguments.seed), arguments.models, arguments.out)
    print(f"{path}: {sum(counts.values())} towers ({json.dumps(counts)})")


if __name__ == "__main__":
    main()
