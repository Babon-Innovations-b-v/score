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


def test_no_world_1_place_has_a_prop_row_and_the_surface_line_reads_without_one():
    runner = stages.runner()
    places = stages.places(runner.world)
    assert not [node for node in runner.nodes(places) if node[0].name in PROPS]
    inputs = runner.stages["surfaces-inputs"]
    assert "pixal" in inputs.after and "pixal" not in runner.reads(inputs, "hub")


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
