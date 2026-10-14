"""partition-proposals: the concept partition's SAM 2.1 proposals for scenes whose inventory is not landed yet (a new
place is boxed before it lands: no box is typed), one world node, paid (a rented card through
tools/props/cloud/segment.py, cleared by the runner like any paid row).

    data/definitions/partitions.json   {"scenes": [{"scene", "views": [{"id", "picture" (under {seeds})}], "why"}]}

For each scene, each view's picture is cut into partition.py's overlapping tiles, SAM 2.1 proposes a mask for every
element it finds on each tile, and the masks become proposals on the whole picture (partition.py's tile_proposals and
merged: specks and tile-filling masks dropped, one element found on two tiles kept once). The output: <scene>/tiles/
(the tiles and their masks), <scene>/tiles.json and <scene>/proposals.json, which the agent maps to the scene's rows
(partition.py apply) before its inventory lands. The gate `proposed`: every tile came back with its masks and every
view has proposals; a tile with none fails by name.
"""
import json
import os
import pathlib
import subprocess
import sys

from PIL import Image

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
RECORD = REPO / "data/definitions/partitions.json"
# One rented card a scene, about 2 minutes of work after its set-up (the ledger's segment runs of 2026-10-13: EUR 0.026
# each), rounded up.
EUROS_A_SCENE = 0.1


def record():
    return json.loads(RECORD.read_text()) if RECORD.exists() else {"scenes": []}


def files(place=None):
    """The request record and each scene's view pictures."""
    return {"partitions": "{data}/definitions/partitions.json",
            **{f"view {scene['scene']} {view['id']}": view["picture"]
               for scene in record()["scenes"] for view in scene["views"]}}


def euros():
    return round(EUROS_A_SCENE * max(1, len(record()["scenes"])), 2)


def partition_tools():
    """partition.py, imported with its folder on the path."""
    kept = list(sys.path)
    sys.path[:0] = [str(REPO / "tools/props/scene")]
    try:
        import partition
    finally:
        sys.path[:] = kept
    return partition


def segment(folder):
    """SAM 2.1's masks of every tile in `folder`, on a rented card (segment.py; the runner's ticket in the
    environment clears it)."""
    subprocess.run([sys.executable, str(REPO / "tools/props/cloud/segment.py"), str(folder), "--who",
                    "score partition-proposals"], check=True, env=dict(os.environ))


def tiles_of(scene, inputs, folder, partition):
    """Every view's tiles of one scene into folder/tiles, and where each lies; the views' sizes."""
    (folder / "tiles").mkdir(parents=True, exist_ok=True)
    placed, sizes = {}, {}
    for view in scene["views"]:
        picture = Image.open(inputs[f"view {scene['scene']} {view['id']}"]).convert("RGB")
        sizes[view["id"]] = picture.size
        for line, column, box in partition.tile_boxes(picture.size):
            name = f"{view['id']}__{line}{column}"
            picture.crop(box).save(folder / "tiles" / f"{name}.png")
            placed[name] = {"view": view["id"], "box": list(box)}
    (folder / "tiles.json").write_text(json.dumps(placed, indent=1))
    return placed, sizes


def make(inputs, out, seed, params, segmenter=segment):
    """Each scene's tiles, their masks and its proposals."""
    partition = partition_tools()
    scenes = json.loads(pathlib.Path(inputs["partitions"]).read_text())["scenes"]
    for scene in scenes:
        folder = out / scene["scene"]
        placed, sizes = tiles_of(scene, inputs, folder, partition)
        segmenter(folder / "tiles")
        proposals = partition.merged(partition.tile_proposals(placed, folder / "tiles" / "masks", sizes))
        (folder / "proposals.json").write_text(json.dumps(proposals, indent=1))
    (out / "scenes.json").write_text(json.dumps([scene["scene"] for scene in scenes]))


def proposals_faults(folder):
    return [] if (pathlib.Path(folder) / "scenes.json").exists() else ["no scenes.json"]


CONTRACT = contracts.Contract("partition-proposals", 1, proposals_faults)


def scene_faults(folder):
    """Why one scene's proposals are not whole: a tile with no masks, a view with no proposals."""
    placed = json.loads((folder / "tiles.json").read_text())
    proposals = json.loads((folder / "proposals.json").read_text())
    found = [f"{folder.name}: tile {name} came back with no masks" for name in placed
             if not (folder / "tiles" / "masks" / f"{name}.npz").exists()]
    views = {place["view"] for place in placed.values()}
    found += [f"{folder.name}: view {view} has no proposals" for view in sorted(views)
              if not any(item["view"] == view for item in proposals)]
    return found


def judge_proposed(output, inputs, evidence):
    """Every tile of every scene came back with its masks and every view has proposals (module docstring)."""
    scenes = json.loads((pathlib.Path(output) / "scenes.json").read_text())
    faults = [fault for scene in scenes for fault in scene_faults(pathlib.Path(output) / scene)]
    counted = sum(len(json.loads((pathlib.Path(output) / scene / "proposals.json").read_text())) for scene in scenes)
    reason = "; ".join(faults[:3]) if faults else f"{counted} proposals over {len(scenes)} scenes, every tile segmented"
    return checks.Verdict("proposed", checks.FAIL if faults else checks.PASS, reason,
                          {"scenes": len(scenes), "proposals": counted, "faults": len(faults)}, {"faults": "lower"},
                          tuple(faults))


CHECKS = (checks.Check("proposed", judge_proposed),)
