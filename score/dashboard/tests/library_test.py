"""The Library pages read a tiny library folder (entries, an index, a blob folder): the grid by kind with its filters,
an entry's page (where it came from, its takes, its 3D view), the place page's strip, the owner's lock and withdraw
(queued when hosted, applied with the library's own command, committed and pushed, refused for anyone else and in an
agent's process), and the library in the state export, read back by a hosted cockpit."""
import hashlib
import json
import struct
import subprocess
import sys

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from fastapi.testclient import TestClient

from score.dashboard.pages import actions, library_actions
from score.dashboard.pages.models import SyncRequest
from score.dashboard.state import library as lib
from score.dashboard.state.models import Spend
from score.dashboard.sync import applying, building
from score.dashboard.tests import fixture

pytestmark = pytest.mark.django_db
MADE = "2026-10-18T12:00:00+00:00"
# The library's own lock and withdraw, as small as the test needs: the entry's state, and the index rewritten.
FAKE_COMMAND = """
import json, pathlib, sys
root = pathlib.Path.cwd()
action, addresses = sys.argv[1], sys.argv[2:]
for address in addresses:
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    path = root / "entries" / kind / entry_id / version / "entry.json"
    record = json.loads(path.read_text())
    wanted = {"lock": "draft", "withdraw": "locked", "index": None}[action]
    if record["state"] != wanted:
        sys.exit(f"{address}: is {record['state']}")
    record["state"] = "locked" if action == "lock" else "withdrawn"
    path.write_text(json.dumps(record))
(root / "index" / "catalogue.json").write_text(json.dumps({"action": action, "addresses": addresses}))
print(f"{action} {len(addresses)}")
"""


def glb():
    """A GLB of one triangle's facts: its JSON chunk, no buffers."""
    facts = json.dumps({"asset": {"version": "2.0"}, "accessors": [{"count": 3}],
                        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}).encode()
    facts += b" " * (-len(facts) % 4)
    return struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(facts)) + struct.pack("<II", len(facts), 0x4E4F534A) + facts


def stored(blobs, data):
    """Put bytes into the blob folder; their sha."""
    sha = hashlib.sha256(data).hexdigest()
    path = blobs / "blobs" / sha[:2] / sha
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha


def entry(root, blobs, kind, entry_id, state="draft", place="alpha", node="closeup@alpha", files=None, **more):
    """Write one entry.json with a picture; the record."""
    described = {"preview.png": {"role": "picture", "bytes": 1, "sha256": stored(blobs, fixture.picture())}}
    for name, (role, data) in (files or {}).items():
        described[name] = {"role": role, "bytes": len(data), "sha256": stored(blobs, data)}
    record = {"address": f"{kind}/{entry_id}@1", "id": entry_id, "kind": kind, "version": 1, "state": state,
              "title": entry_id.split(".")[0].replace("_", " ").capitalize(), "files": described,
              "picture": {"file": "preview.png"}, "licence": {"spdx": "MIT", "commercial_ok": True},
              "provenance": {"world": "world1", "place": place, "node": node, "commit": "c" * 40},
              "seen_in": [place] if place else [], "tags": {"model": ["piece"]}, "requires": [], **more}
    path = root / "entries" / kind / entry_id / "1" / "entry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    return record


@pytest.fixture
def shelf(tmp_path):
    """A tiny library in a git folder with a bare remote, and its blob folder."""
    root, blobs = tmp_path / "lib", tmp_path / "blobs"
    entry(root, blobs, "model", "lamp_post.alpha")
    entry(root, blobs, "model", "crate", state="locked", place="beta", node="assembly@beta")
    entry(root, blobs, "sound", "hum.alpha", files={"audio/hum_1.ogg": ("audio", b"OggS one"),
                                                   "audio/hum_2.ogg": ("audio", b"OggS two")})
    entry(root, blobs, "character", "walker", place=None, node="people-walker",
          files={"body.glb": ("gltf", glb())})
    entry(root, blobs, "place", "alpha", node="assembly@alpha", requires=["model/lamp_post.alpha@1"])
    (root / "index").mkdir()
    (root / "index" / "catalogue.json").write_text("{}")
    command = tmp_path / "score_lib_command.py"
    command.write_text(FAKE_COMMAND)
    run = lambda *arguments, where=root: subprocess.run(["git", "-C", str(where), *arguments], check=True,  # noqa: E731
                                                         capture_output=True)
    subprocess.run(["git", "init", "-q", "--bare", str(tmp_path / "remote.git")], check=True)
    run("init", "-q")
    run("config", "user.email", "test@example.invalid")
    run("config", "user.name", "test")
    run("add", ".")
    run("commit", "-q", "-m", "entries")
    run("remote", "add", "origin", str(tmp_path / "remote.git"))
    run("push", "-q", "-u", "origin", "HEAD")
    with override_settings(SCORE_LIB_ROOT=str(root), SCORE_LIB_BLOBS_DIR=str(blobs),
                           SCORE_LIB_COMMAND=f"{sys.executable} {command}"):
        yield root


def signed_in(name="joey"):
    client = Client()
    client.force_login(get_user_model().objects.create_user(name, password="a long enough password"))
    return client


def files_client():
    from score.dashboard.site.asgi import app
    client = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    for cookie in signed_in().cookies.values():
        client.cookies.set(cookie.key, cookie.value)
    return client


def test_the_grid_shows_every_kind_with_pictures_and_one_mit_note(world, shelf):
    html = signed_in().get("/library/").content.decode()
    for label in ("Models", "Sound", "Characters", "Places"):
        assert f"<h2>{label}</h2>" in html
    assert html.count("/library-files/thumbs/") == 5
    assert html.count(">MIT<") == 1 and "commercial" not in html.lower() and "licence" not in html.lower().replace(
        'class="licence-note"', "")
    assert 'name="address"' in html and 'value="lock"' in html  # the owner's choice and buttons


def test_the_filters_narrow_the_grid(world, shelf):
    client = signed_in()
    assert client.get("/library/?kind=model").content.decode().count("/library-files/thumbs/") == 2
    assert client.get("/library/?place=beta").content.decode().count("/library-files/thumbs/") == 1
    assert client.get("/library/?state=locked").content.decode().count("/library-files/thumbs/") == 1
    assert client.get("/library/?q=lamp").content.decode().count("/library-files/thumbs/") == 1
    assert "Nothing matches" in client.get("/library/?q=nothing+like+it").content.decode()


def test_a_visitor_has_no_owner_buttons(world, shelf):
    html = signed_in("guest").get("/library/").content.decode()
    assert 'name="address"' not in html and 'value="lock"' not in html
    assert signed_in("guest2").post("/library/ask/", {"action": "lock", "address": "model/lamp_post.alpha@1"}
                                    ).status_code == 403


def test_an_entry_page_says_what_it_is_and_where_it_came_from(world, shelf):
    html = signed_in().get("/library/model/lamp_post.alpha/1/").content.decode()
    assert "A model, made for alpha." in html
    assert 'href="/place/alpha/step/closeup/"' in html and 'href="/place/alpha/"' in html and "world1" in html
    assert "/library-files/pictures/" in html and "Lock: approve as final" in html
    assert "licence" not in html.lower() and "MIT" not in html


def test_a_sound_plays_and_a_model_with_a_glb_opens_in_3d(world, shelf):
    client = signed_in()
    sound = client.get("/library/sound/hum.alpha/1/").content.decode()
    assert sound.count("<audio") == 2 and "/library-files/files/" in sound
    walker = client.get("/library/character/walker/1/").content.decode()
    assert 'href="/library/character/walker/1/3d/"' in walker
    viewer = client.get("/library/character/walker/1/3d/").content.decode()
    assert '"base": "/library-files/view/"' in viewer
    place = client.get("/library/place/alpha/1/").content.decode()
    assert "Lamp post" in place  # what it needs, by name
    assert client.get("/library/model/crate/1/3d/").status_code == 404


@pytest.mark.django_db(transaction=True)
def test_the_file_routes_serve_only_listed_files(world, shelf):
    web = files_client()
    found = lib.library().entry("character/walker@1")
    assert web.get(f"/library-files/thumbs/{found.picture}.jpg").headers["content-type"] == "image/jpeg"
    assert web.get(f"/library-files/view/{found.glb.sha}.json").json()["triangles"] == 1
    assert web.get(f"/library-files/view/{found.glb.sha}.glb").status_code == 200
    assert web.get(f"/library-files/view/{found.glb.sha}-light.glb").status_code == 404
    assert web.get(f"/library-files/files/{'0' * 64}").status_code == 404
    assert web.get(f"/library-files/thumbs/{'0' * 64}.jpg").headers["content-type"].startswith("image/svg")


def test_the_place_page_shows_its_library_strip(world, shelf):
    html = signed_in().get("/place/alpha/").content.decode()
    assert "In the library" in html and 'href="/library/?place=alpha"' in html
    assert html.count("/library-files/thumbs/") == 3  # the lamp post, the hum and the place itself


def test_the_owner_locks_a_selection_committed_and_pushed(world, shelf):
    client = signed_in()
    answer = client.post("/library/ask/", {"action": "lock", "address": ["model/lamp_post.alpha@1", "sound/hum.alpha@1"],
                                           "back": "/library/?kind=model"}, follow=True)
    assert "locked 2 entries" in answer.content.decode()
    assert lib.library().entry("model/lamp_post.alpha@1").state == "locked"
    remote = subprocess.run(["git", "-C", str(shelf.parent / "remote.git"), "log", "-1", "--format=%s"],
                            capture_output=True, text=True).stdout
    assert remote.startswith("lock: 2 entries, the owner's decision on the cockpit")


def test_a_lock_of_a_locked_entry_or_by_an_agent_is_refused(world, shelf, monkeypatch):
    said = library_actions.ask("joey", "lock", ["model/crate@1"], hosted=False)
    assert said.startswith("refused") and "only a draft" in said
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    said = library_actions.ask("joey", "lock", ["model/lamp_post.alpha@1"], hosted=False)
    assert "an agent never locks" in said
    assert lib.library().entry("model/lamp_post.alpha@1").state == "draft"


def test_hosted_a_lock_is_queued_and_applied_by_the_owners_sync_only(world, shelf):
    said = library_actions.ask("joey", "withdraw", ["model/crate@1"], hosted=True)
    assert said.startswith("queued")
    queued = SyncRequest.objects.get(kind="library")
    assert library_actions.waiting() == {"model/crate@1": "withdraw"}
    item = {"kind": "library", "user": "mallory", "payload": queued.payload}
    assert applying.apply(item, world.source).state == "refused"
    applied = applying.apply({**item, "user": "joey"}, world.source)
    assert applied.state == "done", applied.detail
    assert lib.library().entry("model/crate@1").state == "withdrawn"


def test_the_export_carries_the_library_to_a_hosted_cockpit(world, shelf, tmp_path):
    spend = Spend(spent=1.0, reserved=0.0, ceiling=250.0)
    first = building.build(world.source, tmp_path / "home/export/one", MADE, 50, spend, world.root)
    again = building.build(world.source, tmp_path / "home/export/two", MADE, 50, spend, world.root)
    assert first["written"] == again["written"] and "library/entries.json" in first["written"]
    pictures = {entry.picture for entry in lib.library().entries()}
    assert all(f"files/{sha}-360.jpg" in first["written"] for sha in pictures)
    assert sum(path.startswith("library/files/") for path in first["written"]) == 2  # the two takes
    (tmp_path / "home/export/current").symlink_to("one")
    with override_settings(SCORE_MODE="hosted", SCORE_HOME=tmp_path / "home", SCORE_LIB_ROOT=None):
        hosted = lib.library()
        assert isinstance(hosted, lib.ExportedLibrary) and len(hosted.entries()) == 5
        assert hosted.picture_path(next(iter(pictures)), 360) is not None
        html = signed_in().get("/library/sound/hum.alpha/1/").content.decode()
        assert html.count("<audio") == 2 and "3d/" not in html
