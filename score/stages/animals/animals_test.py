"""The animal rows from a design alone: a roaming row gets a body and a clips row at the place showing it, its body by
its kind's rule, its picture cut by its box, and the gates answer pass, fail and unknown. Nothing paid runs."""
import json

from PIL import Image

from score.checks import FAIL, PASS, UNKNOWN
from score.stages import animals, design_layers, row_kinds

INVENTORY = {"rows": [{"id": "guard_dog", "name": "guard dog", "noun": "dog", "size": [0.9, 0.3, 0.6],
                       "box": [100, 100, 200, 160]},
                      {"id": "koi", "name": "koi", "noun": "koi", "size": [0.1, 0.4, 0.1], "box": [0, 0, 10, 10]},
                      {"id": "crate", "name": "crate", "noun": "crate", "size": [1, 1, 1]}]}


def test_a_roaming_row_gets_a_body_and_clips_row_where_its_design_shows_it(tmp_path, monkeypatch):
    monkeypatch.setattr(design_layers, "KEPT", tmp_path)
    (tmp_path / "yard.json").write_text(json.dumps(INVENTORY))
    (tmp_path / "hall.json").write_text(json.dumps({"rows": [INVENTORY["rows"][2]]}))
    assert animals.animals_of("yard") == {"guard_dog", "koi"} and animals.animals_of("hall") == frozenset()
    names = [stage.name for stage in animals.rows()]
    assert names == ["animal-body-guard_dog", "animal-clips-guard_dog", "animal-body-koi", "animal-clips-koi"]
    body, clips = animals.rows_for("koi")
    assert body.paid and clips.paid and body.euros and clips.after == {"animal-body-koi": ("animal-body", 1)}
    assert body.applies("yard") and not body.applies("hall") and not body.applies("nowhere")


def test_the_spec_takes_its_body_from_the_kind_and_its_picture_from_the_box(tmp_path):
    kinds = row_kinds.table()
    dog, koi = INVENTORY["rows"][:2]
    assert animals.spec_of("yard", dog, kinds, "p.png")["body"] == "quadruped"
    spec = animals.spec_of("yard", koi, kinds, "p.png")
    assert spec["body"] == "fish" and spec["length_m"] == 0.4 and spec["clips"] == animals.CLIPS["fish"]
    assert spec["name"] == "yard_koi" and spec["approved"]
    Image.new("RGB", (400, 300)).save(tmp_path / "concept.png")
    cut = animals.cut_out(tmp_path / "concept.png", dog["box"], tmp_path / "cut.png")
    assert Image.open(cut).size == (120, 72)  # 100 x 60 widened by a tenth each side


def test_the_gates_pass_fail_and_answer_unknown_on_a_missing_record(tmp_path):
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
