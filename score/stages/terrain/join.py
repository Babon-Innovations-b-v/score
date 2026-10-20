"""ground-join@<place> (#27, #41; the terrain adapter's one after-step in the shared loop, shapes_first.ADAPTERS; free,
local, pxr and ray casts): a place's detail areas, each a model the shared loop made (the terrain-layer rows the place
handed it, areas.py; close-up, Pixal3D, the finish route, the bake), joined into its made ground. The plan's code ground
(the terrain row's) stays only where the loop made no piece: the named fallback, each with the loop's own why.

    make     the terrain row's layer of the place's ground (<ground>/places/<place>.usdc) copied, and for each terrain
             row the loop made a model of (made.made: its baked model; a gap or the code route is left to the code
             ground, named):
             cut       the code ground's faces wholly within CUT_SHARE of the piece's half size round its middle taken
                       out, so the ring left under its rim overlaps it and no gap opens at the seam
             seat      the piece (its baked mesh, in metres, foot on its origin) stood at its row's middle, let down
                       until its rim (its points past RIM_SHARE of its half size) lies nowhere over the code ground
             finish    each face its library surface from its paint's labelled parts (export.face_surfaces), bound to
                       that surface's look in its design token's colour (outside.look, as the ground's own zones)
             collide   the piece's own mesh its collider (UsdPhysics, no convex hull: a crater is walked inside)
             under /<place>/Outside/Detail/<row>, its row and kind written (score:row, score:kind ground);
             join.json: each piece's lift and cut faces, and each row left to the code ground with why
    gate     seam   a ray straight down at every SEAM_STEP metres round each piece's seam ring (between its cut and
                    its box) finds a surface: the joined ground has no gap there; it names the rows left to the code
                    ground (measured, never a fault: the fallback is named, the line goes on)

The output holds the layer where the terrain row's does (`<ground>/places/<place>.usdc`), so the assembly takes it in
place of the terrain row's (the table's `joined_ground`), and ground-fit judges the whole ground on the assembly.
"""
import json
import pathlib
import shutil
import sys

import numpy as np
from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt

from score import checks, contracts
from score.stages.terrain import gates, outside, record, sight
import score.stages.shapes_first.made as made

REPO = pathlib.Path(__file__).resolve().parents[3]
JOIN = "join.json"
# The code ground is cut under a piece within this share of its half size; the ring past it, out to the piece's box,
# lies under the piece's rim.
CUT_SHARE = 0.8
# A piece's rim: its points past this share of its half size across or along.
RIM_SHARE = 0.9
# The seam is sampled this many metres apart round its ring.
SEAM_STEP = 0.5
OVER = 50.0  # a ray down starts this far over a seam spot
NOT_GROUND = ("water", "ball", "Detail")  # what under /<place>/Outside is no code ground to cut
LAYER = "terrain"  # areas.LAYER: the rows this after-step joins


def files(place):
    """The place's inventory (its detail area rows), and the library and design tokens the looks are coloured from."""
    return {"inventory": "{data}/inventory/" + f"{place}.json", "library": "{data}/library/materials.json",
            "tokens": "{data}/../design/tokens/tokens.json"}


def place_layer(terrain, place, out):
    """The terrain row's layer of the place's ground copied into the output where it lay; its path."""
    found = sorted(pathlib.Path(terrain).glob(f"*/places/{place}.usdc"))
    if not found:
        raise FileNotFoundError(f"the terrain row made no ground layer for {place}")
    target = out / found[0].relative_to(terrain)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(found[0], target)
    return target


def ground_meshes(stage, place):
    """The code ground's meshes under /<place>/Outside."""
    root = stage.GetPrimAtPath(f"/{place}/Outside")
    return [UsdGeom.Mesh(prim) for prim in root.GetChildren()
            if prim.IsA(UsdGeom.Mesh) and prim.GetName() not in NOT_GROUND]


def inside_cut(points, middle, half):
    """Which points lie within CUT_SHARE of a piece's half size round its middle (across and along)."""
    return np.all(np.abs(points[:, [0, 2]] - middle) <= CUT_SHARE * half, axis=1)


def cut_mesh(mesh, middle, half):
    """Take out the mesh's triangles wholly within the cut, its subsets' faces renumbered; how many were cut."""
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3)
    cut = inside_cut(points, middle, half)[triangles].all(axis=1)
    if not cut.any():
        return 0
    renumbered = np.cumsum(~cut) - 1
    mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray.FromNumpy(np.full(int((~cut).sum()), 3, dtype=np.int32)))
    mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray.FromNumpy(triangles[~cut].reshape(-1).astype(np.int32)))
    for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):
        faces = np.asarray(subset.GetIndicesAttr().Get(), dtype=np.int64)
        subset.GetIndicesAttr().Set(Vt.IntArray.FromNumpy(renumbered[faces[~cut[faces]]].astype(np.int32)))
    return int(cut.sum())


def export_tools():
    """tools/usd/export.py and the assembly's bake helpers (the assembly's import puts tools/usd on the path)."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import export
    from score.stages.assembly import baked
    return export, baked


def piece_geometry(model, paint):
    """A baked piece's mesh (export.model_geometry, metres, foot on its origin; `model` the loop's baked .gltf) and
    each face's library surface from its paint's labelled parts."""
    export, baked = export_tools()
    model = pathlib.Path(model)
    entry = json.loads((model.parent.parent / "baked.json").read_text())[model.stem]
    geometry = export.model_geometry(model)
    labelled, turn, size = baked.laid_parts(model.parent, model.stem, paint / "labelled" / entry["parts"], entry)
    points, names = export.part_points(labelled, turn, size)
    return geometry, export.face_surfaces(geometry, points, names)


def rim(positions, half):
    """The piece's rim points: past RIM_SHARE of its half size across or along its own middle."""
    middle = (positions[:, [0, 2]].max(axis=0) + positions[:, [0, 2]].min(axis=0)) / 2
    return np.any(np.abs(positions[:, [0, 2]] - middle) >= RIM_SHARE * half, axis=1)


def seated(positions, middle, half, rays):
    """The piece's points stood on its row's middle (across, along) and let down until no rim point lies over the code
    ground (`rays` over it); (points, the lift given)."""
    own = (positions[:, [0, 2]].max(axis=0) + positions[:, [0, 2]].min(axis=0)) / 2
    placed = positions + np.array([middle[0] - own[0], 0.0, middle[1] - own[1]])
    edge = placed[rim(placed, half)]
    under = edge[:, 1] + OVER - gates.drops(rays, edge + [0.0, OVER, 0.0], [0.0, -1.0, 0.0])
    reached = np.isfinite(under)
    lift = float(np.min(under[reached] - edge[reached, 1])) if reached.any() else 0.0
    return placed + [0.0, lift, 0.0], lift


def write_piece(stage, place, row_id, points, triangles, surfaces, looks):
    """The piece's mesh under /<place>/Outside/Detail/<row>: a subset a library surface bound to its look, its own
    mesh its collider."""
    mesh = outside.write_mesh(stage, f"/{place}/Outside/Detail/{row_id}", points, triangles, "ground")
    mesh.GetPrim().CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(row_id)
    for surface in sorted(set(surfaces)):
        subset = UsdGeom.Subset.Define(stage, f"{mesh.GetPath()}/{surface}")
        subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
        subset.CreateFamilyNameAttr(UsdShade.Tokens.materialBind)
        subset.CreateIndicesAttr(Vt.IntArray.FromNumpy(np.nonzero(surfaces == surface)[0].astype(np.int32)))
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(looks[surface])
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr(UsdPhysics.Tokens.none)


def piece_looks(stage, place, surfaces, inputs):
    """{surface: its look under /<place>/Outside/Looks}, the ground's own where it has one."""
    colours = record.surface_colours(sorted(surfaces), inputs["library"], inputs["tokens"])
    return {surface: outside.look(stage, f"/{place}/Outside/Looks/{surface}", surface, colour)
            for surface, colour in colours.items()}


def left_why(result):
    """Why the loop's result for a row leaves it to the code ground: its gap, its pipeline failure, or no model file."""
    if "gap" in result:
        return result["gap"]
    if result["route"] == "code":
        return f"its pipeline failed and it went the code route ({result['model']}): the plan's code ground stays"
    return f"the bake wrote no model file for it ({result['model']})"


def made_pieces(inputs, inventory):
    """({row: why it is left to the code ground}, [(inventory row, its baked model)]) of the terrain rows the place
    handed the loop (made.made)."""
    rows = {row["id"]: row for row in inventory["rows"]}
    left, pieces = {}, []
    for row_id, result in made.made(inputs, LAYER).items():
        if result.get("route") == "prop" and pathlib.Path(result["model"]).exists():
            pieces.append((rows[row_id], result["model"]))
        else:
            left[row_id] = left_why(result)
    return left, pieces


def make(inputs, out, seed, params):
    """The place's ground layer with its made detail pieces joined in, and join.json."""
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    place = pathlib.Path(inputs["inventory"]).stem  # the file's own name (its `place` is the library's: the camp's)
    layer = place_layer(inputs["terrain"], place, out)
    stage = Usd.Stage.Open(str(layer))
    left, pieces = made_pieces(inputs, inventory)
    rays = gates.caster(sight.gathered(stage))
    found = {}
    shaped = {row["id"]: piece_geometry(model, pathlib.Path(inputs["surfaces-paint"])) for row, model in pieces}
    looks = piece_looks(stage, place, {surface for _, surfaces in shaped.values() for surface in surfaces}, inputs) \
        if pieces else {}
    for row, _ in pieces:
        geometry, surfaces = shaped[row["id"]]
        half = np.array([row["size"][0], row["size"][1]]) / 2  # the row's across and along (areas.inventory_rows)
        middle = np.array([row["at"][0]["x"], row["at"][0]["z"]])
        points, lift = seated(np.asarray(geometry["positions"], dtype=float), middle, half, rays)
        cut = sum(cut_mesh(mesh, middle, half) for mesh in ground_meshes(stage, place))
        write_piece(stage, place, row["id"], points, np.asarray(geometry["triangles"]), surfaces, looks)
        found[row["id"]] = {"lift": round(lift, 3), "cut faces": cut, "middle": middle.tolist(),
                            "half": half.round(3).tolist()}
    stage.GetRootLayer().Save()
    (out / JOIN).write_text(json.dumps({"place": place, "pieces": found, "code ground": left}, indent=1))


def join_faults(folder):
    return [] if (folder / JOIN).exists() and list(folder.glob("*/places/*.usdc")) else [f"no {JOIN} or no layer"]


def seam_spots(middle, half):
    """Spots SEAM_STEP apart on the ring between a piece's cut and its box, at the ring's middle."""
    reach = half * (1.0 + CUT_SHARE) / 2
    steps = max(int(np.ceil(2 * reach.max() / SEAM_STEP)), 2)
    line = np.linspace(-1.0, 1.0, steps)
    ring = np.concatenate([np.column_stack([line * reach[0], np.full(steps, side * reach[1])]) for side in (-1, 1)] +
                          [np.column_stack([np.full(steps, side * reach[0]), line * reach[1]]) for side in (-1, 1)])
    return ring + middle


def judge_seam(output, inputs, evidence):
    """Every seam spot of every piece has a surface under it; the rows left to the code ground named."""
    joined = json.loads((output / JOIN).read_text())
    place = joined["place"]
    stage = Usd.Stage.Open(str(next(output.glob(f"*/places/{place}.usdc"))))
    rays = gates.caster(sight.gathered(stage))
    gaps = []
    for row, piece in joined["pieces"].items():
        spots = seam_spots(np.asarray(piece["middle"]), np.asarray(piece["half"]))
        origins = np.column_stack([spots[:, 0], np.full(len(spots), OVER), spots[:, 1]])
        gaps += [f"{row}: no ground at ({spot[0]:.1f}, {spot[1]:.1f})"
                 for spot, drop in zip(spots, gates.drops(rays, origins, [0.0, -1.0, 0.0])) if not np.isfinite(drop)]
    left = joined["code ground"]
    reason = (f"{len(joined['pieces'])} pieces joined, no gap at a seam" if not gaps else
              f"{len(gaps)} seam spots with no ground: " + "; ".join(gaps[:3])) + \
        (f"; {len(left)} areas left to the code ground: " + ", ".join(f"{row} ({why})" for row, why in left.items())
         if left else "")
    return checks.Verdict("seam", checks.FAIL if gaps else checks.PASS, reason,
                          {"gaps": len(gaps), "joined": len(joined["pieces"]), "code ground": len(left)},
                          {"gaps": "lower"}, tuple(gaps))


CONTRACT = contracts.Contract("ground-join", 1, join_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("seam", judge_seam),)
AFTER = {"terrain": ("grounds", 1), **made.ENDS, "surfaces-paint": ("surfaces-paint", 1)}
