"""The thin straight code route (thin_straight.py): which rows it takes, the model it sweeps, the take it writes where
the finish route and the likeness row read one, and the Pixal3D row building it for a row whose close-up failed.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/props/thin_straight_test.py
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import score.stages.batch_gaps as batch_gaps  # noqa: E402
import score.stages.props.likeness as likeness  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402
import score.stages.props.thin_straight as thin_straight  # noqa: E402

PIPE = {"id": "pipe", "name": "wall pipe", "noun": "pipe", "size": [4.0, 0.1, 0.1]}
POST = {"id": "porch_post", "name": "wooden post", "size": [0.1, 0.1, 2.5]}


def crop(path, colour=(180, 30, 30)):
    """A concept crop on a plain wall: a thin bar across it."""
    pixels = np.full((200, 600, 3), 140, dtype=np.uint8)
    pixels[90:110, 40:560] = colour
    Image.fromarray(pixels).save(path)
    return path


def test_only_thin_rows_of_a_straight_kind_are_taken():
    assert thin_straight.thin_straight(PIPE) and thin_straight.thin_straight(POST)
    assert thin_straight.thin_straight({"name": "bundles of cables", "size": [0.2, 0.1, 4.35]})
    assert not thin_straight.thin_straight({"name": "coiled hose", "size": [0.4, 0.4, 0.2]})  # not slender
    assert not thin_straight.thin_straight({"name": "wall poster", "size": [0.4, 0.01, 0.6]})  # post is not poster
    assert not thin_straight.thin_straight({"name": "metal railing", "size": [50.0, 0.1, 1.0]})  # posts and rails
    assert not thin_straight.thin_straight({"name": "strip floor light", "size": [0.8, 0.1, 0.05]})  # no such kind


def test_the_profile_is_swept_along_the_longest_side_at_the_row_s_size():
    pipe = thin_straight.build(PIPE)
    assert np.allclose(pipe.extents, [0.1, 0.1, 4.0]) and np.allclose(pipe.bounds.mean(0), 0.0)  # along z
    assert pipe.is_watertight and thin_straight.profile(PIPE) == "round"
    assert len(pipe.vertices) > 8  # round, not a box
    post = thin_straight.build(POST)  # size is wide, deep, tall: the post stands 2.5 m up y
    assert np.allclose(post.extents, [0.1, 2.5, 0.1]) and thin_straight.profile(POST) == "rect"
    assert len(post.vertices) == 8


def test_the_take_is_written_where_the_finish_route_and_the_likeness_row_read_it(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    assert thin_straight.write_take("garage_pipe_1", PIPE, crop(tmp_path / "pipe.jpg"), 4000, pixal, tmp_path / "cut")
    for name in ("garage_pipe_1.glb", "garage_pipe_1-final.glb", "garage_pipe_1-4000.glb",
                 "garage_pipe_1.svviews/input.png"):
        assert (pixal / name).exists(), name
    assert thin_straight.code_built("garage_pipe_1", pixal)
    # its one colour is the bar's, which the finish route measures as the model's own texture (route_cast)
    import trimesh
    loaded = trimesh.load(pixal / "garage_pipe_1.glb", force="scene")
    factor = next(iter(loaded.geometry.values())).visual.material.baseColorFactor
    assert np.abs(factor[:3].astype(int) - [180, 30, 30]).max() <= 6, factor  # the crop is a JPEG
    # the paint replays the finish's turn from the slimmed file onto the final one (labels.finish_turn): none here
    with prop_data.tools("props/library", "props"):
        import labels
    monkeypatch.setattr(labels, "PIXAL", pixal)
    labels.finish_turn("garage_pipe_1")  # exits when no stand of it matches the final model within FINISH_MISS
    assert np.allclose(trimesh.load(pixal / "garage_pipe_1-final.glb", force="mesh").extents, [0.1, 0.1, 4.0], atol=0.01)
    # the likeness row holds it to the cut crop: the bar's own outline matches it
    outline = likeness.best_way(pixal / "garage_pipe_1-final.glb", pixal / "garage_pipe_1.svviews/input.png",
                                PIPE["size"])["outline"]
    assert outline >= likeness.OUTLINE_LEAST, outline
    # a square post comes out of the finish's stand square, as built (glb_file.squared turned one set square 45 degrees)
    assert thin_straight.write_take("post_1", POST, crop(tmp_path / "post.jpg"), 4000, pixal, tmp_path / "cut")
    assert np.allclose(trimesh.load(pixal / "post_1-final.glb", force="mesh").extents, [0.1, 2.5, 0.1], atol=0.01)
    labels.finish_turn("post_1")
    thin_straight.unbuild("post_1", pixal)
    thin_straight.unbuild("garage_pipe_1", pixal)
    assert not list(pixal.iterdir())


def test_a_crop_with_no_object_is_no_build(tmp_path):
    flat = tmp_path / "wall.jpg"
    Image.fromarray(np.full((100, 300, 3), 140, dtype=np.uint8)).save(flat)
    assert thin_straight.write_take("t", PIPE, flat, 4000, tmp_path, tmp_path / "cut") is None
    assert not thin_straight.code_built("t", tmp_path)


def test_the_pixal_row_builds_a_failed_thin_row_and_drops_its_close_up_gap(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    monkeypatch.setattr(pixal_row, "take_files",
                        lambda take: [pixal / f"{take}{suffix}" for suffix in pixal_row.SUFFIXES])
    closeup = tmp_path / "closeup"
    (closeup / "closeups").mkdir(parents=True)
    (closeup / "crops").mkdir()
    crop(closeup / "crops/pipe.jpg")
    crop(closeup / "crops/hose.jpg")
    batch_gaps.write(closeup, [batch_gaps.gap(f"{row}: no close-up passed", "closeup", "close-up", (row, take),
                                              [], "every Pro take failed") for row, take in
                               (("pipe", "g_pipe"), ("hose", "g_hose"))])
    objects = {"pipe": {"route": "prop", "take": "g_pipe"}, "hose": {"route": "prop", "take": "g_hose"}}
    (tmp_path / "props.json").write_text(json.dumps({"place": "garage", "objects": objects}))
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [
        PIPE, {"id": "hose", "name": "coiled hose", "size": [0.4, 0.4, 0.2]}]}))
    (tmp_path / "surfaces.json").write_text(json.dumps({"takes": {"g_pipe": {}, "g_hose": {}}, "bake": {
        "models": {"garage_pipe": "g_pipe", "garage_hose": "g_hose"},
        "entries": {"garage_pipe": {"faces": 4000}, "garage_hose": {"faces": 4000}}}}))
    inputs = {"props": tmp_path / "props.json", "inventory": tmp_path / "inventory.json",
              "surfaces": tmp_path / "surfaces.json", "closeup": closeup}
    out = tmp_path / "out"
    out.mkdir()
    pixal_row.make_pixal(inputs, out, 0, {})  # no close-up passed: nothing for the batch, so nothing rented
    takes = json.loads((out / "takes.json").read_text())
    assert list(takes) == ["pipe"] and "g_pipe.svviews" in takes["pipe"]
    gaps = [entry["name"] for entry in json.loads((out / batch_gaps.FILE).read_text())["gaps"]]
    assert gaps == ["hose: no close-up passed"], gaps  # the coiled hose is no straight thing: still a gap


def test_the_likeness_row_holds_a_code_take_to_its_crop_and_closes_its_gap_only_when_it_passes(tmp_path):
    import score.stages.props.likeness_row as likeness_row
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    thin_straight.write_take("g_pipe", PIPE, crop(tmp_path / "pipe.jpg"), 4000, pixal, tmp_path / "cut")
    (tmp_path / "closeup/closeups").mkdir(parents=True)  # every Pro take failed: no close-up kept
    inputs = {"closeup": tmp_path / "closeup", "pixal input pipe": pixal / "g_pipe.svviews/input.png",
              "code take pipe": pixal / f"g_pipe.svviews/{thin_straight.MARK}"}
    record = {"place": "garage", "objects": {"pipe": {"route": "prop", "take": "g_pipe"}}}
    found = {"pipe": likeness_row.object_record(
        "pipe", record, inputs, {"g_pipe": pixal / "g_pipe-final.glb"},
        {"takes": {"g_pipe": {"parts": [{"words": "red pipe"}], "finishes": [{"finish": "red pipe"}]}}},
        {"pipe": PIPE}, set(), tmp_path / "cuts")}
    assert found["pipe"]["made"] == "code" and found["pipe"]["outline"] >= likeness.OUTLINE_LEAST, found
    assert likeness_row.free_passed(found, "pipe")
    assert not likeness_row.free_passed({"pipe": {**found["pipe"], "outline": 0.1}}, "pipe")
