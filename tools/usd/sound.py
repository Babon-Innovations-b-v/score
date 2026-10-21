"""The sound stage's prim writer and its hearing helpers: what the assembly (score/stages/assembly/sounds.py) writes
a place's accepted sound output with, into `<stage>/layers/sound.usda`, a layer of its own between the creator's edit
layer and the base (export.STAGE_LAYERS), every file it names copied into `<stage>/assets/`. Every sound is a
UsdMedia.SpatialAudio prim (`audio_prim`), its file (a library reference, tools/library/library_files.py), its gain
(from its level in dB) and how it plays, with the framework's own facts beside it as `score:sound:*`, in this layout:

    /<place>/Sound/Room/<name>        the place's room tones: non-spatial, looping from the stage's start; outside
                                      on the Moon, what is heard through the suit instead
    <object>/Sound                    an object's own sound (a hum, a buzz, a fan): spatial, at the object, looping
    /<place>/Sound/Bank/<name>        every surface sound (footstep, impact, scrape) as a sound an engine plays on
                                      an event; each library surface (/<place>/Library/<surface>) points at its own
                                      through the relationships score:sound:footstep, :impact and :scrape

The old command-line writer, which read each place's room tones from data/sound/places.json and its objects' sounds
from the old inventories, is retired with them (owner, 2026-10-21: all old stuff is retired); what a scene plays is
worked out from its design (score/stages/sound).

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
sys.path.insert(0, str(REPO / "tools/library"))
sys.path.insert(0, str(REPO / "tools/props/library"))
import library_files  # noqa: E402

LAYER = "layers/sound.usda"
CATALOGUE = REPO / "data/sound/catalogue.json"
SOUNDS = REPO / "data/sound/sounds.json"
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
    """The files copied once into the stage's assets/ (from the library); each as the layer's path. A gap (a file
    the library does not hold) is left out."""
    found = []
    for name in names:
        target = out / "assets" / library_files.stage_name(name)
        if not target.exists():
            source = library_files.resolve(name)
            if source is None:
                library_files.say_gap(name, "a sound")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        found.append(f"../assets/{library_files.stage_name(name)}")
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


def rounds_of(motion):
    """When each round of a motion starts, in the stage's seconds: once at its start, or for a looping motion every
    `length` seconds over SOUND_SPAN_SECONDS, so its sounds come back with it (a sound prim plays once)."""
    start = float(motion.get("start", 0.0))
    length = float(motion.get("length") or 0.0)
    if not motion.get("loop") or length <= 0.0:
        return [start]
    return [start + length * number for number in range(max(1, math.ceil(SOUND_SPAN_SECONDS / length)))]


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
