"""Check the sound stage's prim writer (tools/usd/sound.py's audio_prim) without Blender and without the world's
release: on a small stage of the hub made here, with a world folder of short made sounds and the test's own sound
entries (the library's sounds are withdrawn, 2026-10-21), a room tone is a non-spatial loop, the console's hum a
spatial loop at the console at its level's gain, a library surface points at its footstep in the bank, every file is
copied into the stage and found from the layer, and the base is untouched; and the soundtrack hears a spatial sound
louder near it and on the side it stands.

Run: .venv/bin/python tools/usd/test_each_sound_is_laid_where_and_how_it_plays.py   (make tests runs it with the framework's environment)
"""
import os
import pathlib
import sys
import tempfile
import wave

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdMedia, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PLACE = "hub"


def tone(path, seconds=1.0, hertz=220.0):
    """A short sine as a 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 48000
    samples = (0.3 * np.sin(2 * np.pi * hertz * np.arange(int(rate * seconds)) / rate) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(samples.tobytes())


# The test's own sounds (a made tone each), as the assembly's entries name them: what a place plays comes from its
# design (score/stages/sound), never from a list here.
ENTRIES = {"habitat": {"file": "test/habitat.wav", "bus": "ambience", "loops": True, "volume_db": -12.0},
           "base_hum": {"file": "test/base_hum.wav", "bus": "ambience", "loops": True, "volume_db": -18.0},
           "console_hum": {"file": "test/console_hum.wav", "bus": "effects", "loops": True, "volume_db": -9.0,
                           "reach": 6.0},
           "footsteps_deck": {"file": "test/footsteps_deck.wav", "bus": "effects", "volume_db": -6.0}}


def world_folder(folder, sound):
    """A world folder holding a short tone at every file the test's sounds name."""
    for entry in ENTRIES.values():
        for file in sound.takes(entry):
            tone(folder / file)


def small_stage(out):
    """A stage like export.py's: its root over an empty edit layer and a base with the hub's console and a surface."""
    (out / "layers").mkdir(parents=True)
    Sdf.Layer.CreateNew(str(out / "layers/edit.usda")).Save()
    base = Usd.Stage.CreateNew(str(out / "layers/base.usda"))
    UsdGeom.Xform.Define(base, f"/{PLACE}")
    UsdGeom.Scope.Define(base, f"/{PLACE}/Library")
    UsdShade.Material.Define(base, f"/{PLACE}/Library/deck")
    console = UsdGeom.Xform.Define(base, f"/{PLACE}/Objects/console_1")
    console.AddTranslateOp().Set(Gf.Vec3d(4.0, 0.0, 0.0))
    console.GetPrim().CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set("console")
    base.GetRootLayer().Save()
    root = Sdf.Layer.CreateNew(str(out / f"{PLACE}.usda"))
    root.subLayerPaths.append("./layers/edit.usda")
    root.subLayerPaths.append("./layers/base.usda")
    root.defaultPrim = PLACE
    root.Save()


def laid_sounds(sound, out):
    """The test's sounds written into the stage's sound layer with sound.py's prim writer, as the assembly lays a
    place's accepted sound output: the room tones, the console's hum and the deck's footstep in the bank."""
    from pxr import UsdMedia
    layer = Sdf.Layer.CreateNew(str(out / sound.LAYER))
    root = Sdf.Layer.FindOrOpen(str(out / f"{PLACE}.usda"))
    root.subLayerPaths.insert(1, f"./{sound.LAYER}")
    root.Save()
    stage = Usd.Stage.Open(str(out / f"{PLACE}.usda"))
    stage.SetEditTarget(Usd.EditTarget(layer))
    written = [sound.audio_prim(stage, f"/{PLACE}/Sound/Room/{name}", name, ENTRIES[name], out,
                                aural=UsdMedia.Tokens.nonSpatial, playback=UsdMedia.Tokens.loopFromStage)
               for name in ("habitat", "base_hum")]
    written.append(sound.audio_prim(stage, f"/{PLACE}/Objects/console_1/Sound", "console_hum", ENTRIES["console_hum"],
                                    out, aural=UsdMedia.Tokens.spatial, playback=UsdMedia.Tokens.loopFromStage))
    bank = f"/{PLACE}/Sound/Bank/footsteps_deck"
    written.append(sound.audio_prim(stage, bank, "footsteps_deck", ENTRIES["footsteps_deck"], out,
                                    playback=UsdMedia.Tokens.onceFromStart))
    stage.GetPrimAtPath(f"/{PLACE}/Library/deck").CreateRelationship("score:sound:footstep").SetTargets(
        [Sdf.Path(bank)])
    layer.Save()
    assert all(written), written


def check_the_layer(sound, out):
    laid_sounds(sound, out)
    stage = Usd.Stage.Open(str(out / f"{PLACE}.usda"))
    tone_prim = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{PLACE}/Sound/Room/habitat"))
    assert tone_prim.GetAuralModeAttr().Get() == UsdMedia.Tokens.nonSpatial
    assert tone_prim.GetPlaybackModeAttr().Get() == UsdMedia.Tokens.loopFromStage
    hum = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{PLACE}/Objects/console_1/Sound"))
    assert hum and hum.GetAuralModeAttr().Get() == UsdMedia.Tokens.spatial
    level = hum.GetPrim().GetAttribute("score:sound:volumeDb").Get()
    assert abs(hum.GetGainAttr().Get() - 10 ** (level / 20)) < 1e-6
    assert pathlib.Path(hum.GetFilePathAttr().Get().resolvedPath).exists()
    deck = stage.GetPrimAtPath(f"/{PLACE}/Library/deck")
    targets = deck.GetRelationship("score:sound:footstep").GetTargets()
    assert targets and stage.GetPrimAtPath(targets[0]).IsA(UsdMedia.SpatialAudio), targets
    # The base is untouched: the sounds are the sound layer's alone.
    base = Sdf.Layer.FindOrOpen(str(out / "layers/base.usda"))
    assert not base.GetPrimAtPath(f"/{PLACE}/Sound")
    # A sound with no file picked (every withdrawn sound) is written nowhere: a gap, never a silent prim.
    assert sound.audio_prim(stage, f"/{PLACE}/Sound/Room/lost", "lost", {"file": ""}, out) is None
    assert not stage.GetPrimAtPath(f"/{PLACE}/Sound/Room/lost")


def check_the_soundtrack(sound, out):
    stage = out / f"{PLACE}.usda"
    near = [{"eye": [3.0, 1.6, 0.0], "aim": [3.0, 1.6, -5.0], "time": index / 12} for index in range(12)]
    far = [{"eye": [-20.0, 1.6, 0.0], "aim": [-20.0, 1.6, -5.0], "time": index / 12} for index in range(12)]
    sources = [source for source in sound.sources_of(Usd.Stage.Open(str(stage))) if source["spatial"]]
    assert len(sources) == 1
    level_near, pan = sound.heard_gain(sources[0], np.array(near[0]["eye"]), near[0]["aim"], [4.0, 0.0, 0.0])
    level_far, _ = sound.heard_gain(sources[0], np.array(far[0]["eye"]), far[0]["aim"], [4.0, 0.0, 0.0])
    assert level_near > 4 * level_far and pan > 0.3, (level_near, level_far, pan)
    seconds = sound.soundtrack(stage, near, 12, out / "near.wav")
    assert abs(seconds - 1.0) < 0.01
    with wave.open(str(out / "near.wav")) as stream:
        assert stream.getnchannels() == 2 and stream.getframerate() == sound.SAMPLE_RATE
        pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").reshape(-1, 2).astype(float)
    assert np.abs(pcm).max() <= 32767 * 10 ** (sound.PEAK_DBFS / 20) + 2
    assert np.abs(pcm).max() > 1000


def check_the_rounds(sound):
    """A looping motion's sounds come back every round; a one-off motion's play once from its start."""
    assert sound.rounds_of({"start": 1.0}) == [1.0]
    rounds = sound.rounds_of({"start": 0.0, "length": 14.0, "loop": True})
    assert rounds[:3] == [0.0, 14.0, 28.0] and rounds[-1] < sound.SOUND_SPAN_SECONDS <= rounds[-1] + 14.0


def main():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        os.environ["SCORE_LIB_FILES"] = str(folder / "world")
        import sound  # noqa: E402  (after the world folder is set)
        world_folder(folder / "world", sound)
        small_stage(folder / "stage")
        check_the_layer(sound, folder / "stage")
        check_the_soundtrack(sound, folder / "stage")
        check_the_rounds(sound)
    print("test_each_sound_is_laid_where_and_how_it_plays: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
