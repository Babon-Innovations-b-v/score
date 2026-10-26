"""The prop route's rows: in the table without moving a world 1 node, the paid rows' code apart from the checks', the
likeness gate's silhouettes and routes, and the comparison's prepare and free first row on the hub (no spend).

The comparison's folder is one of its own under $PROPS_HOME/store-tests (never /tmp, never the framework's store),
removed at the end. Run: .venv/bin/python score/stages/props/props_test.py

Breaks (applied once, seen red, reverted): model_checks laying the row's size x wide, z deep (`[size[0], size[2],
size[1]]`) turns test_the_model_check_holds_a_prop_s_proportions_whichever_way_round_the_finish_laid_its_footprint red.
"""
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
# Run as a script, this folder leads the path; the runner (python -m score) never has it there, and the code walk would
# take its compare.py for thin_straight's bare `import compare` (tools/usd's) into the paid rows' code versions.
sys.path[:] = [str(REPO)] + [entry for entry in sys.path
                             if pathlib.Path(entry or ".").resolve() != REPO / "score/stages/props"]

from score import graph, stages  # noqa: E402
from score.graph import _code  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402
import score.stages.props as props  # noqa: E402
import score.stages.props.compare as compare  # noqa: E402
import score.stages.props.likeness as likeness  # noqa: E402
import score.stages.props.likeness_row as likeness_row  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402
import score.stages.props.thin_straight as thin_straight  # noqa: E402
from score.stages.surfaces import surface_data  # noqa: E402

# These tests hold their own hand-ins; a designed place's hand-in (the home's design/, which
# the sandbox links) is prepare_test.py's, so none is read here.
import score.stages.surfaces  # noqa: E402
prop_data.DESIGN = surface_data.DESIGN = pathlib.Path(tempfile.mkdtemp()) / "no design"
score.stages.surfaces.data.DESIGN = surface_data.DESIGN  # the table's own import of it (bare `surface_data`)

PROPS = ("props-inputs", "closeup", "pixal", "likeness-calibration", "likeness")


def test_only_the_places_with_prop_data_have_prop_rows_and_a_place_without_them_reads_without_one():
    """A place's prop rows come with its hand-in (its design's: the old data/props hand-ins were retired, 2026-10-21);
    every other place's surface line reads without its rows, so no other key moves."""
    runner = stages.runner()
    held = prop_data.DESIGN
    prop_data.DESIGN = pathlib.Path(tempfile.mkdtemp())
    (prop_data.DESIGN / "campgrounds.json").write_text(json.dumps({"objects": {}}))
    try:
        found = {node[1] for node in runner.nodes(["campgrounds", "hub"]) if node[0].name in PROPS}
        assert found == {"campgrounds"}, found
        inputs = runner.stages["finish-route-views"]
        assert "pixal" in inputs.after and "pixal" not in runner.reads(inputs, "hub")
        assert "pixal" in runner.reads(inputs, "campgrounds")
    finally:
        shutil.rmtree(prop_data.DESIGN)
        prop_data.DESIGN = held


def test_the_inputs_row_declares_its_scenes_inventory_not_the_whole_folder():
    """props-inputs reads the inventory the box gate reads, its scene's, under the name the folder had, and the code
    version stays the file map's own (the table's wrapper is the framework's): the hangar's inventory alone moved every
    place's inputs row (46313397, 2026-10-18)."""
    runner = stages.runner()
    row = runner.stages["props-inputs"]
    for place in ("campgrounds", "hangar", "shiplock"):
        assert runner.files_of(row, place)["inventories"] == "{data}/inventory/" + f"{place}.json", place
    loop_split = stages.shapes_first.SPLIT  # the loop's parts split: props-inputs with its registration gate (#41)
    floor_held = pathlib.Path(stages.shapes_first.floor_fit.__file__)  # its fits-the-plan check, the table's (78461f7f)
    assert set(_code.source_files(graph.code_functions(row))) == {
        *_code.source_files(graph.code_functions(loop_split)), floor_held}


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
    assert compare.bake_entry(lamp)["foot"] == 1.55
    assert compare.bake_entry({**lamp, "at": []})["foot"] == 0.0


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


def test_the_model_check_holds_a_prop_s_proportions_whichever_way_round_the_finish_laid_its_footprint(tmp_path):
    """likeness_row.model_checks lays a row's wide and deep on the model's own ground sides, longer to longer (the
    finish lays a long footprint along z: glb_file.squared; the scene turns it about up to its place). A 2 by 1 by
    0.5 m crate made right passes and one made square fails its spread; a 0.6 by 0.6 by 2 m locker passes. Laid x wide,
    z deep, as before f2ccd22c, the right crate read spread 1.0 and failed."""
    import trimesh
    rows = {"crate": ([2.0, 1.0, 0.5], [1.0, 0.5, 2.0], True), "square crate": ([2.0, 1.0, 0.5], [1.0, 0.5, 1.0], False),
            "locker": ([0.6, 0.6, 2.0], [0.6, 2.0, 0.6], True), "crate across": ([1.0, 2.0, 0.5], [1.0, 0.5, 2.0], True)}
    for name, (size, extents, passes) in rows.items():
        path = tmp_path / f"{name}.glb"
        trimesh.creation.box(extents=extents).export(path)
        found = likeness_row.model_checks(path, size, f"p_{name}", False)["model_check"]
        assert found["pass"] is passes, (name, found)


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
        inputs = {"props": folder / "props.json", "surfaces": folder / "surfaces.json", "closeup": folder}
        (folder / "closeups.json").write_text(json.dumps({"objects": {"cairn": {}, "boulder": {}}}))
        (folder / "surfaces.json").write_text(json.dumps({"takes": {"cairn-p1": {}, "drift-r1": {}}}))
        assert pixal_row.judge_takes(folder, inputs, {}).answer == "pass"
        (folder / "surfaces.json").write_text(json.dumps({"takes": {"cairn-p1": {}, "boulder-p1": {}}}))
        verdict = pixal_row.judge_takes(folder, inputs, {})
        assert verdict.answer == "fail" and "boulder-p1" in " ".join(verdict.findings), verdict
        # narrowed to the cairn (score run --object): the boulder the line was not asked for is not failed
        (folder / "closeups.json").write_text(json.dumps({"objects": {"cairn": {}}}))
        assert pixal_row.judge_takes(folder, inputs, {}).answer == "pass"
    finally:
        pixal_row.take_files = made_files
        shutil.rmtree(folder)


def test_an_object_filter_narrows_the_loop_rows_and_their_forecast():
    """#26: `score run --object <take>` narrows the prop route to that object: the inputs row writes its row alone
    (the close-up, Pixal3D and the finish route work on those rows), and its paid rows are priced for it alone."""
    from score.stages.complete.gaps import price
    import score.stages.props.closeup_row as closeup_row
    assert all(row.selects for row in (props.INPUTS, props.CLOSEUP, props.PIXAL, props.LIKENESS))
    with tempfile.TemporaryDirectory() as held:
        data = pathlib.Path(held)
        (data / "props").mkdir()
        objects = {"cairn": {"route": "prop", "take": "cairn-p1"}, "boulder": {"route": "prop", "take": "boulder-p1"}}
        (data / "props/rocks.json").write_text(json.dumps({"place": "rocks", "objects": objects}))
        (data / "inventory.json").write_text(json.dumps({"scene": "rocks", "rows": [
            {"id": row, "name": row, "size": [1, 1, 1]} for row in objects]}))
        inputs = {"props": data / "props/rocks.json", "inventory": data / "inventory.json"}
        for params, wanted in (({}, ["boulder", "cairn"]), ({"objects": ["boulder-p1"]}, ["boulder"]),
                               ({"objects": ["cairn"]}, ["cairn"])):
            out = data / "out"
            out.mkdir()
            closeup_row.make_inputs(inputs, out, 7, params)
            assert sorted(row["id"] for row in json.loads((out / "rows.json").read_text())["rows"]) == wanted
            shutil.rmtree(out)
        assert price.selected_takes({"cairn-p1", "boulder-p1"}, data, "rocks") == {"cairn-p1", "boulder-p1"}
        token = graph.SELECTED.set(frozenset({"cairn"}))
        try:
            assert price.selected_takes({"cairn-p1", "boulder-p1"}, data, "rocks") == {"cairn-p1"}
        finally:
            graph.SELECTED.reset(token)


def test_a_drawn_close_up_that_does_not_open_is_one_object_s_gap():
    """Buy of 2026-10-24: the square's object `stage` took the row's tool input "close-up stage" (a folder) as its
    drawn close-up, and opening it stopped closeup@square and with it the square's whole line. Only an object whose
    prop data names a close-up has one drawn, and one that does not open is that object's batch gap."""
    import score.stages.props.closeup_row as closeup_row
    with tempfile.TemporaryDirectory() as held:
        data = pathlib.Path(held)
        (data / "props").mkdir()
        (data / "tool").mkdir()
        objects = {"stage": {"route": "prop", "take": "stage-p1"},
                   "crate": {"route": "prop", "take": "crate-p1", "closeup": "{data}/crate.png"}}
        (data / "props/square.json").write_text(json.dumps({"place": "square", "objects": objects}))
        (data / "inventory.json").write_text(json.dumps({"scene": "square", "rows": [
            {"id": row, "name": row, "size": [1, 1, 1]} for row in objects]}))
        inputs = {"props": data / "props/square.json", "inventory": data / "inventory.json",
                  "close-up stage": data / "tool", "close-up crate": data / "tool"}
        (data / "inputs").mkdir()
        closeup_row.make_inputs(inputs, data / "inputs", 7, {})
        drawn = {row["id"]: row["drawn"] for row in json.loads((data / "inputs/rows.json").read_text())["rows"]}
        assert drawn == {"stage": None, "crate": str(data / "tool")}, drawn
        kept = closeup_row.draw_missing
        closeup_row.draw_missing = lambda rows, out: {}
        try:
            (data / "out").mkdir()
            closeup_row.make_closeups({"props-inputs": data / "inputs"}, data / "out", 7, {})
        finally:
            closeup_row.draw_missing = kept
        gaps = json.loads((data / "out/batch-gaps.json").read_text())["gaps"]
        assert [gap["name"] for gap in gaps] == ["stage: no close-up passed",
                                                 "crate: its drawn close-up could not be read"], gaps


def test_a_raw_take_is_finished_on_a_rented_machine_never_here():
    """2026-10-22: no Blender or bake on the owner's PC. The batch brings takes back raw (--no-finish) and the row
    finishes each through blender_cloud.run_elsewhere (tools/props/finish_elsewhere.py), the raw take, its camera
    folder and close-up sent up. Buy of 2026-10-24: each take was finished on its own machine run, one after
    another; every take's finish is one job of one blender_cloud.py call, side by side, a failed one its take's gap
    and a call that brought nothing back a stop."""
    import types
    import score.stages.props.pixal_row as pixal_row
    assert '"--no-finish"' in (REPO / "score/stages/props/pixal_row.py").read_text()
    assert "finish elsewhere" in prop_data.PIXAL_TOOLS
    job = pixal_row.finish_job("crate-t1", pathlib.Path("/close/crate.png"), 12000)
    raw, final, _ = pixal_row.take_files("crate-t1")
    assert job["script"] == "tools/props/finish_elsewhere.py" and job["args"][3:] == ["crate-t1", "--faces=12000"]
    assert pixal_row.finish_job("rug-t1", pathlib.Path("/close/rug.png"), 12000, True)["args"][-1] == "--flat"
    assert pixal_row.lies_flat({"size": [4.0, 4.0, 4.0], "read_size": [2.0, 3.0, 0.02]})
    assert not pixal_row.lies_flat({"size": [2.0, 3.0, 0.02], "read_size": [0.6, 0.5, 0.8]})
    assert str(raw) in job["inputs"] and "/close/crate.png" in job["inputs"], job
    # the paint replays its turn from the slimmed model
    assert job["outputs"] == [str(final), str(final.with_name("crate-t1-12000.glb"))], job
    calls = []

    def one_comes_back(command, **options):
        calls.append(command)
        for path in json.loads(pathlib.Path(command[2]).read_text())["outputs"]:
            pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(path).write_text("made")
        return types.SimpleNamespace(returncode=1, stdout="", stderr="the second job failed")
    jobs = [job, pixal_row.finish_job("lamp-t1", pathlib.Path("/close/lamp.png"), 8000)]
    kept = pixal_row.subprocess.run
    with tempfile.TemporaryDirectory() as held:
        try:
            pixal_row.subprocess.run = one_comes_back
            pixal_row.finish_all(jobs, "yard", pathlib.Path(held))
            assert len(calls) == 1 and len([word for word in calls[0] if word.endswith(".json")]) == 2, calls
            assert calls[0][calls[0].index("--classes") + 1] == ",".join(pixal_row.FINISH_CLASSES)
            for path in job["outputs"]:
                pathlib.Path(path).unlink()
            pixal_row.subprocess.run = lambda command, **options: types.SimpleNamespace(
                returncode=1, stdout="renting\n", stderr="no machine could be rented\n")
            try:
                pixal_row.finish_all(jobs, "yard", pathlib.Path(held))
                raise AssertionError("a call that brought nothing back must stop the row")
            except RuntimeError as error:  # its log's end in the error, so the fault report shows the cause
                assert str(error).endswith("renting\nno machine could be rented"), error
        finally:
            pixal_row.subprocess.run = kept


def test_no_object_is_code_built():
    """#19, #41: no object of a place's prop data is on the code route (a code object, or a prop object moved to the
    fallback): the code fallback was removed on 2026-10-22, so every object is the shared loop's."""
    for path in sorted(props.prop_data.FOLDER.glob("*.json")):
        record = json.loads(path.read_text())
        coded = [row for row, entry in record["objects"].items() if entry["route"] == "code"]
        assert not coded + list(record.get("fallback", {})), f"{path.stem}: code-built: {', '.join(coded)}"


def test_the_paid_rows_code_leaves_the_checks_and_the_comparison_out():
    import score.stages.props.masks_row as masks_row
    for row in (props.CLOSEUP, masks_row.STAGE, props.PIXAL):
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


def test_the_outline_is_held_to_the_close_up_s_one_look_down():
    """The likeness gate draws the model at the one look-down the close-up check holds the picture to, never a search."""
    with likeness.prop_data.tools("props/closeup", "props"):
        import check
    assert likeness.look_down() == check.LOOK_DOWN_DEGREES == 15.0
    # a row that lies flat is drawn from straight above, and its model's outline drawn so: its face, not a line
    assert likeness.look_down([2.0, 3.0, 0.02]) == check.TOP_DOWN_DEGREES
    face = likeness.silhouette(*box((0, 0, 0), (2.0, 0.02, 3.0)), 0, check.TOP_DOWN_DEGREES)
    assert face.sum() > 2 * likeness.silhouette(*box((0, 0, 0), (2.0, 0.02, 3.0)), 0).sum(), face.sum()


def test_a_close_up_s_shaded_backdrop_is_not_its_object():
    from PIL import Image
    backdrop = np.clip(220 - np.add.outer(np.arange(60), np.arange(80)) * 0.9, 0, 255).astype(np.uint8)
    pixels = backdrop[..., None].repeat(3, axis=2)  # darkening 120 toward one corner
    pixels[10:50, 20:40] = (90, 60, 40)
    folder = pathlib.Path(tempfile.mkdtemp())
    Image.fromarray(pixels).save(folder / "crate.png")
    found = likeness.closeup_object(thin_straight.cut_out(folder / "crate.png", folder / "cut"))
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


def test_a_persons_close_up_is_held_to_its_arms_apart_not_a_box():
    """A row the people layer handed (a crowd, no size): its close-up is judged by its framing and arms clear of the
    body (the close-up check's person_faults), never 'no measured size'; an object row with no size still is named."""
    from PIL import Image, ImageDraw
    import score.stages.props.closeup_row as closeup_row
    folder = pathlib.Path(tempfile.mkdtemp())
    for name, arms_out in (("apart", 70), ("fused", 0)):
        picture = Image.new("RGB", (512, 512), closeup_row.GREY)
        draw = ImageDraw.Draw(picture)
        draw.ellipse((236, 60, 276, 100), fill=(60, 70, 80))
        draw.rectangle((226, 100, 286, 260), fill=(60, 70, 80))
        draw.polygon([(226, 260), (256, 260), (236, 450), (206, 450)], fill=(60, 70, 80))
        draw.polygon([(256, 260), (286, 260), (306, 450), (276, 450)], fill=(60, 70, 80))
        for sign, shoulder in ((-1, 226), (1, 286)):
            draw.line([(shoulder, 108), (shoulder + sign * arms_out, 240)], fill=(60, 70, 80), width=14)
        picture.save(folder / f"{name}.png")
    crowd = {"size": None, "layer": "people"}
    assert closeup_row.measured(folder / "apart.png", crowd) == []
    assert closeup_row.measured(folder / "fused.png", crowd)[0].startswith("arms not clear of the body")
    assert closeup_row.measured(folder / "apart.png", {"size": None}) == ["no measured size: its proportions held to none"]
    shutil.rmtree(folder)


def test_a_rejected_close_up_is_retried_strictly_at_its_own_size_and_a_kept_picture_is_never_drawn_again():
    """Owner, 2026-10-24: the check holds a close-up to the object's own size from its reading (the plan's footprint
    failed 23 of the Buy's 80 gaps alone); owner, 2026-10-25: a picture it rejects gets up to three retries, worded
    more strictly, the later ones on their own seeds. Every picture stays cached: a make asked again reads each take
    back free and judges it again, so a passing picture is kept and nothing is drawn twice (coordinator, 2026-10-25)."""
    import types
    from PIL import Image, ImageDraw
    import score.stages.props.closeup_row as closeup_row
    stage, check = closeup_row.closeup_tools()
    spend = stage.pro.google_spend
    folder = pathlib.Path(tempfile.mkdtemp())
    Image.new("RGB", (800, 600), (120, 120, 120)).save(folder / "concept.png")
    own = [0.5, 0.5, 1.0]
    rows = [{"id": name, "scene": "s", "words": name, "size": [4.0, 0.5, 0.5], "read_size": own, "layer": "objects",
             "concept": str(folder / "concept.png"), "box": [100, 100, 600, 500], "drawn": None}
            for name in ("lamp", "crate", "tools")]
    (folder / "inputs").mkdir()
    (folder / "inputs/rows.json").write_text(json.dumps({"rows": rows}))
    tall = 300

    def picture(path, good):
        drawn = Image.new("RGB", (512, 512), closeup_row.GREY)
        if not good:  # a room's floor behind it, to the frame's edge
            ImageDraw.Draw(drawn).rectangle((0, 300, 512, 512), fill=(150, 90, 30))
        wide = round(tall / check.expected_proportion(own))
        ImageDraw.Draw(drawn).rectangle((256 - wide // 2, 106, 256 + wide // 2, 106 + tall), fill=(60, 70, 80))
        drawn.save(path)
    sent = []

    def draw(key, asks):
        for path, ask in asks.items():
            kept_answer = spend.cache_path(stage.pro.MODEL, stage.pro.request_body(*ask))
            if not kept_answer.exists():  # a cached request is read back free (google_batch.generate)
                sent.append((path.parent.name, path.stem, ask[0], ask[3]))
                kept_answer.write_text("{}")
            picture(path, path.stem == "crate" or (path.stem == "lamp" and path.parent.name == "retry-2"))
        return dict.fromkeys(asks, True)
    kept = stage.pro.draw, spend.CACHE, sys.modules.get("secret_store")
    stage.pro.draw, spend.CACHE = draw, folder / "cache"
    spend.CACHE.mkdir()
    sys.modules["secret_store"] = types.SimpleNamespace(secret=lambda name: "key")
    try:
        (folder / "out").mkdir()
        closeup_row.make_closeups({"props-inputs": folder / "inputs"}, folder / "out", 7, {})
        found = json.loads((folder / "out/closeups.json").read_text())["objects"]
        assert [(take, name) for take, name, _, _ in sent] == [
            ("pro", "lamp"), ("pro", "crate"), ("pro", "tools"), ("retry", "lamp"), ("retry", "tools"),
            ("retry-2", "lamp"), ("retry-2", "tools"), ("retry-3", "tools")], sent
        first, retry, firmer = sent[0][2], sent[3][2], sent[5][2]
        assert stage.RETRY not in first and retry == first + stage.RETRY and firmer == retry + stage.FIRMER
        assert [seed for _, _, _, seed in sent] == [None] * 5 + [2, 2, 3]
        assert found["crate"]["drawn_by"] == "pro" and found["lamp"]["drawn_by"] == "retry-2", found
        assert found["tools"]["drawn_by"] is None and found["tools"]["pro_pictures"] == 4
        assert found["lamp"]["takes"]["pro"][0] == "background not plain to the edge"
        assert len(list(spend.CACHE.iterdir())) == 8  # every picture stays cached, a rejected one too
        gaps = json.loads((folder / "out/batch-gaps.json").read_text())
        assert [gap["name"] for gap in gaps["gaps"]] == ["tools: no close-up passed"], gaps
        sent.clear()
        (folder / "again").mkdir()
        closeup_row.make_closeups({"props-inputs": folder / "inputs"}, folder / "again", 7, {})
        # asked again (the gap's step bought again): every take read back free and judged again, and only the gap's
        # row drawn anew, four takes on past the ladder's first four, each firmer and on its own seed
        assert [(take, name, seed) for take, name, _, seed in sent] == [
            ("retry-4", "tools", 4), ("retry-5", "tools", 5), ("retry-6", "tools", 6), ("retry-7", "tools", 7)], sent
        assert all(text.endswith(stage.RETRY + stage.FIRMER) for _, _, text, _ in sent)
        again = json.loads((folder / "again/closeups.json").read_text())["objects"]
        assert list(again["tools"]["takes"]) == ["pro", "retry", "retry-2", "retry-3", "retry-4", "retry-5",
                                                 "retry-6", "retry-7"] and again["lamp"]["drawn_by"] == "retry-2"
        assert (folder / "again/closeups/lamp.png").read_bytes() == (folder / "out/closeups/lamp.png").read_bytes()
        assert closeup_row.measured(folder / "out/closeups/crate.png", {"size": [4.0, 0.5, 0.5]})  # the footprint fails
        assert closeup_row.judge_closeups(folder / "out", {}, {}).answer == "pass"
    finally:
        stage.pro.draw, spend.CACHE = kept[:2]
        if kept[2] is None:
            del sys.modules["secret_store"]
        else:
            sys.modules["secret_store"] = kept[2]
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
        handed = root / "designed.json"
        handed.write_text(json.dumps({"approved": {"by": "the creator's pick"}, "objects": {}}))
        (root / "scores.json").write_text(json.dumps({"good": 0.91, "thin": 0.42}))
        shown = likeness_row.judge_likeness(output, {"props": handed}, root / "scores.json")
        assert shown.answer == "pass" and "not judged" in shown.reason and shown.measures["scored"] == 2, shown
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
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
