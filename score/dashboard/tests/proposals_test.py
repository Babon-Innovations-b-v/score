"""Proposals: a branch's place assembled over the store's accepted outputs takes each node as now, made or stood in
for the paid batch, writes nothing into the real store; the records read back the same locally and from the export;
the API serves them signed in only."""
import dataclasses
import json
import pathlib
import subprocess

import pytest
from fastapi.testclient import TestClient

from score import checks, contracts, graph
from score.dashboard.proposals import assemble, branch, exporting, pictures, records
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
    return graph.World("toy", 7, {"data": str(folder)})


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
    runner = assemble.ProposalRunner(table, world, store, moved)
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


def test_a_branch_moving_nothing_here_shows_the_place_as_it_stands(tmp_path):
    store = standing_store(tmp_path)
    result, _ = proposal_run(tmp_path, "new hull", {})
    assert {item["how"] for item in result["taken"]} == {records.AS_NOW}
    assert result["assembly"] == store.accepted("assembly@hangar")
    assert not (tmp_path / "scratch" / "objects" / "records").exists()


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


def test_stills_take_the_scene_records_first_cameras(tmp_path):
    (tmp_path / "data/scene").mkdir(parents=True)
    views = [{"name": f"v{number}", "eye": [0, 1, 0], "aim": [1, 1, 0]} for number in range(6)]
    (tmp_path / "data/scene/hangar.json").write_text(json.dumps({"views": views}))
    chosen = pictures.views(tmp_path, "hangar")
    assert [view["name"] for view in chosen] == ["v0", "v1", "v2", "v3"]
    assert chosen[0]["up"] == pictures.UP and chosen[0]["fov"] == 75.0
    assert pictures.views(tmp_path, "nowhere") == []


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
