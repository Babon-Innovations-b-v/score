"""The library-clips row with a fake library command and a fake render (no Blender, no card, no spend): its framing,
its price, which entries it wants, the sample shapes, and the make and gate end to end (frames encoded here with the
real ffmpeg, the gate's frames counted with ffprobe).

Run: .venv/bin/python score/stages/library/clips/clips_test.py
"""
import json
import math
import os
import pathlib
import shutil
import sys
import tempfile

HOME = pathlib.Path(tempfile.mkdtemp(prefix="clips-test-"))
os.environ["PROPS_HOME"] = str(HOME / "props")  # before score.store reads it
for variable in ("SCORE_LIB_BACKEND", "SCORE_LIB_HANDOVER", "SCORE_SPEND_TICKET"):
    os.environ.pop(variable, None)
REPO = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from PIL import Image  # noqa: E402

from score import checks  # noqa: E402
from score.stages import library  # noqa: E402
from score.stages.library import backend, clips  # noqa: E402
from score.stages.library.clips import sample  # noqa: E402
from score.stages.library.clips.blender import framing  # noqa: E402

backend.library_files.defaults = lambda: {}  # no score_lib checkout beside score's
LIBRARY = HOME / "library"
LIBRARY.mkdir()
os.environ.update({"SCORE_LIB_ROOT": str(LIBRARY), "SCORE_LIB_BLOBS_DIR": str(HOME / "blobs"),
                   "SCORE_LIB_COMMAND": f"{sys.executable} {LIBRARY / 'fake.py'}"})

# The fake library: clip-plan writes one model's plan (its stage a layer with a default prim) and a sound's refusal;
# clip-attach takes every clip it is given and says it saved them.
FAKE = '''import json, pathlib, sys
words = sys.argv[sys.argv.index("--root") + 2:]
value = lambda option: words[words.index(option) + 1]
if words[0] == "clip-plan":
    into = pathlib.Path(value("--into"))
    rows = []
    for address in [word for word in words[1:words.index("--into")] if word.startswith("model/")]:
        folder = into / "items" / address.replace("/", "-").replace("@", "-")
        folder.mkdir(parents=True)
        (folder / "model.usda").write_text('#usda 1.0\\n(\\n    defaultPrim = "crate"\\n)\\ndef Xform "crate" {}\\n')
        (folder / "clip.usda").write_text('#usda 1.0\\n(\\n    subLayers = [@' + str(folder / "model.usda") + '@]\\n)\\n')
        rows.append({"address": address, "kind": "model", "shelf": "model", "open": str(folder / "clip.usda"),
                     "search": str(into), "focus": None, "points": None, "material": None, "start": 0.0, "end": 0.0,
                     "per_second": 24.0, "why": ""})
    rows.append({"address": "sound/hum@1", "kind": "sound", "shelf": None, "why": "no clip for this sound"})
    (into / "clip-plan.json").write_text(json.dumps(rows))
if words[0] == "clip-attach":
    rows = json.loads(pathlib.Path(value("--clips")).read_text())
    assert all(pathlib.Path(row["file"]).is_file() for row in rows)
    pathlib.Path(value("--out")).write_text(json.dumps({"attached": [row["address"] for row in rows], "refused": [],
                                                        "saved": {"committed": "c" * 40, "pushed": True, "why": ""}}))
'''
(LIBRARY / "fake.py").write_text(FAKE)


RENDERED = []  # the shares each fake render was given, one list of slugs a job


def fake_render(jobs, log, blank=False):
    """Each share's frames as its Blender job would bring them back: a moving bar on grey (one flat grey when
    `blank`, as the blank clips of 2026-10-20 came back); its rendered.json."""
    for manifest, frames, minutes in jobs:
        items = json.loads(manifest.read_text())["items"]
        RENDERED.append([item["slug"] for item in items])
        for item in items:
            folder = frames / item["slug"]
            folder.mkdir(parents=True)
            for number in range(framing.FRAMES):
                picture = Image.new("RGB", (64, 36), (89, 87, 84) if blank else (40, 40, 40))
                if not blank:
                    picture.paste((220, 180, 60), (number % 60, 8, number % 60 + 4, 28))
                picture.save(folder / f"f{number:03d}-look.png")
        (frames / "rendered.json").write_text(json.dumps({item["slug"]: {"rendered": True} for item in items}))
    log.write_text("fake render")


def blank_render(jobs, log):
    fake_render(jobs, log, blank=True)


def test_framing():
    turn = framing.views("turn", [-1, 0, -1], [1, 2, 1])
    assert len(turn) == framing.FRAMES and all(view["aim"] == [0.0, 1.0, 0.0] and view["look_only"] for view in turn)
    distances = {round(math.dist(view["eye"], view["aim"]), 6) for view in turn}
    assert len(distances) == 1, distances
    play = framing.views("play", [0, 0, 0], [1, 1, 1], start=10.0, end=20.0, per_second=24.0)
    assert len({tuple(view["eye"]) for view in play}) == 1
    codes = [view["frame"] for view in play]
    assert codes[0] == 10.0 and max(codes) <= 20.0 + 1e-9 and codes[11] == 10.0  # codes 10 to 20 played, then again
    long = framing.time_codes(0.0, 960.0, 24.0)
    assert long[0] == 0.0 and abs(long[-1] - 960.0) < 1e-6  # a long move plays whole, sped up
    print("framing: ok")


def test_shares():
    assert clips.CLIPS_A_CARD == 7 and [len(share) for share in clips.shares(range(16))] == [7, 7, 2]
    assert clips.shares([]) == [] and clips.forecast(16)["high_minutes"] == clips.forecast(7)["high_minutes"]
    assert clips.forecast(8)["high_euros"] > clips.forecast(7)["high_euros"] + clips.per_item()["high_euros"]  # a card's set-up
    print("shares: ok")


def test_price():
    one = clips.per_item()
    assert one["frames"] == 96 and 0 < one["likely_euros"] < one["high_euros"] and "films" in one["from"]
    assert clips.forecast(0)["high_euros"] == 0.0
    assert clips.EUROS == clips.forecast(clips.PLACE_ITEMS)["high_euros"]
    print(f"price: EUR {one['likely_euros']} likely, {one['high_euros']} high an item; row reserves {clips.EUROS}")


def test_wanted():
    report = {"entries": [{"address": "model/a@1", "status": "new"}, {"address": "model/b@2", "status": "unchanged"},
                          {"address": "model/c@2", "status": "new version"}, {"address": None, "status": "refused"}]}
    assert clips.wanted(report) == ["model/a@1", "model/c@2"]
    print("wanted: ok")


def test_sample_shapes():
    from pxr import Usd, UsdShade
    folder = HOME / "sample"
    folder.mkdir()
    (folder / "material.usda").write_text('#usda 1.0\n(\n    defaultPrim = "steel"\n)\ndef Material "steel" {}\n')
    (folder / "clip.usda").write_text(f'#usda 1.0\n(\n    subLayers = [@{folder / "material.usda"}@]\n)\n')
    row = {"open": str(folder / "clip.usda"), "shelf": "surface", "material": "/steel", "points": None}
    stage = Usd.Stage.Open(str(sample.item_stage(folder / "surface", row)))
    bound = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath("/Sample/Ball")).ComputeBoundMaterial()[0]
    assert bound and str(bound.GetPath()) == "/steel" and stage.GetDefaultPrim().GetName() == "steel"
    from pxr import UsdGeom
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0 and UsdGeom.GetStageUpAxis(stage) == "Y"  # metres, y up
    lamps = {**row, "shelf": "lamp", "points": [[0, 3, 0], [4, 3.5, 2]]}
    stage = Usd.Stage.Open(str(sample.item_stage(folder / "lamp", lamps)))
    assert stage.GetPrimAtPath("/Sample/Ground") and stage.GetPrimAtPath("/Sample/BackWall")
    assert sample.focus("sky") == ["/Sample"] and sample.focus("model") is None  # a sky frames its room
    print("sample shapes: ok")


def handover_output(statuses):
    folder = HOME / "handover"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir()
    entries = [{"address": address, "status": status} for address, status in statuses.items()]
    (folder / "handover.json").write_text(json.dumps({"entries": entries}))
    return folder


def made(name, statuses):
    out = HOME / name
    out.mkdir()
    clips.make({"library": str(handover_output(statuses))}, out, 0, {})
    return out


def test_make_and_gate():
    clips.render = fake_render
    out = made("made", {"model/crate@1": "new", "sound/hum@1": "new", "model/old@1": "unchanged"})
    rows = json.loads((out / "clips.json").read_text())
    assert [(row["address"], row["planned"]) for row in rows] == [("model/crate@1", True), ("sound/hum@1", False)]
    assert (out / "model-crate-1.mp4").is_file() and not (out / ".work").exists()
    verdict = clips.judge_clipped(out, {}, {})
    assert verdict.answer == checks.PASS, verdict.reason
    nothing = made("nothing", {"model/old@1": "unchanged"})
    assert clips.judge_clipped(nothing, {}, {}).answer == checks.PASS
    (out / "model-crate-1.mp4").unlink()
    verdict = clips.judge_clipped(out, {}, {})
    assert verdict.answer == checks.FAIL and "None of 96 frames" in verdict.reason, verdict.reason
    RENDERED.clear()
    many = made("many", {f"model/crate{number}@1": "new" for number in range(9)})  # two shares: two jobs, two cards
    assert [len(share) for share in RENDERED] == [7, 2], RENDERED
    assert clips.judge_clipped(many, {}, {}).answer == checks.PASS
    clips.render = blank_render
    blank = made("blank", {"model/crate@1": "new"})
    assert json.loads((blank / clips.ATTACH).read_text())["attached"] == []  # a failed gate never attaches
    verdict = clips.judge_clipped(blank, {}, {})
    assert verdict.answer == checks.FAIL and "model/crate@1: blank" in verdict.reason, verdict.reason
    print("make and gate: ok")


def test_table():
    from score import stages
    row = next(stage for stage in stages.STAGES if stage.name == clips.ROW)
    assert row.paid and row.euros == clips.EUROS and set(row.after) == {library.PLACE_ROW} and row.grain == "place"
    assert not any(clips.ROW in stage.after for stage in stages.STAGES)  # nothing reads the clips
    sampled = next(stage for stage in stages.STAGES if stage.name == clips.SAMPLE_ROW)
    assert sampled.paid and sampled.grain == "world" and not sampled.after
    assert sampled.euros == clips.forecast(len(clips.sample_addresses()))["high_euros"]
    assert not any(clips.SAMPLE_ROW in stage.after for stage in stages.STAGES)
    print("table: ok")


if __name__ == "__main__":
    try:
        test_framing()
        test_shares()
        test_price()
        test_wanted()
        test_sample_shapes()
        test_make_and_gate()
        test_table()
    finally:
        shutil.rmtree(HOME, ignore_errors=True)
