"""The inventory as a partition of the concept, with every box measured: the concept is cut into tiles, SAM 2.1 proposes
a mask for every element it finds on them, and the agent only maps each proposal to an inventory row or drops it with
a reason. No box is typed: a row's box is its proposals' box, and it records which proposals it came from
(`box_from`), so the box gate (box_check.py) can tell a measured box from a typed one.

    .venv/bin/python tools/props/scene/partition.py tiles <scene> <work folder>
    .venv/bin/python tools/props/cloud/segment.py <work folder>/tiles --who <session>      # SAM 2.1, a rented card
    .venv/bin/python tools/props/scene/partition.py proposals <scene> <work folder>
    .venv/bin/python tools/props/scene/partition.py apply <scene> <work folder> <mapping.json>

`tiles` writes each view's picture as overlapping tiles (tiles/<view>__<row><column>.png) and where each lies
(tiles.json). `proposals` reads segment.py's masks back, puts every mask's box on the whole picture, drops specks and
masks that take most of a tile, merges the same element found on two tiles, and writes proposals.json:
[{"id": "<view>.<n>", "view", "box", "area"}]. The mapping is {"<proposal id>": {"row": "<row id>"} |
{"drop": "<why>"} | {"new": "<words for a row the inventory lacks>"}}; a proposal lying inside a mapped one is a part
of it (PART) and needs no entry; `apply` refuses a mapping that leaves a
proposal unmapped, names a row the inventory has not got, or leaves a boxed row with no proposal and no `unseen`
reason, and otherwise sets each mapped row's box to the box round its proposals (for a row that `repeats`, its first
proposal: one clear example) and its `box_from`. The new elements are written to new-rows.json for the scene agent.
"""
import argparse
import json
import pathlib
import re
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import box_check  # noqa: E402
import inventory  # noqa: E402

# Tiles: about this many pixels a side, overlapping by OVERLAP pixels so an element on a seam is whole on one tile.
TILE = 720
OVERLAP = 96
# A proposal smaller than SPECK of its picture is a speck; one over MOST of its tile is the background.
SPECK = 0.0004
MOST = 0.6
# Two proposals from neighbouring tiles with boxes overlapping this much (over their union) are one element.
SAME = 0.6
# A proposal lying this much inside a mapped row's box, and smaller than it, is a part of that row (a drawer of a
# desk, a screen on a console) and needs no mapping of its own.
PART = 0.85


def tile_boxes(size):
    """The tiles of a picture of `size` as boxes on it, row by row."""
    wide, tall = size
    columns, lines = max(1, round(wide / TILE)), max(1, round(tall / TILE))
    step_x, step_y = wide / columns, tall / lines
    return [(line, column, (max(0, round(column * step_x - OVERLAP)), max(0, round(line * step_y - OVERLAP)),
                            min(wide, round((column + 1) * step_x + OVERLAP)), min(tall, round((line + 1) * step_y + OVERLAP))))
            for line in range(lines) for column in range(columns)]


def write_tiles(found, folder):
    """Every view's tiles as PNGs in folder/tiles and their places in folder/tiles.json; the places."""
    (folder / "tiles").mkdir(parents=True, exist_ok=True)
    placed = {}
    for view in found["plan"]["views"]:
        picture = Image.open(box_check.picture_path(view["picture"])).convert("RGB")
        for line, column, box in tile_boxes(picture.size):
            name = f"{view['id']}__{line}{column}"
            picture.crop(box).save(folder / "tiles" / f"{name}.png")
            placed[name] = {"view": view["id"], "box": list(box)}
    (folder / "tiles.json").write_text(json.dumps(placed, indent=1))
    return placed


def mask_boxes(npz):
    """Each mask's pixel box and area from one segment.py file."""
    shape = tuple(int(value) for value in npz["shape"])
    masks = np.unpackbits(npz["masks"], axis=-1, count=shape[1]).astype(bool) if len(npz["masks"]) else []
    found = []
    for mask in masks:
        rows, columns = np.nonzero(mask)
        if len(rows):
            found.append(([int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1],
                          int(mask.sum())))
    return shape, found


def overlap(first, second):
    """Two boxes' shared area over their union."""
    left, top = max(first[0], second[0]), max(first[1], second[1])
    right, bottom = min(first[2], second[2]), min(first[3], second[3])
    shared = max(0, right - left) * max(0, bottom - top)
    union = ((first[2] - first[0]) * (first[3] - first[1]) + (second[2] - second[0]) * (second[3] - second[1])
             - shared)
    return shared / union if union else 0.0


def tile_proposals(placed, masks_folder, sizes):
    """Every kept mask of every tile as a proposal on its whole picture, before merging."""
    found = []
    for name, place in placed.items():
        path = masks_folder / f"{name}.npz"
        if not path.exists():
            continue
        shape, boxes = mask_boxes(np.load(path))
        wide, tall = sizes[place["view"]]
        for box, area in boxes:
            if area < SPECK * wide * tall or area > MOST * shape[0] * shape[1]:
                continue
            left, top = place["box"][:2]
            found.append({"view": place["view"], "box": [box[0] + left, box[1] + top, box[2] + left, box[3] + top],
                          "area": area})
    return found


def merged(found):
    """The proposals with one element found on two tiles kept once, the bigger first; numbered per view."""
    kept = []
    for proposal in sorted(found, key=lambda item: -item["area"]):
        if all(other["view"] != proposal["view"] or overlap(other["box"], proposal["box"]) < SAME for other in kept):
            kept.append(proposal)
    counts = {}
    for proposal in kept:
        counts[proposal["view"]] = counts.get(proposal["view"], 0) + 1
        proposal["id"] = f"{proposal['view']}.{counts[proposal['view']]}"
    return kept


def union_box(boxes):
    return [min(box[0] for box in boxes), min(box[1] for box in boxes), max(box[2] for box in boxes),
            max(box[3] for box in boxes)]


def inside(small, big):
    """The share of box `small` that lies inside box `big`."""
    left, top = max(small[0], big[0]), max(small[1], big[1])
    right, bottom = min(small[2], big[2]), min(small[3], big[3])
    area = (small[2] - small[0]) * (small[3] - small[1])
    return max(0, right - left) * max(0, bottom - top) / area if area else 0.0


def parts(proposals, mapping):
    """The unmapped proposals that are parts of a mapped one (lying PART inside it and smaller): {id: its id}."""
    by_id = {proposal["id"]: proposal for proposal in proposals}
    mapped = [by_id[key] for key, entry in mapping.items() if "row" in entry and key in by_id]
    found = {}
    for proposal in proposals:
        if proposal["id"] in mapping:
            continue
        holder = next((other for other in mapped if other["view"] == proposal["view"]
                       and other["area"] > proposal["area"] and inside(proposal["box"], other["box"]) >= PART), None)
        if holder:
            found[proposal["id"]] = holder["id"]
    return found


def mapping_problems(found, proposals, mapping):
    """Everything that keeps a mapping from being applied, one line each."""
    rows = {row["id"]: row for row in found["rows"]}
    held = parts(proposals, mapping)
    problems = [f"proposal {proposal['id']} is neither mapped to a row nor dropped with a reason"
                for proposal in proposals if proposal["id"] not in mapping and proposal["id"] not in held]
    for key, entry in mapping.items():
        if "row" in entry and entry["row"] not in rows:
            problems.append(f"proposal {key} names the row '{entry['row']}', which the inventory has not got")
        if "drop" in entry and not str(entry["drop"]).strip():
            problems.append(f"proposal {key} is dropped without a reason")
        if not {"row", "drop", "new"} & set(entry):
            problems.append(f"proposal {key} is neither a row, a drop nor a new element")
    mapped = {entry["row"] for entry in mapping.values() if "row" in entry}
    problems.extend(f"row {name} has no proposal and no 'unseen' reason" for name, row in rows.items()
                    if name not in mapped and not row.get("unseen"))
    return problems


def apply(found, proposals, mapping):
    """The inventory with each mapped row boxed on its proposals (and `box_from` set); the new elements."""
    by_id = {proposal["id"]: proposal for proposal in proposals}
    chosen = {}
    for key, entry in mapping.items():
        if "row" in entry:
            chosen.setdefault(entry["row"], []).append(by_id[key])
    for row in found["rows"]:
        picked = chosen.get(row["id"])
        if not picked:
            continue
        picked = picked[:1] if row.get("repeats") else picked
        row["view"], row["box"] = picked[0]["view"], union_box([proposal["box"] for proposal in picked])
        row["box_from"] = [proposal["id"] for proposal in picked]
        row.pop("unseen", None)
    return [dict(by_id[key], words=entry["new"]) for key, entry in mapping.items() if "new" in entry]


def save_inventory(path, found):
    """The inventory written back in its own indent."""
    text = path.read_text()
    indent = re.match(r"\{\n(\s*)", text)
    path.write_text(json.dumps(found, indent=indent.group(1) if indent else None, ensure_ascii=False)
                    + ("\n" if text.endswith("\n") else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("tiles", "proposals", "apply"))
    parser.add_argument("scene")
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("mapping", nargs="?", type=pathlib.Path)
    options = parser.parse_args()
    path = inventory.path_of(options.scene)
    found = json.loads(path.read_text())
    if options.step == "tiles":
        print(f"{len(write_tiles(found, options.folder))} tiles in {options.folder / 'tiles'}")
    elif options.step == "proposals":
        placed = json.loads((options.folder / "tiles.json").read_text())
        proposals = merged(tile_proposals(placed, options.folder / "tiles" / "masks", box_check.view_sizes(found)))
        (options.folder / "proposals.json").write_text(json.dumps(proposals, indent=1))
        print(f"{len(proposals)} proposals in {options.folder / 'proposals.json'}")
    else:
        proposals = json.loads((options.folder / "proposals.json").read_text())
        mapping = json.loads(options.mapping.read_text())
        problems = mapping_problems(found, proposals, mapping)
        if problems:
            raise SystemExit("the mapping cannot be applied:\n  " + "\n  ".join(problems))
        new = apply(found, proposals, mapping)
        save_inventory(path, found)
        (options.folder / "new-rows.json").write_text(json.dumps(new, indent=1))
        print(f"{options.scene}: boxes set from {len(mapping)} proposals; {len(new)} new elements in new-rows.json")


if __name__ == "__main__":
    main()
