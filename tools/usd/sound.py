"""The sound stage: a place's sounds written into its OpenUSD stage, so an engine plays them from the stage alone.

    .venv/bin/python tools/usd/sound.py <place> --stage <the place's stage folder (export.py --out)>

It writes `<stage>/layers/sound.usda`, a layer of its own between the creator's edit layer and the base
(export.STAGE_LAYERS), and copies every file it names into `<stage>/assets/sound/`. Every sound is a
UsdMedia.SpatialAudio prim, its file (a name in the world's release, tools/assets/world.py), its gain (from the
catalogue's level in dB) and how it plays, with the framework's own facts beside it as `score:sound:*`:

    /<place>/Sound/Room/<name>        the place's room tones (data/sound/places.json): non-spatial, looping from the
                                      stage's start; outside on the Moon, what is heard through the suit instead
    <object>/Sound                    an object's own sound (its inventory row's `sound`: a hum, a buzz, a fan):
                                      spatial, at the object, looping
    <moving prim>/Sound_<n>           a sound the game plays with a motion (data/motion/<place>.json `sounds`):
                                      spatial, from its start time code, once or looping to its end
    /<place>/Sound/Bank/<name>        every surface sound (footstep, impact, scrape) as a sound an engine plays on
                                      an event; each library surface (/<place>/Library/<surface>) points at its own
                                      through the relationships score:sound:footstep, :impact and :scrape

A sound's fields are the catalogue's (data/sound/catalogue.json: defaults, then its entry) with data/sound/sounds.json
laid over them, as the game read them. `score:sound:takes` lists every take of a sound with several (footsteps: one
played at random each time); `score:sound:bus` is the part of the mix it goes through; `score:sound:reach` how far it
carries in metres (0: as far as it carries); `score:sound:groundThud` whether it is felt through boots, so heard in
vacuum too.

`soundtrack(stage, moments, out)` mixes what a camera moving through the stage hears, for the review's walk and the
demo's videos: the room tones as they are, each spatial sound at its gain over its distance from the eye (inverse
distance from 1 m, silent past its reach) and panned by where it stands across the view, each motion's sound from its
start; the mix brought to a level that is heard (a gain, the same over the whole track, its peak under -3 dBFS).
"""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys

import numpy as np
from pxr import Sdf, Usd, UsdGeom, UsdMedia

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools/assets"))
sys.path.insert(0, str(REPO / "tools/props/library"))
import world as world_assets  # noqa: E402

LAYER = "layers/sound.usda"
CATALOGUE = REPO / "data/sound/catalogue.json"
SOUNDS = REPO / "data/sound/sounds.json"
SURFACES = REPO / "data/sound/surfaces.json"
PLACES = REPO / "data/sound/places.json"
INVENTORIES = REPO / "data/inventory"
MOTIONS = REPO / "data/motion"
# Buses heard as they are, not from a spot in the room: a place's air, and the player's own suit.
NON_SPATIAL_BUSES = ("ambience", "suit")
HAPPENINGS = ("footstep", "impact", "scrape")
# The soundtrack's sample rate, the distance a spatial sound plays at its own gain, and the mix's peak ceiling.
SAMPLE_RATE = 48000
NEAR_METRES = 1.0
PEAK_DBFS = -3.0
# The mix is brought to this loudness (its RMS over the track, dBFS) unless that would take its peak over the ceiling.
MIX_RMS_DBFS = -24.0
# How long a looping motion's sounds are written for, in the stage's seconds: past the longest walk or demo place.
SOUND_SPAN_SECONDS = 60.0


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def entry_of(name, catalogue=None, sounds=None):
    """A sound's fields, as the game read them: the catalogue's defaults, its entry, then the data's over it; a sound
    only the data names takes its loop from its brief."""
    catalogue = catalogue or read(CATALOGUE)
    sounds = (sounds or read(SOUNDS))["sounds"]
    filled = dict(catalogue["defaults"])
    filled.update(catalogue["sounds"].get(name, {}))
    data = {key: value for key, value in sounds.get(name, {}).items() if key != "pick"}
    filled.update(data)
    if name not in catalogue["sounds"] and sounds.get(name, {}).get("pick", {}).get("loop"):
        filled["loops"] = True
    filled.pop("note", None)
    return filled


def takes(entry):
    """Every file an entry plays: one, several, or none when nothing is picked yet."""
    named = entry.get("file") or []
    return [named] if isinstance(named, str) else list(named)


def gain(volume_db):
    """A level in dB as UsdMedia's gain (a linear amplitude, 1 at 0 dB)."""
    return 10.0 ** (float(volume_db) / 20.0)


def copied(names, out):
    """The files copied once into the stage's assets/sound/ (from the world's release); each as the layer's path."""
    found = []
    for name in names:
        target = out / "assets" / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(world_assets.resolve(name), target)
        found.append(f"../assets/{name}")
    return found


def audio_prim(stage, path, name, entry, out, aural=None, playback=None, start=None, end=None, source=""):
    """One SpatialAudio prim playing a sound; None when the sound has no file picked."""
    files = copied(takes(entry), out)
    if not files:
        return None
    audio = UsdMedia.SpatialAudio.Define(stage, path)
    audio.CreateFilePathAttr(Sdf.AssetPath(files[0]))
    spatial = entry.get("bus") not in NON_SPATIAL_BUSES
    audio.CreateAuralModeAttr(aural or (UsdMedia.Tokens.spatial if spatial else UsdMedia.Tokens.nonSpatial))
    if playback is None:
        playback = UsdMedia.Tokens.loopFromStage if entry.get("loops") else UsdMedia.Tokens.onceFromStart
    audio.CreatePlaybackModeAttr(playback)
    audio.CreateGainAttr(gain(entry.get("volume_db", 0.0)))
    if start is not None:
        audio.CreateStartTimeAttr(Sdf.TimeCode(float(start)))
    if end is not None:
        audio.CreateEndTimeAttr(Sdf.TimeCode(float(end)))
    prim = audio.GetPrim()
    values = {"score:sound:name": (Sdf.ValueTypeNames.String, name),
              "score:sound:bus": (Sdf.ValueTypeNames.String, str(entry.get("bus", ""))),
              "score:sound:volumeDb": (Sdf.ValueTypeNames.Float, float(entry.get("volume_db", 0.0))),
              "score:sound:reach": (Sdf.ValueTypeNames.Float, float(entry.get("reach", 0.0))),
              "score:sound:groundThud": (Sdf.ValueTypeNames.Bool, bool(entry.get("ground_thud", False))),
              "score:sound:from": (Sdf.ValueTypeNames.String, source)}
    for key, (kind, value) in values.items():
        prim.CreateAttribute(key, kind).Set(value)
    if len(files) > 1:
        prim.CreateAttribute("score:sound:takes", Sdf.ValueTypeNames.AssetArray).Set(
            Sdf.AssetPathArray([Sdf.AssetPath(file) for file in files]))
    return audio


def room_tones(stage, place, out, found):
    """The place's room tones (and what the suit lets through outside), non-spatial loops from the stage's start."""
    record = read(PLACES)["places"].get(place, {"loops": []})
    names = list(record.get("loops", [])) + list(record.get("heard_through", []))
    UsdGeom.Scope.Define(stage, f"/{place}/Sound/Room")
    for name in names:
        if audio_prim(stage, f"/{place}/Sound/Room/{name}", name, entry_of(name), out,
                      aural=UsdMedia.Tokens.nonSpatial, playback=UsdMedia.Tokens.loopFromStage,
                      source=record.get("from", "")):
            found["room"] += 1


def row_sounds(place):
    """Each inventory row's own sound (a hum, a buzz), by its row id."""
    path = INVENTORIES / f"{place}.json"
    if not path.exists():
        return {}
    return {row["id"]: row["sound"] for row in read(path).get("rows", []) if row.get("sound")}


def object_sounds(stage, place, out, found):
    """Each object whose inventory row names a sound: a spatial loop at the object."""
    sounds = row_sounds(place)
    if not sounds:
        return
    for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{place}")):
        row = prim.GetAttribute("score:row")
        if not row or row.Get() not in sounds:
            continue
        name = sounds[row.Get()]
        entry = dict(entry_of(name), loops=True)
        if audio_prim(stage, prim.GetPath().AppendChild("Sound"), name, entry, out, aural=UsdMedia.Tokens.spatial,
                      playback=UsdMedia.Tokens.loopFromStage,
                      source=f"data/inventory/{place}.json row {row.Get()} (its `sound`)"):
            found["object"] += 1


def rounds_of(motion):
    """When each round of a motion starts, in the stage's seconds: once at its start, or for a looping motion every
    `length` seconds over SOUND_SPAN_SECONDS, so its sounds come back with it (a sound prim plays once)."""
    start = float(motion.get("start", 0.0))
    length = float(motion.get("length") or 0.0)
    if not motion.get("loop") or length <= 0.0:
        return [start]
    return [start + length * number for number in range(max(1, math.ceil(SOUND_SPAN_SECONDS / length)))]


def motion_sounds(stage, place, out, rate, found):
    """The sounds the game plays with each motion (data/motion/<place>.json), spatial at the moving prim from their
    start time code; a looping one plays until its end."""
    path = MOTIONS / f"{place}.json"
    if not path.exists():
        return
    for motion in read(path).get("motions", []):
        target = stage.GetPrimAtPath(motion.get("prim", ""))
        if not target:
            continue
        for round_start in rounds_of(motion):
            for number, sound in enumerate(motion.get("sounds", [])):
                start = (round_start + float(sound["at"])) * rate
                until = sound.get("loops_until")
                end = None if until is None else (round_start + float(until)) * rate
                playback = UsdMedia.Tokens.loopFromStartToEnd if end is not None else UsdMedia.Tokens.onceFromStart
                name = f"Sound_{number}" + (f"_{round(round_start * 1000)}" if round_start else "")
                if audio_prim(stage, target.GetPath().AppendChild(name), sound["name"], entry_of(sound["name"]), out,
                              aural=UsdMedia.Tokens.spatial, playback=playback, start=start, end=end,
                              source=sound.get("from", "")):
                    found["motion"] += 1


def surface_sounds(stage, place, out, found):
    """Every library surface's footstep, impact and scrape as bank sounds, each surface pointing at its own."""
    import export  # noqa: E402  (tools/usd; its import is heavy, so only here)
    import library  # noqa: E402
    sounds = read(SURFACES)
    variants = library.variants(library.theme_library())
    library_root = stage.GetPrimAtPath(f"/{place}/Library")
    if not library_root:
        return
    UsdGeom.Scope.Define(stage, f"/{place}/Sound/Bank")
    banked = set()
    for material in library_root.GetChildren():
        sound = export.sound_of(material.GetName(), variants, sounds)
        if sound is None:
            continue
        for happening in HAPPENINGS:
            name = sound.get(happening)
            if not name:
                continue
            bank = f"/{place}/Sound/Bank/{name}"
            if name not in banked:
                entry = dict(entry_of(name), loops=False)
                if not audio_prim(stage, bank, name, entry, out, playback=UsdMedia.Tokens.onceFromStart,
                                  source=f"data/sound/surfaces.json, the surface {sound['surface']}"):
                    continue
                banked.add(name)
                found["bank"] += 1
            material.CreateRelationship(f"score:sound:{happening}").SetTargets([Sdf.Path(bank)])
        material.CreateAttribute("score:sound:absorbs", Sdf.ValueTypeNames.Float).Set(float(sound.get("absorbs", 0.0)))


def write_layer(place, out):
    """The sound layer of the place's stage under `out`, rewritten whole; how many sounds of each kind it wrote."""
    import export  # noqa: E402
    out = pathlib.Path(out)
    path = out / LAYER
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.FindOrOpen(str(path)) or Sdf.Layer.CreateNew(str(path))
    layer.Clear()
    layer.documentation = "The place's sounds (tools/usd/sound.py); rewritten whole on every run."
    layer.Save()
    export.held_by_root(place, out)
    stage = Usd.Stage.Open(str(out / f"{place}.usda"))
    stage.SetEditTarget(Usd.EditTarget(layer))
    rate = stage.GetTimeCodesPerSecond()
    found = {"room": 0, "object": 0, "motion": 0, "bank": 0}
    room_tones(stage, place, out, found)
    object_sounds(stage, place, out, found)
    motion_sounds(stage, place, out, rate, found)
    surface_sounds(stage, place, out, found)
    layer.Save()
    return found


# --- what a camera hears ------------------------------------------------------------------------------------------

def decoded(path):
    """A sound file as mono float samples at SAMPLE_RATE (ffmpeg)."""
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1",
                          "-ar", str(SAMPLE_RATE), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def sources_of(stage):
    """Every SpatialAudio prim of a composed stage as a source: its samples, gain, how it plays, where it is."""
    found = []
    rate = stage.GetTimeCodesPerSecond()
    cache = {}
    for prim in stage.Traverse():
        if not prim.IsA(UsdMedia.SpatialAudio) or "/Sound/Bank/" in str(prim.GetPath()):
            continue
        audio = UsdMedia.SpatialAudio(prim)
        asset = audio.GetFilePathAttr().Get()
        file = asset.resolvedPath or str(pathlib.Path(prim.GetStage().GetRootLayer().realPath).parent / asset.path)
        if file not in cache:
            cache[file] = decoded(file)
        start, end = audio.GetStartTimeAttr().Get(), audio.GetEndTimeAttr().Get()
        reach = prim.GetAttribute("score:sound:reach")
        found.append({"samples": cache[file], "gain": float(audio.GetGainAttr().Get()),
                      "mode": str(audio.GetPlaybackModeAttr().Get()),
                      "spatial": str(audio.GetAuralModeAttr().Get()) == UsdMedia.Tokens.spatial,
                      "start": float(start.GetValue()) / rate if start is not None else 0.0,
                      "end": float(end.GetValue()) / rate if end is not None and end.GetValue() > 0 else None,
                      "reach": float(reach.Get()) if reach and reach.Get() else 0.0,
                      "prim": prim})
    return found


def heard_gain(source, eye, aim, at):
    """A spatial source's gain at the eye and its pan (-1 left .. 1 right) from where it stands across the view."""
    towards = np.asarray(at) - eye
    distance = float(np.linalg.norm(towards))
    if source["reach"] and distance > source["reach"]:
        return 0.0, 0.0
    level = min(1.0, NEAR_METRES / max(distance, 1e-6))
    forward = np.asarray(aim) - eye
    right = np.cross(forward, [0.0, 1.0, 0.0])
    norm = np.linalg.norm(right)
    pan = float(np.dot(towards, right) / (norm * max(distance, 1e-6))) if norm > 1e-9 else 0.0
    return level, max(-1.0, min(1.0, pan))


def played(source, seconds, count):
    """`count` samples of a source from `seconds` of the stage's time, as its playback mode plays them."""
    samples = source["samples"]
    if not len(samples):
        return np.zeros(count)
    offsets = np.arange(count) + round((seconds - source["start"]) * SAMPLE_RATE)
    alive = offsets >= 0
    if source["end"] is not None:
        alive &= offsets < round((source["end"] - source["start"]) * SAMPLE_RATE)
    if source["mode"].startswith("loop"):
        if source["mode"] == "loopFromStage":
            offsets = np.arange(count) + round(seconds * SAMPLE_RATE)
            alive = np.ones(count, dtype=bool)
        picked = samples[np.mod(offsets, len(samples))]
    else:
        alive &= offsets < len(samples)
        picked = samples[np.clip(offsets, 0, len(samples) - 1)]
    return np.where(alive, picked, 0.0)


def soundtrack(stage_path, moments, frame_rate, out):
    """What a camera hears along `moments` (one a frame: {"eye", "aim", "time": the stage's seconds}), written to
    `out` as a stereo WAV at SAMPLE_RATE; its length in seconds. Silent when the stage has no sounds."""
    stage = Usd.Stage.Open(str(stage_path))
    sources = sources_of(stage)
    cache = UsdGeom.XformCache()
    step = round(SAMPLE_RATE / frame_rate)
    mix = np.zeros((len(moments) * step, 2))
    for index, moment in enumerate(moments):
        eye = np.asarray(moment["eye"], dtype=float)
        seconds = float(moment["time"])
        rows = slice(index * step, (index + 1) * step)
        for source in sources:
            chunk = played(source, seconds, step) * source["gain"]
            if source["spatial"]:
                cache.SetTime(Usd.TimeCode(seconds * stage.GetTimeCodesPerSecond()))
                at = cache.GetLocalToWorldTransform(source["prim"]).ExtractTranslation()
                level, pan = heard_gain(source, eye, moment["aim"], at)
                angle = (pan + 1.0) * math.pi / 4.0
                mix[rows, 0] += chunk * level * math.cos(angle)
                mix[rows, 1] += chunk * level * math.sin(angle)
            else:
                mix[rows] += chunk[:, None] * math.sqrt(0.5)
    write_wav(levelled(mix), out)
    return len(mix) / SAMPLE_RATE


def levelled(mix):
    """The mix brought to MIX_RMS_DBFS, its peak held under PEAK_DBFS (one gain for the whole track)."""
    rms = float(np.sqrt(np.mean(mix ** 2))) if mix.size else 0.0
    peak = float(np.abs(mix).max()) if mix.size else 0.0
    if rms <= 0.0:
        return mix
    wanted = 10.0 ** (MIX_RMS_DBFS / 20.0) / rms
    ceiling = 10.0 ** (PEAK_DBFS / 20.0) / peak
    return mix * min(wanted, ceiling)


def write_wav(mix, out):
    """A float mix as a 16-bit stereo WAV."""
    import wave
    pcm = (np.clip(mix, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(out), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(pcm.tobytes())


def with_sound(video, track, out):
    """A video with a soundtrack laid under it (the picture copied, the sound as AAC)."""
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(track), "-map",
                    "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)],
                   check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place")
    parser.add_argument("--stage", required=True, type=pathlib.Path, help="the place's stage folder (export.py --out)")
    arguments = parser.parse_args()
    print(write_layer(arguments.place, arguments.stage))


if __name__ == "__main__":
    main()
