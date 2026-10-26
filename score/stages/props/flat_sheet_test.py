"""The flat sheet code route (flat_sheet.py): which rows it takes, the model it lays, the take it writes where the
finish route and the likeness row read one, and the Pixal3D row building it for a sheet whose finish made no model.

Breaks (applied once, seen red, reverted): write_take cutting with thin_straight.cut_out instead of flat_sheet.cut_out
turns test_a_light_sheet_on_a_light_backdrop_is_cut_as_itself_not_its_shadow red (its hull the shadow L's, half the
square).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/props/flat_sheet_test.py
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import score.stages.batch_gaps as batch_gaps  # noqa: E402
import score.stages.props.flat_sheet as flat_sheet  # noqa: E402
import score.stages.props.likeness as likeness  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402
import score.stages.props.thin_straight as thin_straight  # noqa: E402

RUG = {"id": "rug", "name": "rug", "size": [1.807, 2.406, 0.02], "view": "v1", "box": [0, 0, 9, 9]}
NOTE = {"id": "sticky_note", "name": "sticky note", "size": [0.129, 0.281, 0.001], "view": "v1", "box": [0, 0, 9, 9]}


def closeup(path, round_=False):
    """A top-down close-up on a plain backdrop: a red rug 3 by 4, or a round one."""
    pixels = np.full((512, 512, 3), 235, dtype=np.uint8)
    if round_:
        down, across = np.mgrid[0:512, 0:512]
        pixels[(down - 256) ** 2 + (across - 256) ** 2 < 200 ** 2] = (170, 40, 40)
    else:
        pixels[56:456, 106:406] = (170, 40, 40)
    Image.fromarray(pixels).save(path)
    return path


def test_only_rows_lying_flat_as_a_sheet_are_taken():
    assert flat_sheet.sheet(RUG) and flat_sheet.sheet(NOTE)
    assert flat_sheet.sheet({"size": [0.2, 0.517, 0.02]})  # a door mat
    assert not flat_sheet.sheet({"size": [0.375, 0.355, 0.03]})  # a book has relief
    assert not flat_sheet.sheet({"size": [1.434, 3.85, 0.6]})  # cabinets lying low
    assert not flat_sheet.sheet({"size": [0.4, 0.01, 0.6]})  # a poster read standing is not laid flat
    assert flat_sheet.sheet({"size": [4.0, 4.0, 4.0], "read_size": [2.0, 3.0, 0.02]})  # as its close-up was drawn


def test_the_sheet_is_its_close_up_s_outline_at_the_row_s_size(tmp_path):
    cut = Image.open(thin_straight.cut_out(closeup(tmp_path / "rug.png"), tmp_path / "cut")).convert("RGBA")
    mesh = flat_sheet.build(RUG, cut)
    assert mesh.is_watertight and np.allclose(mesh.extents, [1.807, 0.02, 2.406], atol=1e-6)
    assert np.allclose(mesh.bounds.mean(0), 0.0)
    assert abs(mesh.area / 2 / (1.807 * 2.406) - 1) < 0.02  # a rectangle laid flat (its cut's corners eased)
    cut = Image.open(thin_straight.cut_out(closeup(tmp_path / "round.png", True), tmp_path / "cut")).convert("RGBA")
    mesh = flat_sheet.build({"size": [1.5, 1.5, 0.02]}, cut)
    top = mesh.area_faces[mesh.face_normals[:, 1] > 0.9].sum()
    assert abs(top / (np.pi * 0.75 ** 2) - 1) < 0.02  # round, not its box


def light_note(path):
    """quarters' sticky note seen from above (2026-10-26): a cream sheet (22, 15, 6) off a light grey backdrop that
    darkens downwards, with a dark drop shadow along its right and bottom edges, and ink on it."""
    down, _ = np.mgrid[0:600, 0:440]
    pixels = np.repeat((222 - 25 * down / 600)[..., None], 3, axis=2)
    pixels[150:470, 110:330] += (22, 15, 6)
    pixels[470:478, 116:338] = pixels[156:478, 330:338] = (130, 127, 122)  # the shadow, an L along two edges
    pixels[200:440:40, 140:300] = (90, 60, 50)  # lines of ink
    Image.fromarray(pixels.astype(np.uint8)).save(path)
    return path


def test_a_light_sheet_on_a_light_backdrop_is_cut_as_itself_not_its_shadow(tmp_path):
    note = {**NOTE, "size": [0.08, 0.08, 0.001]}
    views = flat_sheet.write_take("q_note", note, light_note(tmp_path / "note.png"), 200, tmp_path / "pixal",
                                  tmp_path / "cut")
    import trimesh
    extents = trimesh.load(tmp_path / "pixal/q_note.glb", force="mesh").extents
    assert np.allclose(extents, [0.08, 0.001, 0.08], atol=0.001), extents
    hull = trimesh.load(tmp_path / "pixal/q_note.glb", force="mesh")
    assert abs(hull.area / 2 / 0.08 ** 2 - 1) < 0.05, hull.area  # a square, not the hull of its shadow's L
    outline = likeness.best_way(tmp_path / "pixal/q_note-final.glb", views / "input.png", note["size"])["outline"]
    assert outline >= likeness.OUTLINE_LEAST, outline


def test_the_take_replaces_the_pixal3d_one_where_the_finish_route_and_the_likeness_row_read_it(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    (pixal / "q_rug.svviews").mkdir(parents=True)  # Pixal3D's raw take, whose finish made no model
    (pixal / "q_rug.svviews/transforms.json").write_text("{}")
    (pixal / "q_rug.glb").write_text("raw")
    picture = closeup(tmp_path / "rug.png")
    flat_sheet.write_take("q_rug", RUG, picture, 19000, pixal, tmp_path / "cut")
    assert sorted(path.name for path in pixal.iterdir()) == ["q_rug-19000.glb", "q_rug-final.glb", "q_rug.glb",
                                                            "q_rug.svviews"]
    assert sorted(path.name for path in (pixal / "q_rug.svviews").iterdir()) == ["code.json", "input.png"]
    assert flat_sheet.built("q_rug", pixal) and thin_straight.code_built("q_rug", pixal)
    import trimesh
    assert np.allclose(trimesh.load(pixal / "q_rug-final.glb", force="mesh").extents, [1.807, 0.02, 2.406], atol=0.01)
    with prop_data.tools("props/library", "props"):
        import labels
    monkeypatch.setattr(labels, "PIXAL", pixal)
    labels.finish_turn("q_rug")  # exits when no stand of it matches the final model
    outline = likeness.best_way(pixal / "q_rug-final.glb", pixal / "q_rug.svviews/input.png", RUG["size"])["outline"]
    assert outline >= likeness.OUTLINE_LEAST, outline


def test_the_pixal_row_builds_a_sheet_whose_finish_made_no_model_and_keeps_it(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    monkeypatch.setattr(pixal_row, "take_files",
                        lambda take: [pixal / f"{take}{suffix}" for suffix in pixal_row.SUFFIXES])
    finishes = []
    monkeypatch.setattr(pixal_row, "finish_all", lambda jobs, place, out: finishes.append(len(jobs)))  # none back
    for take in ("q_rug", "q_book"):  # both raw takes came back from the batch
        (pixal / f"{take}.svviews").mkdir()
        (pixal / f"{take}.glb").write_text("raw")
    closeups = tmp_path / "closeup/closeups"
    closeups.mkdir(parents=True)
    closeup(closeups / "rug.png")
    closeup(closeups / "book.png")
    book = {"id": "book", "name": "book", "size": [0.355, 0.375, 0.03], "view": "v1", "box": [0, 0, 9, 9]}
    objects = {"rug": {"route": "prop", "take": "q_rug"}, "book": {"route": "prop", "take": "q_book"}}
    (tmp_path / "props.json").write_text(json.dumps({"place": "quarters", "objects": objects}))
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [RUG, book]}))
    (tmp_path / "surfaces.json").write_text(json.dumps({"takes": {"q_rug": {}, "q_book": {}}, "bake": {
        "models": {"quarters_rug": "q_rug", "quarters_book": "q_book"},
        "entries": {"quarters_rug": {"faces": 19000}, "quarters_book": {"faces": 5000}}}}))
    inputs = {"props": tmp_path / "props.json", "inventory": tmp_path / "inventory.json",
              "surfaces": tmp_path / "surfaces.json", "closeup": tmp_path / "closeup"}
    out = tmp_path / "out"
    out.mkdir()
    pixal_row.make_pixal(inputs, out, 0, {})
    assert finishes == [2] and flat_sheet.built("q_rug", pixal)
    gaps = [entry["name"] for entry in json.loads((out / batch_gaps.FILE).read_text())["gaps"]]
    assert gaps == ["book: its finish made no model"], gaps  # a book has relief: still a gap
    assert sorted(json.loads((out / "takes.json").read_text())) == ["book", "rug"]
    pixal_row.make_pixal(inputs, out, 0, {})  # the build is kept: its close-up passed, yet it is not unbuilt
    assert finishes == [2, 1] and flat_sheet.built("q_rug", pixal)
