"""The rain algorithm (library entry algorithm/rain, #128): a night street's falling rain as instanced cards in the
render, cheap to draw (one mesh, no particle system, no simulation).

    rain_file(target, low, high, height, density, seed, seconds)

writes one USD of two parts under its root: `streaks`, thin crossed cards (each two quads at right angles, so they
read from any heading) leaning with the wind and falling through the box from `height` to the ground at FALL metres a
second, and `splashes`, small crowns of thin upright blades on the ground where drops land. The streaks are laid in
two copies of one field stacked a field's height apart and the field's Xform `Fall` slides down by that height and
jumps back once a period, so a film sees rain falling without a seam; the splashes stay where they are (a crown a
few centimetres across reads as rain hitting a wet road at a film's distance).

y up, metres, the box from `low` [x, z] to `high` [x, z] on the ground (y 0)."""
import math

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

FALL = 7.0  # metres a second a raindrop falls near its end speed (a 2 mm drop: about 6.5 m/s)
STREAK_LONG = 0.42  # metres a drop's streak is long at a film's shutter (24 frames a second, a half-open shutter)
STREAK_WIDE = 0.01  # metres across a streak (a drop and its blur, about a pixel at a street film's distance)
LEAN = 0.08  # the wind's lean: metres sideways a metre down
SPLASH_SHARE = 0.35  # splashes laid for every streak in the field
SPLASH_WIDE = (0.025, 0.06)  # a splash crown's radius range, metres
SPLASH_HIGH = 0.025  # a crown's blades' height, metres
SPLASH_BLADES = 6  # blades round a crown
FPS = 24.0  # time codes a second, the films' (stage timeCodesPerSecond)


def streak_cards(centres, lean):
    """Each streak's two crossed cards, as points and quad faces: centred on `centres` (n x 3), STREAK_LONG tall and
    STREAK_WIDE across, its top leaning `lean` [x, z] metres from its foot."""
    count = len(centres)
    half = STREAK_LONG / 2.0
    tilt = np.array([lean[0], 0.0, lean[1]]) * STREAK_LONG / 2.0
    top = centres + np.array([0.0, half, 0.0]) + tilt
    foot = centres - np.array([0.0, half, 0.0]) - tilt
    points = []
    for side in (np.array([STREAK_WIDE / 2.0, 0.0, 0.0]), np.array([0.0, 0.0, STREAK_WIDE / 2.0])):
        points.append(np.stack([foot - side, foot + side, top + side, top - side], axis=1))
    points = np.concatenate(points, axis=0).reshape(-1, 3)
    faces = np.arange(len(points)).reshape(-1, 4)
    return points, faces, 2 * count


def splash_crowns(spots, radii):
    """Each splash's crown of SPLASH_BLADES thin upright blades round its spot, leaning out, as points and quad
    faces; `spots` n x 3 on the ground, `radii` n."""
    points = []
    for blade in range(SPLASH_BLADES):
        around = 2.0 * math.pi * blade / SPLASH_BLADES
        out = np.array([math.cos(around), 0.0, math.sin(around)])
        side = np.array([-math.sin(around), 0.0, math.cos(around)]) * 0.004
        inner = spots + out * radii[:, None] * 0.6
        outer = spots + out * radii[:, None] + np.array([0.0, SPLASH_HIGH, 0.0])
        points.append(np.stack([inner - side, inner + side, outer + side, outer - side], axis=1))
    points = np.concatenate(points, axis=0).reshape(-1, 3)
    return points, np.arange(len(points)).reshape(-1, 4)


def part_mesh(stage, path, points, faces):
    """A mesh at `path` of quads `faces` over `points`, two-sided, its extent written."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray([4] * len(faces)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(faces.reshape(-1).tolist()))
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*points.min(axis=0).tolist()), Gf.Vec3f(*points.max(axis=0).tolist())]))
    return mesh


def falling(fall, height, seconds):
    """The field's slide: down `height` metres each period (height / FALL seconds), back up in a hundredth of a time
    code, for `seconds`; time code -> y."""
    period = height / FALL * FPS
    samples, start = {}, 0.0
    while start <= seconds * FPS:
        samples[start] = 0.0
        samples[start + period - 0.01] = -height
        start += period
    for code, value in samples.items():
        fall.Set(Gf.Vec3d(0.0, value, 0.0), Usd.TimeCode(code))


def rain_file(target, low, high, height, density, seed=0, seconds=40.0):
    """The rain of the box from `low` to `high` ([x, z], metres) up to `height`, `density` streaks a cubic metre,
    written to `target`; its counts."""
    rng = np.random.default_rng(seed)
    low, high = np.asarray(low, float), np.asarray(high, float)
    if np.any(high <= low) or height <= STREAK_LONG or density <= 0:
        raise ValueError(f"rain needs a box (low {low.tolist()} under high {high.tolist()}), a height over a streak "
                         f"and a density over 0")
    floor = float(np.prod(high - low))
    count = max(1, int(round(density * floor * height)))
    centres = np.column_stack([rng.uniform(low[0], high[0], count), rng.uniform(0.0, height, count),
                               rng.uniform(low[1], high[1], count)])
    lean = (LEAN, LEAN * 0.3)
    field = np.concatenate([centres, centres + np.array([0.0, height, 0.0])])
    streak_points, streak_faces, cards = streak_cards(field, lean)
    splashes = max(1, int(round(count * SPLASH_SHARE)))
    spots = np.column_stack([rng.uniform(low[0], high[0], splashes), np.full(splashes, 0.002),
                             rng.uniform(low[1], high[1], splashes)])
    splash_points, splash_faces = splash_crowns(spots, rng.uniform(*SPLASH_WIDE, splashes))
    stage = Usd.Stage.CreateNew(str(target))
    stage.SetMetadata("upAxis", "Y")
    stage.SetMetadata("metersPerUnit", 1.0)
    stage.SetTimeCodesPerSecond(FPS)
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(seconds * FPS)
    root = UsdGeom.Xform.Define(stage, "/Rain")
    stage.SetDefaultPrim(root.GetPrim())
    fall = UsdGeom.Xform.Define(stage, "/Rain/Fall")
    falling(fall.AddTranslateOp(), height, seconds)
    part_mesh(stage, "/Rain/Fall/streaks", streak_points, streak_faces)
    part_mesh(stage, "/Rain/splashes", splash_points, splash_faces)
    for prim in (root.GetPrim(),):
        prim.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set("algorithm rain (rainfall.rain_file)")
    stage.GetRootLayer().Save()
    return {"streaks": count, "cards": cards, "splashes": splashes, "points": len(streak_points) + len(splash_points)}
