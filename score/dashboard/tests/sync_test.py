"""Hosted mode: the export built from the fixture (its files, its cap, the same twice, thumbnails before films), the
content-addressed upload (the token, path, name, offset and hash checks, two passes that send only what is lacking and
swap the export in whole, unused files swept), a request's round trip, a decision from someone not the local owner
refused, and the hosted pages drawn from the export with its time shown."""
import gzip
import hashlib
import io
import json
import os
import shutil
import threading
import urllib.error

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from fastapi.testclient import TestClient

from score.dashboard.pages.models import SyncRequest
from score.dashboard.state.exported import ExportedSource
from score.dashboard.state import versions
from score.dashboard.state.models import Spend
from score.dashboard.sync import applying, building, client

pytestmark = pytest.mark.django_db(transaction=True)
TOKEN = "t" * 40
MADE = "2026-10-18T12:00:00+00:00"
SPEND = Spend(spent=100.0, reserved=10.0, ceiling=250.0, as_of=MADE)
PRICED = "priced by the runner: EUR 1.00 to 2.00 measured, 3 paid steps with no measured price"


def offline(monkeypatch):
    """Prepare, the library's pictures and the plans kept as lines, so no test pass reads the real library, fetches
    a picture or writes a plan where the plan stage reads it."""
    monkeypatch.setattr(client, "plans_kept", lambda: "plans for the plan stage: test")
    monkeypatch.setattr(client, "remake_prepared", lambda: "remake batch (estimate): test")
    monkeypatch.setattr(client, "library_pictures", lambda: "library pictures: test")
    monkeypatch.setattr(client, "library_demos", lambda: "library demos: test")


def fed(monkeypatch):
    """A clean checkout origin's main holds, and the runner's price made: [the environments priced]."""
    priced = []
    offline(monkeypatch)
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    monkeypatch.setattr(client, "runner_price", lambda repo, environment: priced.append(environment) or (PRICED, None))
    return priced


def exported(world, folder, cap_mb=50):
    return building.build(world.source, folder, MADE, cap_mb, SPEND, world.root)


def test_the_export_holds_the_state_places_pictures_and_films(world, tmp_path):
    manifest = exported(world, tmp_path / "one")
    names = {path.name for path in (tmp_path / "one/files").iterdir()}
    assert manifest["made_at"] == MADE and manifest["left_out"] == []
    assert {"state.json", "manifest.json"} <= {path.name for path in (tmp_path / "one").iterdir()}
    assert {"alpha.json", "beta.json", "_world.json"} <= {path.name for path in (tmp_path / "one/places").iterdir()}
    assert any(name.endswith(".mp4") for name in names) and any(name.endswith("-1280.jpg") for name in names)
    assert any(name.endswith("-360.jpg") for name in names)
    source = ExportedSource(tmp_path / "one")
    assert source.places() == ["alpha", "beta"]
    assert source.step_detail("alpha", "closeup").waiting is not None


def test_the_export_holds_each_gaps_picture_and_each_steps_own_picture(world, tmp_path):
    exported(world, tmp_path / "one")
    bundle = json.loads((tmp_path / "one/places/beta.json").read_text())
    gap = bundle["detail"]["accepted_gaps"][0]["picture"]["sha"]
    step = bundle["steps"]["assembly"]["picture"]["sha"]
    assert (tmp_path / f"one/files/{gap}-1280.jpg").is_file() and (tmp_path / f"one/files/{step}-360.jpg").is_file()


def test_the_export_writes_state_then_thumbnails_then_films_then_each_steps_large_picture(world, tmp_path):
    written = exported(world, tmp_path / "one")["written"]
    bundle = json.loads((tmp_path / "one/places/alpha.json").read_text())
    step = bundle["steps"]["closeup"]["picture"]["sha"]
    assert f"files/{step}-1280.jpg" in written
    thumbs = [index for index, path in enumerate(written) if path.endswith("-360.jpg")]
    films = [index for index, path in enumerate(written) if path.endswith(".mp4")]
    assert thumbs and films and max(thumbs) < min(films)
    assert written.index(f"files/{step}-1280.jpg") > max(films)
    assert written[0] == "state.json"


def test_the_export_is_the_same_twice_and_keeps_to_its_cap(world, tmp_path):
    exported(world, tmp_path / "one")
    exported(world, tmp_path / "two")
    for path in sorted((tmp_path / "one").rglob("*")):
        if path.is_file() and path.name != "machine.json":  # the machine's health is a live read: load, memory
            assert path.read_bytes() == (tmp_path / "two" / path.relative_to(tmp_path / "one")).read_bytes(), path
    machines = [json.loads((tmp_path / name / "machine.json").read_text())["machine"] for name in ("one", "two")]
    assert machines[0] == machines[1]
    small = exported(world, tmp_path / "small", cap_mb=0.02)
    assert small["left_out"] and all(entry["why"] == "over the export's cap" for entry in small["left_out"])


def hosted_client():
    from score.dashboard.site.asgi import app
    return TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))


class Answer:
    """A urlopen answer from a TestClient response."""

    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def opener_of(web):
    """A urlopen stand-in that sends client.Remote's requests to the hosted app in this process, one at a time: the
    test database is SQLite in memory with a shared cache, where a second writer is refused at once ("database table
    is locked") instead of waiting out the busy timeout as the hosted side's file database does, so the listener's
    side-by-side answers (listen.round_once) write to it in turn."""
    one_at_a_time = threading.Lock()

    def opened(request, timeout):
        path = request.full_url.removeprefix("http://hosted")
        with one_at_a_time:
            answer = web.request(request.get_method(), path, content=request.data,
                                 headers=dict(request.header_items()))
        if answer.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, answer.status_code, answer.text, {},
                                         io.BytesIO(answer.content))
        return Answer(answer.content)
    return opened


def remote_of(web):
    return client.Remote("http://hosted", TOKEN, opener_of(web))


def sha_of(data):
    return hashlib.sha256(data).hexdigest()


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_every_sync_route_needs_the_token():
    web, sha = hosted_client(), sha_of(b"x")
    for wrong in ({}, {"Authorization": "Bearer wrong"}):
        assert web.post("/api/sync/lacking", json={"files": {sha: 1}}, headers=wrong).status_code == 401
        assert web.put(f"/api/sync/blobs/{sha}?offset=0&size=1", content=gzip.compress(b"x"),
                       headers=wrong).status_code == 401
        assert web.post("/api/sync/commit", json={"name": "n", "files": {}}, headers=wrong).status_code == 401
        assert web.get("/api/sync/pin", headers=wrong).status_code == 401


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN, SCORE_COMMIT="a" * 40)
def test_the_pin_tells_the_store_s_machine_the_commit_the_cockpit_runs():
    """/healthz's body is the hosting proxy's own, so the pin comes from here, behind the token."""
    answer = hosted_client().get("/api/sync/pin", headers={"Authorization": f"Bearer {TOKEN}"})
    assert answer.status_code == 200 and answer.json() == {"commit": "a" * 40}


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_a_bad_sha_path_or_name_is_refused(settings):
    web, bearer = hosted_client(), {"Authorization": f"Bearer {TOKEN}"}
    assert web.post("/api/sync/lacking", json={"files": {"../etc": 1}}, headers=bearer).status_code == 400
    sha = sha_of(b"{}")
    assert web.put(f"/api/sync/blobs/{sha}?offset=0&size=2", content=gzip.compress(b"{}"),
                   headers=bearer).json()["done"]
    for path in ("../x", "/abs", "a//b", "a\\b"):
        files = {"manifest.json": sha, path: sha}
        assert web.post("/api/sync/commit", json={"name": "one", "files": files}, headers=bearer).status_code == 400
    for name in ("current", "x.partial", "a/b", ""):
        answer = web.post("/api/sync/commit", json={"name": name, "files": {"manifest.json": sha}}, headers=bearer)
        assert answer.status_code == 400, name
    assert web.post("/api/sync/commit", json={"name": "one", "files": {"state.json": sha}},
                    headers=bearer).status_code == 400
    assert not (settings.SCORE_HOME / "export/current").exists()


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_a_chunk_at_the_wrong_offset_is_told_where_to_go_on_and_a_wrong_hash_is_refused(settings):
    web, bearer = hosted_client(), {"Authorization": f"Bearer {TOKEN}"}
    data = b"abcdefgh"
    sha = sha_of(data)
    assert web.put(f"/api/sync/blobs/{sha}?offset=0&size=8", content=gzip.compress(data[:3]),
                   headers=bearer).json() == {"have": 3, "done": False}
    answer = web.put(f"/api/sync/blobs/{sha}?offset=6&size=8", content=gzip.compress(data[6:]), headers=bearer)
    assert answer.status_code == 409 and answer.json() == {"have": 3}
    assert web.put(f"/api/sync/blobs/{sha}?offset=3&size=8", content=gzip.compress(data[3:]),
                   headers=bearer).json() == {"have": 8, "done": True}
    assert (settings.SCORE_HOME / "blobs" / sha).read_bytes() == data
    liar = sha_of(b"something else")
    answer = web.put(f"/api/sync/blobs/{liar}?offset=0&size=8", content=gzip.compress(data), headers=bearer)
    assert answer.status_code == 400 and not (settings.SCORE_HOME / "blobs" / liar).exists()
    assert not (settings.SCORE_HOME / "blobs" / f"{liar}.part").exists()
    past = web.put(f"/api/sync/blobs/{liar}?offset=0&size=2", content=gzip.compress(data), headers=bearer)
    assert past.status_code == 400


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_two_passes_send_only_what_is_lacking_and_swap_the_export_in_whole(world, settings, monkeypatch):
    from score.dashboard.tests.fixture import FakeBackend
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
    from score.dashboard.tests.fixture import FakeBackend
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
def test_a_file_no_kept_export_uses_is_swept(settings):
    web, bearer = hosted_client(), {"Authorization": f"Bearer {TOKEN}"}
    blobs = settings.SCORE_HOME / "blobs"
    for made, data in (("a", b"{\"made_at\": \"a\", \"format\": 3}"), ("b", b"{\"made_at\": \"b\", \"format\": 3}"),
                       ("c", b"{\"made_at\": \"c\", \"format\": 3}")):
        sha = sha_of(data)
        web.put(f"/api/sync/blobs/{sha}?offset=0&size={len(data)}", content=gzip.compress(data), headers=bearer)
        answer = web.post("/api/sync/commit", json={"name": made, "files": {"manifest.json": sha}}, headers=bearer)
        assert answer.status_code == 200, answer.text
    assert not (blobs / sha_of(b'{"made_at": "a", "format": 3}')).exists()
    assert (blobs / sha_of(b'{"made_at": "b", "format": 3}')).exists()
    assert (blobs / sha_of(b'{"made_at": "c", "format": 3}')).exists()


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_a_change_to_the_exporting_code_sends_every_bundle_again(world, settings, monkeypatch):
    from score.dashboard.tests.fixture import FakeBackend
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
    from score.dashboard.tests.fixture import FakeBackend
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)
    monkeypatch.setattr(versions, "FORMAT", 1)  # an old store side: gaps and stops as words
    fed(monkeypatch)
    said = client.sync_pass(remote_of(hosted_client()), world.source, FakeBackend())
    assert said.startswith("REFUSED") and "export format 1 cannot be read here" in said, said
    assert not (settings.SCORE_HOME / "export/current").exists()


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_a_request_round_trip():
    request = SyncRequest.objects.create(kind="change", user="joey", payload={"stage": "closeup", "words": "redder"})
    web, bearer = hosted_client(), {"Authorization": f"Bearer {TOKEN}"}
    waiting = web.get("/api/sync/requests?state=waiting", headers=bearer).json()
    assert [item["id"] for item in waiting] == [request.pk]
    for step in ("picked_up", "running", "done"):
        assert web.post(f"/api/sync/requests/{request.pk}", json={"state": step}, headers=bearer).status_code == 200
    request.refresh_from_db()
    assert request.state == "done"
    assert web.post(f"/api/sync/requests/{request.pk}", json={"state": "nonsense"}, headers=bearer).status_code == 422
    assert web.get("/api/sync/requests?state=done", headers={"Authorization": "Bearer x"}).status_code == 401


def test_a_decision_from_someone_not_the_local_owner_is_refused(world):
    applied = applying.apply({"kind": "decision", "user": "mallory", "payload": {
        "node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}},
        world.source)
    assert applied.state == "refused" and "not this store's owner" in applied.detail
    applied = applying.apply({"kind": "decision", "user": "joey", "payload": {
        "node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept",
        "worse_reason": "fine"}}, world.source)
    assert applied.state == "done", applied.detail


def owner_figures(world):
    """One request of each owner's money figure and waiver kind, by user name: {kind: payload}."""
    return {"books-figure": {"euros": 12.5},
            "waiver": {"node": "closeup@beta", "output": world.outputs["closeup@beta"], "check": "looks",
                       "reason": "three faults are fine here"}}


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


def test_the_owners_figures_and_waiver_are_applied_for_him_and_refused_for_anyone_else(owner_books):
    """Each owner request kind from the cockpit's buttons: someone not the local owner writes nothing; the owner's
    goes through the same owner-only function as his local cockpit, recorded with his name; no request sets a stop
    (a batch's stop is written by his checkout's yes)."""
    from score.review import web
    world = owner_books
    key = world.store.records("closeup@beta")[-1]["key"]
    for kind, payload in owner_figures(world).items():
        applied = applying.apply({"kind": kind, "user": "mallory", "payload": payload}, world.source)
        assert applied.state == "refused" and "not this store's owner" in applied.detail, (kind, applied)
    assert not world.books.exists() and not world.store.waivers("closeup@beta", key)
    for kind, payload in owner_figures(world).items():
        applied = applying.apply({"kind": kind, "user": "joey", "payload": payload}, world.source)
        assert applied.state == "done", (kind, applied)
    assert web.stop_line(world.store, "world1") is None
    for kind in ("stop", "month"):
        assert applying.apply({"kind": kind, "user": "joey", "payload": {"euros": 40.0}}, world.source).state == \
            "refused"
    books = json.loads(world.books.read_text())
    assert books["google_before"] == 12.5 and books["google_by"] == "joey" and books["state"] == "known"
    assert world.store.waivers("closeup@beta", key)["looks"]["by"] == "joey"


def test_the_owners_figures_are_refused_in_an_agents_process(owner_books, monkeypatch):
    """The sync pass applies an owner request only outside an agent's process: the same barrier as his terminal."""
    from score.dashboard.pages import actions
    from score.review import web
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    for kind in ("books-figure", "waiver"):
        applied = applying.apply({"kind": kind, "user": "joey", "payload": owner_figures(owner_books)[kind]},
                                 owner_books.source)
        assert applied.state == "refused", (kind, applied)
    assert web.stop_line(owner_books.store, "world1") is None


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


def test_a_change_request_is_applied_into_the_inbox(world, settings):
    applied = applying.apply({"kind": "change", "user": "joey", "payload": {
        "place": "alpha", "stage": "closeup", "words": "redder"}}, world.source)
    assert applied.state == "done" and list((settings.SCORE_HOME / "inbox").glob("*.json"))


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
    from score.dashboard.tests.fixture import FakeBackend
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
    assert said.endswith(f"{PRICED}; plans for the plan stage: test; remake batch (estimate): test; benchmarks: none listed; basket made: 0 items, 0 paid steps; library pictures: test; library demos: test")
    assert "checkouts: 0 left launching failed, 0 ended batches' lines taken back" in said
    assert priced == [world.source.world.name]
    assert hosted.reports == [(7, "picked_up"), (7, "done"), (8, "picked_up"), (8, "refused")]


def test_each_pass_makes_the_basket_again_from_the_runners_plan_in_this_checkout(world, monkeypatch, settings):
    """A basket an agent's worktree made yesterday (a scene merged away since, none of today's rows) is replaced by
    the runner's plan of today, made here, when and on which commit said: what the checkout reads."""
    from score.dashboard.proposals import make, records
    from score.dashboard.tests.fixture import FakeBackend
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
    from score.dashboard.tests.fixture import FakeBackend
    fed(monkeypatch)
    commits = iter(["a" * 40, "b" * 40])
    monkeypatch.setattr(client, "head", lambda repo: next(commits))
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}}])
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert "the checkout moved from aaaaaaaa to bbbbbbbb during the pass" in said and "Buy waits" in said, said
    assert hosted.commits and hosted.reports == [(7, "picked_up"), (7, "done")]  # pushed, his requests applied


def test_a_pass_syncs_nothing_from_a_checkout_not_clean_and_pushed_or_when_the_price_fails(world, monkeypatch):
    from score.dashboard.tests.fixture import FakeBackend
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}}])
    offline(monkeypatch)
    monkeypatch.setattr(client, "tree_refusal", lambda repo: "commit 0123abcd is not on origin's main: push it first")
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert said == "REFUSED: nothing synced: commit 0123abcd is not on origin's main: push it first"
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    monkeypatch.setattr(client, "runner_price", lambda repo, environment: (None, "the runner's price failed: exit 1"))
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert said.startswith("REFUSED: nothing synced: the runner's price failed: exit 1; ") and "gaps" in said
    assert said.endswith("; remake batch (estimate): test; benchmarks: none listed; library pictures: test; library demos: test")
    assert hosted.commits == [] and hosted.chunks == [] and hosted.reports == []


def a_checkout(tmp_path):
    """A clone of a bare origin with one commit pushed to its main: (origin, clone)."""
    import subprocess

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
    import subprocess
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
