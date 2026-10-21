"""The partition-proposals row with a stand-in SAM 2.1 (no spend): the make cuts each view into partition.py's tiles,
segments them and writes the merged proposals; the gate passes whole proposals and fails a tile with no masks by name.

Run: .venv/bin/python score/stages/proposals/proposals_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from score import checks  # noqa: E402
from score.stages import proposals  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def stand_in_segment(tiles):
    """One mask a tile: a 40 x 30 px box at its top-left corner, packed as segment.py packs its masks."""
    (tiles / "masks").mkdir(exist_ok=True)
    for path in tiles.glob("*.png"):
        wide, tall = Image.open(path).size
        mask = np.zeros((1, tall, wide), dtype=bool)
        mask[0, 10:40, 10:50] = True
        np.savez(tiles / "masks" / f"{path.stem}.npz", shape=np.array([tall, wide]), masks=np.packbits(mask, axis=-1))


def made(root, segmenter):
    picture = Image.new("RGB", (1600, 900), "white")
    ImageDraw.Draw(picture).rectangle([200, 200, 600, 500], fill="black")
    picture.save(root / "concept.png")
    (root / "partitions.json").write_text(json.dumps({"scenes": [{"scene": "room", "views": [
        {"id": "v1", "picture": "x"}]}]}))
    (root / "out").mkdir()
    proposals.make({"partitions": root / "partitions.json", "view room v1": root / "concept.png"}, root / "out", 0,
                   {}, segmenter=segmenter)
    return root / "out"


def test_the_make_tiles_segments_and_proposes():
    root = folder()
    try:
        out = made(root, stand_in_segment)
        placed = json.loads((out / "room/tiles.json").read_text())
        found = json.loads((out / "room/proposals.json").read_text())
        assert len(placed) >= 2 and found and all(item["view"] == "v1" for item in found)
        assert proposals.judge_proposed(out, {}, {}).answer == checks.PASS
    finally:
        shutil.rmtree(root)


def test_a_tile_with_no_masks_fails_by_name():
    root = folder()
    try:
        def half(tiles):
            stand_in_segment(tiles)
            next((tiles / "masks").glob("*.npz")).unlink()
        verdict = proposals.judge_proposed(made(root, half), {}, {})
        assert verdict.answer == checks.FAIL and "came back with no masks" in verdict.reason, verdict.reason
    finally:
        shutil.rmtree(root)


def designed_as(places):
    """prop_data.designed answering for `places` alone (the machine's own designs left out); the one it replaced."""
    import score.stages.props.prop_data as prop_data
    kept = prop_data.designed
    prop_data.designed = lambda place: place in places
    return kept


def test_the_row_declares_its_record_and_every_view():
    import score.stages.props.prop_data as prop_data
    kept = designed_as(set())
    try:
        found = proposals.files()
        assert found["partitions"] == "{data}/definitions/partitions.json"
        assert all(f"view {scene['scene']} {view['id']}" in found
                   for scene in proposals.record()["scenes"] for view in scene["views"])
    finally:
        prop_data.designed = kept


def test_a_designed_scene_is_asked_no_more_and_its_lost_views_are_read_by_nothing():
    """Both ways: with the cockpit designed (its locked concept read into its hand-in) its six old views are no input
    and the make leaves it out; the scenes not designed stay asked, priced a scene each."""
    import score.stages.props.prop_data as prop_data
    scenes = proposals.record()["scenes"]
    kept = designed_as({"cockpit"})
    try:
        found = proposals.files()
        assert not [name for name in found if name.startswith("view cockpit ")], found
        assert [scene["scene"] for scene in proposals.asked()] == [scene["scene"] for scene in scenes
                                                                   if scene["scene"] != "cockpit"]
        assert proposals.euros() == round(proposals.EUROS_A_SCENE * (len(scenes) - 1), 2)
        assert [scene["scene"] for scene in proposals.declared(scenes, found)] == [
            scene["scene"] for scene in proposals.asked()]
        prop_data.designed = lambda place: True
        assert proposals.asked() == [] and proposals.euros() == 0 and set(proposals.files()) == {"partitions"}
    finally:
        prop_data.designed = kept


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
