"""The animal rows follow the design alone, and their gates never pass on a missing record (animals/__init__.py).

A roaming row of a kept inventory gets a body and a clips row at the places whose design shows it, and nowhere else;
its body comes from its kind's rule (fish or four-legged), its length from its metres across, its picture from its box
widened by MARGIN; `made` and `clips made` answer unknown on a missing record, fail on a missing part, pass when whole.
One toy world (two designs, a concept picture, the toy table) and a table of record folders; nothing paid runs.

Breaks that turn it red (each applied once and seen red, then reverted):
- `holding`: `applies` returns True for every place  -> the guard_dog / koi rows (applies("hall")).
- `spec_of`: `max(row["size"][:2])` read as `row["size"][2]`, or the `fish` test inverted  -> the ANIMALS rows.
- `MARGIN = 0.0`  -> the ANIMALS rows (the dog's cut-out is 100 x 60, not 120 x 72).
- `judge_made`: `wanted = ["model.glb"]` for every body  -> the RECORDS row "four-legged, no rig" (it passes).
- `judge_clips_made`: the review-frames list left out  -> the RECORDS row "walk has no review frames".
"""
import json

from PIL import Image

from score.checks import FAIL, PASS, UNKNOWN
from score.stages import animals, design_layers, row_kinds

DOG = {"id": "guard_dog", "name": "guard dog", "noun": "dog", "size": [0.9, 0.3, 0.6], "box": [100, 100, 200, 160]}
KOI = {"id": "koi", "name": "koi", "noun": "koi", "size": [0.1, 0.4, 0.1], "box": [0, 0, 10, 10]}
CRATE = {"id": "crate", "name": "crate", "noun": "crate", "size": [1, 1, 1]}
DESIGNS = {"yard": [DOG, KOI, CRATE], "hall": [CRATE]}

# Each roaming row of the yard: its body, its length (the longer of its metres across), its spec name and its
# cut-out of a 400 x 300 concept (its box widened by a tenth each side, clipped at the picture's edge).
ANIMALS = {
    "guard_dog": (DOG, "quadruped", 0.9, "yard_guard_dog", (120, 72)),
    "koi": (KOI, "fish", 0.4, "yard_koi", (11, 11)),
}

ANIMAL = {"animal.json": json.dumps({"name": "yard_guard_dog", "body": "quadruped"}), "model.glb": "glTF"}
FISH = {"animal.json": json.dumps({"name": "yard_koi", "body": "fish"}), "model.glb": "glTF"}
CLIPS = {"clips.json": json.dumps({"spec": {"clips": ["idle", "walk"]}, "glb": "dog.glb", "usd": "usd"}),
         "dog.glb": "x", "rig.json": "x", "usd/": None, "review/idle/0001.png": "png"}
# A record folder's files (a name ending in / is a folder) -> the `made` answer, the `clips made` answer, its findings.
RECORDS = [
    ("nothing written", {}, UNKNOWN, UNKNOWN, None),
    ("four-legged, no rig", ANIMAL, FAIL, UNKNOWN, None),
    ("four-legged with its rig", {**ANIMAL, "rigged.glb": "glTF"}, PASS, UNKNOWN, None),
    ("fish needs no rig", FISH, PASS, UNKNOWN, None),
    ("walk has no review frames", CLIPS, UNKNOWN, FAIL, ("walk: no review frames",)),
    ("every clip reviewed", {**CLIPS, "review/walk/0001.png": "png"}, UNKNOWN, PASS, ()),
]


def written(folder, files):
    """`folder` holding `files`."""
    folder.mkdir()
    for name, text in files.items():
        if text is None:
            (folder / name).mkdir(parents=True)
        else:
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(text)
    return folder


def test_animal_rows_follow_the_design(tmp_path, monkeypatch):
    kept = tmp_path / "kept"
    kept.mkdir()
    monkeypatch.setattr(design_layers, "KEPT", kept)
    for place, rows in DESIGNS.items():
        (kept / f"{place}.json").write_text(json.dumps({"rows": rows}))
    Image.new("RGB", (400, 300)).save(tmp_path / "concept.png")
    kinds = row_kinds.table()

    shown = {"yard": set(ANIMALS), "hall": set(), "nowhere": set()}
    for place, ids in shown.items():
        assert animals.animals_of(place) == ids, place
    stages = animals.rows()
    assert [stage.name for stage in stages] == [f"animal-{part}-{row}" for row in sorted(ANIMALS)
                                                for part in ("body", "clips")]
    for body, clips in zip(stages[::2], stages[1::2]):
        row = body.params["row"]
        assert body.paid and clips.paid and clips.after == {f"animal-body-{row}": ("animal-body", 1)}, row
        for stage in (body, clips):
            assert {place for place in shown if stage.applies(place)} == {"yard"}, stage.name

    for row_id, (row, body, length, name, cut_size) in ANIMALS.items():
        spec = animals.spec_of("yard", row, kinds, "p.png")
        assert (spec["body"], spec["length_m"], spec["name"]) == (body, length, name), row_id
        cut = animals.cut_out(tmp_path / "concept.png", row["box"], tmp_path / f"{row_id}.png")
        assert Image.open(cut).size == cut_size, row_id

    made = animals.guarded("made", animals.judge_made)
    clips = animals.guarded("clips made", animals.judge_clips_made)
    for case, (label, files, made_answer, clips_answer, findings) in enumerate(RECORDS):
        folder = written(tmp_path / f"record{case}", files)
        assert made.judge(folder, {}, None).answer == made_answer, label
        verdict = clips.judge(folder, {}, None)
        assert verdict.answer == clips_answer, label
        if findings is not None:
            assert verdict.findings == findings, label
