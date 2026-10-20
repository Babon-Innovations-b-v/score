"""The finish route's own checks, with no spend: a two-box model (one textured red, one blue by its colour factor)
is cast from every side with its colours read from its own texture, split into two colour groups that the views
agree on, its finish list parsed to library surfaces with settings (a group the answer leaves out joined by colour),
filled and colour-checked against what its texture shows, a failing finish tweaked to the library token nearest its
seen colour; the paid rows refuse outside a cleared run, without an object filter and past the trial's cap; the
route's rows are on no line unless asked for by name; the runner's object filter keys and narrows a selecting row only.

Run: .venv/bin/python score/stages/surfaces/route_test.py
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image
from trimesh.visual.material import PBRMaterial

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages import surfaces  # noqa: E402
from score.stages.surfaces import (route_cap, route_cast, route_data, route_fill, route_list,  # noqa: E402
                                   route_recheck, route_split, route_views)

RED, BLUE = (200, 30, 30), (30, 40, 200)
TAKE = "two_boxes-t1"


def two_boxes(folder):
    """A glb of two boxes side by side: the left one textured red, the right one blue by its colour factor."""
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
    path.write_text(json.dumps({"place": "cockpit", "takes": {
        TAKE: {"places": ["cockpit"], "library_places": ["cockpit"], "place": "cockpit", "kind": "two_boxes",
               "object": "two boxes"},
        "other-t1": {"places": ["cockpit"], "library_places": ["cockpit"], "place": "cockpit", "kind": "other",
                     "object": "another"}}}))
    return path


def cast_and_split(folder):
    """The views and split rows' makes on the two boxes, the object filter keeping TAKE: their output folders."""
    views, split = folder / "views", folder / "split"
    views.mkdir()
    split.mkdir()
    inputs = {"surfaces": place_data(folder), f"model {TAKE}": two_boxes(folder)}
    params = {"objects": [TAKE]}
    route_views.make_views(inputs, views, 7, params)
    route_split.make_split({**inputs, "finish-route-views": views}, split, 7, params)
    return inputs, views, split


def test_views_read_the_texture_and_the_split_finds_both_colours():
    with tempfile.TemporaryDirectory() as temporary:
        inputs, views, split = cast_and_split(pathlib.Path(temporary))
        record = json.loads((views / "views.json").read_text())
        assert list(record) == [TAKE], record  # the filter left other-t1 out
        assert record[TAKE]["close_up"] == route_data.STAND_IN
        assert route_views.judge_views(views, inputs, {}).answer == "pass"
        colours = np.load(views / TAKE / "colours.npz")["front"]
        faces = np.load(views / TAKE / "faces.npz")["front"]
        seen = {tuple(colour) for colour in colours[faces >= 0]}
        assert seen == {RED, BLUE}, seen
        groups = json.loads((split / "groups.json").read_text())[TAKE]["groups"]
        assert sorted(tuple(entry["srgb"]) for entry in groups) == sorted([BLUE, RED]), groups
        assert route_split.judge_split(split, {**inputs, "finish-route-views": views}, {}).answer == "pass"


def test_a_model_with_no_file_fails_by_name():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        inputs = {"surfaces": place_data(folder)}
        route_views.make_views(inputs, folder, 7, {"objects": ["other-t1"]})
        verdict = route_views.judge_views(folder, inputs, {})
        assert verdict.answer == "fail" and verdict.findings[0].startswith("other-t1: no model"), verdict


def test_a_filter_that_keeps_no_take_fails_the_views():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        inputs = {"surfaces": place_data(folder)}
        route_views.make_views(inputs, folder, 7, {"objects": ["no-such-take"]})
        verdict = route_views.judge_views(folder, inputs, {})
        assert verdict.answer == "fail" and "no take to work on" in verdict.findings[0], verdict


def answer_for(groups, red_token):
    """A list answer naming the red group only (the blue one left out)."""
    red = next(entry["group"] for entry in groups if entry["srgb"] == list(RED))
    return {"finishes": [{"parts": "the left box", "finish": "red paint", "groups": [red + 1], "surface": "M1",
                          "token": red_token, "roughness": 1.4, "metal": 0.0, "fits": True}]}


def test_the_list_is_settled_fill_checks_colour_and_a_tweak_takes_the_nearest_token():
    with tempfile.TemporaryDirectory() as temporary:
        inputs, views, split = cast_and_split(pathlib.Path(temporary))
        groups = json.loads((split / "groups.json").read_text())[TAKE]["groups"]
        tokens = route_list.library_tokens()
        surfaces = {"dark_panel": {"family": "painted"}}
        far = max(tokens, key=lambda token: route_cast.lab_of(route_fill.token_srgb(token)[None])[0][0])  # lightest
        answer = answer_for(groups, far)
        finishes = route_list.grouped(route_list.finishes_of(answer, surfaces, 7), answer, groups)
        assert sorted(finishes[0]["groups"]) == [0, 1] and "left out" in finishes[0]["by"], finishes
        assert finishes[0]["settings"] == {"token": far, "roughness": 1.0, "metal": 0.0, "seed": 7}
        out = pathlib.Path(temporary) / "fill"
        filled = route_fill.fill_take({"views": views / TAKE, "split": split / TAKE, "out": out}, finishes,
                                      {"dark_panel": "painted"}, len(groups))
        assert not filled[0]["colour_fits"], filled  # one light token cannot be both red and blue
        assert (out / "filled-front.png").exists()
        nudged = route_recheck.tweaked(filled[0], {}, tokens)
        assert nudged["settings"]["token"] == route_recheck.nearest_token(filled[0]["seen_lab"], tokens)
        assert "colour_fits" not in nudged
        assert route_recheck.failed(filled, {0: {"matches": True}}) == [0]


def group_of(groups, colour):
    """The 1-based number of the split's group of a colour."""
    return next(entry["group"] for entry in groups if entry["srgb"] == list(colour)) + 1


def made_through_the_rows(folder, list_answer, recheck_answers):
    """views, split, list, fill and recheck made on the two boxes with the two Gemini asks stubbed (no spend): the
    list's ask answers `list_answer(groups)`, the recheck's each try's `recheck_answers(try)`; the recheck folder."""
    inputs, views, split = cast_and_split(folder)
    groups = json.loads((split / "groups.json").read_text())[TAKE]["groups"]
    asked = []
    route_list.ask = lambda body: json.dumps(list_answer(groups))
    route_recheck.ask = lambda body: asked.append(body) or recheck_answers(len(asked))
    rows = {"finish-route-views": views, "finish-route-split": split}
    for name, make in (("list", route_list.make_list), ("fill", route_fill.make_fill),
                       ("recheck", route_recheck.make_recheck)):
        out = folder / name
        out.mkdir()
        make({**inputs, **rows}, out, 7, {"objects": [TAKE]})
        rows[f"finish-route-{name}"] = out
    return {**inputs, **rows}


def two_finishes(groups):
    return {"finishes": [
        {"parts": "left box", "finish": "red paint", "groups": [group_of(groups, RED)], "surface": "M1",
         "token": "sign-red", "roughness": 0.4, "metal": 0.0, "fits": True},
        {"parts": "right box", "finish": "blue paint", "groups": [group_of(groups, BLUE)], "surface": "M1",
         "token": "bay-three", "roughness": 0.4, "metal": 0.0, "fits": True, "wear_wish": "more worn"}]}


def test_a_finish_no_library_token_fits_is_named_after_its_tweak_changes_nothing():
    """The red box's sign-red lies within COLOUR_DELTA_E of its texture; no library token lies within it of the blue
    box's, so its tweak (the nearest token) changes nothing and the take fails by name."""
    originals = route_list.ask, route_recheck.ask
    try:
        with tempfile.TemporaryDirectory() as temporary:
            rows = made_through_the_rows(pathlib.Path(temporary), two_finishes,
                                         lambda attempt: {0: {"matches": True}, 1: {"matches": True}})
            assert route_list.judge_list(rows["finish-route-list"], rows, {}).answer == "pass"
            questions = json.loads((rows["finish-route-list"] / "questions.json").read_text())["wear_wishes"]
            assert questions and "more worn" in questions[0], questions
            assert route_fill.judge_fill(rows["finish-route-fill"], rows, {}).answer == "pass"
            filled = json.loads((rows["finish-route-fill"] / "fill.json").read_text())[TAKE]
            assert [entry["colour_fits"] for entry in filled] == [True, False], filled
            verdict = route_recheck.judge_recheck(rows["finish-route-recheck"], rows, {})
            assert verdict.answer == "fail", verdict
            assert verdict.findings[0].startswith(f"{TAKE}: no library surface fits (blue paint"), verdict.findings
            assert "no tweak left" in verdict.findings[0]
    finally:
        route_list.ask, route_recheck.ask = originals


def test_the_recheck_stops_after_three_tries_and_keeps_the_last_checked_settings():
    tokens = ("sign-red", "alarm", "hazard")
    originals = route_list.ask, route_recheck.ask
    try:
        with tempfile.TemporaryDirectory() as temporary:
            rows = made_through_the_rows(pathlib.Path(temporary), lambda groups: {"finishes": [two_finishes(groups)[
                "finishes"][0] | {"groups": [1, 2]}]},
                                         lambda attempt: {0: {"matches": False, "why": "too dull",
                                                              "token": tokens[attempt % 3]}})
            record = json.loads((rows["finish-route-recheck"] / "recheck.json").read_text())[TAKE]
            assert len(record["tries"]) == 3 and not record["passed"], record
            assert record["finishes"][0]["settings"] == record["tries"][-1]["settings"][0]
            assert (rows["finish-route-recheck"] / TAKE / "try-3-front.png").exists()
    finally:
        route_list.ask, route_recheck.ask = originals


def test_paid_rows_refuse_outside_a_cleared_run():
    from score.adapters import compute
    for ask in (route_list.ask, route_recheck.ask):
        try:
            ask({})
        except compute.Refused:
            continue
        raise AssertionError(f"{ask.__module__} asked outside a cleared run")


def test_the_object_filter_keys_only_a_selecting_row():
    from score import graph
    from score.stages import world1
    from score.store import Store
    with tempfile.TemporaryDirectory() as temporary:
        runner = graph.Runner(surfaces.ROUTE, world1(), Store.in_folder(temporary))
        views = runner.stages["finish-route-views"]
        plain = graph.Stage("plain", "place", lambda *args: None, views.contract)
        assert runner.params_of(views) == {}
        runner.objects = frozenset({"b", "a"})
        assert runner.params_of(views) == {"objects": ["a", "b"]}
        assert runner.params_of(plain) == {}
        assert not any(name.startswith("model ") for name in runner.files_of(views, "old_station"))
        assert all(row.selects for row in surfaces.ROUTE)
        assert [row.name for row in surfaces.ROUTE if row.paid] == ["finish-route-list", "finish-route-recheck"]


def test_paid_rows_refuse_without_an_object_filter():
    with tempfile.TemporaryDirectory() as temporary:
        for make in (route_list.make_list, route_recheck.make_recheck):
            try:
                make({}, pathlib.Path(temporary), 7, {})
            except ValueError as refused:
                assert "--object" in str(refused)
                continue
            raise AssertionError(f"{make.__module__} ran without an object filter")


def test_the_trial_cap_refuses_an_ask_past_its_euros():
    import google_spend
    model = route_list.finish_ask.LIST_MODEL
    kept = google_spend.LEDGER, google_spend.CACHE
    with tempfile.TemporaryDirectory() as temporary:
        google_spend.LEDGER, google_spend.CACHE = pathlib.Path(temporary) / "ledger.jsonl", pathlib.Path(temporary)
        try:
            lines = [{"time": "2026-10-20T10:00:00", "call": "a", "state": "finished", "model": model,
                      "caller": "finish-route-list", "euros": 4.92},
                     {"time": "2026-10-20T10:01:00", "call": "b", "state": "finished", "model": "other",
                      "caller": "surfaces-lists", "euros": 9.0}]
            google_spend.LEDGER.write_text("".join(json.dumps(line) + "\n" for line in lines))
            assert abs(route_cap.route_euros() - 4.92) < 1e-9
            route_cap.require_room(model, {"ask": 1})  # 4.92 + 0.05 fits
            started = {"time": "2026-10-20T10:02:00", "call": "c", "state": "started", "caller": "finish-route-recheck",
                       "model": model, "estimate": 0.05}
            with google_spend.LEDGER.open("a") as ledger:
                ledger.write(json.dumps(started) + "\n")
            try:
                route_cap.require_room(model, {"ask": 1})
            except RuntimeError as refused:
                assert "trial cap" in str(refused)
            else:
                raise AssertionError("an ask past the trial's EUR 5 was let through")
            google_spend.keep(google_spend.cache_path(model, {"ask": 1}), {})
            route_cap.require_room(model, {"ask": 1})  # asked before: free
        finally:
            google_spend.LEDGER, google_spend.CACHE = kept


def test_the_route_is_on_no_line_unless_asked_for():
    from score import graph, stages
    from score.store import Store
    with tempfile.TemporaryDirectory() as temporary:
        runner = graph.Runner(stages.STAGES, stages.world1(), Store.in_folder(temporary))
        try:
            graph.ask(None)
            plain = [graph.node_name(*node) for node in runner.line_nodes(["cockpit"], False)]
            assert not [name for name in plain if name.startswith("finish-route-")], plain
            graph.ask(["finish-route-recheck"])
            asked = [graph.node_name(*node) for node in runner.line_nodes(["cockpit"], False, ["finish-route-recheck"])]
            assert asked == [f"{name}@cockpit" for name in surfaces.ROUTE_NAMES], asked
        finally:
            graph.ask(None)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
