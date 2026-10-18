"""Check what a camera hears (tools/usd/hearing.py) without Blender and without the world's release: on a small stage of
the hub made here (sound.py's layer over it, with a world folder of short made sounds), a spatial sound is heard louder
near it and on the side it stands; a shown place's room tone is not heard, and outside (the place's own room on the
suit's bus) only what the boots feel carries; a walk steps on the floor's footstep and a stand does not; every track is
mixed at the one gain, so a quieter stage stays quieter, its peak under the ceiling; and a bed is what the camera hears
standing before its first moment.

Run: .venv/bin/python tools/usd/hearing_test.py   (make tests runs it with the framework's environment)
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
    floor = UsdGeom.Mesh.Define(base, f"/{PLACE}/Structure/deck_floor")
    floor.CreatePointsAttr([(-30, 0, -30), (30, 0, -30), (30, 0, 30), (-30, 0, 30)])
    floor.CreateFaceVertexCountsAttr([3, 3])
    floor.CreateFaceVertexIndicesAttr([0, 2, 1, 0, 3, 2])
    deck = UsdShade.Material(base.GetPrimAtPath(f"/{PLACE}/Library/deck"))
    UsdShade.MaterialBindingAPI.Apply(floor.GetPrim()).Bind(deck)
    base.GetRootLayer().Save()
    root = Sdf.Layer.CreateNew(str(out / f"{PLACE}.usda"))
    root.subLayerPaths.append("./layers/edit.usda")
    root.subLayerPaths.append("./layers/base.usda")
    root.defaultPrim = PLACE
    root.Save()


def check_the_soundtrack(sound, hearing, out):
    stage = out / f"{PLACE}.usda"
    near = [{"eye": [3.0, 1.6, 0.0], "aim": [3.0, 1.6, -5.0], "time": index / 12} for index in range(12)]
    far = [{"eye": [-20.0, 1.6, 0.0], "aim": [-20.0, 1.6, -5.0], "time": index / 12} for index in range(12)]
    sources = [source for source in hearing.sources_of(Usd.Stage.Open(str(stage))) if source["spatial"]]
    assert len(sources) == 1
    level_near, pan = hearing.heard_gain(sources[0], np.array(near[0]["eye"]), near[0]["aim"], [4.0, 0.0, 0.0])
    level_far, _ = hearing.heard_gain(sources[0], np.array(far[0]["eye"]), far[0]["aim"], [4.0, 0.0, 0.0])
    assert level_near > 4 * level_far and pan > 0.3, (level_near, level_far, pan)
    seconds = hearing.soundtrack(stage, near, 12, out / "near.wav")
    assert abs(seconds - 1.0) < 0.01
    with wave.open(str(out / "near.wav")) as stream:
        assert stream.getnchannels() == 2 and stream.getframerate() == sound.SAMPLE_RATE
        pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").reshape(-1, 2).astype(float)
    assert np.abs(pcm).max() <= 32767 * 10 ** (sound.PEAK_DBFS / 20) + 2
    assert np.abs(pcm).max() > 1000


def walk(eye_x, steps, frame_rate=12, still=False):
    """A camera's moments walking (or standing) along x at eye height, looking ahead."""
    return [{"eye": [eye_x + (0.0 if still else 0.1 * index), 1.62, 0.0], "aim": [eye_x, 1.62, -5.0],
             "time": index / frame_rate} for index in range(steps)]


def check_what_is_heard(sound, hearing, out):
    """A shown place's room tone is left out; outside, only what the boots feel and the suit's own room carry."""
    stage = Usd.Stage.Open(str(out / f"{PLACE}.usda"))
    stage.SetEditTarget(Usd.EditTarget(Sdf.Layer.FindOrOpen(str(out / sound.LAYER))))
    shown = UsdMedia.SpatialAudio.Define(stage, f"/{PLACE}/Places/tube/Sound/Room/link_tube")
    shown.CreateFilePathAttr(stage.GetPrimAtPath(f"/{PLACE}/Sound/Room/habitat").GetAttribute("filePath").Get())
    shown.CreateAuralModeAttr(UsdMedia.Tokens.nonSpatial)
    shown.CreateGainAttr(1.0)
    heard = [str(source["prim"].GetPath()) for source in hearing.heard_sources(stage)]
    assert f"/{PLACE}/Places/tube/Sound/Room/link_tube" not in heard and f"/{PLACE}/Sound/Room/habitat" in heard, heard
    room = stage.GetPrimAtPath(f"/{PLACE}/Sound/Room/habitat")
    room.GetAttribute("score:sound:bus").Set("suit")
    outside = hearing.heard_sources(stage)
    assert not any(source["spatial"] for source in outside), "a hum carried through no air"
    room.GetAttribute("score:sound:bus").Set("ambience")
    stage.RemovePrim(shown.GetPath())


def check_the_footsteps(sound, hearing, out):
    stage = Usd.Stage.Open(str(out / f"{PLACE}.usda"))
    walked = hearing.footsteps_mix(stage, walk(-10.0, 24), 12, {})
    stood = hearing.footsteps_mix(stage, walk(-10.0, 24, still=True), 12, {})
    assert len(hearing.stride_frames(walk(-10.0, 24))) == 4
    assert np.abs(walked).max() > 0 and not np.abs(stood).any()


def check_one_level(sound, hearing, out):
    """The soundtrack is mixed at one gain: halving every source halves the track; nothing passes the ceiling."""
    loud = np.full((4800, 2), 0.01)
    assert abs(hearing.mastered(loud).max() / hearing.mastered(loud / 2).max() - 2.0) < 1e-6
    assert np.abs(hearing.mastered(np.full((10, 2), 5.0))).max() <= 10 ** (sound.PEAK_DBFS / 20) + 1e-9
    seconds = hearing.bed(out / f"{PLACE}.usda", {"eye": [-10.0, 1.62, 0.0], "aim": [-10.0, 1.62, -5.0], "time": 4.0},
                        2.0, 12, out / "bed.wav")
    assert abs(seconds - 2.0) < 0.01
    before = hearing.standing_before({"eye": [0, 0, 0], "aim": [0, 0, -1], "time": 4.0}, 2.0, 12)
    assert len(before) == 24 and abs(before[0]["time"] - 2.0) < 1e-9 and before[-1]["time"] < 4.0


def main():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        os.environ["SCORE_WORLD_ASSETS"] = str(folder / "world")
        import sound  # noqa: E402  (after the world folder is set)
        import hearing  # noqa: E402
        world_folder(folder / "world", sound)
        small_stage(folder / "stage")
        sound.write_layer(PLACE, folder / "stage")
        check_the_soundtrack(sound, hearing, folder / "stage")
        check_what_is_heard(sound, hearing, folder / "stage")
        check_the_footsteps(sound, hearing, folder / "stage")
        check_one_level(sound, hearing, folder / "stage")
    print("hearing_test: ok")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
