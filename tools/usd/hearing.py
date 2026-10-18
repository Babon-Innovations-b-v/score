"""What a camera hears in a place's OpenUSD stage, from its sound layer (tools/usd/sound.py's layout), for the review's
walk and the demo's films:

    soundtrack(stage, moments, frame_rate, out)   along a camera's moments, one a frame ({"eye", "aim", "time"})
    bed(stage, moment, seconds, frame_rate, out)  standing at a shot's first view over the seconds before it

The place's own room tones play as they are; a shown place's air is heard only inside it, so the places a stage shows
add none. Each spatial sound plays at its gain out to its `near` (data/sound/sounds.json, else NEAR_METRES, Godot's
AudioStreamPlayer3D unit size, as the game plays a placed sound), then falls with the inverse of the distance, silent
past its reach, and is panned by where it stands across the view; each motion's sound from its start. A footstep plays
at every stride of the walk, from the floor under the eye: its library surface's footstep in the bank, else its kit
kind's surface in data/sound/surfaces.json (a kind not named is steel_plate, as the game reads it). Outside, where the
place's own room plays on the suit's bus, only what the boots feel carries (`score:sound:groundThud`). Every track is
mixed at one gain (MIX_GAIN_DB) with a soft limit under sound.PEAK_DBFS, the same for every place, so a lift-off is
loud and a cabin quiet: no track is brought to a loudness of its own (until 2026-10-18 sound.soundtrack pressed every
shot to -24 dBFS). The bed is laid under a film's title card and the showcase's cards, so no card is silent.

A module of its own beside sound.py: sound.py is in the code of the rows that write stages (assembly, settle, motion),
so a change to the mix there would run them all again for nothing.
"""
import functools
import math
import pathlib
import sys

import numpy as np
from pxr import Sdf, Usd, UsdGeom, UsdMedia

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sound  # noqa: E402

# The distance a spatial sound plays at its own gain (Godot's AudioStreamPlayer3D unit_size, 10 m by default, as the
# game plays every placed sound); a sound's own `near` in the data over it.
NEAR_METRES = 10.0
# The one gain every track is mixed at (dB), the same for every place: the levels are the sounds' own, so a quiet
# cabin stays quiet and a lift-off loud. Set on world 1's 27 films (2026-10-18, measured before the gain: the rooms
# -35 to -47 dBFS RMS, the launch's lift-off -28.5, the peaks -19 to -34), so the loudest rooms sit near -24, the
# ship's cabins near -32 and the lift-off near -16. The limit's knee, where it starts to round the peaks off, is
# LIMIT_KNEE of the ceiling (sound.PEAK_DBFS).
MIX_GAIN_DB = 12.0
LIMIT_KNEE = 0.5
# A footstep every STRIDE_METRES the eye walks on the level, the first half a stride in; a step from the walker's
# feet, EYE_OVER_FEET under the eye, looked for down to FLOOR_BELOW under the feet.
STRIDE_METRES = 0.55
EYE_OVER_FEET = 1.62
FLOOR_BELOW = 1.0
# The bus a place's own room plays on outside, where nothing carries through the air: the suit's.
AIRLESS_BUS = "suit"


def resolved(asset, prim):
    """An asset path's file: as the stage resolved it, else beside the stage's root layer."""
    return asset.resolvedPath or str(pathlib.Path(prim.GetStage().GetRootLayer().realPath).parent / asset.path)


def decoded_once(file, cache):
    """A file's samples, decoded once a run."""
    if file not in cache:
        cache[file] = sound.decoded(file)
    return cache[file]


def sources_of(stage, cache=None):
    """Every SpatialAudio prim of a composed stage but the bank's as a source: its samples, gain, how it plays, where
    it is, the distance it plays at its own gain within, its bus and whether it is felt through the boots."""
    found = []
    rate = stage.GetTimeCodesPerSecond()
    cache = {} if cache is None else cache
    for prim in stage.Traverse():
        if not prim.IsA(UsdMedia.SpatialAudio) or "/Sound/Bank/" in str(prim.GetPath()):
            continue
        audio = UsdMedia.SpatialAudio(prim)
        start, end = audio.GetStartTimeAttr().Get(), audio.GetEndTimeAttr().Get()
        found.append({"samples": decoded_once(resolved(audio.GetFilePathAttr().Get(), prim), cache),
                      "gain": float(audio.GetGainAttr().Get()), "mode": str(audio.GetPlaybackModeAttr().Get()),
                      "spatial": str(audio.GetAuralModeAttr().Get()) == UsdMedia.Tokens.spatial,
                      "start": float(start.GetValue()) / rate if start is not None else 0.0,
                      "end": float(end.GetValue()) / rate if end is not None and end.GetValue() > 0 else None,
                      "reach": sound_value(prim, "reach", 0.0), "near": near_of(sound_value(prim, "name", "")),
                      "bus": sound_value(prim, "bus", ""), "felt": bool(sound_value(prim, "groundThud", False)),
                      "prim": prim})
    return found


@functools.lru_cache(maxsize=None)
def near_of(name):
    """How far out a sound plays at its own level: its `near` in the sound data (data/sound/sounds.json), else
    NEAR_METRES."""
    return float(sound.entry_of(name).get("near") or NEAR_METRES) if name else NEAR_METRES


def sound_value(prim, name, default):
    """A prim's `score:sound:<name>`, else the default where it is not written or empty."""
    attribute = prim.GetAttribute(f"score:sound:{name}")
    value = attribute.Get() if attribute else None
    return value if value else default


def shown_air(source, place):
    """Whether a source is a shown place's room tone: heard only inside that place, never from the place showing it."""
    return not source["spatial"] and f"/{place}/Places/" in str(source["prim"].GetPath())


def airless(sources, place):
    """Whether the place's own room is heard through the suit (outside, on the Moon or Mars)."""
    own = f"/{place}/Sound/Room/"
    return any(source["bus"] == AIRLESS_BUS for source in sources if str(source["prim"].GetPath()).startswith(own))


def heard_sources(stage, cache=None):
    """The sources the place's camera can hear: no shown place's air, and outside only what the boots feel."""
    place = stage.GetDefaultPrim().GetName()
    sources = [source for source in sources_of(stage, cache) if not shown_air(source, place)]
    if airless(sources, place):
        sources = [source for source in sources if not source["spatial"] or source["felt"]]
    return sources


def heard_gain(source, eye, aim, at):
    """A spatial source's gain at the eye and its pan (-1 left .. 1 right) from where it stands across the view: its
    own level within its `near`, then falling as the inverse of the distance (Godot's inverse distance)."""
    towards = np.asarray(at) - eye
    distance = float(np.linalg.norm(towards))
    if source["reach"] and distance > source["reach"]:
        return 0.0, 0.0
    level = min(1.0, source.get("near", NEAR_METRES) / max(distance, 1e-6))
    forward = np.asarray(aim) - eye
    right = np.cross(forward, [0.0, 1.0, 0.0])
    norm = np.linalg.norm(right)
    pan = float(np.dot(towards, right) / (norm * max(distance, 1e-6))) if norm > 1e-9 else 0.0
    return level, max(-1.0, min(1.0, pan))


def sources_mix(stage, sources, moments, frame_rate):
    """The sources as heard along the moments (one a frame), a stereo float mix."""
    cache = UsdGeom.XformCache()
    step = round(sound.SAMPLE_RATE / frame_rate)
    mix = np.zeros((len(moments) * step, 2))
    for index, moment in enumerate(moments):
        eye = np.asarray(moment["eye"], dtype=float)
        seconds = float(moment["time"])
        rows = slice(index * step, (index + 1) * step)
        cache.SetTime(Usd.TimeCode(seconds * stage.GetTimeCodesPerSecond()))
        for source in sources:
            chunk = sound.played(source, seconds, step) * source["gain"]
            if source["spatial"]:
                at = cache.GetLocalToWorldTransform(source["prim"]).ExtractTranslation()
                level, pan = heard_gain(source, eye, moment["aim"], at)
                angle = (pan + 1.0) * math.pi / 4.0
                mix[rows, 0] += chunk * level * math.cos(angle)
                mix[rows, 1] += chunk * level * math.sin(angle)
            else:
                mix[rows] += chunk[:, None] * math.sqrt(0.5)
    return mix


# --- the walker's footsteps ---------------------------------------------------------------------------------------

def stride_frames(moments):
    """The frames a footstep falls on: every STRIDE_METRES the eye has walked on the level, the first half a stride
    in; none while it stands."""
    flat = np.asarray([[moment["eye"][0], moment["eye"][2]] for moment in moments], dtype=float)
    walked = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(flat, axis=0), axis=1))]) if len(flat) else []
    found, next_step = [], STRIDE_METRES / 2.0
    for index, distance in enumerate(walked):
        if distance >= next_step:
            found.append(index)
            next_step += STRIDE_METRES
    return found


def floor_meshes(stage, place):
    """The place's own drawn meshes (not a shown place's, not a collision hull): [(prim, low, high corner)]."""
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = []
    for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{place}")):
        if not prim.IsA(UsdGeom.Mesh) or "/Places/" in str(prim.GetPath()) or prim.GetName() == "collision":
            continue
        if UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
        if not box.IsEmpty():
            found.append((prim, np.asarray(box.GetMin()), np.asarray(box.GetMax())))
    return found


def hit_below(prim, feet):
    """The height and triangle where a ray straight down from `feet` meets the mesh highest under it; None if it
    misses."""
    import resting  # noqa: E402  (tools/usd)
    points, triangles = resting.in_stage(prim)
    corners = points[triangles][:, :, [0, 2]]
    first, second, third = corners[:, 0], corners[:, 1], corners[:, 2]
    spot = np.array([feet[0], feet[2]])
    area = turn(first, second, third)
    usable = np.abs(area) > 1e-12
    safe = np.where(usable, area, 1.0)
    weight_second = turn(first, spot, third) / safe
    weight_third = turn(first, second, spot) / safe
    weight_first = 1.0 - weight_second - weight_third
    inside = usable & (weight_first >= 0) & (weight_second >= 0) & (weight_third >= 0)
    heights = (points[triangles][:, :, 1] * np.column_stack([weight_first, weight_second, weight_third])).sum(axis=1)
    under = inside & (heights <= feet[1] + 0.3) & (heights >= feet[1] - FLOOR_BELOW)
    if not under.any():
        return None
    index = int(np.flatnonzero(under)[np.argmax(heights[under])])
    return float(heights[index]), index


def turn(origin, one, other):
    """The signed area spanned on the level from `origin` to `one` and to `other` ((x, z) points or rows of them)."""
    origin, one, other = (np.atleast_2d(point) for point in (origin, one, other))
    towards_one, towards_other = one - origin, other - origin
    return towards_one[:, 0] * towards_other[:, 1] - towards_other[:, 0] * towards_one[:, 1]


def floor_under(meshes, feet):
    """The mesh the walker stands on at `feet` and the triangle it stands on: (prim, triangle) or None."""
    best = None
    for prim, low, high in meshes:
        if not (low[0] <= feet[0] <= high[0] and low[2] <= feet[2] <= high[2] and low[1] <= feet[1] + 0.3):
            continue
        hit = hit_below(prim, feet)
        if hit and (best is None or hit[0] > best[0]):
            best = (hit[0], prim, hit[1])
    return None if best is None else (best[1], best[2])


def library_material(prim, triangle):
    """The library material bound where the walker stands: the part (GeomSubset) holding the triangle, else the mesh's
    own binding; None for a baked look."""
    from pxr import UsdShade
    for part in prim.GetChildren():
        if part.IsA(UsdGeom.Subset) and triangle in set(UsdGeom.Subset(part).GetIndicesAttr().Get() or []):
            bound = UsdShade.MaterialBindingAPI(part).GetDirectBinding().GetMaterial()
            if bound and "/Library/" in str(bound.GetPath()):
                return bound.GetPrim()
    bound = UsdShade.MaterialBindingAPI(prim).GetDirectBinding().GetMaterial()
    return bound.GetPrim() if bound and "/Library/" in str(bound.GetPath()) else None


def kind_of(prim):
    """The kind of the object a mesh is part of (its nearest `score:kind`), or None."""
    while prim and prim.GetPath() != Sdf.Path.absoluteRootPath:
        kind = prim.GetAttribute("score:kind")
        if kind and kind.Get():
            return kind.Get()
        prim = prim.GetParent()
    return None


def footstep_of(stage, place, prim, triangle, surfaces):
    """The bank's footstep for where the walker stands: its library surface's, else its object kind's surface (a room
    kit's kind names it in surfaces.json `kit`; one not named is steel_plate, the base's own, as the game reads it);
    None when the bank has no such footstep."""
    material = library_material(prim, triangle)
    if material is not None:
        targets = material.GetRelationship("score:sound:footstep").GetTargets() \
            if material.GetRelationship("score:sound:footstep") else []
        return stage.GetPrimAtPath(targets[0]) if targets else None
    surface = surfaces["kit"].get(kind_of(prim) or "", "steel_plate")
    name = surfaces["surfaces"].get(surface, {}).get("footstep")
    found = stage.GetPrimAtPath(f"/{place}/Sound/Bank/{name}") if name else None
    return found if found and found.IsA(UsdMedia.SpatialAudio) else None


def step_take(bank, number, cache):
    """The samples of a footstep's take for the walker's `number`th step (its takes in turn) and its gain."""
    takes = bank.GetAttribute("score:sound:takes")
    files = [resolved(asset, bank) for asset in takes.Get()] if takes and takes.Get() else \
        [resolved(UsdMedia.SpatialAudio(bank).GetFilePathAttr().Get(), bank)]
    return decoded_once(files[number % len(files)], cache), float(UsdMedia.SpatialAudio(bank).GetGainAttr().Get())


def footsteps_mix(stage, moments, frame_rate, cache):
    """The walker's footsteps along the moments, a stereo float mix as long as theirs (silent where it stands)."""
    place = stage.GetDefaultPrim().GetName()
    step = round(sound.SAMPLE_RATE / frame_rate)
    mix = np.zeros((len(moments) * step, 2))
    frames = stride_frames(moments)
    if not frames:
        return mix
    surfaces = sound.read(sound.SURFACES)
    meshes = floor_meshes(stage, place)
    for number, frame in enumerate(frames):
        feet = np.asarray(moments[frame]["eye"], dtype=float) - [0.0, EYE_OVER_FEET, 0.0]
        under = floor_under(meshes, feet)
        bank = footstep_of(stage, place, *under, surfaces) if under else None
        if bank is None:
            continue
        samples, level = step_take(bank, number, cache)
        begin = frame * step
        piece = samples[:len(mix) - begin] * level * math.sqrt(0.5)
        mix[begin:begin + len(piece)] += piece[:, None]
    return mix


def soundtrack(stage_path, moments, frame_rate, out):
    """What a camera hears along `moments` (one a frame: {"eye", "aim", "time": the stage's seconds}), written to
    `out` as a stereo WAV at sound.SAMPLE_RATE; its length in seconds. Silent when the stage has no sounds."""
    stage = Usd.Stage.Open(str(stage_path))
    cache = {}
    mix = sources_mix(stage, heard_sources(stage, cache), moments, frame_rate)
    mix += footsteps_mix(stage, moments, frame_rate, cache)
    sound.write_wav(mastered(mix), out)
    return len(mix) / sound.SAMPLE_RATE


def standing_before(moment, seconds, frame_rate):
    """The moments of a camera standing at `moment`'s view over the `seconds` before it, one a frame."""
    count = round(seconds * frame_rate)
    return [dict(moment, time=float(moment["time"]) - (count - index) / frame_rate) for index in range(count)]


def bed(stage_path, moment, seconds, frame_rate, out):
    """What the camera hears standing at a shot's first view over the `seconds` before it (soundtrack), so a card
    before the shot carries the place's own sound, joined to the shot's."""
    return soundtrack(stage_path, standing_before(moment, seconds, frame_rate), frame_rate, out)


def mastered(mix):
    """The mix at MIX_GAIN_DB, its peaks rounded off softly over LIMIT_KNEE of the ceiling, so none passes
    sound.PEAK_DBFS."""
    ceiling = 10.0 ** (sound.PEAK_DBFS / 20.0)
    scaled = mix * 10.0 ** (MIX_GAIN_DB / 20.0) / ceiling
    size = np.abs(scaled)
    over = size > LIMIT_KNEE
    rounded = LIMIT_KNEE + (1.0 - LIMIT_KNEE) * np.tanh((size - LIMIT_KNEE) / (1.0 - LIMIT_KNEE))
    return np.sign(scaled) * np.where(over, rounded, size) * ceiling
