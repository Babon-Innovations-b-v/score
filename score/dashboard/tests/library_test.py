"""The Library screen reads a tiny library folder (entries, an index, a blob folder): the tree of kinds with counts,
a branch's children only when it opens, a page at a time, an item's page (the item in its kind's viewer: a copy
turned, a surface on sliders, a sound's takes, an effect played, a light's test scene; a few numbers), the
owner's lock and withdraw (queued when hosted, applied with the library's own command, committed and pushed, refused
for anyone else and in an agent's process), refine items into the basket, and the library in the state export, read
back by a hosted cockpit that imports nothing its image lacks."""
import hashlib
import json
import os
import pathlib
import re
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
def Material "steel" {
    custom string score:token = "steel"
    def Shader "surface" {
    color3f inputs:diffuseColor = (0.5, 0.25, 0.125)
    float inputs:metallic = 1
    float inputs:roughness = 0.35
} }"""
SKY = b"""#usda 1.0
def Xform "sky" {
    def DomeLight "Environment" {
        color3f inputs:color = (0.35, 0.48, 0.79)
        float inputs:intensity = 0.22
    }
    def Mesh "Dome" {
    }
}"""
LAMPS = json.dumps({"place": "alpha", "lamps": [
    {"path": "/alpha/Lights/light_2", "spot": [1.0, 3.0, -2.0], "intensity": 3.0, "scale": 2.0},
    {"path": "/alpha/Lights/sun_1", "spot": None, "sun": True, "intensity": 1.0, "scale": 1.0}]}).encode()
DEMO = {"example": "the alpha's two beds", "view": "plan", "bounds": [0, 0, 2, 1],
        "steps": [{"label": "The beds", "shapes": [{"kind": "area", "points": [[0, 0], [1, 0], [1, 1]], "tone": "ground"}]}],
        "numbers": [{"label": "plants", "value": 9, "unit": "", "tip": "plants laid"}]}
SETTINGS = json.dumps({"emitter": "ring", "emitter_size": [4.2, 2.5, 0.6], "count": 15000, "lifetime": 10.0,
                       "loop": 10.0, "speed": [3, 5], "from": "footage: " + "a long source in words " * 20}).encode()
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


CLIP = b"\x00\x00\x00\x18ftypmp42 a clip's bytes"


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
              "title": more.pop("title", entry_id.split(".")[0].replace("_", " ").capitalize()), "files": described,
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
    entry(root, blobs, "model", "lamp_post.alpha",
          files={"web/lamp_post.glb": ("web3d", glb()), "web/lamp_light.glb": ("web3d", glb() + b" " * 4),
                 "closeup.png": ("closeup", fixture.picture((200, 60, 30)))},
          web3d={"file": "web/lamp_post.glb", "light": "web/lamp_light.glb", "objects": 3, "triangles": 1},
          score=42, score_parts=[{"name": "shape", "value": 30, "how": "edges"},
                                 {"name": "likeness", "value": None, "how": "needs a paid judge"}],
          refine_options=["remesh", {"id": "repaint", "label": "paint it again"}])
    entry(root, blobs, "model", "crate", state="locked", place="beta", node="assembly@beta", score=0.91,
          score_parts={"finish": 0.6})
    entry(root, blobs, "model", "wrench", tags={"model": ["prop"]}, files={"clip/clip.mp4": ("clip", CLIP)},
          clip={"file": "clip/clip.mp4", "shelf": "model", "frames": 96, "seconds": 4.0})
    entry(root, blobs, "surface", "brushed_steel.alpha", node=None,
          tags={"family": ["steel"], "recipe": ["bare_metal"]},
          files={"material.usda": ("usd", MATERIAL), "print.png": ("texture", fixture.picture())})
    entry(root, blobs, "sound", "hum.alpha", files={"audio/hum_1.ogg": ("audio", b"OggS one"),
                                                   "audio/hum_2.ogg": ("audio", b"OggS two")}, score=95,
          score_parts=[{"name": "loudness", "measured": -2.0, "unit": "LU off target", "value": 90,
                        "how": "integrated loudness -22.0 LUFS against its shot target -20.0 LUFS"},
                       {"name": "length", "measured": 4.3, "unit": "s", "value": 100, "how": "within"}])
    entry(root, blobs, "effect", "devil.alpha", files={"settings.json": ("record", SETTINGS)})
    entry(root, blobs, "light", "sky.alpha", files={"sky.usda": ("usd", SKY)})
    entry(root, blobs, "layer", "light.alpha", title="Alpha light layer", files={"lamps.json": ("record", LAMPS)})
    entry(root, blobs, "kit", "alpha", files={"web3d/light.glb": ("web3d", glb() + b" " * 8)},
          web3d={"light": "web3d/light.glb", "objects": 12}, tags={"place_kind": ["inside", "moon"]})
    entry(root, blobs, "algorithm", "camera_paths", title="Camera moves: walk paths and film shots",
          provenance={"stage": "demo-film", "nodes": ["demo-film@alpha", "demo-film@beta"]},
          requires=["algorithm/terrain@1"], score=25, files={"presets/world1/data/definitions/demo_films/alpha.json":
                                                              ("record", b"{}")})
    entry(root, blobs, "ground", "earth.alpha")
    entry(root, blobs, "layer", "base.alpha")
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
    for kind, count in (("Models", 3), ("Surfaces", 1), ("Kits", 1), ("Motion", 1), ("Effects", 1), ("Skies", 1),
                        ("Lamps", 1), ("Sound", 1), ("Films", 1), ("Physics", 0), ("Places", 2)):
        assert f'<span class="node-label" data-v>{kind}</span><span class="node-count" data-v>{count}</span>' in html
    assert 'data-v>Algorithms<' not in html  # the shelf holds physics setups only: code sits where its work does
    assert 'data-v>Ground<' not in html and 'data-v>Layers<' not in html  # retired, and a layer sits under its place
    assert 'data-children="/api/library/children?node=model"' in html
    assert "Lamp post" not in html and "Wrench" not in html  # entries load only when their branch opens
    assert html.count(">MIT<") == 1 and "library.js" not in html


def test_code_that_makes_something_sits_on_its_shelf_in_a_made_by_code_folder_beside_the_shelfs_own(world, shelf):
    client = api()
    films = client.get("/api/library/children", params={"node": "film"}).json()
    assert [(node["label"], node["count"]) for node in films] == [("Made by code", 1)]
    held = client.get("/api/library/children", params={"node": "film/made_by_code"}).json()
    assert [node["href"] for node in held] == ["/library/algorithm/camera_paths/1/"]
    skies = client.get("/api/library/children", params={"node": "light"}).json()
    assert [node["href"] for node in skies] == ["/library/light/sky.alpha/1/"]  # no code here: no folder


def test_the_places_shelf_holds_a_folder_a_place_with_its_own_layers(world, shelf):
    client = api()
    places = client.get("/api/library/children", params={"node": "place"}).json()
    assert [(node["label"], node["count"]) for node in places] == [("Alpha", 2)]
    held = client.get("/api/library/children", params={"node": "place/alpha"}).json()
    assert [node["href"] for node in held] == ["/library/place/alpha/1/", "/library/layer/base.alpha/1/"]


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


def test_a_withdrawn_entry_is_in_no_folder():
    entries = named(2, "crate")
    entries[1] = entries[1].model_copy(update={"state": "withdrawn"})
    made = folders(entries)
    assert node_of(made["tree"], "model")["count"] == 1
    assert [entry.state for entry in made["members"]["model"]] == ["draft"]


def item_data(html):
    """The viewer's JSON the item page carries (item3d.js reads it), or None."""
    found = re.search(r'<script id="item-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(found.group(1)) if found else None


def an_item_page(client, path):
    """An item page that keeps to the 40-word rule and shows no file list, ids or blobs."""
    html = client.get(path).content.decode()
    words = prose(html)
    assert len(words) <= WORD_BUDGET, (path, len(words), words)
    for gone in ('class="files"', 'class="ids"', "preview.png", "<table", "sha256"):
        assert gone not in html, (path, gone)
    return html


def number_shown(html, label, value):
    """A number card of `label` showing `value`."""
    return re.search(rf'<div class="num-label">{re.escape(label)}</div>\s*<div class="num-value" data-v>'
                     rf'{re.escape(value)}', html) is not None


def test_a_model_turns_in_3d_from_its_light_copy_with_its_size_parts_and_score(world, shelf):
    client = signed_in()
    lamp = an_item_page(client, "/library/model/lamp_post.alpha/1/")
    found = lib.library().entry("model/lamp_post.alpha@1")
    viewer = item_data(lamp)
    assert viewer["mode"] == "copy" and viewer["light"] == f"/library-files/files/{found.web3d_light.sha}"
    assert viewer["full"] == f"/library-files/files/{found.web3d.sha}"
    assert 'id="item3d"' in lamp and '<script type="module" src="/static/pages/item3d.js">' in lamp
    assert '"three": "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.170.0/three.module.min.js"' in lamp
    assert f"/library-files/pictures/{found.picture}.jpg" in lamp  # under it while it loads
    assert f"/library-files/pictures/{found.closeup.sha}.jpg" in lamp  # beside it: the close-up it was made from
    assert api("ann").get(f"/library-files/pictures/{found.closeup.sha}.jpg").status_code == 200
    assert number_shown(lamp, "parts", "3") and number_shown(lamp, "score", "42") and 'data-fact="size"' in lamp
    assert 'title="how sound its mesh is: holes, crowded edges, seams; shape 30, likeness not measured"' in lamp
    assert 'href="/library/model/lamp_post.alpha/1/3d/"' in lamp and 'value="lock"' in lamp and 'value="repaint"' in lamp
    crate = an_item_page(client, "/library/model/crate/1/")
    assert item_data(crate) is None and 'class="pic"' in crate and 'value="withdraw"' in crate and "/3d/" not in crate
    assert "data-post" not in an_item_page(signed_in("guest"), "/library/model/crate/1/")  # only the owner decides
    assert client.get("/library/model/nothing/1/").status_code == 404


def test_an_item_with_a_preview_clip_plays_it_first_and_its_viewer_is_the_second_tab(world, shelf):
    client = signed_in()
    wrench = an_item_page(client, "/library/model/wrench/1/")
    found = lib.library().entry("model/wrench@1")
    assert f'<video src="/library-files/files/{found.clip.sha}"' in wrench and 'href="?tab=3d"' in wrench
    assert 'id="item3d"' not in wrench and "item3d.js" not in wrench
    served = api("ann").get(f"/library-files/files/{found.clip.sha}")
    assert served.status_code == 200 and served.headers["content-type"] == "video/mp4"
    second = an_item_page(client, "/library/model/wrench/1/?tab=3d")
    assert "<video" not in second and 'href="?tab=clip"' in second
    lamp = an_item_page(client, "/library/model/lamp_post.alpha/1/")
    assert "<video" not in lamp and "?tab=" not in lamp  # no clip: its viewer alone, no tabs


def test_a_kit_is_laid_as_its_place_lays_it_and_a_character_plays_its_clips(world, shelf):
    client = signed_in()
    kit = an_item_page(client, "/library/kit/alpha/1/")
    assert item_data(kit)["mode"] == "kit" and item_data(kit)["inside"]  # an inside kit is cut open
    assert number_shown(kit, "pieces", "12") and 'id="kit-pieces"' in kit  # its kinds of piece, filled once loaded
    walker = an_item_page(client, "/library/character/walker/1/")  # its raw body only: its picture, a 3D link
    assert item_data(walker) is None and 'href="/library/character/walker/1/3d/"' in walker


def test_a_copy_the_library_lost_is_said_missing_and_travels_so_in_the_export(world, shelf, tmp_path):
    shown = lib.library()
    kit = shown.entry("kit/alpha@1")
    (shelf.parent / "blobs" / "blobs" / kit.web3d_light.sha[:2] / kit.web3d_light.sha).unlink()
    marked = shown.cache / "kit/alpha/1/web3d/light.glb.lost"
    marked.parent.mkdir(parents=True)
    marked.write_text("0" * 64)  # a mark of other bytes than the entry names: not this file
    client = signed_in()
    page = an_item_page(client, "/library/kit/alpha/1/")
    assert item_data(page) is None and ">3D not here<" in page and "data-fact" not in page
    marked.write_text(kit.web3d_light.sha)
    page = an_item_page(client, "/library/kit/alpha/1/")
    assert ">3D missing<" in page and "sync" not in page.lower().replace("score-sync", "")
    building.build(world.source, tmp_path / "home/export/one", MADE, 50, Spend(spent=1.0, reserved=0.0, ceiling=250.0),
                   world.root)
    rows = json.loads((tmp_path / "home/export/one" / lib.EXPORT_ROWS).read_text())
    assert next(row["missing"] for row in rows if row["address"] == "kit/alpha@1") == ["web3d/light.glb"]


def test_a_surface_is_lit_on_a_sphere_with_its_settings_on_sliders(world, shelf):
    steel = an_item_page(signed_in(), "/library/surface/brushed_steel.alpha/1/")
    viewer = item_data(steel)
    assert viewer["mode"] == "surface" and viewer["token"] == "steel"
    assert viewer["finish"]["colour"] == [0.5, 0.25, 0.125] and viewer["finish"]["roughness"] == 0.35
    assert viewer["print"].startswith("/library-files/files/") and viewer["palette"]["sign-gold"].startswith("#")
    for slider in ('name="token"', 'name="shine"', 'name="metal"', 'name="wear"', 'name="seed"',
                   '<option value="steel" selected>'):
        assert slider in steel, slider
    assert number_shown(steel, "token", "steel")


def test_a_sound_plays_its_takes_side_by_side_with_its_loudness_and_length(world, shelf):
    hum = an_item_page(signed_in(), "/library/sound/hum.alpha/1/")
    assert hum.count("data-wave=") == 2 and '<script src="/static/pages/takes.js">' in hum and "item3d.js" not in hum
    assert number_shown(hum, "loudness", "-22.0 <small>LUFS</small>") and number_shown(hum, "length", "4.3 <small>s</small>")


def test_an_effect_plays_from_its_settings_with_a_time_scrubber(world, shelf):
    devil = an_item_page(signed_in(), "/library/effect/devil.alpha/1/")
    viewer = item_data(devil)
    assert viewer["mode"] == "effect" and viewer["settings"]["emitter"] == "ring" and viewer["settings"]["count"] == 15000
    assert "from" not in viewer["settings"]  # its sources in words stay in the library
    assert 'id="clock"' in devil and "data-time" in devil
    assert number_shown(devil, "length", "10.0 <small>s</small>") and number_shown(devil, "loop", "10.0 <small>s</small>")


def test_a_sky_is_looked_around_in_and_a_place_s_lamps_light_a_test_scene(world, shelf):
    client = signed_in()
    sky = an_item_page(client, "/library/light/sky.alpha/1/")
    viewer = item_data(sky)
    assert viewer["mode"] == "sky" and viewer["sky"] == "dome" and viewer["picture"].startswith("/library-files/")
    assert ">Skies<" in sky
    lamps = an_item_page(client, "/library/layer/light.alpha/1/")
    found = item_data(lamps)["lamps"]
    assert [(lamp["type"], lamp["name"], lamp["power"]) for lamp in found] == [("point", "light_2", 6.0),
                                                                                ("sun", "sun_1", 1.0)]
    assert found[0]["spot"] == [1.0, 3.0, -2.0] and ">Lamps<" in lamps and ">Alpha lamps<" in lamps
    assert number_shown(lamps, "power", "6.0") and 'title="Alpha light layer"' in lamps


def test_an_algorithm_shows_its_work_on_a_real_example_else_what_it_reads_and_makes(world, shelf):
    from django.conf import settings
    client = signed_in()
    paths = an_item_page(client, "/library/algorithm/camera_paths/1/")  # no demo made yet: the plain diagram
    assert ">Camera paths<" in paths and 'title="Camera moves: walk paths and film shots"' in paths
    assert ">Films<" in paths and ">made by code<" in paths
    assert "demo films" in paths and "demo film &times; 2" in paths and "code only" not in paths
    assert "score" not in paths.split('class="nums"')[-1].split("item-actions")[0].lower()  # its score means nothing
    demos = settings.SCORE_PROPS_HOME / "cache" / "library" / "demos.json"
    demos.parent.mkdir(parents=True, exist_ok=True)
    demos.write_text(json.dumps({"camera_paths": DEMO}))
    shown = an_item_page(client, "/library/algorithm/camera_paths/1/")
    assert '<script type="module" src="/static/pages/demo.js">' in shown and "the alpha&#x27;s two beds" in shown
    assert ">The beds<" in shown and number_shown(shown, "plants", "9")
    demos.write_text(json.dumps({"camera_paths": {"missing": "no example kept"}}))
    assert "no example of its work is here yet: no example kept" in an_item_page(client, "/library/algorithm/camera_paths/1/")


def test_a_place_or_layer_shows_its_places_3d_copy_and_a_ground_its_picture(world, shelf):
    client = signed_in()
    assert "<iframe" not in an_item_page(client, "/library/place/alpha/1/")  # no web copy yet: its picture
    copy = world.source.web_copies / "alpha"
    copy.mkdir(parents=True)
    (copy / "alpha.json").write_text(json.dumps({"objects": []}))
    for path in ("/library/place/alpha/1/", "/library/layer/base.alpha/1/"):
        assert '<iframe src="/view/alpha?embed=1"' in an_item_page(client, path), path
    ground = an_item_page(client, "/library/ground/earth.alpha/1/")
    assert item_data(ground) is None and 'class="pic"' in ground


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
    # the two takes, the wrench's clip, the light copies of the lamp post and the kit, the surface's print; never a
    # whole copy
    assert sum(path.startswith("library/files/") for path in first["written"]) == 6
    assert "library/palette.json" in first["written"]
    (tmp_path / "home/export/current").symlink_to("one")
    with override_settings(SCORE_MODE="hosted", SCORE_HOME=tmp_path / "home", SCORE_LIB_ROOT=None):
        hosted = lib.library()
        assert isinstance(hosted, lib.ExportedLibrary) and len(hosted.entries()) == 14
        assert hosted.picture_path(next(iter(pictures)), 360) is not None
        client = api("joey3")
        assert [node["label"] for node in client.get("/api/library/children", params={"node": "model/piece"}).json()
                ] == ["Crate", "Lamp post"]
        pages = signed_in("joey4")
        assert 'data-children="/api/library/children?node=model"' in pages.get("/library/").content.decode()
        hum = pages.get("/library/sound/hum.alpha/1/").content.decode()
        assert hum.count("data-wave=") == 2 and "hum_1.ogg" in hum
        lamp = item_data(pages.get("/library/model/lamp_post.alpha/1/").content.decode())
        found = hosted.entry("model/lamp_post.alpha@1")
        assert lamp["light"] == f"/library-files/files/{found.web3d_light.sha}" and lamp["full"] is None  # light only
        steel = item_data(pages.get("/library/surface/brushed_steel.alpha/1/").content.decode())
        assert steel["token"] == "steel" and steel["print"] and steel["palette"]["sign-gold"].startswith("#")
        assert item_data(pages.get("/library/effect/devil.alpha/1/").content.decode())["settings"]["count"] == 15000
        assert "/3d/" not in pages.get("/library/character/walker/1/").content.decode()  # its raw GLB is not sent
        wrench = pages.get("/library/model/wrench/1/").content.decode()
        assert f'<video src="/library-files/files/{hosted.entry("model/wrench@1").clip.sha}"' in wrench


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
codes = [client.get(page, HTTP_HOST="127.0.0.1").status_code for page in (
    "/library/", "/library/model/crate/1/", "/library/model/lamp_post.alpha/1/", "/library/surface/brushed_steel.alpha/1/",
    "/library/sound/hum.alpha/1/", "/library/effect/devil.alpha/1/", "/library/light/sky.alpha/1/",
    "/library/algorithm/camera_paths/1/", "/library/place/alpha/1/")]
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
    assert found == {"codes": [200] * 9, "branch": ["Pieces", "Props"], "heavy": []}, found


def test_the_library_screen_shows_numbers_not_prose(world, shelf):
    words = prose(signed_in().get("/library/").content.decode())
    assert len(words) <= WORD_BUDGET, (len(words), words)


def test_names_are_everyday_words_with_the_library_title_kept_as_hover_text():
    from score.dashboard.state.names import plain
    assert plain("algorithm", "camera_paths", "Camera moves: RRT* walk paths (the render needs a GPU)") == (
        "Camera paths", "Camera moves: RRT* walk paths (the render needs a GPU)")
    assert plain("ground", "earth.flat", "Flat ground (earth)")[0] == "Flat ground, earth"
    assert plain("model", "ac_unit_1", "Ac unit 1")[0] == "Air conditioner 1"
    assert plain("model", "apron_2p6", "Apron 2p6")[0] == "Apron 2.6 m"
    assert plain("effect", "drift_0_3.camp", "Drift 0 3")[0] == "Drift, row 1 spot 4"
    assert plain("layer", "light.camp", "Camp light layer")[0] == "Camp lamps"
    assert plain("model", "wrench", "Wrench") == ("Wrench", "")
