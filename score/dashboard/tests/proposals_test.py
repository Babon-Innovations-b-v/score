"""Proposals: a branch's place assembled over the store's accepted outputs takes each node as now, made or stood in
for the paid batch, writes nothing into the real store; the records read back the same locally and from the export;
the API serves them signed in only."""
import dataclasses
import json
import math
import pathlib
import subprocess

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from score import checks, contracts, graph
from score.dashboard.proposals import assemble, branch, compare, drawing, exporting, pictures, records
from score.dashboard.site.asgi import app
from score.dashboard.tests.api_test import api
from score.store import Store, tree_listing


def make_clean(inputs, out, seed, params):
    (out / "clean.txt").write_text(inputs["brief"].read_text().upper())


def make_paint(inputs, out, seed, params):
    (out / "paint.txt").write_text("painted " + (inputs["clean"] / "clean.txt").read_text())


def make_assembly(inputs, out, seed, params):
    (out / "stage.txt").write_text((inputs["clean"] / "clean.txt").read_text() + " | " +
                                   (inputs["paint"] / "paint.txt").read_text())


def judge_written(output, inputs, evidence):
    return checks.Verdict("written", checks.PASS, "a text was written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
WRITTEN = (checks.Check("written", judge_written),)
CLEAN = graph.Stage("clean", "place", make_clean, TEXT, WRITTEN, files={"brief": "{data}/{place}/brief.txt"})
PAINT = graph.Stage("paint", "place", make_paint, TEXT, WRITTEN, after={"clean": ("toy-text", 1)})
ASSEMBLY = graph.Stage("assembly", "place", make_assembly, TEXT, WRITTEN,
                       after={"clean": ("toy-text", 1), "paint": ("toy-text", 1)})


def a_world(folder, brief):
    (folder / "hangar").mkdir(parents=True)
    (folder / "hangar" / "brief.txt").write_text(brief)
    return graph.Environment("toy", 7, {"data": str(folder)})


def standing_store(tmp_path):
    """A real store where every node of the toy table stands accepted on the brief "old hull"."""
    store = Store.in_folder(tmp_path / "real")
    runner = graph.Runner((CLEAN, PAINT, ASSEMBLY), a_world(tmp_path / "main", "old hull"), store,
                          model_record=lambda kind: {})
    runner.run(["hangar"])
    assert store.accepted("assembly@hangar")
    return store


def proposal_run(tmp_path, brief, moved):
    """The toy assembly as a proposal on `brief`, the paint row paid: (its result, the runner)."""
    world = a_world(tmp_path / "branch", brief)
    store = assemble.overlay_store(tmp_path / "real", tmp_path / "scratch")
    table = (CLEAN, dataclasses.replace(PAINT, paid=True, euros=1.0), ASSEMBLY)
    runner = assemble.ProposalRunner(table, world, store, moved, "hangar")
    return assemble.assemble(runner, "hangar", tmp_path / "stage"), runner


def test_a_branch_change_is_made_free_and_a_paid_row_waits_for_the_batch(tmp_path):
    standing_store(tmp_path)
    before = tree_listing(tmp_path / "real")
    result, _ = proposal_run(tmp_path, "new hull", {"clean": {"paid": False, "code": False,
                                                              "files": {"hangar/brief.txt": ["hangar"]}}})
    how = {item["node"]: item["how"] for item in result["taken"]}
    assert how == {"clean@hangar": records.MADE, "paint@hangar": records.PAID, "assembly@hangar": records.MADE}
    assert (tmp_path / "stage" / "stage.txt").read_text() == "NEW HULL | painted OLD HULL"
    assert tree_listing(tmp_path / "real") == before  # the real store is only read
    assert all(item["answer"] == checks.PASS for item in result["taken"] if item["how"] == records.MADE)


def make_failing_assembly(inputs, out, seed, params):
    raise KeyError("a part the old paint does not name")


def test_a_free_node_that_cannot_be_made_before_the_paid_batch_stands_in_for_it(tmp_path):
    standing_store(tmp_path)
    world = a_world(tmp_path / "branch", "new hull")
    store = assemble.overlay_store(tmp_path / "real", tmp_path / "scratch")
    table = (CLEAN, dataclasses.replace(PAINT, paid=True, euros=1.0),
             dataclasses.replace(ASSEMBLY, make=make_failing_assembly))
    runner = assemble.ProposalRunner(table, world, store, {"clean": {"paid": False, "code": True, "files": {}}},
                                     "hangar")
    result = assemble.assemble(runner, "hangar", tmp_path / "stage")
    taken = {item["node"]: item for item in result["taken"]}
    assert taken["assembly@hangar"]["how"] == records.PAID
    assert "KeyError" in taken["assembly@hangar"]["why"]
    assert result["assembly"] == store.accepted("assembly@hangar")


def test_another_places_node_is_shown_as_it_stands(tmp_path):
    standing_store(tmp_path)
    world = a_world(tmp_path / "branch", "new hull")
    store = assemble.overlay_store(tmp_path / "real", tmp_path / "scratch")
    runner = assemble.ProposalRunner((CLEAN, PAINT, ASSEMBLY), world, store,
                                     {"clean": {"paid": False, "code": True, "files": {}}}, "station")
    assert runner.usable("clean", "hangar", None) == store.accepted("clean@hangar")
    assert runner.taken["clean@hangar"]["how"] == records.AS_NOW


def test_a_branch_moving_nothing_here_shows_the_place_as_it_stands(tmp_path):
    store = standing_store(tmp_path)
    result, _ = proposal_run(tmp_path, "new hull", {})
    assert {item["how"] for item in result["taken"]} == {records.AS_NOW}
    assert result["assembly"] == store.accepted("assembly@hangar")
    assert not (tmp_path / "scratch" / "objects" / "records").exists()


def test_the_place_is_shown_with_its_neighbours_only_when_the_branch_moves_them(tmp_path):
    standing_store(tmp_path)
    _, runner = proposal_run(tmp_path, "old hull", {})
    assert assemble.target(runner, "hangar") == assemble.ASSEMBLY
    shows = graph.Stage("neighbours", "place", make_assembly, TEXT, WRITTEN, after={"assembly": ("toy-text", 1)})
    runner = assemble.ProposalRunner((CLEAN, PAINT, ASSEMBLY, shows), runner.world, runner.store,
                                     {"neighbours": {"paid": False, "code": True, "files": {}}}, "hangar")
    assert assemble.target(runner, "hangar") == assemble.NEIGHBOURS


def test_the_overlay_reads_through_and_writes_only_its_own_root(tmp_path):
    real = tmp_path / "real" / "objects"
    (real / "blobs").mkdir(parents=True)
    (real / "blobs" / "abc").write_text("real")
    overlay = assemble.Overlay(tmp_path / "scratch", real)
    assert overlay.read_bytes("blobs/abc") == b"real"
    overlay.write_bytes("records/x.json", b"{}")
    assert (tmp_path / "scratch" / "records" / "x.json").is_file() and not (real / "records").exists()
    assert overlay.keys("") == ["blobs/abc", "records/x.json"]


def test_how_a_node_is_taken_is_named_alike_on_both_sides():
    assert (assemble.AS_NOW, assemble.MADE, assemble.PAID) == (records.AS_NOW, records.MADE, records.PAID)


def a_proposal(root, branch_name="fix-ship-hull", place="hangar", made_at="2026-10-18T12:00:00Z"):
    partial = root / f".{branch_name}-partial"
    (partial / "stills").mkdir(parents=True)
    (partial / "stills" / "ship.jpg").write_bytes(b"jpeg")
    (partial / "web3d").mkdir()
    (partial / "web3d" / f"{place}.glb").write_bytes(b"whole")
    (partial / "web3d" / f"{place}-light.glb").write_bytes(b"light")
    (partial / "web3d" / f"{place}.json").write_text("{}")
    return records.put(root, partial, {"branch": branch_name, "place": place, "commit": "c0ffee", "made_at": made_at,
                                       "change": "The hull is one piece.", "needs_paid_batch": ["surfaces-bake"],
                                       "hero": "stills/ship.jpg", "has_3d": True})


def test_records_are_kept_and_listed_newest_first(tmp_path):
    a_proposal(tmp_path, "fix-ship-hull", made_at="2026-10-18T12:00:00Z")
    a_proposal(tmp_path, "fix-sound", made_at="2026-10-18T13:00:00Z")
    assert [item["branch"] for item in records.listing(tmp_path)] == ["fix-sound", "fix-ship-hull"]
    assert records.read(tmp_path, "fix-sound", "hangar")["change"] == "The hull is one piece."
    assert records.file_path(tmp_path, "fix-sound", "hangar", "stills/ship.jpg").read_bytes() == b"jpeg"
    assert records.file_path(tmp_path, "fix-sound", "hangar", "proposal.json") is None
    assert records.file_path(tmp_path, "fix-sound", "hangar", "stills/../../x") is None


def test_a_name_with_a_path_in_it_is_refused(tmp_path):
    for bad in ("..", "../x", "a/b", ".hidden", ""):
        try:
            records.folder(tmp_path, bad, "hangar")
        except records.BadName:
            continue
        raise AssertionError(f"{bad!r} was taken as a name")


def test_the_export_carries_records_first_and_whole_copies_last(tmp_path):
    a_proposal(tmp_path)
    order = [target for _, target in exporting.files(tmp_path)]
    assert order[:2] == ["proposals/index.json", "proposals/fix-ship-hull/hangar/proposal.json"]
    assert order[-1] == "proposals/fix-ship-hull/hangar/web3d/hangar.glb"
    assert len(order) == len(set(order)) == 6
    assert exporting.files(tmp_path / "none") == []


def test_one_sentence_from_the_commits():
    listed = [{"sha": "1", "subject": "library: the ship's own surface set"}, {"sha": "2", "subject": "kit: doors."}]
    assert branch.change_sentence(listed) == "The ship's own surface set; doors."
    assert branch.change_sentence([]) == ""


def test_the_commits_past_main_are_read_from_git(tmp_path):
    def run(*words):
        subprocess.run(["git", "-C", str(tmp_path), *words], check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "start")
    run("branch", "fix")
    run("checkout", "-q", "fix")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "hull: one piece")
    listed = branch.commits(tmp_path, "main", branch.tip(tmp_path, "fix"))
    assert [item["subject"] for item in listed] == ["hull: one piece"]


def test_the_places_draft_films_and_sounds_are_carried_and_nothing_else(tmp_path):
    drafts = tmp_path / "fix-sound"
    real = b"x" * pictures.LEAST_BYTES
    for name in ("hangar/door take.wav", "cut.mp4", "demo-film@hangar/film.mp4", "demo-film@camp/film.mp4",
                 "old/demo-film@hangar/film.mp4", "notes.txt"):
        (drafts / name).parent.mkdir(parents=True, exist_ok=True)
        (drafts / name).write_bytes(real)
    (drafts / "hangar" / "pointer.ogg").write_bytes(b"115 bytes of a stand-in")
    found = pictures.media(drafts, "hangar", tmp_path / "out")
    assert [(item["name"], item["kind"]) for item in found] == [
        ("cut.mp4", "film"), ("demo-film-hangar-film.mp4", "film"), ("hangar-door-take.wav", "sound")]
    assert all(records.FILE.match(item["file"]) for item in found)
    assert pictures.media(tmp_path / "missing", "hangar", tmp_path / "out") == []


def test_stills_take_the_scene_record_the_stage_was_assembled_from_else_the_branchs(tmp_path):
    (tmp_path / "data/scene").mkdir(parents=True)
    views = [{"name": f"v{number}", "eye": [0, 1, 0], "aim": [1, 1, 0]} for number in range(6)]
    (tmp_path / "data/scene/hangar.json").write_text(json.dumps({"views": views}))
    assert [view["name"] for view in pictures.record_views(tmp_path / "stage", tmp_path, "hangar")] == [
        f"v{number}" for number in range(6)]
    assert pictures.record_views(tmp_path / "stage", tmp_path, "nowhere") == []
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/scene.json").write_text(json.dumps({"views": views[4:]}))
    assert [view["name"] for view in pictures.record_views(tmp_path / "stage", tmp_path, "hangar")] == ["v4", "v5"]


SIX_VIEWS = [{"name": f"v{number}", "eye": [0, 1, number], "aim": [1, 1, 0]} for number in range(6)]


def layer(stage, how):
    return {"node": f"{stage}@hangar", "stage": stage, "how": how}


def test_a_still_drawing_takes_the_branchs_first_cameras_and_says_it_is_a_local_preview():
    planned = drawing.plan([layer("assembly", records.MADE)], SIX_VIEWS, span=(1.0, 97.0))
    assert [view["name"] for view in planned["views"]] == ["v0", "v1", "v2", "v3"]
    assert all("frame" not in view and view["look_only"] for view in planned["views"])
    assert planned["views"][0]["up"] == drawing.UP and planned["views"][0]["fov"] == 75.0
    assert planned["clip"] == [] and planned["labels"] == [drawing.LOCAL_LABEL] and planned["size"] == [640, 360]


def test_a_branch_that_makes_a_moving_layer_is_drawn_at_moments_over_the_stage_and_clipped():
    planned = drawing.plan([layer("assembly", records.MADE), layer("motion", records.MADE)], SIX_VIEWS,
                           span=(1.0, 96.0))
    timed = [view for view in planned["views"] if "frame" in view]
    assert [view["frame"] for view in timed] == [1, 20, 39, 58, 77, 96]
    assert all(view["eye"] == SIX_VIEWS[0]["eye"] for view in timed)
    assert planned["clip"] == [view["name"] for view in timed] == [f"v0-at-{frame:04d}" for frame in
                                                                    (1, 20, 39, 58, 77, 96)]
    assert planned["moving"] == ["motion"]
    assert drawing.plan([layer("motion", records.MADE)], SIX_VIEWS, span=None)["clip"] == []


def test_a_branchs_film_plan_gives_film_cameras_at_their_own_frames():
    film = [{"name": f"shot0-{number:03d}", "eye": [number, 1, 0], "aim": [0, 1, 0], "frame": number}
            for number in range(1, 193)]
    planned = drawing.plan([layer("assembly", records.MADE)], [], film)
    assert [view["name"] for view in planned["views"]] == [f"film-{number}" for number in range(1, 7)]
    assert [view["frame"] for view in planned["views"]] == [1, 39, 77, 116, 154, 192]
    assert planned["clip"] == [f"film-{number}" for number in range(1, 7)]


def test_a_paid_row_with_a_free_preview_is_labelled_and_one_without_is_named_unshown():
    planned = drawing.plan([layer("light-passes", records.PAID), layer("surfaces-bake", records.PAID)], SIX_VIEWS)
    assert [item["stage"] for item in planned["previews"]] == ["light-passes"]
    assert planned["unshown"] == ["surfaces-bake"]
    assert planned["labels"] == [drawing.LOCAL_LABEL, drawing.PAID_LABEL]


TOY_STAGE = """#usda 1.0
(
    defaultPrim = "hangar"
    startTimeCode = 1
    endTimeCode = 48
    upAxis = "Y"
)
def Xform "hangar"
{
    def Xform "Lights"
    {
        double3 xformOp:translate = (2, 3, 4)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        def SphereLight "lamp"
        {
            float inputs:intensity = 10
            float inputs:exposure = 1
            float inputs:radius = 0.2
        }
    }
}
"""


def test_the_stages_own_lamps_and_time_span_are_read_for_the_drawing(tmp_path):
    stage = tmp_path / "hangar.usda"
    stage.write_text(TOY_STAGE)
    [lamp] = pictures.stage_lamps(stage)
    assert lamp["at"] == [2.0, 3.0, 4.0] and abs(lamp["energy"] - 10 * math.pi * 2) < 1e-6
    assert abs(lamp["radius"] - 0.2) < 1e-6
    assert pictures.time_span(stage) == (1.0, 48.0)
    still = tmp_path / "still.usda"
    still.write_text('#usda 1.0\n(\n    defaultPrim = "hangar"\n)\ndef Xform "hangar"\n{\n}\n')
    assert pictures.stage_lamps(still) == [] and pictures.time_span(still) is None


def test_stills_are_drawn_lit_by_the_stages_lamps_and_labelled_under_the_picture(tmp_path, monkeypatch):
    stage = tmp_path / "hangar.usda"
    stage.write_text(TOY_STAGE)
    planned = drawing.plan([layer("light-passes", records.PAID)], SIX_VIEWS[:1])
    jobs = []

    def blender(command, **options):
        job = json.loads(pathlib.Path(command[-2]).read_text())
        jobs.append(job)
        for view in job["views"]:
            look = pathlib.Path(command[-1]) / f"{view['name']}-look.png"
            Image.new("RGB", tuple(job["size"]), (90, 90, 90)).save(look)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(pictures.subprocess, "run", blender)
    found = pictures.stills(stage, planned, tmp_path / "before", "before")
    assert found == [{"name": "v0", "file": "before/v0.jpg"}]
    assert len(jobs[0]["lights"]) == 1 and jobs[0]["views"] == planned["views"]
    with Image.open(tmp_path / "before" / "v0.jpg") as drawn:
        assert drawn.size == (640, 360 + 2 * pictures.LABEL_LINE)


def a_still(path, colour, block=0):
    """A 640x360 still in one colour with a `block`-pixel square of white in its corner, and the label strip under."""
    picture = Image.new("RGB", (640, 360 + 16), colour)
    if block:
        picture.paste((255, 255, 255), (0, 0, block, block))
    path.parent.mkdir(parents=True, exist_ok=True)
    picture.save(path, quality=95)


def measured(tmp_path, block):
    a_still(tmp_path / "before" / "v0.jpg", (40, 40, 40))
    a_still(tmp_path / "stills" / "v0.jpg", (40, 40, 40), block)
    record = {"commit": "c0ffee", "drawing": {"size": [640, 360], "unshown": ["surfaces-bake"]},
              "stills": [{"name": "v0", "file": "stills/v0.jpg"}], "before": [{"name": "v0", "file": "before/v0.jpg"}]}
    return compare.difference(tmp_path, record)


def test_an_after_that_looks_like_its_before_is_held_with_its_reason(tmp_path):
    found = measured(tmp_path, 0)
    assert found["pairs"]["v0"]["changed"] == 0.0 and not found["shows_change"]
    assert "looks the same" in found["held"] and "paid batch" in found["held"]
    assert not measured(tmp_path, 20)["shows_change"]  # 400 pixels, under 0.5% of the picture


def test_an_after_that_changes_a_visible_part_of_the_picture_is_shown(tmp_path):
    found = measured(tmp_path, 60)  # 3,600 pixels, about 1.6% of the picture
    assert found["shows_change"] and found["held"] is None and found["pairs"]["v0"]["changed"] > 0.01


def test_a_proposal_without_a_before_is_held_unless_the_place_is_all_new(tmp_path):
    a_still(tmp_path / "stills" / "v0.jpg", (40, 40, 40))
    record = {"commit": "c0ffee", "stills": [{"name": "v0", "file": "stills/v0.jpg"}],
              "before": [{"error": "Blender's stills failed (exit 137): "}]}
    assert "No before picture" in compare.difference(tmp_path, record)["held"]
    record["before"] = [{"error": f"hangar {compare.NOTHING_ACCEPTED}: no before picture"}]
    assert compare.difference(tmp_path, record)["shows_change"]
    assert "No after picture" in compare.difference(tmp_path, {"commit": "c0ffee", "stills": []})["held"]


def test_the_moments_clip_lays_the_before_beside_the_after(tmp_path):
    names = ["v0-at-0001", "v0-at-0048"]
    for name in names:
        a_still(tmp_path / "before" / f"{name}.jpg", (40, 40, 40))
        a_still(tmp_path / "stills" / f"{name}.jpg", (40, 40, 40), 60)
    record = {"commit": "c0ffee", "drawing": {"clip": names},
              "stills": [{"name": name, "file": f"stills/{name}.jpg"} for name in names],
              "before": [{"name": name, "file": f"before/{name}.jpg"} for name in names]}
    made = compare.clip(tmp_path, record, tmp_path / "media" / "clip.mp4")
    assert made["file"] == "media/clip.mp4" and records.FILE.match(made["file"]) and made["bytes"] > 0
    record["drawing"]["clip"] = names + ["v0-at-0096"]
    assert compare.clip(tmp_path, record, tmp_path / "media" / "missing.mp4") is None


@pytest.mark.django_db(transaction=True)
def test_the_api_serves_proposals_signed_in(world, settings):
    a_proposal(pathlib.Path(settings.SCORE_HOME) / "proposals")
    client = api()
    assert client.get("/api/proposals").json()[0]["branch"] == "fix-ship-hull"
    assert client.get("/api/proposals/fix-ship-hull/hangar").json()["hero"] == "stills/ship.jpg"
    assert client.get("/api/proposals/fix-ship-hull/nowhere").status_code == 404
    assert client.get("/proposal/fix-ship-hull/hangar/web3d/hangar-light.glb").content == b"light"
    assert client.get("/proposal/fix-ship-hull/hangar/proposal.json").status_code == 404
    assert client.get("/proposal/fix-ship-hull/hangar/stills/..%2F..%2Findex.json").status_code == 404
    unsigned = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    assert unsigned.get("/api/proposals").status_code == 401
    assert unsigned.get("/proposal/fix-ship-hull/hangar/stills/ship.jpg").status_code == 401
