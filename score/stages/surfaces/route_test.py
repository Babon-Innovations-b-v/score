"""The finish route's own checks, with no spend (Google faked, the bake's cloud call faked): a two-box
model (one textured red, one blue by its colour factor) is rendered from its base views plus what the coverage check
adds, its colours split into regions the views share; one batch answer a take lists its finishes library first and
labels each region of each view; the split votes the labels into one finish a face, and an unassigned face or views
that disagree make the take a hole; the parts row writes the method's interface with each finish checked against
its colour, keeping the list's settings; the bake paints and bakes each take in one card job, each part with
settings as its settings' surface, and the paint takes its painted takes over; the check reads the bake's specs; the
recheck sorts one batch answer a take into pass or a
named hole, a take off its colour not asked at all. The route is the default line: its rows are on every painting
place's line and the finish-map method's rows are not.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/surfaces/route_test.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image
from trimesh.visual.material import PBRMaterial

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages import surfaces  # noqa: E402
from score.stages.surfaces import (route_ask, route_bake, route_cast, route_check, route_data,  # noqa: E402
                                   route_list, route_paint, route_parts, route_recheck, route_settings, route_split,
                                   route_views)

RED, BLUE = (200, 30, 30), (30, 40, 200)
TAKE, OTHER = "two_boxes-t1", "other-t1"


def two_boxes(folder):
    """A glb of two boxes side by side, 0.2 apart: the left one textured red, the right one blue by its colour
    factor."""
    left = trimesh.creation.box((1, 1, 1))
    left.apply_translation((-0.6, 0, 0))
    left.visual = trimesh.visual.TextureVisuals(uv=left.vertices[:, :2] + 0.5, material=PBRMaterial(
        baseColorTexture=Image.new("RGB", (4, 4), RED)))
    right = trimesh.creation.box((1, 1, 1))
    right.apply_translation((0.6, 0, 0))
    right.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(baseColorFactor=[*BLUE, 255]))
    path = folder / "two.glb"
    trimesh.Scene([left, right]).export(str(path))
    return path


def place_data(folder):
    path = folder / "place.json"
    entry = {"places": ["cockpit"], "library_places": ["cockpit"], "place": "cockpit", "kind": "two_boxes",
             "object": "two boxes"}
    path.write_text(json.dumps({"place": "cockpit", "takes": {TAKE: entry, OTHER: dict(entry, object="another")}}))
    return path


def cast_views(folder, takes=(TAKE,)):
    """The views row's make on the two boxes (each take named the same model), the object filter keeping `takes`."""
    views = folder / "views"
    views.mkdir()
    model = two_boxes(folder)
    inputs = {"surfaces": place_data(folder), **{f"model {take}": model for take in takes}}
    route_views.make_views(inputs, views, 7, {"objects": list(takes)})
    return inputs, views


def region_of(views, colour, take=TAKE):
    """The views row's region (0-based) of a colour."""
    regions = json.loads((views / "views.json").read_text())[take]["regions"]
    return next(entry["region"] for entry in regions if entry["srgb"] == list(colour))


def finish_entry(words, surface="M1", token="sign-red"):
    return {"parts": words, "finish": words, "surface": surface, "token": token, "roughness": 1.4, "metal": 0.0,
            "fits": True}


def labelled(views, finish_of_colour, take=TAKE):
    """Labels for every region showing in every view: the region of each colour takes finish_of_colour(view, colour)
    (1-based, None to leave it out)."""
    angles = json.loads((views / "views.json").read_text())[take]["views"]
    shown = route_list.regions_shown(views / take, angles)
    found = []
    for view, regions in shown.items():
        for colour in (RED, BLUE):
            finish = finish_of_colour(view, colour)
            if region_of(views, colour, take) in regions and finish is not None:
                found.append({"view": view, "region": region_of(views, colour, take) + 1, "finish": finish})
    return found


def two_finish_answer(views, finish_of_colour=lambda view, colour: 1 if colour == RED else 2):
    finishes = [finish_entry("red paint"), dict(finish_entry("blue paint", token="bay-three"), wear_wish="more worn")]
    return {"finishes": finishes, "labels": labelled(views, finish_of_colour)}


def listed(folder, answer, takes=(TAKE,)):
    """The views and list rows made with the list's batch faked to answer `answer(views, take)` (a dict, or an
    exception the batch holds): the rows' inputs and the batches asked."""
    inputs, views = cast_views(folder, takes)
    asked = []
    original = route_list.ask
    route_list.ask = lambda bodies: asked.append(bodies) or {
        take: (answer(views, take) if isinstance(answer(views, take), Exception) else json.dumps(answer(views, take)))
        for take in bodies}
    try:
        out = folder / "list"
        out.mkdir()
        route_list.make_list({**inputs, "finish-route-views": views}, out, 7, {"objects": list(takes)})
    finally:
        route_list.ask = original
    return {**inputs, "finish-route-views": views, "finish-route-list": out}, asked


def split(folder, rows):
    out = folder / "split"
    out.mkdir()
    route_split.make_split(rows, out, 7, {})
    return {**rows, "finish-route-split": out}


def parted(folder, rows):
    out = folder / "parts"
    out.mkdir()
    route_parts.make_parts(rows, out, 7, {"objects": [TAKE]})
    return {**rows, "surfaces-parts": out}


def test_the_views_cover_every_side_and_find_both_colours():
    with tempfile.TemporaryDirectory() as temporary:
        inputs, views = cast_views(pathlib.Path(temporary))
        record = json.loads((views / "views.json").read_text())
        assert list(record) == [TAKE], record  # the filter left other-t1 out
        assert set(route_cast.BASE) <= set(record[TAKE]["views"]), record[TAKE]["views"]
        assert record[TAKE]["close_up"] == route_data.STAND_IN
        assert record[TAKE]["paint_faces"] == record[TAKE]["faces"] == 24, record[TAKE]
        assert record[TAKE]["unseen_faces"] == 0 and record[TAKE]["seen_share"] == 1.0, record[TAKE]
        assert sorted(tuple(entry["srgb"]) for entry in record[TAKE]["regions"]) == sorted([BLUE, RED])
        assert (views / TAKE / "regions-bottom.png").exists() and (views / TAKE / "right.png").exists()
        verdict = route_views.judge_views(views, inputs, {})
        assert verdict.answer == "pass" and verdict.measures["views_most"] == len(record[TAKE]["views"]), verdict


def test_the_coverage_check_adds_a_view_for_faces_the_base_views_miss():
    """An open tube standing up: the base views miss part of its inside, the check adds views until every face is
    seen, each added view seeing faces no chosen view saw."""
    mesh = trimesh.creation.annulus(0.3, 0.5, 1.0)
    angles, casts = route_views.covering_views(mesh)
    assert list(angles)[:len(route_cast.BASE)] == list(route_cast.BASE) and len(angles) > len(route_cast.BASE), angles
    seen = np.zeros(len(mesh.faces), dtype=bool)
    for view in list(angles)[:len(route_cast.BASE)]:
        seen[casts[view][0][casts[view][0] >= 0]] = True
    for view in list(angles)[len(route_cast.BASE):]:
        found = casts[view][0]
        assert (~seen[found[found >= 0]]).any(), view  # an added view saw something new
        seen[found[found >= 0]] = True
    assert seen.all()


def test_a_model_with_no_file_or_no_take_fails_by_name():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        inputs = {"surfaces": place_data(folder)}
        route_views.make_views(inputs, folder, 7, {"objects": [OTHER]})
        verdict = route_views.judge_views(folder, inputs, {})
        assert verdict.answer == "fail" and verdict.findings[0].startswith(f"{OTHER}: no raw take"), verdict
        folder = folder / "none"
        folder.mkdir()
        route_views.make_views(inputs, folder, 7, {"objects": ["no-such-take"]})
        verdict = route_views.judge_views(folder, inputs, {})
        assert verdict.answer == "fail" and "no take to work on" in verdict.findings[0], verdict


def test_one_batch_lists_every_take_library_first_and_the_split_gives_every_face_one_finish():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        rows, asked = listed(folder, lambda views, take: two_finish_answer(views), takes=(TAKE, OTHER))
        assert len(asked) == 1 and sorted(asked[0]) == [OTHER, TAKE], asked  # one batch, one ask a take
        body = asked[0][TAKE]
        count = len(json.loads((rows["finish-route-views"] / "views.json").read_text())[TAKE]["views"])
        assert "serviceTier" not in body and len(body["contents"][0]["parts"]) == 2 * count + 2  # close-up, views, text
        found = json.loads((rows["finish-route-list"] / f"{TAKE}.json").read_text())
        assert found["finishes"][0]["settings"] == {"token": "sign-red", "roughness": 1.0, "metal": 0.0, "seed": 7}
        assert route_list.judge_list(rows["finish-route-list"], rows, {}).answer == "pass"
        questions = json.loads((rows["finish-route-list"] / "questions.json").read_text())["wear_wishes"]
        assert len(questions) == 2 and "more worn" in questions[0], questions
        rows = split(folder, rows)
        record = json.loads((rows["finish-route-split"] / "split.json").read_text())[TAKE]
        assert record["fault"] is None and record["unassigned"] == record["disagree"] == 0, record
        finish_of = np.load(rows["finish-route-split"] / TAKE / "finish.npy")
        faces = np.load(rows["finish-route-views"] / TAKE / "faces.npz")["front"]
        colours = np.load(rows["finish-route-views"] / TAKE / "colours.npz")["front"]
        red = np.unique(faces[(faces >= 0) & (colours == RED).all(-1)])
        assert set(finish_of[red]) == {0} and sorted(np.unique(finish_of)) == [0, 1], finish_of
        assert sorted(np.bincount(finish_of)) == [12, 12], finish_of
        assert route_split.judge_split(rows["finish-route-split"], rows, {}).answer == "pass"


def test_an_unassigned_face_or_views_that_disagree_make_a_hole():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        blue_left_out = lambda views, take: two_finish_answer(views, lambda view, colour: 1 if colour == RED else None)
        rows = split(folder, listed(folder, blue_left_out)[0])
        verdict = route_split.judge_split(rows["finish-route-split"], rows, {})
        assert verdict.answer == "fail" and "unassigned" in verdict.findings[0], verdict
        assert not (rows["finish-route-split"] / TAKE).exists()
    mesh = trimesh.creation.box((1, 1, 1))
    tied = {"right": np.zeros(12, dtype=int), "left": np.ones(12, dtype=int)}  # two views, one vote each, apart
    found = route_split.shares(mesh, tied, route_split.finish_parts.voted(tied, 2))
    assert found == {"unassigned": 0.0, "disagree": 1.0, "unseen": 0.0}, found
    assert "disagree" in route_split.split_fault(found)


def test_a_take_with_no_usable_answer_is_a_hole_named_by_the_list():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        lost = route_ask.google_batch.Unanswered("the batch ended JOB_STATE_EXPIRED")
        rows, _ = listed(folder, lambda views, take: lost if take == TAKE else two_finish_answer(views),
                         takes=(TAKE, OTHER))
        assert not (rows["finish-route-list"] / f"{TAKE}.json").exists()
        assert (rows["finish-route-list"] / f"{OTHER}.json").exists()
        verdict = route_list.judge_list(rows["finish-route-list"], rows, {})
        assert verdict.answer == "fail" and list(verdict.findings) == [
            f"{TAKE}: no finish list (no usable answer: Unanswered('the batch ended JOB_STATE_EXPIRED'))"], verdict


def test_the_parts_row_writes_the_methods_interface_each_finish_checked_against_its_colour():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        rows = parted(folder, split(folder, listed(folder, lambda views, take: two_finish_answer(views))[0]))
        found = json.loads((rows["surfaces-parts"] / "parts.json").read_text())
        record = found["takes"][TAKE]
        assert record["method"] == "finish-route" and found["left_out"] == {}, found
        assert {row["words"] for row in record["parts"]} == {"red paint", "blue paint"}, record["parts"]
        assert all(entry["measured_lab"] is not None and entry["by"] for entry in record["finishes"]), record
        assert len(np.load(rows["surfaces-parts"] / TAKE / "parts.npy")) == 24
        assert surfaces.finish_parts.parts_faults(rows["surfaces-parts"]) == []
        assert route_parts.judge_parts(rows["surfaces-parts"], rows, {}).answer == "pass"


def baked(folder, rows):
    """The bake made through the rows, the cloud call faked: each take's job writes back its labelled take, its
    models' entries and a baked model. The bake's inputs, its output and the calls made (with the jobs' files)."""
    data = json.loads(rows["surfaces"].read_text())
    rows["surfaces"].write_text(json.dumps(dict(data, library="cockpit", bake={"models": {"two_boxes": TAKE}})))
    inputs = {"surfaces": rows["surfaces"], "surfaces-parts": rows["surfaces-parts"],
              "resting rules": REPO / "data/checks/resting.json"}
    out = folder / "bake"
    out.mkdir()
    calls = []

    def run(command, **_):
        jobs = [json.loads(pathlib.Path(path).read_text()) for path in command if str(path).endswith("-job.json")]
        calls.append({"command": command, "jobs": jobs,
                      "files": {path.name: json.loads(path.read_text()) for path in out.glob(".bake-*.json")}})
        for job in jobs:
            take = json.loads(pathlib.Path(job["args"][0]).read_text())[route_bake.place_line.TAKE]
            labelled = out / "labelled" / take
            labelled.mkdir(parents=True)
            (labelled / "labels.json").write_text(json.dumps({"take": take, "unnamed_parts": []}))
            (out / "entries").mkdir(exist_ok=True)
            (out / "entries" / f"{take}.json").write_text(json.dumps({"two_boxes": {"parts": str(labelled),
                                                                                   "faces": 100}}))
            (out / "made").mkdir(exist_ok=True)
            (out / "made" / "two_boxes.gltf").write_text("{}")
        return subprocess.CompletedProcess(command, 0, "", "")
    original = route_bake.subprocess.run
    route_bake.subprocess.run = run
    try:
        route_bake.make_bake(inputs, out, 7, {})
    finally:
        route_bake.subprocess.run = original
    return inputs, out, calls


def test_the_bake_paints_and_bakes_each_take_in_one_card_job_with_the_lists_settings_and_the_paint_takes_it_over():
    import library
    finish_parts = route_parts.finish_parts
    kept = finish_parts.COLOUR_DELTA_E
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        finish_parts.COLOUR_DELTA_E = 1000.0  # held wide: every finish keeps its listed surface, so its settings
        try:
            rows = parted(folder, split(folder, listed(folder, lambda views, take: two_finish_answer(views))[0]))
            inputs, out, calls = baked(folder, rows)
        finally:
            finish_parts.COLOUR_DELTA_E = kept
        parts = json.loads((rows["surfaces-parts"] / "parts.json").read_text())["takes"][TAKE]["parts"]
        assert all(row["settings"] for row in parts), parts
        assert len(calls) == 1 and pathlib.Path(calls[0]["command"][1]).name == "blender_cloud.py", calls
        assert calls[0]["command"][-1] == route_bake.place_line.CLASSES  # the bake's cards, one call
        (job,) = calls[0]["jobs"]
        assert job["script"] == route_bake.SCRIPT and str(out / "made") in job["outputs"], job
        records = calls[0]["files"][f".bake-{TAKE}-records.json"]
        head = calls[0]["files"][f".bake-{TAKE}-head.json"]
        assert head["models"] == ["two_boxes"], head
        for record, row in zip(records, parts):
            assert record["surface"] == route_settings.settings_name(row["judge"], row["settings"]), record
            spec = head["specs"][record["surface"]]
            assert spec["library"] == row["judge"] and spec["token"] == row["settings"]["token"], spec
            assert spec["colour"] == library.token_colours()[row["settings"]["token"]], spec
            assert spec["roughness"] == row["settings"]["roughness"] == 1.0, spec  # the list's 1.4, clipped
        assert json.loads((out / "specs.json").read_text()) == head["specs"]
        assert json.loads((out / "baked.json").read_text())["two_boxes"]["parts"] == TAKE
        assert not list(out.glob(".bake-*"))  # the jobs' files are gone
        assert route_bake.bake_faults(out) == [] and route_bake.judge_baked(out, inputs, {}).answer == "pass"
        paint = folder / "paint"
        paint.mkdir()
        route_paint.make_paint({"surfaces-bake": out}, paint, 7, {})
        assert (paint / "painted.json").read_text() == (out / "painted.json").read_text()
        assert (paint / "labelled" / TAKE / "labels.json").exists()


def test_the_check_holds_each_surface_against_the_spec_the_bake_baked():
    import library
    with tempfile.TemporaryDirectory() as temporary:
        bake = pathlib.Path(temporary)
        (bake / "specs.json").write_text(json.dumps({"painted_panel__sign_red_r100_m000": {"colour": [1, 0, 0]}}))
        seen = {}
        original, by_library = route_check.bake_check.check_step, library.by_library
        route_check.bake_check.check_step = lambda inputs, out: seen.update(library=library.by_library("cockpit"))
        try:
            route_check.check_step({"bake": bake}, bake)
        finally:
            route_check.bake_check.check_step, library.by_library = original, by_library
        assert seen["library"]["painted_panel__sign_red_r100_m000"] == {"colour": [1, 0, 0]}
        assert "painted_panel" in seen["library"]  # the library's own surfaces stay


def rechecked(folder, answer, wide=True):
    """The recheck made through the rows (the colour check held wide unless `wide` is False), its one batch faked to
    answer `answer` (a dict, or an exception the batch holds): the take's record, its verdict and the batches asked."""
    finish_parts = route_parts.finish_parts
    kept = finish_parts.COLOUR_DELTA_E
    finish_parts.COLOUR_DELTA_E = 1000.0 if wide else 0.5
    asked = []
    original = route_recheck.ask
    route_recheck.ask = lambda bodies: asked.append(bodies) or {
        take: answer if isinstance(answer, Exception) else json.dumps(answer) for take in bodies}
    try:
        rows = parted(folder, split(folder, listed(folder, lambda views, take: two_finish_answer(views))[0]))
        out = folder / "recheck"
        out.mkdir()
        route_recheck.make_recheck(rows, out, 7, {"objects": [TAKE]})
        record = json.loads((out / "recheck.json").read_text())[TAKE]
        return record, route_recheck.judge_recheck(out, rows, {}), asked
    finally:
        route_recheck.ask = original
        finish_parts.COLOUR_DELTA_E = kept


def test_the_recheck_sorts_one_answer_into_pass_or_a_named_hole_its_suggestion_unapplied():
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary),
                                           {"finishes": [{"finish": 1, "matches": True, "why": "red"},
                                                         {"finish": 2, "matches": True, "why": "blue"}]})
        assert len(asked) == 1 and record["passed"] and verdict.answer == "pass", (record, verdict)
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary), {"finishes": [
            {"finish": 1, "matches": False, "why": "too dull", "token": "alarm", "roughness": 0.2},
            {"finish": 2, "matches": True, "why": "blue"}]})
        assert len(asked) == 1 and not record["passed"], record
        assert record["suggested"] == {"red paint": {"token": "alarm", "roughness": 0.2}}, record["suggested"]
        assert verdict.answer == "fail" and "too dull" in verdict.findings[0], verdict
        assert (pathlib.Path(temporary) / "recheck" / TAKE / "checked-front.png").exists()


def test_the_recheck_makes_an_unanswered_take_a_hole_and_never_asks_a_take_off_its_colour():
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary),
                                           route_ask.google_batch.Unanswered("the batch gave no answer for it"))
        assert len(asked) == 1 and record["asked"] and record["fault"].startswith("no usable answer"), record
        assert verdict.answer == "fail", verdict
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary), {"finishes": []}, wide=False)
        assert not asked and not record["asked"] and record["colour_faults"], (record, asked)
        assert verdict.answer == "fail" and "the free colour check, not asked" in verdict.findings[0], verdict


def test_paid_asks_refuse_outside_a_cleared_run():
    from score.adapters import compute
    try:
        route_ask.asked({TAKE: {}}, "test")
    except compute.Refused:
        return
    raise AssertionError("a Gemini batch was sent outside a cleared run")


def test_the_object_filter_keys_only_a_selecting_row():
    from score import graph
    from score.stages import world1
    from score.store import Store
    with tempfile.TemporaryDirectory() as temporary:
        runner = graph.Runner(surfaces.ROWS, world1(), Store.in_folder(temporary))
        views = runner.stages["finish-route-views"]
        assert runner.params_of(views) == {}
        runner.objects = frozenset({"b", "a"})
        assert runner.params_of(views) == {"objects": ["a", "b"]}
        assert runner.params_of(runner.stages["surfaces-bake"]) == {}
        assert not any(name.startswith("model ") for name in runner.files_of(views, "old_station"))


def test_the_route_is_the_default_line():
    from score import graph, stages
    from score.store import Store
    assert [row.name for row in surfaces.ROWS] == [
        "finish-route-views", "finish-route-list", "finish-route-split", "surfaces-parts", "surfaces-bake",
        "surfaces-paint", "finish-route-recheck", "surfaces-check"]
    assert [row.name for row in surfaces.ROWS if row.paid] == ["finish-route-list", "surfaces-bake",
                                                               "finish-route-recheck"]
    with tempfile.TemporaryDirectory() as temporary:
        runner = graph.Runner(stages.STAGES, stages.world1(), Store.in_folder(temporary))
        line = [graph.node_name(*node) for node in runner.line_nodes(["cockpit"], False)]
        assert all(f"{row.name}@cockpit" in line for row in surfaces.ROWS), line
        gone = ("surfaces-inputs", "surfaces-turntable", "surfaces-lists", "surfaces-maps", "surfaces-names",
                "surfaces-segvigen", "finish-route-fill")
        assert not [name for name in line if name.split("@")[0] in gone], line


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
