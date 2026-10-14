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


def test_the_row_declares_its_record_and_every_view():
    found = proposals.files()
    assert found["partitions"] == "{data}/definitions/partitions.json"
    assert all(f"view {scene['scene']} {view['id']}" in found
               for scene in proposals.record()["scenes"] for view in scene["views"])


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
