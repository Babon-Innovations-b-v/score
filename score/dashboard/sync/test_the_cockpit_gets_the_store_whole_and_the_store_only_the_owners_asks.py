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
- client.push_export: `whole = True` -> test_two_passes_send_only_what_is_lacking_and_swap_the_export_in_whole
- client.uploaded: the deadline as if counted before the build -> test_a_build_longer_than_the_pass_still_sends_...
- endpoints.swept: unused blobs kept (`if stale:`) -> test_the_cockpit_gets_the_store_whole_...
- building.pictures_folder: old versions kept -> test_a_change_to_the_exporting_code_sends_every_bundle_again
- endpoints.readable: the format check -> `if False:` -> test_an_export_of_a_format_the_hosted_side_cannot_read_...
- endpoints.report: the state kept "waiting" -> test_the_cockpit_gets_the_store_whole_...
- applying.apply_decision: the owner check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- applying.OWNER_FIGURES: a "month" kind added -> test_the_cockpit_gets_the_store_whole_...
- pages/actions.owner_figure_off_why: the agent check -> `if False:` -> test_the_cockpit_gets_the_store_whole_...
- pages/actions.set_books_figure: the amount check -> `if False:` -> test_the_hosted_buttons_queue_the_owners_...
- pages/actions.scene_name: the name check -> `if False:`; or library_actions.carried_out: the refusal dropped ->
  test_the_cockpit_gets_the_store_whole_...
- pages/actions.record_change: no inbox write -> test_the_cockpit_gets_the_store_whole_...
- client.sync_pass: `applied = []` -> test_a_sync_pass_pushes_the_export_and_reports_each_request
- client.sync_pass: a `usd_sweep()` also inside the pricing lock -> test_the_usd_check_runs_outside_the_pricing_lock
- client.step_run: `err` without "out of time after ..." -> test_a_step_out_of_time_is_ended_and_says_so
- client.design_moved: the copy check -> `if False:` -> test_a_pass_says_the_design_moved_when_a_live_runs_copy_differs
- client.sync_pass: the basket not made -> test_each_pass_makes_the_basket_again_from_the_runners_plan_...
- client.sync_pass: the moved-checkout words never said -> test_a_pass_still_pushes_its_export_when_the_checkout_...
- client.sync_pass: the tree refusal ignored -> test_a_pass_syncs_nothing_from_a_checkout_not_clean_and_pushed_...
- client.tree_refusal: uncommitted changes ignored -> test_the_tree_check_wants_every_tracked_file_committed_...
- state/exported.made_words: "export of" for "state from" -> test_hosted_pages_render_from_the_export_with_its_time
- client.readings_fixed: the places not given -> test_a_pass_fixes_no_reading_that_holds_no_part_of_another_rows_thing
- client.asked_of_readings: the Stop everything check -> `if False:` -> test_a_pass_asks_the_parts_of_a_locked_place_...
- client.light_read: asks the unparted places -> test_a_pass_asks_the_light_of_a_locked_place_read_before_it_...
- client.film_previews: "" for none wanted -> test_a_pass_makes_the_free_preview_of_each_locked_script_...
- client.step_run: the group not ended -> test_a_step_leaves_nothing_running_after_it
- listen.round_once: no kinds asked -> test_a_hosted_buy_is_applied_by_the_listener_and_its_launch_followed
- listen.answered_here: a Buy left for the pass not kept in `left` -> test_a_buy_whose_price_needs_a_pass_...
- client.buy_waits: the pass's pricing ignored -> test_a_buy_during_a_pass_waits_only_for_a_basket_on_another_commit
- listen.round_once: the stopping check -> `if False:` -> test_a_slow_request_never_holds_back_the_next_and_a_stop_...
- client.figures_moved: the basket's commit check -> `if False:` -> test_the_figures_must_price_this_commit_...
- listen.batch_pushed: `if live:` alone -> test_the_batch_record_is_sent_while_it_lives_and_once_as_it_ends
- endpoints.note: a claimed request noted too -> test_the_hosted_side_notes_skips_and_serves_the_newer_batch_record
- state/exported.store_batch: the machine check -> `if False:` -> test_a_moved_or_reset_store_shows_no_old_batch
- release.message: the subject not cut -> test_a_release_pins_the_pushed_head_in_one_commit_of_the_hosts_style
- release.release: `moved = ""` (the conductor's checkout left on the old pin, its door running old code) -> the same
- release.score_commit: the refusal not raised -> test_a_release_refuses_a_commit_not_pushed_or_a_checkout_...
- release.inside: the ".." check dropped -> test_a_release_refuses_a_dockerfile_path_outside_the_host_...
- release.pinned: `if not found:` -> test_a_dockerfile_must_pin_exactly_one_commit
- timer.env_refusal: the reader check -> `if False:` -> test_the_install_refuses_an_env_file_without_its_url_...
- timer.install: no listener restart -> test_the_install_writes_both_units_filled_and_enables_the_timer
- timer.unquoted: `return value` -> test_a_quoted_reader_is_read_as_systemd_reads_it_...
- timer.unit_text: the pull never replaced -> test_the_units_render_for_the_conductors_user_and_no_pull_...
- timer.dashboard_refusal: the dashboard diff -> `if False:` -> test_without_a_host_the_install_checks_the_commit_...
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
- state/exported.py: `import numpy` at its top -> test_hosted_renders_every_page_light
- launch/localrun.py: `from score.graph import runs` at its top (93fec2b1) -> test_hosted_renders_every_page_light,
  test_every_module_the_hosted_image_holds_imports_from_it_alone
"""
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
import time
import types
from unittest.mock import ANY

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
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


def test_the_cockpit_gets_the_store_whole_and_the_store_only_the_owners_asks(owner_books, tmp_path, settings,
                                                                             monkeypatch):
    """The fixture world exported twice and once under a tiny cap, then the hosted side's sync routes driven through one
    exchange table (uploads, refusals, commits, the request states) and every route asked with a wrong token; then the
    store side applies one request table (a stranger's, an agent's process's, bad names and library addresses, kinds
    no button sends, then the owner's own), a refused request writing nothing; then his decisions made in chat
    through one table of decision kinds (each with a twin asked before its target changed) and one of yeses never
    recorded."""
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
        ("the request waits", ("GET", "/api/sync/requests?state=waiting", None), 200, None),
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
    assert [item["id"] for item in answers["the request waits"].json()] == [request.pk]
    request.refresh_from_db()
    assert request.state == "done"
    assert not (home / "blobs" / liar).exists() and not (home / "blobs" / f"{liar}.part").exists()
    # only the three good commits landed, the oldest swept with the blob no kept export uses
    assert sorted(path.name for path in (home / "export").iterdir()) == ["b", "c", "current"]
    assert [(home / "blobs" / sha_of(body)).exists() for body in manifests.values()] == [False, True, True]
    routes = [("POST", "/api/sync/lacking", {"files": {sha_of(b"x"): 1}}), gzipped_put(sha_of(b"x"), 0, 1, b"x"),
              commit("n", {}), ("GET", "/api/sync/pin", None), ("GET", "/api/sync/requests?state=done", None)]
    for wrong in ({}, {"Authorization": "Bearer wrong"}):
        for route in routes:
            assert answered(web, route, wrong).status_code == 401, (wrong, route)
    shutil.rmtree(home / "export")  # its names sort after the dated exports the passes below swap in

    from score.dashboard.pages import actions, library_actions
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


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_two_passes_send_only_what_is_lacking_and_swap_the_export_in_whole(world, settings, monkeypatch):
    exports = settings.SCORE_HOME / "export"
    web = hosted_client()
    monkeypatch.setattr(client, "PASS_SECONDS", -1.0)  # the pass is over before its first file: its records wait
    first = client.push_export(remote_of(web), world.source, FakeBackend())
    assert first["files"] == 0 and first["to_come"] > 0 and not first["committed"]
    assert "state.json" in {entry["what"] for entry in first["left_out"] if entry["why"] == client.STILL}
    assert not (exports / "current").exists()  # an export with no records is never swapped in
    monkeypatch.setattr(client, "PASS_SECONDS", 600.0)
    monkeypatch.setattr(client, "made_now", lambda: "2026-10-18T13:00:00+00:00")
    second = client.push_export(remote_of(web), world.source, FakeBackend())
    assert second["to_come"] == 0 and second["files"] == first["to_come"]
    shown = json.loads((exports / "current/manifest.json").read_text())
    assert shown["made_at"] == "2026-10-18T13:00:00+00:00"
    assert not any(entry["why"] == client.STILL for entry in shown["left_out"])
    for path in shown["written"]:
        assert (exports / "current" / path).is_file(), path
    monkeypatch.setattr(client, "made_now", lambda: "2026-10-18T14:00:00+00:00")
    third = client.push_export(remote_of(web), world.source, FakeBackend())
    assert third["files"] <= 2  # only what changed: the new state.json and manifest
    kept = [path for path in exports.iterdir() if path.is_dir() and not path.is_symlink()]
    assert len(kept) == 2 and os.readlink(exports / "current") == "2026-10-18T140000+0000"


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_a_build_longer_than_the_pass_still_sends_the_export(world, settings, monkeypatch):
    """2026-10-21: the build outgrew PASS_SECONDS, the deadline was counted from before it, and every pass sent
    nothing and swapped in an export with no state.json (the cockpit's places 404)."""
    clock, build = [0.0], building.build

    def slow_build(*args):
        clock[0] += client.PASS_SECONDS + 1
        return build(*args)
    monkeypatch.setattr(client.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(client.building, "build", slow_build)
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)
    pushed = client.push_export(remote_of(hosted_client()), world.source, FakeBackend())
    assert pushed["committed"] and pushed["to_come"] == 0
    assert (settings.SCORE_HOME / "export/current/state.json").is_file()


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_a_change_to_the_exporting_code_sends_every_bundle_again(world, settings, monkeypatch):
    web, current = hosted_client(), settings.SCORE_HOME / "export/current"
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)  # other tests' exports sort after a date
    monkeypatch.setattr(client, "made_now", lambda: "2026-10-18T15:00:00+00:00")
    first = client.push_export(remote_of(web), world.source, FakeBackend())
    assert first["to_come"] == 0
    before = json.loads((current / "places/alpha.json").read_text())
    assert before["code_version"] == versions.exporting() and before["format"] == versions.FORMAT
    monkeypatch.setattr(versions, "exporting", lambda: "0123456789ab")  # the building code changed
    monkeypatch.setattr(client, "made_now", lambda: "2026-10-18T16:00:00+00:00")
    second = client.push_export(remote_of(web), world.source, FakeBackend())
    after = json.loads((current / "places/alpha.json").read_text())
    assert after["code_version"] == "0123456789ab" and after["detail"] == before["detail"]
    assert json.loads((current / "manifest.json").read_text())["code_version"] == "0123456789ab"
    assert second["files"] >= len(world.source.places()) + 1  # every place's bundle and the world's, sent again
    pictures = world.source.home / building.PICTURES
    assert [path.name for path in pictures.iterdir()] == ["0123456789ab"]  # the old version's pictures went


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_an_export_of_a_format_the_hosted_side_cannot_read_is_refused_in_the_sync_words(world, settings,
                                                                                         monkeypatch):
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)
    monkeypatch.setattr(versions, "FORMAT", 1)  # an old store side: gaps and stops as words
    fed(monkeypatch)
    said = client.sync_pass(remote_of(hosted_client()), world.source, FakeBackend())
    assert said.startswith("REFUSED") and "export format 1 cannot be read here" in said, said
    assert not (settings.SCORE_HOME / "export/current").exists()


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


def test_the_hosted_buttons_queue_the_owners_request_and_refuse_anyone_else(world, settings):
    """Hosted, each money button is a signed-in owner request in the outbox, with his name, the time and the
    figure; anyone else's is refused at the door."""
    from score.dashboard.pages import actions
    settings.SCORE_MODE = settings.HOSTED
    try:
        assert actions.set_books_figure("joey", 12.5).startswith("queued")
        assert actions.read_books_back("joey").startswith("queued")
        assert actions.waive_check("joey", "beta", "closeup", "abc", "looks", "fine").startswith("queued")
        assert actions.set_books_figure("joey", "nan-ish").startswith("refused")
    finally:
        settings.SCORE_MODE = settings.LOCAL
    queued = {item.kind: item for item in SyncRequest.objects.all()}
    assert set(queued) == {"books-figure", "read-back", "waiver"}
    figure = queued["books-figure"]
    assert figure.user == "joey" and figure.payload["euros"] == 12.5 and figure.created
    user = get_user_model().objects.create_user("mallory", password="a long enough password")
    pages = Client()
    pages.force_login(user)
    assert pages.post("/world/step/terrain/waive/", {"output": "x", "check": "looks", "reason": "r"}).status_code == 403


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


def test_a_sync_pass_pushes_the_export_and_reports_each_request(world, monkeypatch):
    priced = fed(monkeypatch)
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}},
                     {"id": 8, "kind": "decision", "user": "mallory", "payload": {
                         "node": "closeup@alpha", "output": "o", "decision": "reject"}}])
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert "pushed the export" in said and "0 still to come" in said and len(hosted.commits) == 1
    assert "library problems" in said, said  # the library sweep ran before the export was built
    # and the gaps after it: with no store under PROPS_HOME they fail loudly, said in the pass's words
    assert "gaps failed: exit 1: no store at " in said, said
    # priced before the push
    assert said.endswith(f"{PRICED}; plans for the plan stage: test; remake batch (estimate): test; benchmarks: none listed; basket made: 0 items, 0 paid steps; library pictures: test; library demos: test; film previews: test")
    assert "checkouts: 0 left launching failed, 0 ended batches' lines taken back" in said
    assert priced == [world.source.world.name]
    assert hosted.reports == [(7, "picked_up"), (7, "done"), (8, "picked_up"), (8, "refused")]


def test_the_usd_check_runs_outside_the_pricing_lock(world, monkeypatch):
    """The USD check prices nothing, so a pass runs it after the pricing lock: a Buy is never judged by its basket's
    commit alone while a long check runs (review 2026-10-26: 500k quads took 3.9 s, a place)."""
    fed(monkeypatch)
    held = []
    monkeypatch.setattr(client, "usd_sweep", lambda: held.append(client.pass_pricing()) or "usd check: test")
    monkeypatch.setattr(client, "gaps_sweep", lambda: held.append(client.pass_pricing()) or "gaps: test")
    said = client.sync_pass(Hosted([]), world.source, FakeBackend())
    assert held == [True, False] and "usd check: test" in said, said


def test_a_step_out_of_time_is_ended_and_says_so(settings, tmp_path):
    """A pass step given a limit (the USD check) is ended with its group when the limit runs out, its exit nonzero
    and its last error line saying so, so the pass goes on."""
    settings.SCORE_REPO = tmp_path
    done = client.step_run([sys.executable, "-c", "import time; print('began', flush=True); time.sleep(60)"],
                           grace=2, limit=1)
    assert done.returncode != 0 and done.stdout.strip() == "began"
    assert done.stderr.strip().splitlines()[-1] == "out of time after 1 s"


def test_a_pass_says_the_design_moved_when_a_live_runs_copy_differs(world, monkeypatch, settings):
    """A live run reads its own design copy (graph/frozen.py): a pass whose design differs from it says so."""
    fed(monkeypatch)
    home = settings.SCORE_PROPS_HOME
    (home / "design" / "plans").mkdir(parents=True, exist_ok=True)
    (home / "design" / "plans" / "p.json").write_text("{}")
    copy = home / "frozen" / "run1.home" / "design"
    shutil.copytree(home / "design", copy)
    assert "design moved" not in client.sync_pass(Hosted([]), world.source, FakeBackend())
    (home / "design" / "plans" / "p.json").write_text('{"moved": true}')
    assert client.sync_pass(Hosted([]), world.source, FakeBackend()).endswith(
        "design moved since the running batch started (the cockpit prices the design as it is now)")
    shutil.rmtree(copy)
    copy.symlink_to(home / "design")  # the run ended: its copy is a link to the real design
    assert "design moved" not in client.sync_pass(Hosted([]), world.source, FakeBackend())


def test_each_pass_makes_the_basket_again_from_the_runners_plan_in_this_checkout(world, monkeypatch, settings):
    """A basket an agent's worktree made yesterday (a scene merged away since, none of today's rows) is replaced by
    the runner's plan of today, made here, when and on which commit said: what the checkout reads."""
    fed(monkeypatch)
    root = settings.SCORE_HOME / "proposals"
    records.put_index(root, {"made_at": "2026-10-20T17:45:33Z", "checkout": "/x/.claude/worktrees/agent-a",
                             "items": [{"id": "navigation-pieces", "nodes": {"closeup@navigation": {}}}]})
    monkeypatch.setattr(FakeBackend, "plan_buys", ["closeup@alpha", "pixal@beta"])
    said = client.sync_pass(Hosted([]), world.source, FakeBackend())
    assert "basket made: 2 items, 2 paid steps" in said, said
    index = records.index(root)
    assert index["checkout"] == str(make.REPO) and index["plan_only"] and index["made_at"] > "2026-10-20T17:45:33Z"
    assert index["commit"] == make.commit()
    assert sorted(node for item in index["items"] for node in item["nodes"]) == ["closeup@alpha", "pixal@beta"]


def test_a_pass_still_pushes_its_export_when_the_checkout_moved_during_it(world, monkeypatch):
    fed(monkeypatch)
    commits = iter(["a" * 40, "b" * 40])
    monkeypatch.setattr(client, "head", lambda repo: next(commits))
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}}])
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert "the checkout moved from aaaaaaaa to bbbbbbbb during the pass" in said and "Buy waits" in said, said
    assert hosted.commits and hosted.reports == [(7, "picked_up"), (7, "done")]  # pushed, his requests applied


def test_a_pass_syncs_nothing_from_a_checkout_not_clean_and_pushed_or_when_the_price_fails(world, monkeypatch):
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}}])
    offline(monkeypatch)
    monkeypatch.setattr(client, "tree_refusal", lambda repo: "commit 0123abcd is not on origin's main: push it first")
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert said == "REFUSED: nothing synced: commit 0123abcd is not on origin's main: push it first; sweep: test"
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    monkeypatch.setattr(client, "runner_price", lambda repo, environment: (None, "the runner's price failed: exit 1"))
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert said.startswith("REFUSED: nothing synced: the runner's price failed: exit 1; ") and "gaps" in said
    assert said.endswith("; remake batch (estimate): test; benchmarks: none listed; library pictures: test; library demos: test")
    assert hosted.commits == [] and hosted.chunks == [] and hosted.reports == []


def a_checkout(tmp_path):
    """A clone of a bare origin with one commit pushed to its main: (origin, clone)."""

    def run(*args, cwd=tmp_path):
        subprocess.run(args, cwd=cwd, check=True, capture_output=True)
    origin, clone = tmp_path / "origin.git", tmp_path / "clone"
    run("git", "init", "-q", "--bare", "-b", "main", str(origin))
    run("git", "clone", "-q", str(origin), str(clone))
    (clone / "a.txt").write_text("a")
    run("git", "add", "a.txt", cwd=clone)
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "a", cwd=clone)
    run("git", "push", "-q", "origin", "HEAD:main", cwd=clone)
    return origin, clone


def test_the_tree_check_wants_every_tracked_file_committed_and_the_commit_on_origins_main(tmp_path):
    _, clone = a_checkout(tmp_path)
    assert client.tree_refusal(clone) is None
    (clone / "a.txt").write_text("b")
    assert "has changes not committed" in client.tree_refusal(clone)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "b"], cwd=clone,
                   check=True)
    assert "is not on origin's main: push it first" in client.tree_refusal(clone)


def test_hosted_pages_render_from_the_export_with_its_time(world, tmp_path, settings, monkeypatch, read):
    exported(world, tmp_path / "export")
    from score.dashboard import state
    source = ExportedSource(tmp_path / "export")
    monkeypatch.setattr(state, "source", lambda: source)
    settings.SCORE_MODE = "hosted"
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    pages = Client()
    pages.force_login(user)
    for page in ("/", "/places/", "/environments/world1/", "/place/alpha/", "/place/alpha/step/closeup/", "/world/step/terrain/", "/requests/"):
        html = pages.get(page).content.decode()
        assert "state from 2026-10-18 12:00" in html, page
    pages.post("/place/alpha/step/closeup/decide/", {"decision": "reject", "output": "x", "reason": "no"})
    assert SyncRequest.objects.filter(kind="decision").exists()


def test_a_pass_fixes_no_reading_that_holds_no_part_of_another_rows_thing(world):
    """client.readings_fixed: the fixture's readings hold no row inside another row's thing, so none is fixed."""
    assert client.readings_fixed(world.source.store_root) == "readings: none to fix"


def test_a_pass_asks_the_parts_of_a_locked_place_read_before_parts_once_and_never_under_stop_everything(
        world, monkeypatch):
    """client.parts_read: the fixture's readings have no parts, so the first pass asks them (one call a place, under
    the reading's clearance, the owner's standing allowance) before the gaps, plans, prepare and price; a second pass
    asks nothing; while Stop everything holds nothing is asked and the pass's words say why."""
    from score.review import reading
    from score.store import Store
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)  # the books' own test
    monkeypatch.setattr("score.adapters.compute.books_refusal", lambda: None)
    monkeypatch.delenv("SCORE_BENCHMARK_GRANT", raising=False)
    store = Store.in_folder(world.source.store_root)
    places = reading.unparted(store, ["alpha", "beta"])
    assert places
    monkeypatch.setattr(client, "free_only_followed", lambda: True)
    assert client.parts_read(world.source.store_root, ask=None) == (
        f"parts not read for {len(places)} places: refused, Stop everything holds (free only)")
    monkeypatch.setattr(client, "free_only_followed", lambda: False)
    asked = []

    def ask(store, place, folder):
        asked.append(place)
        return {row["id"]: "object" for row in reading.reading_of(store, place)["inventory"]["rows"]}, 0.05, 1.0
    assert client.parts_read(world.source.store_root, ask=ask) == f"parts read: {len(places)} places, " \
        f"EUR {0.05 * len(places):.2f}"
    assert sorted(asked) == sorted(places) and reading.unparted(store, places) == []
    assert client.parts_read(world.source.store_root, ask=ask) == "parts: none missing" and len(asked) == len(places)


def test_a_pass_asks_the_light_of_a_locked_place_read_before_it_once_and_never_under_stop_everything(
        world, monkeypatch):
    """client.light_read: the fixture's readings have no concept light, so the first pass asks it (one call a place,
    under the reading's clearance) before the plans are kept; a second pass asks nothing; while Stop everything holds
    nothing is asked and the pass's words say why."""
    from score.review import reading
    from score.store import Store
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)  # the books' own test
    monkeypatch.setattr("score.adapters.compute.books_refusal", lambda: None)
    monkeypatch.delenv("SCORE_BENCHMARK_GRANT", raising=False)
    store = Store.in_folder(world.source.store_root)
    places = reading.unlit(store, ["alpha", "beta"])
    assert places
    monkeypatch.setattr(client, "free_only_followed", lambda: True)
    assert client.light_read(world.source.store_root, ask=None) == (
        f"light not read for {len(places)} places: refused, Stop everything holds (free only)")
    monkeypatch.setattr(client, "free_only_followed", lambda: False)
    asked = []

    def ask(store, place, folder):
        asked.append(place)
        rows = {row["id"]: {"glows": False, "glowing": "", "colour": "", "brightness": 0}
                for row in reading.reading_of(store, place)["inventory"]["rows"]}
        return {"rows": rows, "scene": {"daylight": True, "unseen": False, "unseen_colour": ""}}, 0.04, 1.0
    assert client.light_read(world.source.store_root, ask=ask) == f"light read: {len(places)} places, " \
        f"EUR {0.04 * len(places):.2f}"
    assert sorted(asked) == sorted(places) and reading.unlit(store, places) == []
    assert reading.concept_light(store, places[0])["scene"]["daylight"] is True
    assert client.light_read(world.source.store_root, ask=ask) == "light: none missing" and len(asked) == len(places)


def test_a_pass_makes_the_free_preview_of_each_locked_script_that_wants_one(monkeypatch):
    """client.film_previews: every film final.previews_wanted names is rendered, each said in the pass's words; none
    wanted is said so, and a failure to read the locks is said, not raised."""
    from score.stages.demo_film import final
    rendered = []
    monkeypatch.setattr(final, "previews_wanted", lambda: ["one", "two"])
    assert client.film_previews(lambda film: rendered.append(film) or f"film-preview {film}: made") == \
        "film-preview one: made; film-preview two: made"
    assert rendered == ["one", "two"]
    monkeypatch.setattr(final, "previews_wanted", lambda: [])
    assert client.film_previews(rendered.append) == "film previews: none wanted"
    monkeypatch.setattr(final, "previews_wanted", lambda: json.loads("{"))
    assert client.film_previews(rendered.append).startswith("film previews failed: JSONDecodeError")


def test_a_step_leaves_nothing_running_after_it(settings, tmp_path):
    """A pass step's leftovers (a film preview's Chromium) end with the step (2026-10-25: chrome-headless stayed
    after the pass); its output and exit code are kept. The leftover lets go of the step's output, so the step itself
    ends at once and only the group's end can stop it (holding the pipe, it would end on its own after its minute)."""
    settings.SCORE_REPO = tmp_path
    left = ("import subprocess; print(subprocess.Popen(['sleep', '60'], stdout=subprocess.DEVNULL, "
            "stderr=subprocess.DEVNULL).pid)")
    done = client.step_run([sys.executable, "-c", left], grace=2)
    assert done.returncode == 0
    stat = pathlib.Path(f"/proc/{int(done.stdout)}/stat")

    def ended():
        try:
            return stat.read_text().rpartition(")")[2].split()[0] == "Z"
        except FileNotFoundError:
            return True
    # a kill lands a moment after it is sent: wait at most 2 s for it, never the leftover's minute
    deadline = time.monotonic() + 2
    while not ended() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert ended()


# --- the listener --------------------------------------------------------------------------------------------------

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


def test_a_hosted_buy_is_applied_by_the_listener_and_its_launch_followed(monkeypatch, settings, tmp_path):
    settings.SCORE_HOME = tmp_path
    monkeypatch.setattr(client, "buy_waits", lambda source: None)
    monkeypatch.setattr(applying, "apply_checkout", lambda item: applying.Applied("running", "launched", launch_id=9))
    hosted = Listened([BUY])
    assert listen.round_once(hosted, None) == [(5, "running")]
    assert hosted.claims == [5] and hosted.reports == [(5, "running")] and client.tracked() == {"5": 9}


def test_a_buy_whose_price_needs_a_pass_is_said_so_and_left_waiting_for_it(monkeypatch):
    monkeypatch.setattr(client, "buy_waits", lambda source: "the basket was made on commit aaaaaaaa")
    hosted, left = Listened([BUY]), set()
    assert listen.round_once(hosted, None, left) == [] and left == {5}
    assert hosted.claims == [] and hosted.notes == [(5, "waits for the next sync pass: the basket was made on commit "
                                                        "aaaaaaaa")]
    monkeypatch.setattr(client, "buy_waits", lambda source: pytest.fail("asked again"))
    assert listen.round_once(hosted, None, left) == [] and hosted.skips[-1] == [5]  # an old hosted side ignores skip


def test_a_buy_during_a_pass_waits_only_for_a_basket_on_another_commit(monkeypatch, settings, tmp_path):
    """A pass makes prepare's figure and the price again on the same commit for about 15 minutes; the last pass's
    stand meanwhile (owner, 2026-10-25: "this process is stupid"), a basket on another commit does not."""
    settings.SCORE_HOME = tmp_path
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    remade = ["prepare's figure: the code moved since it was made",
              "the basket was made at 2026-10-25T09:00:00Z, before prepare's figure (2026-10-25T09:05:00Z)"]
    monkeypatch.setattr(client, "figures_moved", lambda source, now: list(remade))
    assert client.buy_waits(None).startswith("prepare's figure")
    with client.pricing_now():
        assert client.pass_pricing() and client.buy_waits(None) is None
        remade.append("the basket was made on commit aaaaaaaa, the code is at bbbbbbbb")
        assert client.buy_waits(None) == remade[-1]
    assert not client.pass_pricing()


def test_a_slow_request_never_holds_back_the_next_and_a_stop_claims_nothing(monkeypatch):
    """The listener's pool: a draw still answering does not keep Stop everything waiting for it; once SIGTERM set
    `stopping`, nothing more is claimed and what was claimed is answered before the process ends."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    release, answered = threading.Event(), []

    def answer(remote, item, source, chosen=None):
        if item["kind"] == "concept-draw":
            release.wait(5)
        answered.append(item["id"])
        return applying.Applied("done", "")
    monkeypatch.setattr(client, "answered", answer)
    draw, stop = {"id": 1, "kind": "concept-draw"}, {"id": 2, "kind": "stop-everything"}
    hosted, busy, left = Listened([draw]), set(), set()
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert listen.round_once(hosted, None, left, pool, busy) == [] and busy == {1}
        hosted.items = [draw, stop]  # the draw is skipped while it is answered
        listen.round_once(hosted, None, left, pool, busy)
        assert hosted.skips[-1] == [1]
        for _ in range(50):
            if answered == [2]:
                break
            threading.Event().wait(0.05)
        assert answered == [2]
        stopping = threading.Event()
        stopping.set()
        hosted.items = [{"id": 3, "kind": "stop-everything"}]
        assert listen.round_once(hosted, None, left, pool, busy, stopping) == []
        release.set()
    assert answered == [2, 1] and busy == set()


def test_the_figures_must_price_this_commit_and_the_basket_come_after_prepare(settings, tmp_path):
    settings.SCORE_HOME = tmp_path
    source = types.SimpleNamespace(props_home=tmp_path, world=types.SimpleNamespace(name="world1"))
    here = local.priced_here()
    found = client.figures_moved(source, here["commit"])
    assert found[:2] == ["the runner's price: it is not made yet", "prepare's figure: it is not made yet"]
    checks = tmp_path / "work" / local.CHECKS
    (checks / local.GAPS_PRICE).mkdir(parents=True)
    (checks / local.REMAKE).parent.mkdir(parents=True)
    (checks / local.GAPS_PRICE / "world1.json").write_text(json.dumps({"priced_on": here}))
    (checks / local.REMAKE).write_text(json.dumps({"priced_on": {**here, "commit": "b" * 40},
                                                   "made_at": "2026-10-24T13:00:05.123456+00:00"}))
    records.put_index(tmp_path / "proposals", {"made_at": "2026-10-24T13:00:00Z", "commit": here["commit"]})
    found = client.figures_moved(source, here["commit"])
    assert len(found) == 2 and found[0].startswith("prepare's figure: the code moved since it was made")
    assert found[1].startswith("the basket was made at 2026-10-24T13:00:00Z, before prepare's figure")
    (checks / local.REMAKE).write_text(json.dumps({"priced_on": here, "made_at": "2026-10-24T12:59:00+00:00"}))
    assert client.figures_moved(source, here["commit"]) == []
    assert client.figures_moved(source, "c" * 40) == [
        f"the basket was made on commit {here['commit'][:8]}, the code is at cccccccc"]


def test_the_batch_record_is_sent_while_it_lives_and_once_as_it_ends():
    states = iter([None, "running", "waiting", "finished", "finished"])

    class Source:
        def batch_run(self, read_at):
            state = next(states)
            return state and {"state": state, "read_at": read_at}
    hosted, source, live = Listened([]), Source(), False
    for _ in range(5):
        live = listen.batch_pushed(hosted, source, live)
    assert hosted.runs == ["running", "waiting", "finished"]


def test_the_hosted_side_notes_skips_and_serves_the_newer_batch_record(settings, tmp_path):
    from score.dashboard.site.asgi import app
    # all through the settings fixture: an override_settings decorator ends before the fixture's own overrides are
    # undone, which then put the hosted mode back for every later test file (concept_test, run after it)
    settings.SCORE_MODE, settings.SCORE_SYNC_TOKEN, settings.SCORE_HOME = "hosted", TOKEN, tmp_path
    web, bearer = TestClient(app, base_url="http://127.0.0.1:8780"), {"Authorization": f"Bearer {TOKEN}"}
    buy = SyncRequest.objects.create(kind="checkout", user="joey", payload={})
    assert web.post(f"/api/sync/requests/{buy.pk}/note", json={"detail": "waits"}, headers=bearer).status_code == 200
    buy.refresh_from_db()
    assert (buy.state, buy.detail) == ("waiting", "waits")
    assert web.get(f"/api/sync/requests?skip={buy.pk}", headers=bearer).json() == []
    assert web.post(f"/api/sync/requests/{buy.pk}/claim", headers=bearer).status_code == 200
    assert web.post(f"/api/sync/requests/{buy.pk}/note", json={"detail": "x"}, headers=bearer).status_code == 409
    source = export_with_batch(tmp_path, {"checkout": 4, "state": "running", "read_at": "2026-10-24T13:00:00+00:00"})
    assert source.batch_run()["read_at"] == "2026-10-24T13:00:00+00:00"
    sent = {"checkout": 4, "state": "running", "read_at": "2026-10-24T13:09:00+00:00"}
    assert web.put("/api/sync/batch-run", content=json.dumps(sent), headers=bearer).status_code == 200
    assert source.batch_run() == {**sent, "machine": ""}
    assert web.put("/api/sync/batch-run", content=b"[]", headers=bearer).status_code == 400
    assert web.put("/api/sync/batch-run", content=b"{}").status_code == 401


def export_with_batch(tmp_path, run, machine="", made_at="2026-10-24T12:55:00+00:00"):
    """An export from `machine` made at `made_at` carrying the batch record `run` (None: no checkout in it)."""
    export = tmp_path / "export"
    export.mkdir(exist_ok=True)
    (export / "manifest.json").write_text(json.dumps({"made_at": made_at, "machine": machine}))
    (export / "batch-run.json").unlink(missing_ok=True)
    if run:
        (export / "batch-run.json").write_text(json.dumps(run))
    return ExportedSource(export, tmp_path / "request-files")


def test_a_moved_or_reset_store_shows_no_old_batch(settings, tmp_path):
    """Owner 2026-10-24 ("can u fix that"): the page kept the PC's batch after the move to the conductor, and a
    batch from before a store reset; a record shows only from the store's machine and of its newest checkout."""
    settings.SCORE_HOME = tmp_path
    (tmp_path / "store-machine.json").write_text(json.dumps({"name": "pc"}))
    (tmp_path / "request-files").mkdir()
    pushed = tmp_path / "request-files" / "batch-run.json"
    pushed.write_text(json.dumps({"checkout": 4, "state": "finished", "read_at": "2026-10-24T22:22:00+00:00",
                                  "machine": "pc"}))
    assert export_with_batch(tmp_path, None, "pc", "2026-10-24T22:00:00+00:00").batch_run()["checkout"] == 4  # a Buy since
    assert export_with_batch(tmp_path, None, "pc", "2026-10-24T22:30:00+00:00").batch_run() is None  # reset: no checkout
    assert export_with_batch(tmp_path, {"checkout": 4, "read_at": "2026-10-24T22:10:00+00:00"}, "pc",
                    "2026-10-24T22:30:00+00:00").batch_run()["read_at"] == "2026-10-24T22:22:00+00:00"
    (tmp_path / "store-machine.json").write_text(json.dumps({"name": "conductor", "before": "pc"}))
    assert export_with_batch(tmp_path, None, "conductor", "2026-10-24T22:00:00+00:00").batch_run() is None  # the PC's
    assert export_with_batch(tmp_path, {"checkout": 4, "read_at": "2026-10-24T22:10:00+00:00"}, "pc").batch_run() is None
    pushed.write_text(json.dumps({"checkout": 4, "state": "finished", "read_at": "2026-10-24T22:22:00+00:00"}))
    assert export_with_batch(tmp_path, None, "conductor", "2026-10-24T22:00:00+00:00").batch_run() is None  # whose unknown


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


def test_a_release_pins_the_pushed_head_in_one_commit_of_the_hosts_style(repositories, tmp_path):
    score, host, first = repositories
    head = git(score, "git", "rev-parse", "HEAD")
    asked = []
    said = release.release(score, host, DOCKERFILE, SUBJECT, trailers=[TRAILER],
                           door=lambda repo, command: asked.append((repo, command)) or (0, "update: moved"))
    assert f"moved from score {first[:8]} to {head[:8]}" in said, said
    assert asked == [(score, f"release-pin {head} {first}")] and said.endswith("; the conductor: update: moved"), said
    assert "NOT moved (door exit 1: no door)" in release.conductor_moved(score, head, first, lambda *_: (1, "no door"))
    git(host, "git", "fetch", "-q", "origin", "main")
    pinned = git(host, "git", "show", f"FETCH_HEAD:{DOCKERFILE}")
    assert pinned == f"FROM x\nARG SCORE_COMMIT={head}\nRUN y"
    words = git(host, "git", "log", "-1", "--format=%B", "FETCH_HEAD")
    subject, body, trailer = words.split("\n\n")
    assert subject == f"dashboards: the cockpit at score {head[:8]} (#1)" and trailer == TRAILER
    assert body == f"{head[:8]} " + ("dashboard: the second, a subject " + "long " * 30)[:release.SUBJECT_WIDTH]
    assert git(host, "git", "worktree", "list").count("\n") == 0  # its own worktree is gone
    assert "already pins" in release.release(score, host, DOCKERFILE, SUBJECT)


def test_a_release_refuses_a_commit_not_pushed_or_a_checkout_with_changes(repositories):
    score, host, _ = repositories
    (score / "score/dashboard/a.py").write_text("a = 3\n")
    with pytest.raises(release.Refused, match="has changes not committed"):
        release.release(score, host, DOCKERFILE, SUBJECT)
    local = committed(score, "score/dashboard/a.py", "a = 3\n", "dashboard: not pushed")
    for commit in (None, local):
        with pytest.raises(release.Refused, match="is not on origin's main: push it first"):
            release.release(score, host, DOCKERFILE, SUBJECT, commit)
    assert "ARG SCORE_COMMIT=" in (host / DOCKERFILE).read_text()


def test_a_release_refuses_a_dockerfile_path_outside_the_host_and_keeps_other_braces(repositories):
    score, host, _ = repositories
    for path in (str(host / DOCKERFILE), "../host/" + DOCKERFILE):
        with pytest.raises(release.Refused, match="inside the host's repository"):
            release.release(score, host, path, SUBJECT)
    release.release(score, host, DOCKERFILE, "cockpit {short} {not a slot}")
    git(host, "git", "fetch", "-q", "origin", "main")
    assert git(host, "git", "log", "-1", "--format=%s", "FETCH_HEAD").endswith(" {not a slot}")


def test_a_dockerfile_must_pin_exactly_one_commit():
    for text in ("FROM x\n", "ARG SCORE_COMMIT=" + "a" * 40 + "\nARG SCORE_COMMIT=" + "b" * 40 + "\n"):
        with pytest.raises(release.Refused, match="expected one"):
            release.pinned(text)
    assert release.repinned("ARG SCORE_COMMIT=" + "a" * 40 + "\n", "c" * 40) == "ARG SCORE_COMMIT=" + "c" * 40 + "\n"


def an_env_file(tmp_path, reader=True):
    path = tmp_path / "sync.env"
    script = tmp_path / "read-secret"
    script.write_text("#!/bin/sh\necho token\n")
    script.chmod(0o755)
    path.write_text("SCORE_SYNC_URL=https://cockpit.test\n" + (f"SCORE_SECRET_READER={script}\n" if reader else ""))
    return path


def test_the_install_refuses_an_env_file_without_its_url_or_reader_and_a_cockpit_on_another_dashboard(
        repositories, tmp_path, monkeypatch):
    score, host, _ = repositories
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    assert timer.env_refusal(tmp_path / "none.env") == f"no env file at {tmp_path / 'none.env'}"
    assert "SCORE_SECRET_READER" in timer.env_refusal(an_env_file(tmp_path, reader=False))
    with pytest.raises(release.Refused, match="whose dashboard is not this checkout's: release this commit first"):
        timer.install(score, an_env_file(tmp_path), host, DOCKERFILE, systemctl=lambda *args: None)
    assert not (tmp_path / "config").exists()  # nothing written


def test_the_install_writes_both_units_filled_and_enables_the_timer(repositories, tmp_path, monkeypatch):
    score, host, _ = repositories
    release.release(score, host, DOCKERFILE, SUBJECT)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    called = []
    timer.install(score, an_env_file(tmp_path), host, DOCKERFILE, systemctl=lambda *args: called.append(args))
    assert called == [("daemon-reload",), ("enable", "--now", "score-sync.timer", "score-listen.service"),
                      ("restart", "score-listen.service")]
    listener = (tmp_path / "config/systemd/user/score-listen.service").read_text()
    assert "<" not in "".join(line for line in listener.splitlines() if not line.startswith("#"))
    service = (tmp_path / "config/systemd/user/score-sync.service").read_text()
    lines = [line for line in service.splitlines() if not line.startswith("#")]
    assert not any("<" in line for line in lines), lines  # every slot filled
    assert f"EnvironmentFile={tmp_path / 'sync.env'}" in lines and f"WorkingDirectory={score}" in lines
    start = next(line for line in lines if line.startswith("ExecStart="))
    assert '"$$SCORE_SECRET_READER" "score-cockpit-sync-token"' in start


def test_a_quoted_reader_is_read_as_systemd_reads_it_and_a_failed_user_manager_is_said(repositories, tmp_path,
                                                                                         monkeypatch):
    score, host, _ = repositories
    release.release(score, host, DOCKERFILE, SUBJECT)
    env = an_env_file(tmp_path)
    env.write_text(env.read_text().replace("SCORE_SECRET_READER=", 'SCORE_SECRET_READER="').replace(
        "read-secret\n", 'read-secret"\n'))
    assert timer.env_refusal(env) is None
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    with pytest.raises(release.Refused, match="systemctl --user daemon-reload failed: no user manager"):
        timer.install(score, env, host, DOCKERFILE, systemctl=lambda *args: "no user manager")


def test_the_units_render_for_the_conductors_user_and_no_pull_runs_the_update_in_the_pulls_place():
    """On the conductor the same templates fill in for user score; --no-pull puts the conductor's update in place of
    the sync unit's pull before each pass (so every pass starts on the cockpit's pin) and changes nothing else."""
    repo, env = "/home/score/projects/score", "/home/score/.config/score/dashboard.env"
    pulled = timer.unit_text("score-sync.service", repo, env, timer.SECRET).splitlines()
    unpulled = timer.unit_text("score-sync.service", repo, env, timer.SECRET, pull=False).splitlines()
    pull = f"ExecStartPre=/usr/bin/git -C {repo} pull -q --ff-only"
    update = f"ExecStartPre=/usr/bin/python3 -I {repo}/tools/cloud/conductor/update.py --repo {repo}"
    assert pull in pulled and update not in pulled
    assert [update if line == pull else line for line in pulled] == unpulled
    lines = [line for line in unpulled if not line.startswith("#")]
    assert not any("<" in line for line in lines) and not any("/home/dupe" in line for line in unpulled)
    assert f"WorkingDirectory={repo}" in lines and f"EnvironmentFile={env}" in lines
    assert any(line.startswith("ExecStart=") and f'"{repo}/.venv/bin/python" -m score.dashboard sync' in line
               for line in lines)
    listener = timer.unit_text("score-listen.service", repo, env, timer.SECRET, pull=False)
    assert f"WorkingDirectory={repo}" in listener and "WSL" not in listener


class Pin:
    """A urlopen stand-in for the cockpit's /api/sync/pin; what it was asked, with the token it was given."""

    def __init__(self, commit):
        self.body = json.dumps({"commit": commit}).encode()
        self.asked = []

    def __call__(self, request, timeout):
        self.asked.append((request.full_url, request.get_header("Authorization")))
        return io.BytesIO(self.body)


def test_without_a_host_the_install_checks_the_commit_the_cockpits_pin_reports(repositories, tmp_path, monkeypatch):
    """Not /healthz: the hosting proxy answers that with a body of its own, so it never names the commit."""
    score, _, first = repositories
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    for commit, why in ((None, "reports no commit"), (first, "whose dashboard is not this checkout's")):
        with pytest.raises(release.Refused, match=why):
            timer.install(score, an_env_file(tmp_path), systemctl=lambda *args: None, opener=Pin(commit))
    assert not (tmp_path / "config").exists()  # nothing written
    cockpit = Pin(git(score, "git", "rev-parse", "HEAD"))
    said = timer.install(score, an_env_file(tmp_path), systemctl=lambda *args: None, pull=False, opener=cockpit)
    assert cockpit.asked == [("https://cockpit.test/api/sync/pin", "Bearer token")]
    assert "no pull before a pass" in said
    service = (tmp_path / "config/systemd/user/score-sync.service").read_text()
    assert "\nExecStartPre=/usr/bin/git" not in service and f"WorkingDirectory={score}" in service
    assert f"\nExecStartPre=/usr/bin/python3 -I {score}/tools/cloud/conductor/update.py --repo {score}\n" in service


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
print(json.dumps({"codes": codes, "heavy": heavy, "rss_mb": rss}))
"""


WALK = """
import importlib, json, pkgutil, sys
sys.path.insert(0, sys.argv[1])
import django
django.setup()
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
print(json.dumps(missing))
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


# owner rule: hosted mode never imports score.stages, score.store, numpy or usd-core (dashboard overlay); the pages
# render from the hosted image's files alone (2026-10-26: a top-level score.graph import crash-looped the image)
def test_hosted_renders_every_page_light(world, tmp_path):
    home = tmp_path / "hosted"
    exported(world, home / "export" / "one")
    (home / "export" / "current").symlink_to("one")
    done = subprocess.run([sys.executable, "-I", "-c", CHILD, str(hosted_tree(tmp_path))], env=hosted_env(home),
                          cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-3000:]
    found = json.loads(done.stdout.strip().splitlines()[-1])
    assert set(found["codes"].values()) == {200}, found["codes"]
    assert found["heavy"] == [], found["heavy"]
    assert found["rss_mb"] < MOST_MB, found["rss_mb"]


def test_every_module_the_hosted_image_holds_imports_from_it_alone(tmp_path):
    """Every dashboard module but the store-side ones imports in the hosted tree alone, so none the hosted process
    may load reaches score.graph, score.conductor or anything else the image lacks."""
    tree, home = hosted_tree(tmp_path), tmp_path / "hosted"
    home.mkdir()
    done = subprocess.run([sys.executable, "-I", "-c", WALK, str(tree), json.dumps(sorted(STORE_SIDE))],
                          env=hosted_env(home), cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-3000:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {}
