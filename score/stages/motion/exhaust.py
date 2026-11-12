"""A launching rocket's exhaust, made from the library (data/effects/exhaust.json): motion@square, 2026-11-12: its
rocket's launch (from_design.launched) left its exhaust's flame and smoke `unmade`, so `covered` failed it, every
old rocket flame and exhaust effect having been withdrawn from score_lib with the old records (score_lib 60da34e6,
2026-10-21). The recipe stands beside data/library, not in it: data/library is read whole by the paint line, the
surface tiles and the dresses (44 paid rows), so a file there would buy them again. Drawn for a launch seen from
afar, as shapes that read at that distance: the flame and its white core, glowing cones held under the rocket's foot
frame by frame as it climbs, their lengths in rocket heights as the footage measured them; the smoke column, puffs
born where its foot stood, each growing and then gone. Written into the place's motion layer under its effects scope
(/<place>/Effects/<rocket>_exhaust, tagged `score:effect:kind`), where
no motion gate reads a thing to move, so only `covered` judges it. Kept apart from the motion package: the table sets
`made` on the motion row's make and `judge_covered` on its `covered` check (as shown_rows.py's `designed`), so a place
with no launch keeps its output byte for byte.

    made(make)                         motion's make, then each launch's exhaust written (write)
    write(inputs, out, source)         each launch's exhaust line taken off the record's `unmade`, its exhaust drawn
    judge_covered(output, ...)         motion's `covered`, with every launch's exhaust held to the library's checks
"""
import functools
import json
import math
import pathlib
import sys

import numpy as np

from score import checks
from score.stages import motion

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import builders  # noqa: E402

KIND = "rocket_exhaust"
LIBRARY = "data/effects/exhaust.json"
SUFFIX = "_exhaust"
PARTS = ("flame", "core")
# How far a drawn flame's top may stand off its rocket's foot at any whole second, metres.
RIDE_MOST = 0.05


def made(make):
    """A make that writes each launch's exhaust into the layer once the motion make has run (write)."""
    @functools.wraps(make)
    def making(inputs, out, seed, params):
        make(inputs, out, seed, params)
        if "exhaust" in inputs and exhaust_lines(read(pathlib.Path(out) / motion.RECORD)):
            with motion.built(inputs) as source:
                write(inputs, pathlib.Path(out), source)
    return making


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def exhaust_lines(record):
    """{rocket prim: its unmade line} of every launch the record leaves its exhaust unmade on
    (from_design.launched: "<prim>: exhaust, <the rule's words>")."""
    climbing = {entry["prim"] for entry in record.get("moves", []) if "climb" in entry}
    return {line.split(": ", 1)[0]: line for line in record.get("unmade", [])
            if line.split(": ", 1)[-1].startswith("exhaust, ") and line.split(": ", 1)[0] in climbing}


def place_of(path):
    return path.split("/")[1]


def effect_path(prim):
    """Where a rocket's exhaust stands: under its place's effects scope, named for it."""
    return f"/{place_of(prim)}/Effects/{prim.rsplit('/', 1)[-1]}{SUFFIX}"


def linear(hex_colour):
    """A #rrggbb colour as linear RGB."""
    channels = [int(hex_colour.lstrip("#")[at:at + 2], 16) / 255 for at in (0, 2, 4)]
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]


def at(knots, moment):
    """A recipe's knots ([[moment, value]], held before the first and after the last) read at `moment`."""
    moments, values = zip(*knots)
    return float(np.interp(moment, moments, values))


def box_at(stage, prim, code):
    """(low, high) of a prim's bounds in its place's own frame at a time code."""
    from pxr import UsdGeom
    found = UsdGeom.BBoxCache(code, ["default", "render"]).ComputeRelativeBound(
        stage.GetPrimAtPath(prim), stage.GetPrimAtPath(f"/{place_of(prim)}")).ComputeAlignedRange()
    return np.asarray(found.GetMin(), dtype=np.float64), np.asarray(found.GetMax(), dtype=np.float64)


def foot_at(stage, prim, code):
    """The middle of a prim's underside in its place's frame at a time code (Y up)."""
    low, high = box_at(stage, prim, code)
    return np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])


def measures_of(stage, prim):
    """(height, narrower width) of the rocket at rest, metres."""
    low, high = box_at(stage, prim, 0.0)
    size = high - low
    return float(size[1]), float(min(size[0], size[2]))


def material(stage, path, colour, emits=0.0, opacity=1.0):
    """A preview surface of a recipe's colour: given off as light `emits` times where it glows, else matte."""
    from pxr import Sdf, UsdShade
    found = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shade = linear(colour)
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(tuple(shade))
    if emits:
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(tuple(value * emits for value in shade))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(opacity))
    found.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return found


def mesh(stage, path, built, looks):
    """A built mesh (tools/usd/builders.py) as a drawn UsdGeomMesh bound to `looks`."""
    from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt
    prim = UsdGeom.Mesh.Define(stage, path)
    points = built["points"].astype(np.float32)
    prim.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
    prim.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(built["triangles"]), 3, dtype=np.int32)))
    prim.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(built["triangles"].reshape(-1).astype(np.int32)))
    prim.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    prim.CreateDoubleSidedAttr(True)
    prim.CreateExtentAttr([Gf.Vec3f(*map(float, points.min(axis=0))), Gf.Vec3f(*map(float, points.max(axis=0)))])
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(looks)
    prim.GetPrim().CreateAttribute("score:effect:part", Sdf.ValueTypeNames.String).Set(path.rsplit("/", 1)[-1])
    return prim


def flame_shape(part, height, width, segments):
    """A flame's cone of unit length hanging down from its top (radius 1 there), widening its recipe's spread either
    side over its longest length, in units of its top's radius."""
    top = part["radius"] * width
    longest = max(value for _, value in part["length"]) * height
    bottom = 1.0 + math.tan(math.radians(part["spread_degrees"])) * longest / top
    return builders.cone_arc(-1.0, 0.0, bottom, 1.0, KIND, segments=segments), top


def write_flame(stages, root, name, part, rocket, lift, codes, rate, looks, segments):
    """One glowing cone held under the rocket's foot at every code, its length the recipe's in rocket heights since
    lift-off; its numbers back. `stages`: (the composed stage the rocket is read on, the layer's own it is written
    on)."""
    from pxr import Gf, UsdGeom
    stage, layer_stage = stages
    height, width = measures_of(stage, rocket)
    shape, top = flame_shape(part, height, width, segments)
    holder = UsdGeom.Xform.Define(layer_stage, f"{root}/{name}")
    move, size = holder.AddTranslateOp(), holder.AddScaleOp()
    for code in codes:
        since = max(0.0, code / rate - lift)
        move.Set(Gf.Vec3d(*foot_at(stage, rocket, code)), code)
        size.Set(Gf.Vec3f(top, at(part["length"], since) * height, top), code)
    mesh(layer_stage, f"{root}/{name}/cone", shape, looks)
    return {"top radius": round(top, 4), "length": [[when, round(value * height, 4)] for when, value in part["length"]]}


def births(stage, rocket, lift, seconds, rate, spacing, most):
    """(code, foot) of each puff: one at lift-off, then one each time the foot has risen `spacing` (never more than
    `most`, spaced wider where it climbs that far)."""
    codes = np.arange(math.ceil(lift * rate), math.floor(seconds * rate) + 1)
    feet = [foot_at(stage, rocket, float(code)) for code in codes]
    risen = feet[-1][1] - feet[0][1] if feet else 0.0
    step = max(spacing, risen / max(1, most - 1))
    found, last = [], None
    for code, foot in zip(codes, feet):
        if last is None or foot[1] - last >= step:
            found.append((float(code), foot))
            last = foot[1]
    return found


def write_trail(stages, root, trail, rocket, lift, seconds, rate, looks, drawn):
    """The smoke column: a puff born where the rocket's foot stands, growing by the recipe and gone after its
    lifetime, unseen before its birth; how many back."""
    from pxr import Gf, UsdGeom
    stage, layer_stage = stages
    height, _ = measures_of(stage, rocket)
    shape = builders.sphere((0.0, 0.0, 0.0), 1.0, KIND, rings=drawn["rings"], segments=drawn["segments"])
    born = births(stage, rocket, lift, seconds, rate, at(trail["radius"], 0.0) * height, trail["most"])
    UsdGeom.Scope.Define(layer_stage, f"{root}/trail")
    for index, (code, foot) in enumerate(born):
        holder = UsdGeom.Xform.Define(layer_stage, f"{root}/trail/puff_{index}")
        holder.AddTranslateOp().Set(Gf.Vec3d(*foot))
        size = holder.AddScaleOp()
        for age, value in trail["radius"]:
            size.Set(Gf.Vec3f(*([value * height] * 3)), code + age * rate)
        seen = holder.GetVisibilityAttr()
        seen.Set(UsdGeom.Tokens.invisible, 0.0)
        seen.Set(UsdGeom.Tokens.inherited, code)
        seen.Set(UsdGeom.Tokens.invisible, code + float(trail["lifetime"]) * rate)
        mesh(layer_stage, f"{root}/trail/puff_{index}/ball", shape, looks)
    return len(born)


def write_one(stages, rocket, recipe, lift, seconds, rate):
    """A rocket's exhaust under its place's effects scope, read off the composed stage and written on the layer's
    own (`stages`); its record entry back."""
    from pxr import Sdf, UsdGeom
    place, root, layer_stage = place_of(rocket), effect_path(rocket), stages[1]
    UsdGeom.Scope.Define(layer_stage, f"/{place}/Effects")
    holder = UsdGeom.Xform.Define(layer_stage, root).GetPrim()
    for key, value in (("kind", KIND), ("on", rocket), ("from", f"{LIBRARY}, the library's rocket exhaust")):
        holder.CreateAttribute(f"score:effect:{key}", Sdf.ValueTypeNames.String).Set(value)
    codes = [float(code) for code in range(math.ceil(lift * rate), math.floor(seconds * rate) + 1)]
    drawn = recipe["drawn"]
    entry = {"prim": root, "on": rocket, "from": LIBRARY, "lift": lift}
    for name in PARTS:
        part = recipe[name]
        looks = material(layer_stage, f"{root}/Looks/{name}", part["colour"], emits=float(part["brightness"]),
                         opacity=float(part.get("opacity", 1.0)))
        entry[name] = write_flame(stages, root, name, part, rocket, lift, codes, rate, looks, drawn["segments"])
    smoke = material(layer_stage, f"{root}/Looks/trail", recipe["trail"]["colour"],
                     opacity=recipe["trail"]["opacity"])
    entry["puffs"] = write_trail(stages, root, recipe["trail"], rocket, lift, seconds, rate, smoke, drawn)
    return entry


def write(inputs, out, source):
    """Each launch's exhaust the record leaves unmade, drawn from the library into the motion layer over the built
    stage `source`; its line taken off `unmade` and the exhaust named in the record's `exhaust` ({rocket: entry})."""
    from pxr import Usd
    record_path = out / motion.RECORD
    record = read(record_path)
    lines = exhaust_lines(record)
    recipe = read(inputs["exhaust"])
    stage = motion.composed(out, dict(inputs, built=source, moves=record_path))
    layer = stage.GetEditTarget().GetLayer()
    rate, seconds = layer.timeCodesPerSecond, float(record["seconds"])
    climbs = {entry["prim"]: entry for entry in record["moves"] if "climb" in entry}
    stages = (stage, Usd.Stage.Open(layer))
    written = {rocket: write_one(stages, rocket, recipe, float(climbs[rocket]["start"]) +
                                 float(climbs[rocket]["climb"]["lift"]), seconds, rate) for rocket in sorted(lines)}
    layer.Save()
    record["unmade"] = [line for line in record["unmade"] if line not in lines.values()]
    record["exhaust"] = written
    record_path.write_text(json.dumps(record, indent=1))


# --- covered ------------------------------------------------------------------------------------------------------

def length_at(stage, root, name, code):
    """A drawn flame's length at a time code (its scale's up)."""
    from pxr import UsdGeom
    for operation in UsdGeom.Xformable(stage.GetPrimAtPath(f"{root}/{name}")).GetOrderedXformOps():
        if operation.GetOpType() == UsdGeom.XformOp.TypeScale:
            return float(operation.Get(code)[1])
    return 0.0


def top_at(stage, root, name, code):
    """Where a drawn flame's top stands at a time code, in its place's frame."""
    from pxr import UsdGeom
    for operation in UsdGeom.Xformable(stage.GetPrimAtPath(f"{root}/{name}")).GetOrderedXformOps():
        if operation.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            return np.asarray(operation.Get(code), dtype=np.float64)
    return None


def faults_of(stages, rocket, entry, recipe, seconds, rate):
    """What a launch's exhaust lacks: its parts drawn, its flame riding the rocket's foot, its lengths in the footage's
    ranges, its smoke column. `stages`: (the composed stage the rocket is read on, the motion layer's own the effects
    scope is read on: the composed stage holds the place's own scopes only)."""
    stage, drawn = stages
    root = entry["prim"] if entry else effect_path(rocket)
    prim = drawn.GetPrimAtPath(root)
    if not prim or prim.GetAttribute("score:effect:kind").Get() != KIND:
        return [f"{rocket}: exhaust, none of the library's ({root}) stands on the stage"]
    faults = [f"{rocket}: exhaust, its {name} is not drawn" for name in PARTS
              if not drawn.GetPrimAtPath(f"{root}/{name}/cone")]
    if faults:
        return faults
    height, lift = measures_of(stage, rocket)[0], float(entry.get("lift", 0.0)) if entry else 0.0
    for moment in np.arange(math.ceil(lift), seconds + 1e-9, 1.0):
        off = float(np.linalg.norm(top_at(drawn, root, "flame", moment * rate) - foot_at(stage, rocket, moment * rate)))
        if off > RIDE_MOST:
            faults.append(f"{rocket}: exhaust, its flame stands {off:.2f} m off the rocket's foot at {moment:g} s")
            break
    for check in recipe["checks"]:
        share = length_at(drawn, root, check["part"], (lift + check["after_lift"]) * rate) / height
        low, high = check["range"]
        if not low <= share <= high:
            faults.append(f"{rocket}: exhaust, {check['name']} {share:.2f} rocket heights, outside the footage's "
                          f"{low:g} to {high:g}")
    trail = drawn.GetPrimAtPath(f"{root}/trail")
    if not trail or not trail.GetChildren():
        faults.append(f"{rocket}: exhaust, it leaves no smoke column")
    return faults


def judge_covered(output, inputs, evidence):
    """motion.judge_covered, with every launch the record says its exhaust is made for held to the library's
    exhaust on the composed stage (faults_of): a launch whose exhaust line is gone and no exhaust drawn fails."""
    verdict = motion.judge_covered(output, inputs, evidence)
    record = read(inputs["moves"])
    unmade = exhaust_lines(record)
    launches = sorted(entry["prim"] for entry in record.get("moves", []) if "climb" in entry and
                      entry["prim"] not in unmade)
    if not launches:
        return verdict
    from pxr import Usd
    stage = motion.composed(output, inputs)
    stages = (stage, Usd.Stage.Open(stage.GetEditTarget().GetLayer()))
    recipe = read(inputs["exhaust"]) if "exhaust" in inputs else None
    rate, seconds = stage.GetTimeCodesPerSecond(), motion.seconds_of(output)
    faults = [fault for rocket in launches for fault in
              (faults_of(stages, rocket, record.get("exhaust", {}).get(rocket), recipe, seconds, rate) if recipe else
               [f"{rocket}: exhaust, no library exhaust read for it"])]
    if not faults:
        return checks.Verdict("covered", verdict.answer, f"{verdict.reason}; {len(launches)} launches show the "
                              "library's exhaust", {**verdict.measures, "exhausts": len(launches)}, verdict.better,
                              verdict.findings)
    held = len(launches) - len({fault.split(":")[0] for fault in faults})
    return checks.Verdict("covered", checks.FAIL, f"{verdict.reason}; {len(faults)} exhaust faults",
                          {**verdict.measures, "exhausts": held},
                          verdict.better, verdict.findings + tuple(faults))
