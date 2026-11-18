"""The rain algorithm (library entry algorithm/rain, #128): a night street's falling rain as cards in the render,
cheap to draw (meshes moved by their transforms, no particle system, no simulation).

    rain_file(target, low, high, height, density, seed, seconds)

writes one USD of two parts under its root. `Fall/streaks`: thin crossed cards (each two quads at right angles, so
they read from any heading), each a drop's blur over a film's open shutter (STREAK_LONG along its fall), leaning with
the wind; the field's Xform `Fall` carries them down and sideways along that same lean at the drops' speed, so a
streak falls the way it points. The streaks are two copies of one field stacked a field's height apart along the
fall, `Fall` slides by that height in a whole number of frames (`period_frames`) and jumps back between two frames,
so a film sees rain falling without a seam. `Splashes`: one mesh a frame of the period (`at_<frame>`), shown only on
its own frames (moved far under the ground between them, while a shutter is shut) and holding each drop's crown on
the frames after its streak's foot reaches the ground, at the spot it reaches it: a crown rises, opens and sinks
over SPLASH_FRAMES frames, so a drop ends in its splash where and when it lands, never in mid-air and never at a
spot no drop falls on. Every drop lands once a period, its landing spot drawn evenly over the box.

y up, metres, the box from `low` [x, z] to `high` [x, z] on the ground (y 0); time codes are film frames (FPS)."""
import math

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

MADE = 2  # the algorithm's make, in its file's name: a rain laid after a change is written anew
FALL = 7.0  # metres a second a raindrop falls near its end speed (a 2 mm drop: about 6.5 m/s)
FPS = 24.0  # time codes a second, the films' (stage timeCodesPerSecond)
SHUTTER = 0.5  # the share of a frame a film's shutter is open (180 degrees)
STREAK_LONG = FALL * SHUTTER / FPS  # metres a drop's streak is long: its fall while the shutter is open (0.146 m)
STREAK_WIDE = 0.01  # metres across a streak (a drop and its blur, about a pixel at a street film's distance)
LEAN = 0.08  # the wind's lean: metres sideways a metre down
SPLASH_WIDE = (0.025, 0.06)  # a splash crown's full radius range, metres
SPLASH_HIGH = 0.025  # a crown's blades' full height, metres
SPLASH_BLADES = 6  # blades round a crown
SPLASH_GROWTH = ((0.45, 0.6), (1.0, 1.0), (1.3, 0.45))  # a crown's (radius, height) shares on its frames from landing
HIDDEN = -1000.0  # metres under the ground a splash frame's mesh waits off its frames


def period_frames(height):
    """Whole frames a drop takes to fall `height` metres near FALL, at least one more than a splash lasts."""
    return max(len(SPLASH_GROWTH) + 1, int(round(height / FALL * FPS)))


def streak_cards(centres, lean):
    """Each streak's two crossed cards, as points and quad faces: centred on `centres` (n x 3), STREAK_LONG tall and
    STREAK_WIDE across, its top leaning `lean` [x, z] metres a metre up from its foot."""
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


def splash_crowns(spots, radii, high):
    """Each splash's crown of SPLASH_BLADES thin upright blades round its spot, leaning out, `high` metres tall, as
    points and quad faces; `spots` n x 3 on the ground, `radii` n."""
    points = []
    for blade in range(SPLASH_BLADES):
        around = 2.0 * math.pi * blade / SPLASH_BLADES
        out = np.array([math.cos(around), 0.0, math.sin(around)])
        side = np.array([-math.sin(around), 0.0, math.cos(around)]) * 0.004
        inner = spots + out * radii[:, None] * 0.6
        outer = spots + out * radii[:, None] + np.array([0.0, high, 0.0])
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


def falling(fall, height, lean, seconds):
    """The field's slide: `height` metres down (and `lean` [x, z] metres sideways a metre down) each period of
    period_frames, back in the last hundredth of a time code, for `seconds`; time code -> translate."""
    period = period_frames(height)
    drop = np.array([-lean[0] * height, -height, -lean[1] * height])
    start = 0
    while start <= seconds * FPS:
        fall.Set(Gf.Vec3d(0.0, 0.0, 0.0), Usd.TimeCode(start))
        fall.Set(Gf.Vec3d(*(drop * (period - 0.01) / period).tolist()), Usd.TimeCode(start + period - 0.01))
        start += period


def landings(feet, height):
    """The frame of the period on which each drop's streak foot (`feet`, metres over the ground at the period's
    start, in [0, height)) first stands at or under the ground."""
    period = period_frames(height)
    return np.ceil(feet / height * period - 1e-9).astype(int) % period


def shown(item, frame, seconds, period):
    """A splash frame's mesh at the ground on its `frame` of every period (from the shutter's shut half before it to
    the one after it) and HIDDEN under it otherwise, for `seconds`; time code -> translate."""
    away, here = Gf.Vec3d(0.0, HIDDEN, 0.0), Gf.Vec3d(0.0, 0.0, 0.0)
    item.Set(away, Usd.TimeCode(-1.0))
    code = frame
    while code <= seconds * FPS:
        for offset, value in ((-0.49, away), (-0.01, here), (SHUTTER, here), (0.99, away)):
            item.Set(value, Usd.TimeCode(code + offset))
        code += period


def splash_frames(stage, spots, radii, landed, period, seconds):
    """Under /Rain/Splashes one mesh a frame of the period holding each drop's crown on its frames from landing
    (SPLASH_GROWTH), each shown only on its own frames; how many crowns they hold."""
    UsdGeom.Xform.Define(stage, "/Rain/Splashes")
    crowns = 0
    for frame in range(period):
        points, faces = [], []
        for age, (wide, high) in enumerate(SPLASH_GROWTH):
            these = (landed + age) % period == frame
            if not these.any():
                continue
            made, quads = splash_crowns(spots[these], radii[these] * wide, SPLASH_HIGH * high)
            faces.append(quads + sum(len(part) for part in points))
            points.append(made)
            crowns += int(these.sum())
        if not points:
            continue
        holder = UsdGeom.Xform.Define(stage, f"/Rain/Splashes/at_{frame:03d}")
        shown(holder.AddTranslateOp(), frame, seconds, period)
        part_mesh(stage, f"/Rain/Splashes/at_{frame:03d}/crowns", np.concatenate(points), np.concatenate(faces))
    return crowns


def rain_file(target, low, high, height, density, seed=0, seconds=40.0):
    """The rain of the box from `low` to `high` ([x, z], metres) up to `height`, `density` drops a cubic metre,
    written to `target`; its counts."""
    rng = np.random.default_rng(seed)
    low, high = np.asarray(low, float), np.asarray(high, float)
    if np.any(high <= low) or height <= STREAK_LONG or density <= 0:
        raise ValueError(f"rain needs a box (low {low.tolist()} under high {high.tolist()}), a height over a streak "
                         f"and a density over 0")
    floor = float(np.prod(high - low))
    count = max(1, int(round(density * floor * height)))
    lean = np.array([LEAN, LEAN * 0.3])
    spots = np.column_stack([rng.uniform(low[0], high[0], count), np.full(count, 0.002),
                             rng.uniform(low[1], high[1], count)])
    feet = rng.uniform(0.0, height, count)
    centres = spots + np.column_stack([lean[0] * feet, feet, lean[1] * feet])
    centres = centres + np.array([lean[0], 1.0, lean[1]]) * STREAK_LONG / 2.0 - np.array([0.0, 0.002, 0.0])
    field = np.concatenate([centres, centres + np.array([lean[0], 1.0, lean[1]]) * height])
    streak_points, streak_faces, cards = streak_cards(field, lean)
    stage = Usd.Stage.CreateNew(str(target))
    stage.SetMetadata("upAxis", "Y")
    stage.SetMetadata("metersPerUnit", 1.0)
    stage.SetTimeCodesPerSecond(FPS)
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(seconds * FPS)
    root = UsdGeom.Xform.Define(stage, "/Rain")
    stage.SetDefaultPrim(root.GetPrim())
    fall = UsdGeom.Xform.Define(stage, "/Rain/Fall")
    falling(fall.AddTranslateOp(), height, lean, seconds)
    part_mesh(stage, "/Rain/Fall/streaks", streak_points, streak_faces)
    period = period_frames(height)
    crowns = splash_frames(stage, spots, rng.uniform(*SPLASH_WIDE, count), landings(feet, height), period, seconds)
    root.GetPrim().CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set("algorithm rain (rainfall.rain_file)")
    stage.GetRootLayer().Save()
    return {"streaks": count, "cards": cards, "splashes": crowns, "period": period,
            "points": len(streak_points) + crowns * SPLASH_BLADES * 4}
