"""The Library screen reads a tiny library folder (entries, an index, a blob folder): the tree of kinds with counts,
a branch's children only when it opens, a page at a time, an item's page (picture, version, score, files, 3D), the
owner's lock and withdraw (queued when hosted, applied with the library's own command, committed and pushed, refused
for anyone else and in an agent's process), refine items into the basket, and the library in the state export, read
back by a hosted cockpit that imports nothing its image lacks."""
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from fastapi.testclient import TestClient

from score.dashboard.pages import actions, library_actions
from score.dashboard.pages import library as pages_library
from score.dashboard.pages.models import RefineItem, SyncRequest
from score.dashboard.state import library as lib
from score.dashboard.state.library_tree import folders
from score.dashboard.state.models import Spend
from score.dashboard.sync import applying, building
from score.dashboard.tests import fixture
from score.dashboard.tests.pages_test import WORD_BUDGET, prose

pytestmark = pytest.mark.django_db(transaction=True)
ORIGIN = "http://127.0.0.1:8780"
REPO = pathlib.Path(__file__).resolve().parents[3]
MATERIAL = b"""#usda 1.0
def Material "steel" { def Shader "surface" {
    color3f inputs:diffuseColor = (0.5, 0.25, 0.125)
    float inputs:metallic = 1
    float inputs:roughness = 0.35
} }"""
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
    record = {"schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "id": entry_id, "kind": kind, "version": 1, "state": state,
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
    entry(root, blobs, "model", "lamp_post.alpha", files={"web/lamp_post.glb": ("web3d", glb())},
          web3d={"file": "web/lamp_post.glb"}, score=42, score_parts=[{"name": "shape", "value": 30, "how": "edges"},
                                             {"name": "likeness", "value": None, "how": "needs a paid judge"}],
          refine_options=["remesh", {"id": "repaint", "label": "paint it again"}])
    entry(root, blobs, "model", "crate", state="locked", place="beta", node="assembly@beta", score=0.91,
          score_parts={"finish": 0.6})
    entry(root, blobs, "model", "wrench", tags={"model": ["prop"]})
    entry(root, blobs, "surface", "brushed_steel.alpha", node=None,
          tags={"family": ["steel"], "recipe": ["bare_metal"]},
          files={"material.usda": ("usd", MATERIAL)})
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


def api(name="joey"):
    """A FastAPI test client with a signed-in session and its CSRF cookie and header (the page's own fetch)."""
    from score.dashboard.site.asgi import app
    pages = signed_in(name)
    pages.get("/library/")  # sets the csrftoken cookie
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        client.cookies.set(cookie.key, cookie.value)
    client.headers.update({"X-CSRFToken": pages.cookies["csrftoken"].value, "Origin": ORIGIN})
    return client


def node_of(tree, node_id):
    """A tree node by id, searched depth first."""
    for node in tree:
        if node["id"] == node_id:
            return node
        found = node_of(node["children"], node_id)
        if found:
            return found
    return None


def test_the_screen_is_the_tree_of_kinds_with_counts_and_no_entry_until_a_branch_opens(world, shelf):
    html = signed_in().get("/library/").content.decode()
    for kind, count in (("Models", 3), ("Surfaces", 1), ("Sound", 1), ("Characters", 1), ("Places", 1), ("Kits", 0),
                        ("Algorithms", 0), ("Layers", 0), ("Effects", 0), ("Lights", 0), ("Ground", 0)):
        assert f'<span class="node-label" data-v>{kind}</span><span class="node-count" data-v>{count}</span>' in html
    assert 'data-children="/api/library/children?node=model"' in html and "node=kit" not in html  # an empty kind
    assert "Lamp post" not in html and "Wrench" not in html  # entries load only when their branch opens
    assert html.count(">MIT<") == 1 and "library.js" not in html


def test_a_branch_answers_its_children_a_page_at_a_time(world, shelf, monkeypatch):
    client = api()
    models = client.get("/api/library/children", params={"node": "model"}).json()
    assert [(node["label"], node["count"], node["children_url"]) for node in models] == [
        ("Pieces", 2, "/api/library/children?node=model/piece"), ("Props", 1, "/api/library/children?node=model/prop")]
    pieces = client.get("/api/library/children", params={"node": "model/piece"}).json()
    assert [(node["label"], node["count"], node["tone"], node["href"]) for node in pieces] == [
        ("Crate", 91, "done", "/library/model/crate/1/"), ("Lamp post", 42, "review", "/library/model/lamp_post.alpha/1/")]
    monkeypatch.setattr(pages_library, "PAGE", 1)
    first = client.get("/api/library/children", params={"node": "model/piece"}).json()
    assert [node["label"] for node in first] == ["Crate", "more"] and first[1]["count"] == 1
    assert [node["label"] for node in client.get(first[1]["children_url"]).json()] == ["Lamp post"]
    assert client.get("/api/library/children", params={"node": "nowhere"}).status_code == 404


def named(count, stem, place="alpha"):
    return [lib.LibraryEntry(address=f"model/{stem}_{rank}.{place}@1", kind="model", entry_id=f"{stem}_{rank}.{place}",
                             version=1, title=stem, state="draft", place=place, tags={"model": ["piece"]})
            for rank in range(count)]


def test_a_large_folder_is_split_by_name_words_then_by_place_and_small_groups_go_to_other():
    entries = [*named(30, "wall_upper_plain"), *named(20, "wall_upper_plain", "beta"), *named(4, "wall_lower"),
               *named(1, "lamp"), *named(1, "crate")]
    made = folders(entries)
    wall = node_of(made["tree"], "model/wall")
    assert [child["id"] for child in wall["children"]] == ["model/wall/wall_lower", "model/wall/wall_upper"]
    upper = node_of(made["tree"], "model/wall/wall_upper")
    assert [(child["label"], child["count"]) for child in upper["children"]] == [("from alpha", 30), ("from beta", 20)]
    assert node_of(made["tree"], "model/other")["count"] == 2
    assert len(made["members"]["model/wall/wall_upper/@beta"]) == 20


def test_an_item_page_shows_its_picture_version_score_files_and_3d(world, shelf):
    client = signed_in()
    lamp = client.get("/library/model/lamp_post.alpha/1/").content.decode()
    found = lib.library().entry("model/lamp_post.alpha@1")
    assert f"/library-files/pictures/{found.picture}.jpg" in lamp and 'href="/library/model/lamp_post.alpha/1/3d/"' in lamp
    for shown in (">42 <small>%</small>", ">30 <small>%</small>", "shape", "likeness", "web/lamp_post.glb",
                  "preview.png", 'value="lock"', 'value="repaint"'):
        assert shown in lamp, shown
    crate = client.get("/library/model/crate/1/").content.decode()
    assert ">91 <small>%</small>" in crate and 'value="withdraw"' in crate and "/3d/" not in crate
    hum = client.get("/library/sound/hum.alpha/1/").content.decode()
    assert hum.count("<audio") == 2
    guest = signed_in("guest").get("/library/model/crate/1/").content.decode()
    assert "data-post" not in guest  # only the owner decides
    assert client.get("/library/model/nothing/1/").status_code == 404
    words = prose(lamp)
    assert len(words) <= WORD_BUDGET, (len(words), words)


def test_the_full_screen_viewer_and_the_file_routes_serve_only_listed_files(world, shelf):
    web = api()
    found = lib.library().entry("character/walker@1")
    assert web.get(f"/library-files/thumbs/{found.picture}.jpg").headers["content-type"] == "image/jpeg"
    assert web.get(f"/library-files/view/{found.glb.sha}.json").json()["triangles"] == 1
    assert web.get(f"/library-files/view/{found.glb.sha}.glb").status_code == 200
    assert web.get(f"/library-files/view/{found.glb.sha}-light.glb").status_code == 404
    assert web.get(f"/library-files/files/{'0' * 64}").status_code == 404
    assert web.get(f"/library-files/thumbs/{'0' * 64}.jpg").headers["content-type"].startswith("image/svg")
    viewer = signed_in("guest").get("/library/model/lamp_post.alpha/1/3d/").content.decode()
    assert '"base": "/library-files/view/"' in viewer
    assert lib.library().entry("model/lamp_post.alpha@1").web3d.sha in viewer
    assert signed_in("guest2").get("/library/model/crate/1/3d/").status_code == 404


def test_the_owner_adds_refine_items_to_the_basket_and_a_visitor_cannot(world, shelf):
    client = api()
    said = client.post("/api/library/refine", json={"addresses": ["model/lamp_post.alpha@1", "model/crate@1"]}).json()
    assert said["added"] == 2 and said["in_basket"] == 2
    assert client.post("/api/library/refine", json={"addresses": ["model/lamp_post.alpha@1"], "option": "repaint"}
                       ).json()["added"] == 1
    refused = client.post("/api/library/refine", json={"addresses": ["model/crate@1"], "option": "repaint"})
    assert refused.status_code == 400 and "no refine option" in refused.json()["detail"]
    assert client.post("/api/library/refine", json={"addresses": ["model/crate@1"]}).json()["added"] == 0  # already in
    assert sorted(RefineItem.objects.values_list("address", "option")) == [
        ("model/crate@1", ""), ("model/lamp_post.alpha@1", ""), ("model/lamp_post.alpha@1", "repaint")]
    basket = signed_in("joey2").get("/basket/").content.decode()
    assert "Library entries to refine" in basket and "paint it again" in basket and "Not priced yet" in basket
    assert api("guest").post("/api/library/refine", json={"addresses": ["model/crate@1"]}).status_code == 403


def test_the_owner_locks_a_selection_committed_and_pushed(world, shelf):
    answer = api().post("/api/library/ask", json={"action": "lock",
                                                  "addresses": ["model/lamp_post.alpha@1", "sound/hum.alpha@1"]})
    assert "locked 2 entries" in answer.json()["said"]
    assert lib.library().entry("model/lamp_post.alpha@1").state == "locked"
    remote = subprocess.run(["git", "-C", str(shelf.parent / "remote.git"), "log", "-1", "--format=%s"],
                            capture_output=True, text=True).stdout
    assert remote.startswith("lock: 2 entries, the owner's decision on the cockpit")
    assert api("guest").post("/api/library/ask", json={"action": "lock", "addresses": ["model/crate@1"]}
                             ).status_code == 403


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


def test_the_export_carries_the_library_and_its_web_copies_to_a_hosted_cockpit(world, shelf, tmp_path):
    spend = Spend(spent=1.0, reserved=0.0, ceiling=250.0)
    first = building.build(world.source, tmp_path / "home/export/one", MADE, 50, spend, world.root)
    again = building.build(world.source, tmp_path / "home/export/two", MADE, 50, spend, world.root)
    assert first["written"] == again["written"] and "library/entries.json" in first["written"]
    pictures = {entry.picture for entry in lib.library().entries()}
    assert all(f"files/{sha}-360.jpg" in first["written"] for sha in pictures)
    assert sum(path.startswith("library/files/") for path in first["written"]) == 3  # the two takes, the web copy
    (tmp_path / "home/export/current").symlink_to("one")
    with override_settings(SCORE_MODE="hosted", SCORE_HOME=tmp_path / "home", SCORE_LIB_ROOT=None):
        hosted = lib.library()
        assert isinstance(hosted, lib.ExportedLibrary) and len(hosted.entries()) == 7
        assert hosted.picture_path(next(iter(pictures)), 360) is not None
        client = api("joey3")
        assert [node["label"] for node in client.get("/api/library/children", params={"node": "model/piece"}).json()
                ] == ["Crate", "Lamp post"]
        pages = signed_in("joey4")
        assert 'data-children="/api/library/children?node=model"' in pages.get("/library/").content.decode()
        hum = pages.get("/library/sound/hum.alpha/1/").content.decode()
        assert hum.count("<audio") == 2 and "audio/hum_1.ogg" in hum
        lamp = pages.get("/library/model/lamp_post.alpha/1/").content.decode()
        assert 'href="/library/model/lamp_post.alpha/1/3d/"' in lamp  # its web copy travelled
        assert "/3d/" not in pages.get("/library/character/walker/1/").content.decode()  # its raw GLB is not sent


HOSTED_CHILD = """
import json, sys
import django
django.setup()
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
from django.contrib.auth import get_user_model
from django.test import Client
from score.dashboard.pages import library
from score.dashboard.state import library as lib
client = Client()
client.force_login(get_user_model().objects.create_user("joey", password="a long enough password"))
codes = [client.get(page, HTTP_HOST="127.0.0.1").status_code for page in ("/library/", "/library/model/crate/1/")]
branch = [node["label"] for node in library.children(lib.library(), "model")]
import score.dashboard.site.asgi  # what the hosted image serves
heavy = [name for name in sys.modules if name.startswith("score.") and not name.startswith("score.dashboard")]
print(json.dumps({"codes": codes, "branch": branch, "heavy": heavy}))
"""


def test_a_hosted_library_screen_imports_nothing_the_hosted_image_lacks(world, shelf, tmp_path):
    home = tmp_path / "hosted"
    building.build(world.source, home / "export" / "one", MADE, 50, Spend(spent=1.0, reserved=0.0, ceiling=250.0),
                   world.root)
    (home / "export" / "current").symlink_to("one")
    env = {**os.environ, "SCORE_DASHBOARD_MODE": "hosted", "SCORE_DASHBOARD_HOME": str(home), "SCORE_LIB_ROOT": "",
           "DJANGO_SETTINGS_MODULE": "score.dashboard.site.settings", "PYTHONPATH": str(REPO)}
    done = subprocess.run([sys.executable, "-c", HOSTED_CHILD], env=env, cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-3000:]
    found = json.loads(done.stdout.strip().splitlines()[-1])
    assert found == {"codes": [200, 200], "branch": ["Pieces", "Props"], "heavy": []}, found


def test_the_library_screen_shows_numbers_not_prose(world, shelf):
    words = prose(signed_in().get("/library/").content.decode())
    assert len(words) <= WORD_BUDGET, (len(words), words)
