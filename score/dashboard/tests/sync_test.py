"""Hosted mode: the export built from the fixture (its files, its cap, the same twice), the upload's token and tar
checks, the atomic swap, a request's round trip, a decision from someone not the local owner refused, and the hosted
pages drawn from the export with its time shown."""
import io
import json
import tarfile

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from fastapi.testclient import TestClient

from score.dashboard.pages.models import SyncRequest
from score.dashboard.state.exported import ExportedSource
from score.dashboard.state.models import Spend
from score.dashboard.sync import applying, building, client

pytestmark = pytest.mark.django_db(transaction=True)
TOKEN = "t" * 40
MADE = "2026-10-18T12:00:00+00:00"
SPEND = Spend(spent=100.0, reserved=10.0, ceiling=250.0, as_of=MADE)


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


def test_the_export_is_the_same_twice_and_keeps_to_its_cap(world, tmp_path):
    exported(world, tmp_path / "one")
    exported(world, tmp_path / "two")
    for path in sorted((tmp_path / "one").rglob("*")):
        if path.is_file():
            assert path.read_bytes() == (tmp_path / "two" / path.relative_to(tmp_path / "one")).read_bytes(), path
    small = exported(world, tmp_path / "small", cap_mb=0.02)
    assert small["left_out"] and all(entry["why"] == "over the export's cap" for entry in small["left_out"])


def archive(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as packed:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            if data is None:
                info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
                packed.addfile(info)
                continue
            info.size = len(data)
            packed.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def hosted_client():
    from score.dashboard.site.asgi import app
    return TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_upload_needs_the_token_and_refuses_escaping_archives(settings):
    web = hosted_client()
    good = archive({"one/manifest.json": json.dumps({"made_at": MADE}).encode()})
    assert web.put("/api/sync/export", content=good).status_code == 401
    assert web.put("/api/sync/export", content=good, headers={"Authorization": "Bearer wrong"}).status_code == 401
    bearer = {"Authorization": f"Bearer {TOKEN}"}
    assert web.put("/api/sync/export", content=archive({"../x": b"x"}), headers=bearer).status_code == 400
    assert web.put("/api/sync/export", content=archive({"/abs": b"x"}), headers=bearer).status_code == 400
    assert web.put("/api/sync/export", content=archive({"link": None}), headers=bearer).status_code == 400
    assert not (settings.SCORE_HOME / "export/current").exists()


@override_settings(SCORE_MODE="hosted", SCORE_SYNC_TOKEN=TOKEN)
def test_an_export_is_swapped_in_whole_and_two_are_kept(settings, monkeypatch):
    from score.dashboard import state
    monkeypatch.setattr(state, "source", lambda: ExportedSource(settings.SCORE_HOME / "export/current"))
    web, bearer = hosted_client(), {"Authorization": f"Bearer {TOKEN}"}
    for hour in ("10", "11", "12"):
        made = f"2026-10-18T{hour}:00:00+00:00"
        name = client.folder_name(made)
        answer = web.put("/api/sync/export", content=archive({f"{name}/manifest.json": json.dumps(
            {"made_at": made}).encode()}), headers=bearer)
        assert answer.status_code == 200, answer.text
    current = settings.SCORE_HOME / "export/current"
    assert current.is_symlink() and json.loads((current / "manifest.json").read_text())["made_at"].startswith(
        "2026-10-18T12")
    kept = [path for path in (settings.SCORE_HOME / "export").iterdir() if path.is_dir() and not path.is_symlink()]
    assert len(kept) == 2


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


def test_a_change_request_is_applied_into_the_inbox(world, settings):
    applied = applying.apply({"kind": "change", "user": "joey", "payload": {
        "place": "alpha", "stage": "closeup", "words": "redder"}}, world.source)
    assert applied.state == "done" and list((settings.SCORE_HOME / "inbox").glob("*.json"))


class Hosted:
    """A stand-in for the hosted dashboard's endpoints, in memory."""

    def __init__(self, waiting):
        self.waiting_items, self.reports, self.archives = waiting, [], []

    def put_export(self, body):
        self.archives.append(body)

    def waiting(self):
        return self.waiting_items

    def report(self, request_id, state, detail="", log_tail=""):
        self.reports.append((request_id, state))


def test_a_sync_pass_pushes_the_export_and_reports_each_request(world):
    from score.dashboard.tests.fixture import FakeBackend
    hosted = Hosted([{"id": 7, "kind": "change", "user": "joey", "payload": {"stage": "closeup", "words": "x"}},
                     {"id": 8, "kind": "decision", "user": "mallory", "payload": {
                         "node": "closeup@alpha", "output": "o", "decision": "reject"}}])
    said = client.sync_pass(hosted, world.source, FakeBackend())
    assert "pushed the export" in said and len(hosted.archives) == 1
    assert hosted.reports == [(7, "picked_up"), (7, "done"), (8, "picked_up"), (8, "refused")]


def test_hosted_pages_render_from_the_export_with_its_time(world, tmp_path, settings, monkeypatch):
    exported(world, tmp_path / "export")
    from score.dashboard import state
    source = ExportedSource(tmp_path / "export")
    monkeypatch.setattr(state, "source", lambda: source)
    settings.SCORE_MODE = "hosted"
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    pages = Client()
    pages.force_login(user)
    for page in ("/", "/place/alpha/", "/place/alpha/step/closeup/", "/world/step/terrain/", "/requests/"):
        html = pages.get(page).content.decode()
        assert "state from 2026-10-18 12:00" in html, page
    html = pages.get("/place/alpha/").content.decode()
    assert "No 3D web copy" in html and "/thumbs/" in html or "/files/" in html
    pages.post("/place/alpha/step/closeup/decide/", {"decision": "reject", "output": "x", "reason": "no"})
    assert SyncRequest.objects.filter(kind="decision").exists()
