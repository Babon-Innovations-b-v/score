"""The listener's hosted Buy and its run monitor record (sync/listen.py, owner 2026-10-24: "can we make that delay
less for the following runs"): a Buy applied within a round through the same checkout and followed to its end, one
whose price needs a fresh pass said so on the request and left waiting for the pass (never claimed, never asked
again), the figures' checks against the code, the batch record sent while a batch lives and once as it ends, and the
hosted side's note, skip and batch record served newer than the export's."""
import json
import types

import pytest
from fastapi.testclient import TestClient

from score.dashboard.pages.models import SyncRequest
from score.dashboard.proposals import records
from score.dashboard.state import local
from score.dashboard.state.exported import ExportedSource
from score.dashboard.sync import applying, client, listen

pytestmark = pytest.mark.django_db(transaction=True)
TOKEN = "t" * 40
BUY = {"id": 5, "kind": "checkout", "user": "joey", "payload": {"key": "k", "items": []}}


class Hosted:
    """The hosted side in memory: the waiting requests, what was claimed, noted, reported and sent."""
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
    hosted = Hosted([BUY])
    assert listen.round_once(hosted, None) == [(5, "running")]
    assert hosted.claims == [5] and hosted.reports == [(5, "running")] and client.tracked() == {"5": 9}


def test_a_buy_whose_price_needs_a_pass_is_said_so_and_left_waiting_for_it(monkeypatch):
    monkeypatch.setattr(client, "buy_waits", lambda source: "the basket was made on commit aaaaaaaa")
    hosted, left = Hosted([BUY]), set()
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
    hosted, busy, left = Hosted([draw]), set(), set()
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
    hosted, source, live = Hosted([]), Source(), False
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
    source = exported(tmp_path, {"checkout": 4, "state": "running", "read_at": "2026-10-24T13:00:00+00:00"})
    assert source.batch_run()["read_at"] == "2026-10-24T13:00:00+00:00"
    sent = {"checkout": 4, "state": "running", "read_at": "2026-10-24T13:09:00+00:00"}
    assert web.put("/api/sync/batch-run", content=json.dumps(sent), headers=bearer).status_code == 200
    assert source.batch_run() == {**sent, "machine": ""}
    assert web.put("/api/sync/batch-run", content=b"[]", headers=bearer).status_code == 400
    assert web.put("/api/sync/batch-run", content=b"{}").status_code == 401


def exported(tmp_path, run, machine="", made_at="2026-10-24T12:55:00+00:00"):
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
    assert exported(tmp_path, None, "pc", "2026-10-24T22:00:00+00:00").batch_run()["checkout"] == 4  # a Buy since
    assert exported(tmp_path, None, "pc", "2026-10-24T22:30:00+00:00").batch_run() is None  # reset: no checkout
    assert exported(tmp_path, {"checkout": 4, "read_at": "2026-10-24T22:10:00+00:00"}, "pc",
                    "2026-10-24T22:30:00+00:00").batch_run()["read_at"] == "2026-10-24T22:22:00+00:00"
    (tmp_path / "store-machine.json").write_text(json.dumps({"name": "conductor", "before": "pc"}))
    assert exported(tmp_path, None, "conductor", "2026-10-24T22:00:00+00:00").batch_run() is None  # the PC's
    assert exported(tmp_path, {"checkout": 4, "read_at": "2026-10-24T22:10:00+00:00"}, "pc").batch_run() is None
    pushed.write_text(json.dumps({"checkout": 4, "state": "finished", "read_at": "2026-10-24T22:22:00+00:00"}))
    assert exported(tmp_path, None, "conductor", "2026-10-24T22:00:00+00:00").batch_run() is None  # whose unknown
