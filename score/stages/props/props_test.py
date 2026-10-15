"""The prop route's rows: in the table without moving a world 1 node, the paid rows' code apart from the checks', the
likeness gate's silhouettes and routes, and the comparison's prepare and free first row on the hub (no spend).

The comparison's folder is one of its own under $PROPS_HOME/store-tests (never /tmp, never the framework's store),
removed at the end. Run: .venv/bin/python score/stages/props/props_test.py
"""
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import graph, stages  # noqa: E402
from score.graph import _code  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402
import score.stages.props as props  # noqa: E402
import score.stages.props.compare as compare  # noqa: E402
import score.stages.props.likeness as likeness  # noqa: E402
import score.stages.props.likeness_row as likeness_row  # noqa: E402

PROPS = ("props-inputs", "closeup", "pixal", "likeness-calibration", "likeness")


def test_only_the_camp_grounds_have_prop_rows_and_a_place_without_them_reads_without_one():
    """The camp grounds' cairn (2026-10-13) is world 1's first object by the prop route; every other place's surface
    line reads without its rows, so no other key moves."""
    runner = stages.runner()
    places = stages.places(runner.world)
    assert {node[1] for node in runner.nodes(places) if node[0].name in PROPS} == {"campgrounds"}
    inputs = runner.stages["surfaces-inputs"]
    assert "pixal" in inputs.after and "pixal" not in runner.reads(inputs, "hub")
    assert "pixal" in runner.reads(inputs, "campgrounds")


def test_a_take_s_faces_come_from_the_bake_model_made_from_it_whatever_its_name():
    """Fault (2026-10-13): pixal@campgrounds looked for `cairn_1`, a name made from the row, where the camp grounds
    name their models by the row alone (`cairn`). The entry is found by the take the model is made from."""
    import score.stages.props.pixal_row as pixal_row
    folder = PROPS_HOME / "store-tests/faces"
    folder.mkdir(parents=True, exist_ok=True)
    surfaces = folder / "surfaces.json"
    surfaces.write_text(json.dumps({"bake": {"models": {"cairn": "cairn-p1", "drift": "drift-r1"},
                                             "entries": {"cairn": {"faces": 19000}}}}))
    try:
        assert pixal_row.faces_of(surfaces, "cairn-p1") == 19000
        try:
            pixal_row.faces_of(surfaces, "drift-r1")  # its entry is an old bake job's: not read here
            raise AssertionError("a take with no written entry passed")
        except KeyError:
            pass
    finally:
        shutil.rmtree(folder)


def test_a_new_take_s_bake_entry_stands_its_foot_at_its_lowest_laid_spot():
    """Fault (2026-10-15): every ship model's entry said foot 0, so the kick wear scuffed the corner lamp laid 1.55 m
    up bare. The foot is the lowest spot the row lays it at; a row laid nowhere stands on its floor."""
    lamp = {"id": "corner_lamp", "size": [0.15, 0.08, 0.12],
            "at": [{"x": -2.45, "y": 1.55, "z": 1.25}, {"x": 2.45, "y": 1.8, "z": 1.25}]}
    assert compare.bake_entry("cockpit", lamp, {})["foot"] == 1.55
    assert compare.bake_entry("cockpit", {**lamp, "at": []}, {})["foot"] == 0.0


def test_a_retake_asks_pixal3d_for_its_own_seed():
    """Both ways (the galley's fold-down seat, a floor block from seed 1, 2026-10-15): a take `-s2` is asked with seed
    2, while a `-s1` take is asked with pixal.py's own default, seed 1, as every batch before asked it."""
    import score.stages.props.pixal_row as pixal_row
    folder = PROPS_HOME / "store-tests/seeds"
    folder.mkdir(parents=True, exist_ok=True)
    surfaces = folder / "surfaces.json"
    surfaces.write_text(json.dumps({"bake": {"models": {"seat_1": "seat-s2", "table_1": "table-s1"},
                                             "entries": {"seat_1": {"faces": 9000}, "table_1": {"faces": 19000}}}}))
    try:
        listing = pixal_row.batch_list({"seat": {"take": "seat-s2"}, "table": {"take": "table-s1"}}, folder,
                                       surfaces, folder)
        lines = listing.read_text().splitlines()
        assert lines[0].endswith("--faces 9000 --seed 2") and lines[1].endswith("--faces 19000 --seed 1"), lines
        assert pixal_row.seed_of("cairn") == 1
    finally:
        shutil.rmtree(folder)


def test_the_likeness_pairs_are_read_from_the_stored_output():
    """Fault (2026-10-15): likeness@campgrounds sent DINOv2 the paths pairs.json holds, into the folder its make ran
    in, removed once the output was stored. The pictures are read from the output's own pairs/ folder."""
    folder = PROPS_HOME / "store-tests/likeness-pairs"
    (folder / "pairs").mkdir(parents=True, exist_ok=True)
    try:
        for name in ("cairn-model.png", "cairn-closeup.png"):
            (folder / "pairs" / name).write_bytes(b"png")
        gone = "/nowhere/making/abc-tmp/pairs"
        (folder / "pairs.json").write_text(json.dumps({"cairn": [f"{gone}/cairn-model.png",
                                                                 f"{gone}/cairn-closeup.png"]}))
        found = likeness_row.stored_pairs(folder)
        assert found == {"cairn": [str(folder / "pairs/cairn-model.png"), str(folder / "pairs/cairn-closeup.png")]}
        assert all(pathlib.Path(picture).exists() for picture in found["cairn"])
    finally:
        shutil.rmtree(folder)


def test_the_takes_gate_judges_the_prop_objects_takes_only():
    """Fault (2026-10-13): pixal@campgrounds failed on the twelve takes earlier routes made, listed in the camp
    grounds' surface data beside the cairn. Only a prop object's take listed and not made fails."""
    import score.stages.props.pixal_row as pixal_row
    folder = PROPS_HOME / "store-tests/takes"
    folder.mkdir(parents=True, exist_ok=True)
    made_files = pixal_row.take_files
    pixal_row.take_files = lambda take: [folder / f"{take}{suffix}" for suffix in (".glb", "-final.glb")]
    try:
        for suffix in (".glb", "-final.glb"):
            (folder / f"cairn-p1{suffix}").write_text("made")
        (folder / "takes.json").write_text(json.dumps({"cairn": {"take": "cairn-p1", **{
            path.name: pixal_row.file_hash(path) for path in pixal_row.take_files("cairn-p1")}}}))
        objects = {"cairn": {"route": "prop", "take": "cairn-p1"}, "boulder": {"route": "prop", "take": "boulder-p1"}}
        (folder / "props.json").write_text(json.dumps({"objects": objects}))
        inputs = {"props": folder / "props.json", "surfaces": folder / "surfaces.json"}
        (folder / "surfaces.json").write_text(json.dumps({"takes": {"cairn-p1": {}, "drift-r1": {}}}))
        assert pixal_row.judge_takes(folder, inputs, {}).answer == "pass"
        (folder / "surfaces.json").write_text(json.dumps({"takes": {"cairn-p1": {}, "boulder-p1": {}}}))
        verdict = pixal_row.judge_takes(folder, inputs, {})
        assert verdict.answer == "fail" and "boulder-p1" in " ".join(verdict.findings), verdict
    finally:
        pixal_row.take_files = made_files
        shutil.rmtree(folder)


def test_the_paid_rows_code_leaves_the_checks_and_the_comparison_out():
    for row in (props.CLOSEUP, props.PIXAL):
        files = {path.relative_to(REPO).as_posix() for path in _code.source_files(
            [row.make, row.contract.faults, *(check.judge for check in row.checks), row.files])}
        here = "score/stages/props/"
        assert not files & {here + name for name in ("likeness.py", "likeness_row.py", "compare.py", "__init__.py")}, \
            files  # nor the prop route's table: an edit there or to a check re-buys no picture or model
        assert here + "prop_data.py" in files


def box(low, high):
    """A box's corners and its twelve triangles."""
    corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6),
             (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return corners.astype(float), np.array(faces)


def test_a_box_s_silhouette_matches_itself_and_not_a_rod():
    ring = likeness.candidate()
    cube = likeness.silhouette(*box((0, 0, 0), (1, 1, 1)), 1)
    rod = likeness.silhouette(*box((0, 0, 0), (0.1, 2, 0.1)), 1)
    assert cube.sum() > 1000
    assert ring.outline(cube, cube) == 1.0
    assert ring.outline(cube, rod) < likeness.OUTLINE_LEAST


def test_a_close_up_s_shaded_backdrop_is_not_its_object():
    from PIL import Image
    backdrop = np.clip(220 - np.add.outer(np.arange(60), np.arange(80)) * 0.9, 0, 255).astype(np.uint8)
    pixels = backdrop[..., None].repeat(3, axis=2)  # darkening 120 toward one corner
    pixels[10:50, 20:40] = (90, 60, 40)
    folder = pathlib.Path(tempfile.mkdtemp())
    Image.fromarray(pixels).save(folder / "crate.png")
    found = likeness.closeup_object(likeness_row.cut_out(folder / "crate.png", folder / "cut"))
    assert abs(int(found.sum()) - 40 * 20) < 40, found.sum()
    shutil.rmtree(folder)


def test_a_prop_close_up_is_pixal3d_s_cut_one_piece_and_filled():
    """The galley's fold-down seat: white cushions on a white backdrop, which the colour cut lost; Pixal3D's own cut
    keeps them. Its frame's holes are filled and a stray speck dropped, as every other cut."""
    from PIL import Image
    pixels = np.full((60, 80, 4), 240, dtype=np.uint8)
    pixels[..., 3] = 0
    pixels[10:50, 20:60, 3] = 255
    pixels[20:40, 30:50, 3] = 0  # the frame's opening
    pixels[2:4, 2:4, 3] = 255  # a speck
    folder = pathlib.Path(tempfile.mkdtemp())
    Image.fromarray(pixels).save(folder / "input.png")
    found = likeness.closeup_object(likeness_row.pixal_cut(folder / "input.png", folder / "cut", "seat"))
    assert int(found.sum()) == 40 * 40, found.sum()
    shutil.rmtree(folder)


def likeness_output(folder, objects):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "likeness.json").write_text(json.dumps({"objects": objects}))
    return folder


def entry(route, outline=0.8, parts=(), model_pass=True, straight=None):
    found = {"route": route, "outline": outline, "parts_missing": list(parts) if parts is not None else None,
             "model_check": {"pass": model_pass, "thinnest": 0.01, "spread": 0.0}}
    return {**found, **({"straight": {"pass": straight}} if straight is not None else {})}


def test_routes_send_a_failed_prop_object_to_code_and_a_failed_code_build_to_a_builder():
    root = PROPS_HOME / "store-tests" / "props-routes"
    try:
        output = likeness_output(root, {"good": entry("prop"), "thin": entry("prop", outline=0.2),
                                        "bent": entry("prop", straight=False), "built": entry("code"),
                                        "plain_miss": entry("code", parts=["handle"]),
                                        "untold": entry("code", parts=None), "gone": {"route": "prop",
                                                                                      "missing": "no model"}})
        found = likeness_row.routes(output, {})
        assert found == {"good": "unknown", "thin": "code", "bent": "code", "built": "unknown",
                         "plain_miss": "builder", "untold": "unknown", "gone": "code"}, found
        outline = likeness_row.free_judge("outline")(output, {}, None)
        assert outline.answer == "fail" and any(line.startswith("thin:") for line in outline.findings)
        parts = likeness_row.free_judge("close-up parts present")(output, {}, None)
        assert parts.answer == "fail" and any("untold: cannot tell" == line for line in parts.findings)
        assert likeness_row.judge_likeness(output, {}, None).answer == "unknown"  # no calibration, no least
        scored = likeness_row.routes(output, {"good": 0.9, "built": 0.4}, 0.5)
        assert scored["good"] == "prop" and scored["built"] == "builder", scored
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_both_orders_come_from_the_prop_and_code_results():
    try_order = compare.order_route
    assert try_order(("prop", "prop"), ("code", "code")) == "prop"
    assert try_order(("prop", "code"), ("code", "code")) == "code"  # prop failed, its code build passed
    assert try_order(("prop", "code"), ("code", "builder")) == "builder"
    assert try_order(("prop", "code"), ("code", None)) == "builder"  # no code build at all
    assert try_order(("code", "unknown"), ("prop", "prop")) == "unknown"


def test_the_ledger_tag_marks_cloud_and_google_lines():
    import os
    import types
    spec = importlib.util.spec_from_file_location("tagging", compare.LEDGER_TAG / "sitecustomize.py")
    tagging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tagging)
    written = []
    cloud = types.SimpleNamespace(entries=lambda: [], record=written.append)
    google = types.SimpleNamespace(write=written.append)
    os.environ[tagging.TAG] = "compare-test"
    try:
        tagging.tag_cloud(cloud)
        tagging.tag_google(google)
        tagging.tag_cloud(cloud)  # once only
        cloud.record({"euros": 1.0})
        google.write({"state": "finished"})
    finally:
        del os.environ[tagging.TAG]
    assert written == [{"euros": 1.0, "tag": "compare-test"}, {"state": "finished", "tag": "compare-test"}]


def test_the_comparison_prepares_the_hub_and_runs_its_free_first_row():
    if not (PROPS_HOME / "work/place/hub-round6/objects").exists():
        print("skipped: no hub round-six builds on this machine")
        return
    root = PROPS_HOME / "store-tests" / "props-compare"
    shutil.rmtree(root, ignore_errors=True)
    kept = compare.FOLDER, props.prop_data.FOLDER, stages.surfaces.data.FOLDER
    compare.FOLDER = root
    try:
        compare.prepare("hub", "prop-first", compare.default_code_builds("hub"))
        record = json.loads((root / "hub/prop-first/data/props/hub.json").read_text())
        surfaces = json.loads((root / "hub/prop-first/data/surfaces/hub.json").read_text())
        assert record["objects"] and all(entry["route"] == "prop" for entry in record["objects"].values())
        assert {entry["take"] for entry in record["objects"].values()} == set(surfaces["takes"])
        assert set(surfaces["bake"]["entries"]) == set(surfaces["bake"]["models"])
        assert record["accepted"], "no accepted models to calibrate DINOv2 on"
        runner = compare.runner_for("hub", "prop-first")
        runner.drive(["hub"], jobs=1, whole=False, only=["props-inputs"])
        made = runner.store.records("props-inputs@hub")
        assert made, "props-inputs made nothing"
        print(f"prop-first: {len(record['objects'])} objects, {len(record['left_out'])} left out; props-inputs:",
              runner.node_status(runner.stages["props-inputs"], "hub"))
    finally:
        compare.FOLDER, props.prop_data.FOLDER, stages.surfaces.data.FOLDER = kept
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
