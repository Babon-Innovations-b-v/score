"""Check the sound stage (tools/usd/sound.py) without Blender and without the world's release: on a small stage of the
hub made here, with a world folder of short made sounds, the layer holds the hub's room tones as non-spatial loops,
the console's hum as a spatial loop at the console, a library surface pointing at its footstep in the bank, every
file copied into the stage and found from the layer; the layer sits between the edit layer and the base; and the
soundtrack hears a spatial sound louder near it and on the side it stands.

Run: .venv/bin/python tools/usd/sound_test.py   (make tests runs it with the framework's environment)
"""
import json
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


def world_folder(folder, sound):
    """A world folder holding a short tone at every file the sounds this test reaches name."""
    names = ["habitat", "base_hum", "console_hum"]
    surfaces = json.loads(sound.SURFACES.read_text())["surfaces"]
    names += [name for entry in surfaces.values() for name in (entry.get("footstep"), entry.get("impact"),
                                                                 entry.get("scrape")) if name]
    for name in names:
        for file in sound.takes(sound.entry_of(name)):
            tone(folder / file)
    (folder / ".checked").write_text("made by the test\n")  # so world.py takes it as fetched


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


def check_the_layer(sound, out):
    found = sound.write_layer(PLACE, out)
    assert found["room"] == 2 and found["object"] == 1 and found["bank"] >= 1, found
    root = Sdf.Layer.FindOrOpen(str(out / f"{PLACE}.usda"))
    assert list(root.subLayerPaths) == ["./layers/edit.usda", "./layers/sound.usda", "./layers/base.usda"]
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
        os.environ["SCORE_WORLD_ASSETS"] = str(folder / "world")
        import sound  # noqa: E402  (after the world folder is set)
        world_folder(folder / "world", sound)
        small_stage(folder / "stage")
        check_the_layer(sound, folder / "stage")
        check_the_soundtrack(sound, folder / "stage")
        check_the_rounds(sound)
    print("sound_test: ok")


if __name__ == "__main__":
    main()
