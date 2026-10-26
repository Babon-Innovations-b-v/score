"""The animal rows follow the design alone, and their gates never pass on a missing record (animals/__init__.py).

A roaming row of a kept inventory gets a body and a clips row at the places whose design shows it, and nowhere else;
its body comes from its kind's rule (fish or four-legged), its length from its metres across, its picture from its box
widened by MARGIN; `made` and `clips made` answer unknown on a missing record, fail on a missing part, pass when whole.
Toy designs and a toy table; nothing paid runs.

Breaks that turn it red (each applied once and seen red, then reverted):
- `holding`: `applies` returns True for every place  -> the rows test (applies("hall")).
- `spec_of`: `max(row["size"][:2])` read as `row["size"][2]`, or the `fish` test inverted  -> the spec test.
- `MARGIN = 0.0`  -> the spec test (the cut-out is 100 x 60, not 120 x 72).
- `judge_made`: `wanted = ["model.glb"]` for every body  -> the gates test (a four-legged body with no rig passes).
- `judge_clips_made`: the review-frames list left out  -> the gates test.
"""
import json

from PIL import Image

from score.checks import FAIL, PASS, UNKNOWN
from score.stages import animals, design_layers, row_kinds

DOG = {"id": "guard_dog", "name": "guard dog", "noun": "dog", "size": [0.9, 0.3, 0.6], "box": [100, 100, 200, 160]}
KOI = {"id": "koi", "name": "koi", "noun": "koi", "size": [0.1, 0.4, 0.1], "box": [0, 0, 10, 10]}
CRATE = {"id": "crate", "name": "crate", "noun": "crate", "size": [1, 1, 1]}


def test_a_roaming_row_gets_a_body_and_clips_row_only_where_its_design_shows_it(tmp_path, monkeypatch):
    monkeypatch.setattr(design_layers, "KEPT", tmp_path)
    (tmp_path / "yard.json").write_text(json.dumps({"rows": [DOG, KOI, CRATE]}))
    (tmp_path / "hall.json").write_text(json.dumps({"rows": [CRATE]}))
    assert animals.animals_of("yard") == {"guard_dog", "koi"} and animals.animals_of("hall") == frozenset()
    assert [stage.name for stage in animals.rows()] == ["animal-body-guard_dog", "animal-clips-guard_dog",
                                                        "animal-body-koi", "animal-clips-koi"]
    body, clips = animals.rows_for("koi")
    assert body.paid and clips.paid and clips.after == {"animal-body-koi": ("animal-body", 1)}
    assert body.applies("yard") and not body.applies("hall") and not body.applies("nowhere")


def test_the_spec_takes_its_body_from_the_kind_its_length_from_its_metres_and_its_picture_from_its_box(tmp_path):
    kinds = row_kinds.table()
    assert animals.spec_of("yard", DOG, kinds, "p.png")["body"] == "quadruped"
    assert animals.spec_of("yard", DOG, kinds, "p.png")["length_m"] == 0.9  # the longer of 0.9 and 0.3 across
    koi = animals.spec_of("yard", KOI, kinds, "p.png")
    assert (koi["body"], koi["length_m"], koi["name"]) == ("fish", 0.4, "yard_koi")
    Image.new("RGB", (400, 300)).save(tmp_path / "concept.png")
    cut = animals.cut_out(tmp_path / "concept.png", DOG["box"], tmp_path / "cut.png")
    assert Image.open(cut).size == (120, 72)  # 100 x 60 widened by a tenth each side


def test_the_gates_answer_unknown_on_a_missing_record_fail_on_a_missing_part_and_pass_when_whole(tmp_path):
    made = animals.guarded("made", animals.judge_made)
    assert made.judge(tmp_path, {}, None).answer == UNKNOWN
    (tmp_path / "animal.json").write_text(json.dumps({"name": "yard_guard_dog", "body": "quadruped"}))
    (tmp_path / "model.glb").write_bytes(b"glTF")
    assert made.judge(tmp_path, {}, None).answer == FAIL  # four-legged and no rig
    (tmp_path / "rigged.glb").write_bytes(b"glTF")
    assert made.judge(tmp_path, {}, None).answer == PASS
    clips = animals.guarded("clips made", animals.judge_clips_made)
    assert clips.judge(tmp_path, {}, None).answer == UNKNOWN
    (tmp_path / "clips.json").write_text(json.dumps({"spec": {"clips": ["idle", "walk"]}, "glb": "dog.glb",
                                                     "usd": "usd"}))
    for name in ("dog.glb", "rig.json"):
        (tmp_path / name).write_text("x")
    (tmp_path / "usd").mkdir()
    (tmp_path / "review/idle").mkdir(parents=True)
    (tmp_path / "review/idle/0001.png").write_bytes(b"png")
    verdict = clips.judge(tmp_path, {}, None)
    assert verdict.answer == FAIL and verdict.findings == ("walk: no review frames",)
    (tmp_path / "review/walk").mkdir()
    (tmp_path / "review/walk/0001.png").write_bytes(b"png")
    assert clips.judge(tmp_path, {}, None).answer == PASS
