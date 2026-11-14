"""Invariant: the hosted cockpit gets the store whole and the store gets only the owner's asks. The export holds the
state, places, pictures and films in its upload order and under its cap, the same twice; it goes up content-addressed
behind the sync token (bad names, paths, offsets and hashes refused) and is swapped in only whole; a pass syncs
nothing from a checkout not clean and pushed or when the runner's price fails, and says what moved. A request comes
back once; a decision, figure or waiver applies only for the store's owner and never in an agent's process, but for
his decision made in chat, applied once by its quoted yes through the same request code while its target stands; the
listener answers a Buy at once unless its price needs a pass, never lets a slow request hold back the next, and sends
the batch record while it lives and once as it ends; a moved or reset store shows no old batch. The release pins a
pushed commit in the host's style; the timer's install refuses what cannot feed it. A hosted process stays light.

Breaks that turn this red (each applied once and seen red, then reverted):
- building.build: only the first place's bundle -> test_the_cockpit_gets_the_store_whole_...
- building.build: no node thumbnails (`range(0)`) -> test_the_cockpit_gets_the_store_whole_...
- building.build: each step's large picture at the thumbnail side -> test_the_cockpit_gets_the_store_whole_...
- building.Filler.room: the cap check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- endpoints.token_ok: the compare dropped -> test_the_cockpit_gets_the_store_whole_...
- endpoints.pin: `{"commit": None}` -> test_the_cockpit_gets_the_store_whole_...
- endpoints.checked_path: the ".." check dropped -> test_the_cockpit_gets_the_store_whole_...
- endpoints.blob: `if offset != have:` -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- client.push_export: `whole = True` -> test_the_cockpit_gets_the_store_whole_...
- client.uploaded: the deadline as if counted before the build -> test_the_cockpit_gets_the_store_whole_...
- endpoints.swept: unused blobs kept (`if stale:`) -> test_the_cockpit_gets_the_store_whole_...
- building.pictures_folder: old versions kept -> test_the_cockpit_gets_the_store_whole_...
- endpoints.readable: the format check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- endpoints.report: the state kept "waiting" -> test_the_cockpit_gets_the_store_whole_...
- applying.apply_decision: the owner check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- applying.OWNER_FIGURES: a "month" kind added -> test_the_cockpit_gets_the_store_whole_...
- pages/actions.owner_figure_off_why: the agent check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- pages/actions.set_books_figure: the amount check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- pages/actions.scene_name: the name check -> `if False:`; or library_actions.carried_out: the refusal dropped ->
  test_the_cockpit_gets_the_store_whole_...
- pages/actions.record_change: no inbox write -> test_the_cockpit_gets_the_store_whole_...
- client.sync_pass: `applied = []` -> test_the_cockpit_gets_the_store_whole_...
- client.sync_pass: a `usd_sweep()` also inside the pricing lock -> test_the_cockpit_gets_the_store_whole_...
- client.step_run: `err` without "out of time after ..." -> test_the_cockpit_gets_the_store_whole_...
- client.design_moved: the copy check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- client.sync_pass: the basket not made -> test_the_cockpit_gets_the_store_whole_...
- client.sync_pass: the moved-checkout words never said -> test_the_cockpit_gets_the_store_whole_...
- client.sync_pass: the tree refusal ignored -> test_the_cockpit_gets_the_store_whole_...
- client.tree_refusal: uncommitted changes ignored -> test_the_cockpit_gets_the_store_whole_...
- state/exported.made_words: "export of" for "state from" -> test_the_cockpit_gets_the_store_whole_...
- client.readings_fixed: `reading_fixes.said(...)` -> `str(...)` (its words never said) ->
  test_the_cockpit_gets_the_store_whole_...
- client.asked_of_readings: the Stop everything check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- client.light_read: asks the unparted places -> test_the_cockpit_gets_the_store_whole_...
- client.film_previews: "" for none wanted -> test_the_cockpit_gets_the_store_whole_...
- client.step_run: the group not ended -> test_the_cockpit_gets_the_store_whole_...
- listen.round_once: no kinds asked -> test_the_cockpit_gets_the_store_whole_...
- listen.answered_here: a Buy left for the pass not kept in `left` -> test_the_cockpit_gets_the_store_whole_...
- client.buy_waits: the pass's pricing ignored -> test_the_cockpit_gets_the_store_whole_...
- listen.round_once: the stopping check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- client.figures_moved: the basket's commit check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- listen.batch_pushed: `if live:` alone -> test_the_cockpit_gets_the_store_whole_...
- endpoints.note: a claimed request noted too -> test_the_cockpit_gets_the_store_whole_...
- state/exported.store_batch: the machine check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- release.message: the subject not cut -> test_the_cockpit_gets_the_store_whole_...
- release.release: `moved = ""` (the conductor's checkout left on the old pin, its door running old code) -> the same
- release.score_commit: the refusal not raised -> test_the_cockpit_gets_the_store_whole_...
- release.inside: the ".." check dropped -> test_the_cockpit_gets_the_store_whole_...
- release.pinned: `if not found:` -> test_the_cockpit_gets_the_store_whole_...
- timer.env_refusal: the reader check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- timer.install: no listener restart -> test_the_cockpit_gets_the_store_whole_...
- timer.unquoted: `return value` -> test_the_cockpit_gets_the_store_whole_...
- timer.unit_text: the pull never replaced -> test_the_cockpit_gets_the_store_whole_...
- timer.dashboard_refusal: the dashboard diff -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- review/web.as_owner_deciding: `with markers_lifted():` -> `with contextlib.nullcontext():` ->
  test_the_cockpit_gets_the_store_whole_...
- chat_decisions.refusal: the `now != yes["target"]` check -> `if False:` ->
  test_the_cockpit_gets_the_store_whole_...
- applying.OWNER_FIGURES: the "spend-override" line dropped (his spend override in chat has no request kind) ->
  test_the_cockpit_gets_the_store_whole_...
- chat_decisions.override_state: the `web.override_yes(...) is not None` check -> `if False:` ->
  test_the_cockpit_gets_the_store_whole_...
- chat_decisions.books_state: `"books": books` dropped from its target (a books month asked before the books were
  written since applies anyway) -> test_the_cockpit_gets_the_store_whole_...
- chat_decisions.request_of: the books month branch dropped (his books month in chat has no request kind) ->
  test_the_cockpit_gets_the_store_whole_...
- applying.OWNER_FIGURES: the "stop-line" line dropped (his stop line in chat has no request kind) ->
  test_the_cockpit_gets_the_store_whole_...
- applying.OWNER_FIGURES: the "cap-line" line dropped, or chat_decisions.cap_state's `"current"` set to None (a cap
  written since applies anyway) -> test_the_cockpit_gets_the_store_whole_...
- chat_decisions.stop_state: its `"line"` set to None (a stop line asked before another line was written applies
  anyway) -> test_the_cockpit_gets_the_store_whole_...
- chat_decisions.request_of: a reject's `takes` dropped (a retake of named takes remakes every take) ->
  test_the_cockpit_gets_the_store_whole_...
- chat_decisions.apply: the `handed_back(store, yes_id, applied.detail)` after a refused apply dropped (a yes the
  cockpit refused stays used, 2026-11-05) -> test_the_cockpit_gets_the_store_whole_...
- state/exported.py: `import numpy` at its top -> test_the_cockpit_gets_the_store_whole_...
- launch/localrun.py: `from score.graph import runs` at its top (93fec2b1) -> test_the_cockpit_gets_the_store_whole_...
"""
import contextlib
import datetime
import gzip
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import ANY

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from fastapi.testclient import TestClient

from score.dashboard.pages.models import SyncRequest
from score.dashboard.proposals import make, records
from score.dashboard.state import local, versions
from score.dashboard.state.exported import ExportedSource
from score.dashboard.sync import applying, building, client, listen, release, timer
from score.dashboard.tests.fixture import FakeBackend, MADE, TOKEN, exported, hosted_client, remote_of

pytestmark = pytest.mark.django_db(transaction=True)
REPO = pathlib.Path(__file__).resolve().parents[3]
PRICED = "priced by the runner: EUR 1.00 to 2.00 measured, 3 paid steps with no measured price"


def offline(monkeypatch):
    """Prepare, the library's pictures, the parts and light read, the USD check, the frozen copies' sweep and the plans
    kept as lines, so no test pass reads the real library, hands to it, fetches a picture, asks a model, removes a copy
    or writes a plan where the plan stage reads it."""
    monkeypatch.setattr(client, "plans_kept", lambda: "plans for the plan stage: test")
    monkeypatch.setattr(client, "readings_fixed", lambda store_root: "readings: test")
    monkeypatch.setattr(client, "parts_read", lambda store_root: "parts: test")
    monkeypatch.setattr(client, "light_read", lambda store_root: "light: test")
    monkeypatch.setattr(client, "remake_prepared", lambda: "remake batch (estimate): test")
    monkeypatch.setattr(client, "library_pictures", lambda: "library pictures: test")
    monkeypatch.setattr(client, "library_demos", lambda: "library demos: test")
    monkeypatch.setattr(client, "library_handing", lambda world: "library handover: test")
    monkeypatch.setattr(client, "film_previews", lambda: "film previews: test")
    monkeypatch.setattr(client, "usd_sweep", lambda: "usd check: test")
    monkeypatch.setattr(client, "copies_swept", lambda: "sweep: test")


def fed(monkeypatch):
    """A clean checkout origin's main holds, and the runner's price made: [the environments priced]."""
    priced = []
    offline(monkeypatch)
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    monkeypatch.setattr(client, "runner_price", lambda repo, environment: priced.append(environment) or (PRICED, None))
    return priced


def sha_of(data):
    return hashlib.sha256(data).hexdigest()


def gzipped_put(sha, offset, size, data):
    """A blob chunk's PUT row: the method, its path and its gzipped body."""
    return "PUT", f"/api/sync/blobs/{sha}?offset={offset}&size={size}", gzip.compress(data)


def commit(name, files):
    return "POST", "/api/sync/commit", {"name": name, "files": files}


def answered(web, row, headers):
    """One sync exchange `row` ((method, path, body), body bytes sent as content, else as JSON) sent to `web`."""
    method, path, body = row
    kind = "content" if isinstance(body, bytes) else "json"
    return web.request(method, path, headers=headers, **({kind: body} if body is not None else {}))


def test_the_cockpit_gets_the_store_whole_and_the_store_only_the_owners_asks(owner_books, repositories, tmp_path,
                                                                             settings, monkeypatch):
    """The fixture world exported twice and once under a tiny cap, then the hosted side's sync routes driven through one
    exchange table (uploads, refusals, commits, the request states) and every route asked with a wrong token, then
    pushed to pass after pass (late, slow, unchanged, new code, an old format); then the store side applies one request
    table (a stranger's, an agent's process's, bad names and library addresses, kinds
    no button sends, then the owner's own), a refused request writing nothing; then sync passes against a hosted side
    in memory (two refused, three that push as the design copy moves); then his decisions made in chat
    through one table of decision kinds (each with a twin asked before its target changed) and one of yeses never
    recorded; then the pass's own steps through tables (the parts and light asked, the film previews, a step's
    leftovers and its time); then the release and the timer's install on one score checkout and host (the env files,
    the refusals before the release, the release, the installs with and without the pull, the checkouts that feed
    nothing); then the listener on a store home of its own (the pass's figures judged through one table, a Buy's
    rounds through another, a slow draw beside a Stop everything, the batch record sent); then the hosted image's tree
    rendering that first export and importing every module, light. The hosted part also notes, skips and claims a
    Buy, keeps the batch record sent, shows the batch record through one table of stores, exports and records, and
    renders the pages and queues the owner's buttons from the first export."""
    world = owner_books
    one, small = exported(world, tmp_path / "one"), exported(world, tmp_path / "small", cap_mb=0.02)
    exported(world, tmp_path / "two")
    names = {path.name for path in (tmp_path / "one/files").iterdir()}
    bundles = {name: json.loads((tmp_path / f"one/places/{name}.json").read_text()) for name in ("alpha", "beta")}
    closeup = bundles["alpha"]["steps"]["closeup"]["picture"]["sha"]
    gap = bundles["beta"]["detail"]["accepted_gaps"][0]["picture"]["sha"]
    assembly = bundles["beta"]["steps"]["assembly"]["picture"]["sha"]
    written = one["written"]
    thumbs = [index for index, path in enumerate(written) if path.endswith("-360.jpg")]
    films = [index for index, path in enumerate(written) if path.endswith(".mp4")]
    assert one["made_at"] == MADE and one["left_out"] == []
    assert {"state.json", "manifest.json"} <= {path.name for path in (tmp_path / "one").iterdir()}
    assert {"alpha.json", "beta.json", "_world.json"} <= {path.name for path in (tmp_path / "one/places").iterdir()}
    assert any(name.endswith(".mp4") for name in names) and any(name.endswith("-1280.jpg") for name in names)
    assert {f"{gap}-1280.jpg", f"{assembly}-360.jpg"} <= names  # each gap's picture, each step's own thumbnail
    source = ExportedSource(tmp_path / "one")
    assert source.places() == ["alpha", "beta"] and source.step_detail("alpha", "closeup").waiting is not None
    # upload order: state, then thumbnails, then films, then each step's large picture
    assert written[0] == "state.json" and thumbs and films and max(thumbs) < min(films)
    assert written.index(f"files/{closeup}-1280.jpg") > max(films)
    live = ("machine.json", "manifest.json")  # machine.json a live read (load, memory), counted in the manifest
    for path in sorted((tmp_path / "one").rglob("*")):
        if path.is_file() and path.name not in live:
            assert path.read_bytes() == (tmp_path / "two" / path.relative_to(tmp_path / "one")).read_bytes(), path
    manifests = [json.loads((tmp_path / name / "manifest.json").read_text()) for name in ("one", "two")]
    for name, manifest in zip(("one", "two"), manifests):
        manifest["bytes"] -= (tmp_path / name / "machine.json").stat().st_size
    assert manifests[0] == manifests[1]
    machines = [json.loads((tmp_path / name / "machine.json").read_text())["machine"] for name in ("one", "two")]
    assert machines[0] == machines[1]
    assert small["left_out"] and all(entry["why"] == "over the export's cap" for entry in small["left_out"])
    assert {path.name for path in (tmp_path / "small/files").iterdir()} < names  # past the cap stays out of the files

    settings.SCORE_MODE, settings.SCORE_SYNC_TOKEN, settings.SCORE_COMMIT = "hosted", TOKEN, "a" * 40
    web, bearer, home = hosted_client(), {"Authorization": f"Bearer {TOKEN}"}, settings.SCORE_HOME
    shutil.rmtree(home / "export", ignore_errors=True)
    request = SyncRequest.objects.create(kind="change", user="joey", payload={"stage": "closeup", "words": "redder"})
    buy = SyncRequest.objects.create(kind="checkout", user="joey", payload={})
    sent = {"checkout": 4, "state": "running", "read_at": "2026-10-24T13:09:00+00:00"}
    data, empty, liar = b"abcdefgh", sha_of(b"{}"), sha_of(b"something else")
    manifests = {made: f'{{"made_at": "{made}", "format": 3}}'.encode() for made in ("a", "b", "c")}
    exchanges = [  # in order: (what, (method, path, body), status, the answer's JSON or None)
        ("the pin", ("GET", "/api/sync/pin", None), 200, {"commit": "a" * 40}),
        ("lacking a path", ("POST", "/api/sync/lacking", {"files": {"../etc": 1}}), 400, None),
        ("a whole blob", gzipped_put(empty, 0, 2, b"{}"), 200, {"have": 2, "done": True}),
        *[(f"commit path {path}", commit("one", {"manifest.json": empty, path: empty}), 400, None)
          for path in ("../x", "/abs", "a//b", "a\\b")],
        *[(f"commit name {name!r}", commit(name, {"manifest.json": empty}), 400, None)
          for name in ("current", "x.partial", "a/b", "")],
        ("commit without a manifest", commit("one", {"state.json": empty}), 400, None),
        ("a first chunk", gzipped_put(sha_of(data), 0, 8, data[:3]), 200, {"have": 3, "done": False}),
        ("a chunk past the gap", gzipped_put(sha_of(data), 6, 8, data[6:]), 409, {"have": 3}),
        ("the chunk where told", gzipped_put(sha_of(data), 3, 8, data[3:]), 200, {"have": 8, "done": True}),
        ("a wrong hash", gzipped_put(liar, 0, 8, data), 400, None),
        ("more than its size", gzipped_put(liar, 0, 2, data), 400, None),
        ("a waiting Buy noted", ("POST", f"/api/sync/requests/{buy.pk}/note", {"detail": "waits"}), 200, None),
        ("the requests wait", ("GET", "/api/sync/requests?state=waiting", None), 200, None),
        ("the Buy skipped", ("GET", f"/api/sync/requests?skip={buy.pk}", None), 200, None),
        ("the Buy claimed", ("POST", f"/api/sync/requests/{buy.pk}/claim", None), 200, None),
        ("a claimed Buy noted", ("POST", f"/api/sync/requests/{buy.pk}/note", {"detail": "x"}), 409, None),
        ("a batch record", ("PUT", "/api/sync/batch-run", json.dumps(sent).encode()), 200, {"kept": sent["read_at"]}),
        ("a batch record not an object", ("PUT", "/api/sync/batch-run", b"[]"), 400, None),
        *[(f"request {state}", ("POST", f"/api/sync/requests/{request.pk}", {"state": state}), 200, None)
          for state in ("picked_up", "running", "done")],
        ("request nonsense", ("POST", f"/api/sync/requests/{request.pk}", {"state": "nonsense"}), 422, None),
    ]
    exports = [row for made, body in manifests.items() for row in (  # three exports, each uploaded then committed
        (f"export {made}", gzipped_put(sha_of(body), 0, len(body), body), 200, {"have": len(body), "done": True}),
        (f"commit {made}", commit(made, {"manifest.json": sha_of(body)}), 200, None))]
    answers = {}

    def exchanged(rows):
        for what, row, status, json_answer in rows:
            answer = answers[what] = answered(web, row, bearer)
            assert answer.status_code == status, (what, answer.text)
            assert json_answer is None or answer.json() == json_answer, (what, answer.json())
    exchanged(exchanges)
    assert (home / "blobs" / sha_of(data)).read_bytes() == data  # whole, before a commit sweeps it unused
    exchanged(exports)
    # a note leaves the Buy waiting with its words; a skipped one is not listed; a claimed one takes no note
    assert [(item["id"], item["state"], item["detail"]) for item in answers["the requests wait"].json()] == [
        (request.pk, "waiting", ""), (buy.pk, "waiting", "waits")]
    assert [item["id"] for item in answers["the Buy skipped"].json()] == [request.pk]
    request.refresh_from_db()
    buy.refresh_from_db()
    assert request.state == "done" and (buy.state, buy.detail) == ("picked_up", "waits")
    assert not (home / "blobs" / liar).exists() and not (home / "blobs" / f"{liar}.part").exists()
    # only the three good commits landed, the oldest swept with the blob no kept export uses
    assert sorted(path.name for path in (home / "export").iterdir()) == ["b", "c", "current"]
    assert [(home / "blobs" / sha_of(body)).exists() for body in manifests.values()] == [False, True, True]
    routes = [("POST", "/api/sync/lacking", {"files": {sha_of(b"x"): 1}}), gzipped_put(sha_of(b"x"), 0, 1, b"x"),
              commit("n", {}), ("GET", "/api/sync/pin", None), ("GET", "/api/sync/requests?state=done", None),
              ("PUT", "/api/sync/batch-run", b"{}")]
    for wrong in ({}, {"Authorization": "Bearer wrong"}):
        for route in routes:
            assert answered(web, route, wrong).status_code == 401, (wrong, route)

    # the batch record shown: only the store's machine's, the export's or the one the listener sent since, whichever
    # was read later, and none of a checkout before a reset (owner 2026-10-24: a moved or reset store kept showing an
    # old batch)
    kept, machine_record = home / "request-files" / "batch-run.json", home / "store-machine.json"
    pushed_pc = {"checkout": 4, "state": "finished", "read_at": "2026-10-24T22:22:00+00:00", "machine": "pc"}
    earlier = {"checkout": 4, "read_at": "2026-10-24T22:10:00+00:00"}
    running = {"checkout": 4, "state": "running", "read_at": "2026-10-24T13:00:00+00:00"}
    reads = [  # (what, the store's machine record, the listener's record (KEPT: the one sent above), the export's
        #          record, the export's machine, when it was made, the record shown)
        ("the newer one sent", None, KEPT, running, "", "2026-10-24T12:55:00+00:00", {**sent, "machine": ""}),
        ("the export's own", None, None, running, "", "2026-10-24T12:55:00+00:00", running),
        ("a Buy since the export", {"name": "pc"}, pushed_pc, None, "pc", "2026-10-24T22:00:00+00:00", pushed_pc),
        ("a reset: no checkout in it", {"name": "pc"}, pushed_pc, None, "pc", "2026-10-24T22:30:00+00:00", None),
        ("the later of the two", {"name": "pc"}, pushed_pc, earlier, "pc", "2026-10-24T22:30:00+00:00", pushed_pc),
        ("moved: the PC's sent record", {"name": "conductor", "before": "pc"}, pushed_pc, None, "conductor",
         "2026-10-24T22:00:00+00:00", None),
        ("moved: the PC's export", {"name": "conductor", "before": "pc"}, pushed_pc, earlier, "pc",
         "2026-10-24T12:55:00+00:00", None),
        ("moved: a record whose machine is unknown", {"name": "conductor", "before": "pc"},
         {key: value for key, value in pushed_pc.items() if key != "machine"}, None, "conductor",
         "2026-10-24T22:00:00+00:00", None),
    ]
    for what, store_machine, pushed_run, run, machine, made_at, shown in reads:
        machine_record.unlink(missing_ok=True)
        if store_machine:
            machine_record.write_text(json.dumps(store_machine))
        if pushed_run is not KEPT:
            kept.unlink(missing_ok=True)
            if pushed_run:
                kept.write_text(json.dumps(pushed_run))
        assert export_with_batch(tmp_path, kept.parent, run, machine, made_at).batch_run() == shown, what
    machine_record.unlink()
    kept.unlink()

    # the hosted pages render from the export with its time, and each money button and decision is a signed-in owner
    # request in the outbox, with his name, the time and the figure; anyone else's is refused at the door
    from score.dashboard import state
    from score.dashboard.pages import actions, library_actions
    owner, stranger = Client(), Client()
    owner.force_login(get_user_model().objects.create_user("joey", password="a long enough password"))
    stranger.force_login(get_user_model().objects.create_user("mallory", password="a long enough password"))
    with monkeypatch.context() as patch:
        patch.setattr(state, "source", lambda: source)
        for page in ("/", "/places/", "/environments/world1/", "/place/alpha/", "/place/alpha/step/closeup/",
                     "/world/step/terrain/", "/requests/"):
            assert "state from 2026-10-18 12:00" in owner.get(page).content.decode(), page
        owner.post("/place/alpha/step/closeup/decide/", {"decision": "reject", "output": "x", "reason": "no"})
        asks = [  # (what, the button's answer, how it starts)
            ("his books figure", actions.set_books_figure("joey", 12.5), "queued"),
            ("his read back", actions.read_books_back("joey"), "queued"),
            ("his waiver", actions.waive_check("joey", "beta", "closeup", "abc", "looks", "fine"), "queued"),
            ("a figure not an amount", actions.set_books_figure("joey", "nan-ish"), "refused"),
        ]
        for what, said, words in asks:
            assert said.startswith(words), (what, said)
        assert stranger.post("/world/step/terrain/waive/", {"output": "x", "check": "looks",
                                                            "reason": "r"}).status_code == 403
    queued = {item.kind: item for item in SyncRequest.objects.exclude(pk__in=(request.pk, buy.pk))}
    assert set(queued) == {"books-figure", "read-back", "waiver", "decision"}
    assert queued["books-figure"].user == "joey" and queued["books-figure"].payload["euros"] == 12.5
    assert queued["books-figure"].created
    shutil.rmtree(home / "export")  # its names sort after the dated exports the passes below swap in

    # the store side pushes the world's export here, pass after pass: one over its time before its first file sends
    # nothing and swaps in nothing; one whose build outgrows the pass still sends all it lacks (2026-10-21: the
    # deadline counted from before the build, every pass sent nothing and swapped in an export with no state.json);
    # one with nothing new sends only the new state and manifest; one after the exporting code changed sends every
    # bundle again and keeps only that version's pictures; one of a format this side cannot read is refused
    exports, current, remote = home / "export", home / "export/current", remote_of(web)
    clock, build = [0.0], building.build

    def pushed(made_at, seconds=600.0, slow=False, code=None):
        """The export pushed at `made_at` with the pass given `seconds`, its build outgrowing the pass when `slow`,
        under the exporting code `code` when given: (what the push said, the shown manifest or None, alpha's bundle)."""
        with monkeypatch.context() as patch:
            patch.setattr(client, "PASS_SECONDS", seconds)
            patch.setattr(client, "made_now", lambda: made_at)
            if slow:
                patch.setattr(client.time, "monotonic", lambda: clock[0])
                patch.setattr(client.building, "build", lambda *args: clock.__setitem__(0, clock[0] + seconds + 1)
                              or build(*args))
            if code:
                patch.setattr(versions, "exporting", lambda: code)
            said = client.push_export(remote, world.source, FakeBackend())
            shown = (current / "manifest.json").exists() and json.loads((current / "manifest.json").read_text())
            return said, shown or None, shown and json.loads((current / "places/alpha.json").read_text())
    late, _, _ = pushed("2026-10-18T12:30:00+00:00", seconds=-1.0)
    assert late["files"] == 0 and late["to_come"] > 0 and not late["committed"]
    assert "state.json" in {entry["what"] for entry in late["left_out"] if entry["why"] == client.STILL}
    assert not current.exists()  # an export with no records is never swapped in
    whole, shown, before = pushed("2026-10-18T13:00:00+00:00", slow=True)
    assert whole["committed"] and whole["to_come"] == 0 and whole["files"] == late["to_come"]
    assert shown["made_at"] == "2026-10-18T13:00:00+00:00" and (current / "state.json").is_file()
    assert not any(entry["why"] == client.STILL for entry in shown["left_out"])
    assert all((current / path).is_file() for path in shown["written"]), shown["written"]
    assert before["code_version"] == versions.exporting() and before["format"] == versions.FORMAT
    again, _, _ = pushed("2026-10-18T14:00:00+00:00")
    assert again["files"] <= 2  # only what changed: the new state.json and manifest
    kept = [path for path in exports.iterdir() if path.is_dir() and not path.is_symlink()]
    assert len(kept) == 2 and os.readlink(current) == "2026-10-18T140000+0000"
    moved, shown, after = pushed("2026-10-18T16:00:00+00:00", code="0123456789ab")
    assert after["code_version"] == shown["code_version"] == "0123456789ab" and after["detail"] == before["detail"]
    assert moved["files"] >= len(world.source.places()) + 1  # every place's bundle and the world's, sent again
    assert [path.name for path in (world.source.home / building.PICTURES).iterdir()] == ["0123456789ab"]
    with monkeypatch.context() as patch:
        patch.setattr(versions, "FORMAT", 1)  # an old store side: gaps and stops as words
        fed(patch)
        said = client.sync_pass(remote, world.source, FakeBackend())
    assert said.startswith("REFUSED") and "export format 1 cannot be read here" in said, said
    assert os.readlink(current) == "2026-10-18T160000+0000"  # never swapped in
    shutil.rmtree(exports)

    from score.review import web as review_web
    agent_started = actions.agent_started
    settings.SCORE_MODE, settings.SCORE_LIB_ROOT = settings.LOCAL, tmp_path
    monkeypatch.setattr(library_actions, "library", lambda: types.SimpleNamespace(entry=lambda address: None))
    monkeypatch.setattr(library_actions, "run", lambda arguments: pytest.fail(f"ran {arguments}"))
    key = world.store.records("closeup@beta")[-1]["key"]
    decision = {"node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}
    figure, waiver = {"euros": 12.5}, {"node": "closeup@beta", "output": world.outputs["closeup@beta"],
                                       "check": "looks", "reason": "three faults are fine here"}
    requests = [  # in order: (what, kind, user, payload, in an agent's process, state, words in its detail or None)
        *[(f"a stranger's {kind}", kind, "mallory", payload, False, "refused", "not this store's owner")
          for kind, payload in (("decision", decision), ("books-figure", figure), ("waiver", waiver))],
        *[(f"his {kind} in an agent's process", kind, "joey", payload, True, "refused", None)
          for kind, payload in (("books-figure", figure), ("waiver", waiver))],
        *[(f"a {kind}, which no button sends", kind, "joey", {"euros": 40.0}, False, "refused", None)
          for kind in ("stop", "month")],
        *[(f"{kind} naming a path", kind, "joey", payload, False, "refused", "is not a scene name")
          for kind, payload in (("concept-pick", {"place": "../../accepts", "sha": None}),
                                ("plan-write", {"place": "a/b", "euros": 0.0}),
                                ("environment-save", {"world": "..", "concept": {}, "locked": False}))],
        ("a library address not in it", "library", "joey", {"action": "withdraw", "addresses": [
            "--upload-pack=touch x"]}, False, "refused", "is not in the library"),
        ("his books figure", "books-figure", "joey", figure, False, "done", None),
        ("his waiver", "waiver", "joey", waiver, False, "done", None),
        ("his change", "change", "joey", {"place": "alpha", "stage": "closeup", "words": "redder"}, False, "done",
         None),
    ]
    for what, kind, user, payload, agent, state, words in requests:
        monkeypatch.setattr(actions, "agent_started", lambda agent=agent: agent)
        applied = applying.apply({"kind": kind, "user": user, "payload": payload}, world.source)
        assert applied.state == state and (words is None or words in applied.detail), (what, applied.detail)
        if state == "refused":  # a refused request writes nothing: no books, no waiver, no inbox, no stop
            assert not world.books.exists() and not world.store.waivers("closeup@beta", key), what
            assert not list((home / "inbox").glob("*.json")), what
    assert review_web.stop_line(world.store, "world1") is None  # only his stop line made in chat sets a stop
    books = json.loads(world.books.read_text())
    assert books["google_before"] == 12.5 and books["google_by"] == "joey" and books["state"] == "known"
    assert world.store.waivers("closeup@beta", key)["looks"]["by"] == "joey"
    assert list((home / "inbox").glob("*.json"))

    # sync passes against a hosted side in memory: from a checkout not clean and pushed, or when the runner's price
    # fails, nothing is synced; else a pass prices, makes the basket again from the runner's plan in this checkout (an
    # agent worktree's basket of yesterday replaced), pushes the export even when the checkout moved during it,
    # answers and reports each request, runs the USD check after the pricing lock, and says when a live run's design
    # copy differs from the design
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}},
                     {"id": 8, "kind": "decision", "user": "mallory", "payload": {
                         "node": "closeup@alpha", "output": "o", "decision": "reject"}}])
    unpushed = "commit 0123abcd is not on origin's main: push it first"
    refusals = [  # (the tree's refusal, the runner's price, the pattern of what the pass says)
        (unpushed, (PRICED, None), re.escape(f"REFUSED: nothing synced: {unpushed}; sweep: test")),
        (None, (None, "the runner's price failed: exit 1"),
         re.escape("REFUSED: nothing synced: the runner's price failed: exit 1; ") + ".*gaps.*" + re.escape(
             "; remake batch (estimate): test; benchmarks: none listed; library pictures: test; library demos: test")),
    ]
    for tree, price, words in refusals:
        with monkeypatch.context() as patch:
            offline(patch)
            patch.setattr(client, "tree_refusal", lambda repo, tree=tree: tree)
            patch.setattr(client, "runner_price", lambda repo, environment, price=price: price)
            said = client.sync_pass(hosted, world.source, FakeBackend())
        assert re.fullmatch(words, said), said
        assert hosted.commits == [] and hosted.chunks == [] and hosted.reports == [], said
    props, proposals, held, gaps_sweep = settings.SCORE_PROPS_HOME, home / "proposals", [], client.gaps_sweep
    records.put_index(proposals, {"made_at": "2026-10-20T17:45:33Z", "checkout": "/x/.claude/worktrees/agent-a",
                                  "items": [{"id": "navigation-pieces", "nodes": {"closeup@navigation": {}}}]})
    (props / "design" / "plans").mkdir(parents=True, exist_ok=True)
    (props / "design" / "plans" / "p.json").write_text("{}")
    copy = props / "frozen" / "run1.home" / "design"  # a live run's own design copy (graph/frozen.py)
    shutil.copytree(props / "design", copy)
    passes = []
    with monkeypatch.context() as patch:
        priced = fed(patch)
        patch.setattr(client, "usd_sweep", lambda: held.append(client.pass_pricing()) or "usd check: test")
        patch.setattr(client, "gaps_sweep", lambda: held.append(client.pass_pricing()) or gaps_sweep())
        patch.setattr(FakeBackend, "plan_buys", ["closeup@alpha", "pixal@beta"])
        heads = ["a" * 40, "b" * 40]  # the checkout moves during the first pass only
        patch.setattr(client, "head", lambda repo: heads.pop(0) if heads else "b" * 40)
        for change in (None, lambda: (props / "design" / "plans" / "p.json").write_text('{"moved": true}'),
                       lambda: shutil.rmtree(copy) or copy.symlink_to(props / "design")):  # the run ended: a link
            if change:
                change()
            passes.append((client.sync_pass(hosted, world.source, FakeBackend()), len(hosted.commits)))
            hosted.waiting_items = []
    (said, commits), (moved, _), (ended, _) = passes
    assert "pushed the export" in said and "0 still to come" in said and commits == 1, said
    assert "library problems" in said, said  # the library sweep ran before the export was built
    # and the gaps after it: with no store under PROPS_HOME they fail loudly, said in the pass's words
    assert "gaps failed: exit 1: no store at " in said, said
    assert "the checkout moved from aaaaaaaa to bbbbbbbb during the pass" in said and "Buy waits" in said, said
    assert "checkouts: 0 left launching failed, 0 ended batches' lines taken back" in said, said
    assert "usd check: test" in said and "design moved" not in said, said
    assert said.endswith(f"{PRICED}; plans for the plan stage: test; remake batch (estimate): test; benchmarks: none "
                         "listed; basket made: 2 items, 2 paid steps; library pictures: test; library demos: test; "
                         "film previews: test"), said
    assert moved.endswith("design moved since the running batch started (the cockpit prices the design as it is now)")
    assert "design moved" not in ended, ended
    assert priced == [world.source.world.name] * 3 and held == [True, False] * 3  # priced, then USD after the lock
    assert hosted.reports == [(7, "picked_up"), (7, "done"), (8, "picked_up"), (8, "refused")]
    index = records.index(proposals)
    assert index["checkout"] == str(make.REPO) and index["plan_only"] and index["made_at"] > "2026-10-20T17:45:33Z"
    assert index["commit"] == make.commit()
    assert sorted(node for item in index["items"] for node in item["nodes"]) == ["closeup@alpha", "pixal@beta"]

    # his decisions made in chat (sync/chat_decisions.py, owner 2026-10-27), each through one table: recorded quoted
    # by his name, a twin asked before its target changed; a cockpit refusal hands the yes back unused; applied once
    # through the request code of his click, the agent marks lifted only inside; the twin refused, nothing marked used
    from score.dashboard.films import script
    from score.dashboard.sync import chat_decisions
    from score.store import AGENT_MARKERS
    monkeypatch.setattr(actions, "agent_started", agent_started)
    mark, output, seen, real = AGENT_MARKERS[0], world.outputs["closeup@alpha waiting"], [], applying.apply
    monkeypatch.setenv(mark, "1")
    monkeypatch.setattr("score.adapters.compute.cap_baseline",
                        lambda: {"at": "t", "whole": 2127.39, "lines": {"ff|l4": 169.0}})
    world.books.unlink()  # his books figure above was this month's: the books month asks a month not written yet
    month = review_web.books_of("")[0]
    script.save(settings.SCORE_HOME, script.blank("chat-film", "Chat"))
    cap = {"euros": "300", "line": "255", "start": "2026-11-09T18:40:00+00:00", "month_cap": "2970",
           "finish": "2026-11-21T23:59:00+00:00", "standing": "15"}
    takes = {"reason": "stool: outline 0.392 under 0.5", "takes": ["stool_1"]}
    edited = lambda: script.save(settings.SCORE_HOME, script.blank("chat-film", "Chat, edited"))  # noqa: E731
    decided = [  # (decision, target, given, the twin: (its given, why it is refused, what changes after it is asked)
        #          or None, its target, the request his click makes, words of the applied detail, what it reads
        #          afterwards: (reader, the reading))
        ("accept", "closeup@alpha", {"output": output, "worse_reason": "one fault is fine"},
         ({"output": output, "reason": "red"}, "changed since he answered", None),  # a reject, then his accept
         {"node": "closeup@alpha", "output": output, "accepted": ANY},
         {"kind": "decision", "user": "joey", "payload": {"node": "closeup@alpha", "output": output,
                                                          "decision": "accept", "reason": "",
                                                          "worse_reason": "one fault is fine"}},
         "", (lambda: (world.store.accepted("closeup@alpha"),
                       world.store.current_accept("closeup@alpha")["by"]), (output, "joey"))),
        ("reject", "closeup@alpha", {"output": output, **takes}, None,  # its takes reach his reject record
         {"node": "closeup@alpha", "output": output, "accepted": output},
         {"kind": "decision", "user": "joey", "payload": {"node": "closeup@alpha", "output": output,
                                                          "decision": "reject", "worse_reason": "", **takes}},
         "", (lambda: world.store.rejects("closeup@alpha")[-1]["takes"], ["stool_1"])),
        ("spend", "relight-hangar", {"euros": "4", "purpose": "one relight"},
         ({"euros": "2", "purpose": "relight"}, "gone since the question", None),  # the name took a yes since
         {"override": "relight-hangar", "euros": 4.0, "purpose": "one relight"},
         {"kind": "spend-override", "user": "joey", "payload": {"name": "relight-hangar", "euros": 4.0,
                                                                "purpose": "one relight"}},
         'SCORE_SPEND_TICKET="override relight-hangar"',
         (lambda: picked(world.store.spend_yes("override", "relight-hangar"), "euros", "by", "purpose"),
          (4.0, "joey", "one relight"))),
        ("stop", "chat-stop", {"euros": "10"}, ({"euros": "12"}, "changed since he answered", None),  # a line since
         {"world": "chat-stop", "euros": 10.0, "line": None},
         {"kind": "stop-line", "user": "joey", "payload": {"world": "chat-stop", "euros": 10.0,
                                                           "reason": "his yes in chat: Yes", "replaces": None}},
         "EUR 10.00", (lambda: picked(review_web.stop_line(world.store, "chat-stop"), "euros", "by", "baseline.bill"),
                       (10.0, "joey", 1.0))),
        ("cap", "env1", cap, ({**cap, "line": "200"}, "changed since he answered", None),  # a cap written since
         {"cap": "env1", "euros": 300.0, "line": 255.0, "start": cap["start"], "month_cap": 2970.0,
          "finish": cap["finish"], "standing_per_day": 15.0, "open": True, "current": None},
         {"kind": "cap-line", "user": "joey", "payload": {
             "cap": "env1", "euros": 300.0, "line": 255.0, "start": cap["start"], "month_cap": 2970.0,
             "finish": cap["finish"], "standing_per_day": 15.0, "open": True, "replaces": None,
             "words": "his yes in chat: Yes", "yes": ANY}},
         "paid work stops at EUR 255.00",
         (lambda: picked(review_web.cap_now("env1"), "by", "open", "baseline.whole", "line"),
          ("joey", True, 2127.39, 255.0))),
        ("cap", "env1", {"close": True}, None, {"cap": "env1", "open": False, "current": ANY},  # its film accepted
         {"kind": "cap-line", "user": "joey", "payload": {
             "cap": "env1", "euros": None, "line": None, "start": None, "month_cap": None, "finish": None,
             "standing_per_day": None, "open": False, "replaces": ANY, "words": "his yes in chat: Yes", "yes": ANY}},
         "", (lambda: review_web.cap_now("env1")["open"], False)),
        ("lock-film", "chat-film", {}, ({}, "changed since he answered", edited),  # the script edited since
         {"film": "chat-film", "script": ANY},
         {"kind": "film-lock", "user": "joey", "payload": {"film": "chat-film", "script": ANY}},
         "", (lambda: picked(script.locked(settings.SCORE_HOME, "chat-film"), "title"), ("Chat, edited",))),
        (review_web.BOOKS_MONTH, month, {"euros": "0"},
         ({"euros": "5"}, "changed since he answered", None),  # the books written since
         {"month": month, "euros": 0.0, "books": {}},
         {"kind": "books-figure", "user": "joey", "payload": {"euros": 0.0}}, f"books known for {month}",
         (lambda: picked(json.loads(world.books.read_text()), "month", "state", "google_before", "google_by"),
          (month, "known", 0.0, "joey"))),
    ]
    for decision, target, given, twin, then, item, words, (reads, reading) in decided:
        asked = f"{decision} {target}?"
        twin_yes = twin and chat_decisions.record(decision, target, "Yes", asked, **twin[0])
        if twin and twin[2]:
            twin[2]()
        yes = chat_decisions.record(decision, target, "Yes", asked, **given)
        assert (yes["target"], yes["by"], yes["question"]) == (then, "joey", asked), decision
        monkeypatch.setattr(applying, "apply", lambda request, source: applying.Applied("refused", "not now"))
        assert chat_decisions.apply(yes["id"]).state == "refused", decision  # handed back: the same yes applies later
        assert not review_web.decision_yes_used(world.store, yes["id"]) and found(reads) != reading, decision
        monkeypatch.setattr(applying, "apply", lambda request, source: seen.append(
            (request, mark in os.environ)) or real(request, source))
        applied = chat_decisions.apply(yes["id"])
        assert applied.state == "done" and words in applied.detail, (decision, applied.detail)
        assert seen[-1] == (item, False) and os.environ[mark] == "1", (decision, seen[-1])
        assert reads() == reading, decision
        assert "used already" in str(pytest.raises(chat_decisions.Refused, chat_decisions.apply, yes["id"]).value)
        if twin:
            assert twin[1] in str(pytest.raises(chat_decisions.Refused, chat_decisions.apply, twin_yes["id"]).value)
            assert not review_web.decision_yes_used(world.store, twin_yes["id"]) and reads() == reading, decision
    go = chat_decisions.record("go", "world1", "sure", "Let the run accept passing results on its own?")
    assert review_web.owners_go(world.store, go["id"], "world1") == go
    assert review_web.owners_go(world.store, go["id"], "w2") is None
    assert review_web.owners_go(world.store, yes["id"], "world1") is None  # only a go
    for yes_id, why in ((go["id"], "is a go"), ("20261027T000000000000Z", "is no quoted decision yes")):
        assert why in str(pytest.raises(chat_decisions.Refused, chat_decisions.apply, yes_id).value)
    unrecorded = [  # (decision, target, answer, question, given, words of the refusal)
        ("accept", "closeup@alpha", "", "Q?", {"output": output}, "quotes the owner's answer"),
        ("accept", "closeup@alpha", "Yes", "", {"output": output}, "quotes the owner's answer"),
        ("reject", "closeup@alpha", "Yes", "Q?", {"output": output}, "says why"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": "0" * 64}, "has no output"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": output, "euros": "4"}, "only a spend, a books month"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": output, "takes": ["stool_1"]}, "only a reject names takes"),
        *[("spend", name, "Yes", "Q?", {"euros": euros, "purpose": purpose}, why) for euros, purpose, name, why in (
            ("4", "", "a", "says what it is for"), ("0", "x", "a", "above 0"), ("four", "x", "a", "as an amount"),
            ("4", "x", "relight-hangar", "holds a yes already"))],
        *[(review_web.BOOKS_MONTH, target, "Yes", "Q?", {"euros": euros}, why) for euros, target, why in (
            ("-1", month, "finite figure"), ("nan", month, "finite figure"), ("zero", month, "as an amount"),
            ("", month, "as an amount"), ("0", "2020-01", "this month's provider figure only"))],
        (review_web.BOOKS_MONTH, month, "Yes", "Q?", {"euros": "0", "purpose": "x"}, "only a spend names a purpose"),
        *[("stop", "chat-stop", "Yes", "Q?", {"euros": euros}, why) for euros, why in (
            ("0", "finite amount above"), ("-1", "finite amount above"), ("nan", "finite amount above"),
            ("ten", "as an amount"), ("", "as an amount"))],
        ("stop", "chat-stop", "Yes", "Q?", {"euros": "10", "line": "5"}, "only a cap names a line"),
        ("cap", "env1", "Yes", "Q?", {"euros": "300", "line": "400", "start": "2026-11-09T18:40"}, "is within its"),
        ("cap", "env1", "Yes", "Q?", {"euros": "300", "line": "255"}, "names the time its count starts"),
        ("cap", "env1", "Yes", "Q?", {"euros": "nan", "line": "255", "start": "2026-11-09T18:40"}, "finite amount"),
    ]
    for decision, target, answer, question, given, why in unrecorded:
        refused = pytest.raises(chat_decisions.Refused, chat_decisions.record, decision, target, answer, question,
                                **given)
        assert why in str(refused.value), (decision, target, given, str(refused.value))

    # the pass's own steps, on the same world: no reading is fixed; the parts and the light of each locked place are
    # asked once (one call a place, under the reading's clearance) and never while Stop everything holds; each locked
    # script's free preview is made, none wanted said so, a failure to read the locks said and not raised; a step's
    # leftovers end with it, and a step out of time is ended and says so
    from score.review import reading
    from score.stages.demo_film import final
    from score.store import Store
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)  # the books' own test
    monkeypatch.setattr("score.adapters.compute.books_refusal", lambda: None)
    monkeypatch.delenv("SCORE_BENCHMARK_GRANT", raising=False)
    assert client.readings_fixed(world.source.store_root) == "readings: none to fix"
    store = Store.in_folder(world.source.store_root)
    unlit = {"glows": False, "glowing": "", "colour": "", "brightness": 0}
    asks = [  # (the pass's step, its words, the places it leaves unread, an answer of one row, its scene, euros a call)
        (client.parts_read, "parts", reading.unparted, "object", None, 0.05),
        (client.light_read, "light", reading.unlit, unlit, {"daylight": True, "unseen": False, "unseen_colour": ""},
         0.04),
    ]
    for step, label, unread, row_answer, scene, euros in asks:
        places, asked = unread(store, ["alpha", "beta"]), []
        assert places, label

        def ask(store, place, folder, row_answer=row_answer, scene=scene, euros=euros, asked=asked):
            asked.append(place)
            rows = {row["id"]: row_answer for row in reading.reading_of(store, place)["inventory"]["rows"]}
            return (rows if scene is None else {"rows": rows, "scene": scene}), euros, 1.0
        monkeypatch.setattr(client, "free_only_followed", lambda: True)
        assert step(world.source.store_root, ask=None) == (
            f"{label} not read for {len(places)} places: refused, Stop everything holds (free only)")
        monkeypatch.setattr(client, "free_only_followed", lambda: False)
        assert step(world.source.store_root, ask=ask) == f"{label} read: {len(places)} places, " \
            f"EUR {euros * len(places):.2f}"
        assert sorted(asked) == sorted(places) and unread(store, places) == [], label
        assert step(world.source.store_root, ask=ask) == f"{label}: none missing" and len(asked) == len(places), label
        assert scene is None or reading.concept_light(store, places[0])["scene"] == scene
    previews = [  # (the films final.previews_wanted names, the pattern of the pass's words, the films rendered)
        (lambda: ["one", "two"], re.escape("film-preview one: made; film-preview two: made"), ["one", "two"]),
        (lambda: [], re.escape("film previews: none wanted"), []),
        (lambda: json.loads("{"), re.escape("film previews failed: JSONDecodeError") + ".*", []),
    ]
    for wanted, words, films in previews:
        rendered = []
        monkeypatch.setattr(final, "previews_wanted", wanted)
        said = client.film_previews(lambda film, rendered=rendered: rendered.append(film)
                                    or f"film-preview {film}: made")
        assert re.fullmatch(words, said) and rendered == films, said
    settings.SCORE_REPO = tmp_path
    # the leftover lets go of the step's output, so only the group's end can stop it
    leftover = ("import subprocess, time; print(subprocess.Popen(['sleep', '60'], stdout=subprocess.DEVNULL, "
                "stderr=subprocess.DEVNULL).pid, flush=True)")
    steps = [  # (what, the step's program, its limit, its exit is 0, its last error line or None)
        ("a step with a leftover", leftover, None, True, None),  # 2026-10-25: chrome-headless stayed after the pass
        ("a step out of its time", leftover + "; time.sleep(60)", 1, False, "out of time after 1 s"),
    ]
    for what, program, limit, ok, error in steps:
        done = client.step_run([sys.executable, "-c", program], grace=2, **({"limit": limit} if limit else {}))
        assert (done.returncode == 0) == ok and (error is None or done.stderr.strip().splitlines()[-1] == error), what
        stat = pathlib.Path(f"/proc/{int(done.stdout)}/stat")  # its output kept

        def ended(stat=stat):
            try:
                return stat.read_text().rpartition(")")[2].split()[0] == "Z"
            except FileNotFoundError:
                return True
        deadline = time.monotonic() + 2  # a kill lands a moment after it is sent: at most 2 s, never the minute
        while not ended() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ended(), what

    # the release and the timer's install, on a score checkout with two pushed commits and a host pinning the first:
    # the install refuses what cannot feed the cockpit and writes nothing; the release refuses a Dockerfile path
    # outside the host or one not pinning exactly one commit, pins the pushed head in one commit of the host's style
    # and moves the conductor; then the install writes and enables its units, with the pull or, with --no-pull, the
    # conductor's update in its place; a checkout with changes or a commit not pushed feeds neither the pass nor a
    # release
    score, host, first = repositories
    head, config = git(score, "git", "rev-parse", "HEAD"), tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    env, bare, quoted = an_env_file(tmp_path), an_env_file(tmp_path / "bare", reader=False), tmp_path / "quoted.env"
    quoted.write_text(env.read_text().replace("SCORE_SECRET_READER=", 'SCORE_SECRET_READER="').replace(
        "read-secret\n", 'read-secret"\n'))  # read as systemd reads it
    for path, words in ((tmp_path / "none.env", re.escape(f"no env file at {tmp_path / 'none.env'}")),
                        (bare, ".*SCORE_SECRET_READER.*"), (quoted, None)):
        refused = timer.env_refusal(path)
        assert (refused is None) if words is None else re.fullmatch(words, refused), (path, refused)
    for given, why in (({"host": host, "dockerfile": DOCKERFILE},  # a cockpit on another dashboard
                        "whose dashboard is not this checkout's: release this commit first"),
                       ({"opener": Pin(None)}, "reports no commit"),  # not /healthz: the proxy answers that itself
                       ({"opener": Pin(first)}, "whose dashboard is not this checkout's")):
        with pytest.raises(release.Refused, match=why):
            timer.install(score, env, systemctl=lambda *args: None, **given)
    assert not config.exists()  # nothing written
    for path in (str(host / DOCKERFILE), "../host/" + DOCKERFILE):
        with pytest.raises(release.Refused, match="inside the host's repository"):
            release.release(score, host, path, SUBJECT)
    for text in ("FROM x\n", "ARG SCORE_COMMIT=" + "a" * 40 + "\nARG SCORE_COMMIT=" + "b" * 40 + "\n"):
        with pytest.raises(release.Refused, match="expected one"):
            release.pinned(text)
    assert release.repinned("ARG SCORE_COMMIT=" + "a" * 40 + "\n", "c" * 40) == "ARG SCORE_COMMIT=" + "c" * 40 + "\n"
    assert client.tree_refusal(score) is None
    asked = []
    said = release.release(score, host, DOCKERFILE, SUBJECT + " {not a slot}", trailers=[TRAILER],
                           door=lambda repo, command: asked.append((repo, command)) or (0, "update: moved"))
    assert f"moved from score {first[:8]} to {head[:8]}" in said, said
    assert asked == [(score, f"release-pin {head} {first}")] and said.endswith("; the conductor: update: moved"), said
    assert "NOT moved (door exit 1: no door)" in release.conductor_moved(score, head, first, lambda *_: (1, "no door"))
    git(host, "git", "fetch", "-q", "origin", "main")
    assert git(host, "git", "show", f"FETCH_HEAD:{DOCKERFILE}") == f"FROM x\nARG SCORE_COMMIT={head}\nRUN y"
    subject, body, trailer = git(host, "git", "log", "-1", "--format=%B", "FETCH_HEAD").split("\n\n")
    assert subject == f"dashboards: the cockpit at score {head[:8]} (#1) {{not a slot}}" and trailer == TRAILER
    assert body == f"{head[:8]} " + ("dashboard: the second, a subject " + "long " * 30)[:release.SUBJECT_WIDTH]
    assert git(host, "git", "worktree", "list").count("\n") == 0  # its own worktree is gone
    assert "already pins" in release.release(score, host, DOCKERFILE, SUBJECT)
    called, units = [], config / "systemd/user"
    timer.install(score, env, host, DOCKERFILE, systemctl=lambda *args: called.append(args))
    assert called == [("daemon-reload",), ("enable", "--now", "score-sync.timer", "score-listen.service"),
                      ("restart", "score-listen.service")]
    pulled = {name: (units / name).read_text().splitlines() for name in timer.UNITS}
    with pytest.raises(release.Refused, match="systemctl --user daemon-reload failed: no user manager"):
        timer.install(score, quoted, host, DOCKERFILE, systemctl=lambda *args: "no user manager")
    cockpit = Pin(head)
    said = timer.install(score, env, systemctl=lambda *args: None, pull=False, opener=cockpit)
    assert cockpit.asked == [("https://cockpit.test/api/sync/pin", "Bearer token")] and "no pull before a pass" in said
    unpulled = {name: (units / name).read_text().splitlines() for name in timer.UNITS}
    pull = f"ExecStartPre=/usr/bin/git -C {score} pull -q --ff-only"
    update = f"ExecStartPre=/usr/bin/python3 -I {score}/tools/cloud/conductor/update.py --repo {score}"
    assert pull in pulled["score-sync.service"] and update not in pulled["score-sync.service"]
    assert pull not in unpulled["score-sync.service"] and update in unpulled["score-sync.service"]
    # --no-pull puts the update in the pull's place and changes nothing else
    assert {name: [update if line == pull else line for line in lines] for name, lines in pulled.items()} == unpulled
    service = [line for line in unpulled["score-sync.service"] if not line.startswith("#")]
    assert not any("<" in line for lines in unpulled.values() for line in lines if not line.startswith("#"))
    assert f"EnvironmentFile={env}" in service and f"WorkingDirectory={score}" in service
    start = next(line for line in service if line.startswith("ExecStart="))
    assert '"$$SCORE_SECRET_READER" "score-cockpit-sync-token"' in start
    assert f'"{score}/.venv/bin/python" -m score.dashboard sync' in start
    assert f"WorkingDirectory={score}" in unpulled["score-listen.service"]
    assert "WSL" not in "\n".join(unpulled["score-listen.service"])
    conductor = "/home/score/projects/score", "/home/score/.config/score/dashboard.env"
    for name in timer.UNITS:  # the same templates fill in for the conductor's user
        assert "/home/dupe" not in timer.unit_text(name, *conductor, timer.SECRET, pull=False), name
    unpushed = "is not on origin's main: push it first"
    checkouts = [  # (what, the change to the checkout, the pass's and the release's refusal, the commit named too)
        ("changes not committed", lambda: (score / "score/dashboard/a.py").write_text("a = 3\n"),
         "has changes not committed", False),
        ("a commit not pushed", lambda: committed(score, "score/dashboard/a.py", "a = 3\n", "dashboard: not pushed"),
         unpushed, True),
    ]
    for what, change, why, named in checkouts:
        change()
        assert why in client.tree_refusal(score), what
        for given_commit in (None, git(score, "git", "rev-parse", "HEAD")) if named else (None,):
            with pytest.raises(release.Refused, match=why):
                release.release(score, host, DOCKERFILE, SUBJECT, given_commit)
    git(host, "git", "fetch", "-q", "origin", "main")
    assert git(host, "git", "show", f"FETCH_HEAD:{DOCKERFILE}") == f"FROM x\nARG SCORE_COMMIT={head}\nRUN y"

    # the listener, on a store home of its own: a Buy waits for the next pass while the pass's figures do not price
    # this commit (during a pass, which makes prepare's figure and the price again on this commit, only for a basket
    # on another commit), said on the request and not asked again, else it is applied and its launch followed; a slow
    # request never holds back the next, and once stopping nothing more is claimed; the batch record is sent while it
    # lives and once as it ends
    settings.SCORE_HOME = tmp_path / "listener"
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    monkeypatch.setattr(applying, "apply", real)
    here, code = local.priced_here(), []
    monkeypatch.setattr(client, "head", lambda repo: code[-1])
    lone = types.SimpleNamespace(props_home=settings.SCORE_HOME, world=types.SimpleNamespace(name="world1"))
    checks, short = lone.props_home / "work" / local.CHECKS, here["commit"][:8]

    def figured(made):
        """The pass's figures as `made`: none, prepare's on other code and the basket before it, or all standing."""
        shutil.rmtree(checks, ignore_errors=True)
        shutil.rmtree(settings.SCORE_HOME / "proposals", ignore_errors=True)
        if made == "none":
            return
        (checks / local.GAPS_PRICE).mkdir(parents=True)
        (checks / local.GAPS_PRICE / "world1.json").write_text(json.dumps({"priced_on": here}))
        remake = ({"priced_on": {**here, "commit": "b" * 40}, "made_at": "2026-10-24T13:00:05.123456+00:00"}
                  if made == "moved" else {"priced_on": here, "made_at": "2026-10-24T12:59:00+00:00"})
        (checks / local.REMAKE).parent.mkdir(parents=True, exist_ok=True)
        (checks / local.REMAKE).write_text(json.dumps(remake))
        records.put_index(settings.SCORE_HOME / "proposals", {"made_at": "2026-10-24T13:00:00Z",
                                                              "commit": here["commit"]})
    not_made = ["the runner's price: it is not made yet", "prepare's figure: it is not made yet",
                f"the basket was made on commit None, the code is at {short}"]
    moved = f"prepare's figure: the code moved since it was made (commit bbbbbbbb, now {short})"
    before = "the basket was made at 2026-10-24T13:00:00Z, before prepare's figure (2026-10-24T13:00:05.123456+00:00)"
    other = f"the basket was made on commit {short}, the code is at cccccccc"
    judged = [  # (the figures, the code's commit, during a pass, what figures_moved says, why a Buy waits or None)
        ("none", here["commit"], False, not_made, "; ".join(not_made)),
        ("none", here["commit"], True, not_made, "; ".join(not_made)),
        ("moved", here["commit"], False, [moved, before], f"{moved}; {before}"),
        ("moved", here["commit"], True, [moved, before], None),
        ("moved", "c" * 40, True, [moved, other, before], other),
        ("stand", here["commit"], False, [], None),
        ("stand", "c" * 40, False, [other], other),
    ]
    for made, now, during, said, waits in judged:
        figured(made)
        code.append(now)
        with client.pricing_now() if during else contextlib.nullcontext():
            assert client.pass_pricing() == during, (made, now, during)
            assert client.figures_moved(lone, now) == said, (made, now, during)
            assert client.buy_waits(lone) == waits, (made, now, during)
    assert not client.pass_pricing()
    monkeypatch.setattr(applying, "apply_checkout", lambda item: applying.Applied("running", "launched", launch_id=9))
    listened, left, noted = Listened([BUY]), set(), [(5, f"waits for the next sync pass: {other}")]
    rounds = [  # (what, the code's commit, a listener started afresh, its answer, the notes, the claims, skipped ids)
        ("a basket on another commit", "c" * 40, False, [], noted, [], []),
        ("the Buy left for the pass, not asked again", "c" * 40, False, [], noted, [], [5]),
        ("the figures standing", here["commit"], True, [(5, "running")], noted, [5], []),
    ]
    for what, now, afresh, answer, notes, claims, skipped in rounds:
        code.append(now)
        left = set() if afresh else left
        assert listen.round_once(listened, lone, left) == answer, what
        assert (listened.notes, listened.claims, listened.skips[-1]) == (notes, claims, skipped), what
    assert listened.reports == [(5, "running")] and client.tracked() == {"5": 9} and left == set()
    let_go = threading.Event()

    def slow_draw(item, source, chosen=None):
        if item["kind"] == "concept-draw":
            let_go.wait(5)
        return applying.Applied("done", "")
    monkeypatch.setattr(applying, "apply", slow_draw)
    draw, stop, busy = {"id": 1, "kind": "concept-draw"}, {"id": 2, "kind": "stop-everything"}, set()
    with ThreadPoolExecutor(max_workers=4) as pool:
        listened.items = [draw]
        assert listen.round_once(listened, lone, left, pool, busy) == [] and busy == {1}
        listened.items = [draw, stop]  # the draw is skipped while it is answered
        assert listen.round_once(listened, lone, left, pool, busy) == [] and listened.skips[-1] == [1]
        deadline = time.monotonic() + 2.5
        while (2, "done") not in listened.reports and time.monotonic() < deadline:
            time.sleep(0.05)
        assert listened.reports[1:] == [(2, "done")]  # Stop everything answered while the draw still is
        stopping = threading.Event()
        stopping.set()
        listened.items = [{"id": 3, "kind": "stop-everything"}]
        assert listen.round_once(listened, lone, left, pool, busy, stopping) == []
        let_go.set()
    assert listened.reports[1:] == [(2, "done"), (1, "done")] and listened.claims == [5, 1, 2] and busy == set()
    states, live = iter([None, "running", "waiting", "finished", "finished"]), False
    batches = types.SimpleNamespace(batch_run=lambda read_at: (lambda state: state and {
        "state": state, "read_at": read_at})(next(states)))
    for _ in range(5):
        live = listen.batch_pushed(listened, batches, live)
    assert listened.runs == ["running", "waiting", "finished"]

    # a hosted process stays light: the image's files alone render every page of the export above, with nothing
    # heavy loaded and under MOST_MB, and every dashboard module but the store-side ones imports there (owner rule:
    # hosted never imports score.stages, score.store, numpy or usd-core; 2026-10-26 a top-level score.graph import
    # crash-looped the image)
    hosted = tmp_path / "hosted"
    (hosted / "export").mkdir(parents=True)
    (hosted / "export" / "current").symlink_to(tmp_path / "one")
    done = subprocess.run([sys.executable, "-I", "-c", CHILD, str(hosted_tree(tmp_path)),
                           json.dumps(sorted(STORE_SIDE))], env=hosted_env(hosted), cwd=tmp_path, capture_output=True,
                          text=True)
    assert done.returncode == 0, done.stderr[-3000:]
    light = json.loads(done.stdout.strip().splitlines()[-1])
    assert set(light["codes"].values()) == {200}, light["codes"]
    assert light["heavy"] == [] and light["missing"] == {}, (light["heavy"], light["missing"])
    assert light["rss_mb"] < MOST_MB, light["rss_mb"]


def picked(record, *paths):
    """The values at the dotted `paths` of a record (a dict of dicts)."""
    found_values = []
    for path in paths:
        value = record
        for name in path.split("."):
            value = value[name]
        found_values.append(value)
    return tuple(found_values)


def found(reads):
    """What `reads` reads, None while what it reads is not written yet."""
    try:
        return reads()
    except (TypeError, KeyError, IndexError, OSError):
        return None


@pytest.fixture
def owner_books(world, monkeypatch, settings):
    """The fixture world with no agent marks and no books yet (under this run's temp PROPS_HOME), the stop's first
    books given."""
    from score.review import web
    from score.store import AGENT_MARKERS
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(web, "books_now", lambda: {"month": "2026-10", "bill": 1.0, "ledger": 1.0})
    world.books = settings.SCORE_PROPS_HOME / "cloud" / "books.json"
    world.books.unlink(missing_ok=True)
    yield world
    world.books.unlink(missing_ok=True)


class Hosted:
    """A stand-in for the hosted dashboard's endpoints, in memory."""

    not_the_store = None  # this machine is the store's: no claim is refused for being another
    def __init__(self, waiting):
        self.waiting_items, self.reports, self.chunks, self.commits = waiting, [], [], []

    def lacking(self, sizes):
        return list(sizes)

    def put_chunk(self, sha, offset, size, data):
        self.chunks.append(sha)
        return {"have": size, "done": True}

    def commit(self, name, files):
        self.commits.append(files)

    def waiting(self, kinds=(), wait=0, skip=()):
        return [item for item in self.waiting_items if not kinds or item["kind"] in kinds]

    def claim(self, request_id):
        self.reports.append((request_id, "picked_up"))
        return True

    def put_request_file(self, name, data):
        self.chunks.append(name)

    def report(self, request_id, state, detail="", log_tail=""):
        self.reports.append((request_id, state))



# --- the listener --------------------------------------------------------------------------------------------------

KEPT = "the listener's record as the hosted side kept it"
BUY = {"id": 5, "kind": "checkout", "user": "joey", "payload": {"key": "k", "items": []}}


class Listened:
    """The hosted side in memory as the listener sees it: the waiting requests, what was claimed, noted, reported and sent."""
    not_the_store = None

    def __init__(self, waiting):
        self.items, self.claims, self.notes, self.reports, self.runs, self.skips = waiting, [], [], [], [], []

    def waiting(self, kinds=(), wait=0, skip=()):
        self.skips.append(list(skip))
        return [item for item in self.items if item["kind"] in kinds]

    def claim(self, request_id):
        self.claims.append(request_id)
        return True

    def note(self, request_id, detail):
        self.notes.append((request_id, detail))
        return True

    def report(self, request_id, state, detail="", log_tail=""):
        self.reports.append((request_id, state))

    def put_batch_run(self, run):
        self.runs.append(run["state"])


def export_with_batch(tmp_path, results, run, machine="", made_at="2026-10-24T12:55:00+00:00"):
    """An export from `machine` made at `made_at` carrying the batch record `run` (None: no checkout in it), read with
    the listener's records in `results`."""
    export = tmp_path / "export"
    export.mkdir(exist_ok=True)
    (export / "manifest.json").write_text(json.dumps({"made_at": made_at, "machine": machine}))
    (export / "batch-run.json").unlink(missing_ok=True)
    if run:
        (export / "batch-run.json").write_text(json.dumps(run))
    return ExportedSource(export, results)


# --- the release and the timer's install --------------------------------------------------------------------------

DOCKERFILE = "apps/cockpit/Dockerfile"
SUBJECT = "dashboards: the cockpit at score {short} (#1)"
TRAILER = "Co-Authored-By: a tester <t@example.org>"


def git(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def committed(clone, path, text, words):
    """Write a file in a clone, commit it; the commit's sha."""
    (clone / path).parent.mkdir(parents=True, exist_ok=True)
    (clone / path).write_text(text)
    git(clone, "git", "add", path)
    git(clone, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", words)
    return git(clone, "git", "rev-parse", "HEAD")


def a_repository(root, name):
    """A clone of a bare origin of its own (main): the clone."""
    origin, clone = root / f"{name}.git", root / name
    git(root, "git", "init", "-q", "--bare", "-b", "main", str(origin))
    git(root, "git", "clone", "-q", str(origin), str(clone))
    git(clone, "git", "config", "user.name", "t")
    git(clone, "git", "config", "user.email", "t@t")
    return clone


@pytest.fixture
def repositories(tmp_path):
    """(score, host, first): a score checkout with two pushed commits, the host pinning the first of them."""
    score = a_repository(tmp_path, "score")
    first = committed(score, "score/dashboard/a.py", "a = 1\n", "dashboard: the first")
    committed(score, "score/dashboard/a.py", "a = 2\n", "dashboard: the second, a subject " + "long " * 30)
    git(score, "git", "push", "-q", "origin", "HEAD:main")
    host = a_repository(tmp_path, "host")
    committed(host, DOCKERFILE, f"FROM x\nARG SCORE_COMMIT={first}\nRUN y\n", "cockpit: pinned")
    git(host, "git", "push", "-q", "origin", "HEAD:main")
    return score, host, first



def an_env_file(folder, reader=True):
    """An env file in `folder` naming the cockpit's URL and, when `reader`, a secret reader that prints "token"."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "sync.env"
    script = folder / "read-secret"
    script.write_text("#!/bin/sh\necho token\n")
    script.chmod(0o755)
    path.write_text("SCORE_SYNC_URL=https://cockpit.test\n" + (f"SCORE_SECRET_READER={script}\n" if reader else ""))
    return path


class Pin:
    """A urlopen stand-in for the cockpit's /api/sync/pin; what it was asked, with the token it was given."""

    def __init__(self, commit):
        self.body = json.dumps({"commit": commit}).encode()
        self.asked = []

    def __call__(self, request, timeout):
        self.asked.append((request.full_url, request.get_header("Authorization")))
        return io.BytesIO(self.body)


# --- a hosted process stays light ----------------------------------------------------------------------------------

MOST_MB = 200
# the store-side modules: the hosted image holds them but its process never loads them (they need score.graph,
# score.conductor, score.review or the store); a page that loads one fails in the hosted tree below
STORE_SIDE = {"checkout.chat_yes", "films.preview.make", "films.preview.scenes", "proposals.assemble", "proposals.make",
              "state.local", "sync.chat_decisions", "sync.listen"}
CHILD = """
import json, os, sys
sys.path.insert(0, sys.argv[1])  # run with -I: the hosted tree alone, as the image holds it
import django
django.setup()
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
from django.contrib.auth import get_user_model
from django.test import Client
user = get_user_model().objects.create_user("joey", password="a long enough password")
client = Client()
client.force_login(user)
pages = ["/", "/places/", "/environments/world1/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/",
         "/world/step/terrain/", "/basket/", "/runs/", "/requests/", "/healthz"]
codes = {page: client.get(page, HTTP_HOST="127.0.0.1").status_code for page in pages[:-1]}
import score.dashboard.site.asgi  # what the hosted image serves
heavy = [name for name in ("numpy", "pxr", "score.stages", "score.store", "score.graph", "score.conductor",
                          "score.dashboard.previews", "matplotlib")
         if name in sys.modules]
# the hosted image holds score/__init__.py and score/dashboard alone
heavy += [name for name in sys.modules if name.startswith("score.") and not name.startswith("score.dashboard")]
# VmHWM, this process's own peak (ru_maxrss keeps the forking parent's peak across exec)
rss = int(next(line for line in open("/proc/self/status") if line.startswith("VmHWM")).split()[1]) / 1024
# then every dashboard module but the store-side ones, imported from the hosted tree alone
import importlib, pkgutil
import score.dashboard
store_side = set(json.loads(sys.argv[2]))
missing = {}
for found in pkgutil.walk_packages(score.dashboard.__path__, "score.dashboard."):
    short = found.name.removeprefix("score.dashboard.")
    test = short.split(".")[0] == "tests" or short.rsplit(".", 1)[-1].startswith(("test_", "conftest"))
    if test or short in store_side:
        continue
    try:
        importlib.import_module(found.name)
    except ImportError as error:
        missing[found.name] = str(error)
print(json.dumps({"codes": codes, "heavy": heavy, "rss_mb": rss, "missing": missing}))
"""


def hosted_tree(tmp_path):
    """The files the Dockerfile's hosted target copies, read from its COPY lines, laid out as the image holds them."""
    text = (REPO / "score/dashboard/Dockerfile").read_text()
    stage = re.search(r"^FROM \S+ AS hosted$(.*?)(?=^FROM |\Z)", text, re.M | re.S).group(1)
    tree = tmp_path / "app"
    for line in re.findall(r"^COPY (.+)$", stage, re.M):
        *sources, dest = line.split()
        for source in sources:
            target = tree / dest / pathlib.Path(source).name if dest.endswith("/") else tree / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            if (REPO / source).is_dir():
                shutil.copytree(REPO / source, target, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(REPO / source, target)
    assert (tree / "score/dashboard/site/asgi.py").is_file(), "the hosted target copies no score/dashboard"
    return tree


def hosted_env(home):
    return {**os.environ, "SCORE_DASHBOARD_MODE": "hosted", "SCORE_STORE_WRITABLE": "0",
            "SCORE_DASHBOARD_HOME": str(home), "DJANGO_SETTINGS_MODULE": "score.dashboard.site.settings"}
