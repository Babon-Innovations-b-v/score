"""The FILM pages and the film script (score/dashboard/films): a script's clock and checks, its render items priced
from measured frames only, the page with its free preview's data, saving to the cockpit's home only, the basket taking
only rows that exist, and environment 1's starter script."""
import json
import math
import re

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from score.dashboard.films import render, script, takes
from score.dashboard.pages.models import BasketItem

pytestmark = pytest.mark.django_db


def signed_in(name="joey"):
    user = get_user_model().objects.create_user(name, password="a long enough password")
    client = Client(enforce_csrf_checks=False)
    client.force_login(user)
    return client


def a_script(segments, **more):
    return {**script.blank("trailer", "A trailer"), "segments": segments, **more}


def editor_of(html):
    return json.loads(re.search(r'<script id="film-data" type="application/json">(.*?)</script>', html, re.S).group(1))


def test_the_clock_overlaps_cross_fades_and_pushes_only():
    film = a_script([{"cut": "title", "transition": "fade-through-black"},
                     {"cut": "walk-through", "shows": {"place": "alpha"}, "transition": "cross-fade"},
                     {"cut": "step-card", "shows": {"place": "alpha", "step": "plan"}, "transition": "push",
                      "seconds": 2},
                     {"cut": "text", "transition": "cut"}])
    assert script.timeline(film) == [(0.0, 4.0), (3.5, 7.0), (10.0, 2.0), (12.0, 4.0)]
    assert script.total_seconds(film) == 16.0
    film["defaults"] = {"walk-through": 5.0}
    assert script.total_seconds(film) == 14.0


def test_a_script_says_what_is_wrong_in_words():
    film = a_script([{"cut": "spin"}, {"cut": "isolate", "shows": {"place": "alpha"}},
                     {"cut": "step-card", "shows": {"place": "alpha", "step": "paint"}},
                     {"cut": "orbit", "shows": {"place": "gamma"}, "seconds": 99, "transition": "wipe"}])
    found = script.faults(film, {"alpha", "beta"})
    assert "segment 1: no cut type 'spin'" in found
    assert "segment 2 (Isolate a part) names no part" in found
    assert "segment 3: no framework step 'paint'" in found
    assert "segment 4: no transition 'wipe'" in found and any("99" in fault for fault in found)
    assert "segment 4: no scene 'gamma'" in found
    assert script.faults({**film, "film": "Bad Name"}) and script.faults({"format": "other"})


def test_render_items_reuse_films_and_price_film_frames_per_place_from_measured_runs():
    media = {"alpha": {"film": {"url": "/files/a"}, "hero": {"url": "/files/h"}, "extras": {}},
             "beta": {"film": None, "hero": None, "extras": {}},
             "hub": {"film": {"url": "/files/b"}, "hero": None, "extras": {}}}
    film = a_script([{"cut": "title"},
                     {"cut": "walk-through", "shows": {"place": "alpha"}, "seconds": 3.5},
                     {"cut": "walk-through", "shows": {"place": "alpha"}},
                     {"cut": "walk-through", "shows": {"place": "beta"}},
                     {"cut": "hero-still", "shows": {"place": "alpha"}},
                     {"cut": "exploded", "shows": {"place": "alpha"}},
                     {"cut": "step-card", "shows": {"place": "alpha", "step": "plan"}},
                     {"cut": "walk-through", "shows": {"place": "hub"}},
                     {"cut": "hero-still", "shows": {"place": "alpha"}, "camera": "wide"}])
    items = render.items(film, media)
    assert [item["how"] for item in items] == ["free", "reuse", "new", "basket", "reuse", "new", "free", "new", "new"]
    assert items[2]["frames"] == 168 and items[2]["kind"] == "film"
    assert items[2]["euros"] == round(168 * render.MEASURED["film"]["euros"], 2)  # no runs of its own: the median
    assert items[7]["euros"] == round(168 * render.FILM_FRAME_EUROS["hub"], 2)  # the hub's own runs
    assert items[8]["kind"] == "look" and items[8]["euros"] == round(render.MEASURED["look"]["euros"], 2)
    assert items[3]["node"] == "demo-film@beta" and items[3]["frames"] == render.FILM_FRAMES
    assert items[5]["frames"] == 144 and items[5]["euros"] is None  # an exploded view was never rendered on a card
    totals = render.totals(items)
    assert totals["unmeasured"] == ["exploded"] and totals["unmeasured_frames"] == 144
    assert totals["basket"] == ["demo-film@beta"] and totals["reused"] == 2 and totals["free"] == 2
    assert totals["euros"] == round(sum(items[number]["euros"] for number in (2, 3, 7, 8)), 2)


def test_the_film_shot_matches_the_demo_film_rows():
    from score.stages import demo_film
    assert script.FILM_SHOT_SECONDS == demo_film.SECONDS - script.TRANSITION_SECONDS
    assert render.FILM_FRAMES == round(demo_film.SECONDS * 24)


def design_scenes():
    """Environment 1's scenes as its data names them (data/places/within.json's tree and shells, each look's scenes in
    data/definitions/place.json): the test's store holds no design, so no scene of it is a place of the build here."""
    data = settings.SCORE_REPO / "data"
    within = json.loads((data / "places/within.json").read_text())
    looks = json.loads((data / "definitions/place.json").read_text())
    return ({*within["within"], *(entry["within"] for entry in within["within"].values()), *within["shells"]}
            | {scene for look in looks.values() if isinstance(look, dict) for scene in look.get("scenes", [])})


def test_world1_starter_is_sound_and_gives_the_places_the_time():
    film, origin = script.read(settings.SCORE_REPO, "/nonexistent", "k9")
    assert origin == "starter" and script.faults(film, design_scenes()) == []
    lengths = dict(zip(range(len(film["segments"])), script.timeline(film)))
    walks = sum(lengths[index][1] for index, segment in enumerate(film["segments"]) if segment["cut"] == "walk-through")
    assert walks > script.total_seconds(film) / 2
    places = [segment["shows"]["place"] for segment in film["segments"]
              if segment["cut"] == "walk-through" and not segment["shows"].get("film")]
    assert len(places) == len(set(places)) and all(script.seconds_of(film, segment) >= 7
                                                   for segment in film["segments"] if segment["cut"] == "walk-through")
    cards = [segment for segment in film["segments"] if segment["cut"] == "step-card"]
    assert [card["shows"]["step"] for card in cards] == list(script.STEPS)  # the chain once
    assert len({card["shows"]["place"] for card in cards}) == 1
    assert script.total_seconds(film) <= film["target_seconds"]


def test_the_film_pages_render_with_the_preview_data(world, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    script.save(settings.SCORE_HOME, a_script([
        {"cut": "title", "text": "A trailer"},
        {"cut": "walk-through", "shows": {"place": "alpha"}, "text": "Alpha", "seconds": 3.5},
        {"cut": "layer-split", "shows": {"place": "alpha"}}]))
    client = signed_in()
    listing = client.get("/film/all/").content.decode()
    assert "/film/trailer/" in listing and "A trailer" in listing
    html = client.get("/film/trailer/").content.decode()
    editor = editor_of(html)
    assert editor["origin"] == "saved" and editor["places"]["alpha"]["film"]["url"].startswith("/files/")
    assert set(editor["cuts"]) >= {"walk-through", "orbit", "hero-still", "exploded", "isolate", "layer-focus",
                                   "layer-split", "step-card", "before-after", "title", "text"}
    assert [item["how"] for item in editor["answer"]["items"]] == ["free", "reuse", "new"]
    assert editor["answer"]["totals"]["unmeasured"] == ["layer-split"]
    from score.dashboard.tests.pages_test import NODE, outside_details
    assert NODE.search(outside_details(html)) is None  # owner rule (#42): node ids only inside the ids fold
    assert client.get("/film/nothing/").status_code == 404


def test_saving_writes_the_cockpit_home_only_and_refuses_others(world, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    film = a_script([{"cut": "orbit", "shows": {"place": "alpha"}}])
    script.save(settings.SCORE_HOME, film)
    owner = signed_in()
    changed = {**film, "segments": [*film["segments"], {"cut": "text", "text": "the end"}]}
    answer = owner.post("/film/trailer/save/", json.dumps(changed), content_type="application/json")
    assert answer.status_code == 200 and answer.json()["saved"] and answer.json()["totals"]["frames"] == 144
    assert json.loads(script.saved_path(settings.SCORE_HOME, "trailer").read_text())["segments"][-1]["text"] == "the end"
    assert not (tmp_path / "repo").exists()
    wrong = {**film, "segments": [{"cut": "orbit", "shows": {"place": "nowhere"}}]}
    refused = owner.post("/film/trailer/save/", json.dumps(wrong), content_type="application/json")
    assert refused.status_code == 400 and "segment 1: no scene 'nowhere'" in refused.json()["faults"]
    other = signed_in("other")
    assert other.post("/film/trailer/save/", json.dumps(changed), content_type="application/json").status_code == 403
    assert other.post("/film/trailer/compile/", json.dumps(changed), content_type="application/json").status_code == 200


def test_the_basket_takes_only_a_place_film_row_and_launches_nothing(world, tmp_path, monkeypatch):
    from score import review
    from score.dashboard.tests.fixture import FakeBackend
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    review.reject(world.store, "demo-film@beta", world.outputs["demo-film@beta"], by="joey", reason="test")
    world.source.refresh()
    script.save(settings.SCORE_HOME, a_script([{"cut": "walk-through", "shows": {"place": "alpha"}},
                                               {"cut": "walk-through", "shows": {"place": "beta"}},
                                               {"cut": "exploded", "shows": {"place": "alpha"}}]))
    assert signed_in("other").post("/film/trailer/basket/").status_code == 403
    signed_in().post("/film/trailer/basket/")
    assert [(item.place, item.stage) for item in BasketItem.objects.all()] == [("beta", "demo-film")]
    assert not [call for call in FakeBackend.calls if call[0] == "launch"]


def test_a_new_film_starts_with_its_title_card(world, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    client = signed_in()
    assert client.post("/film/new/", {"film": "teaser", "title": "A teaser"}).status_code == 302
    film, origin = script.read(tmp_path / "repo", settings.SCORE_HOME, "teaser")
    assert origin == "saved" and film["segments"][0]["cut"] == "title" and film["title"] == "A teaser"
    client.post("/film/new/", {"film": "new", "title": "x"})
    assert script.read(tmp_path / "repo", settings.SCORE_HOME, "new")[0] is None


def test_a_screen_take_never_clicks_what_spends_and_a_scale_zoom_goes_down_only():
    take = {"cut": "screen-take", "shows": {"page": "/concept/hub/"}, "take": [
        {"at": 0.5, "do": "click", "on": "#concept-draw", "words": "Redraw with notes EUR 0.30"},
        {"at": 1.0, "do": "type", "on": "#concept-note", "text": "taller\n"},
        {"at": 1.5, "do": "spin", "on": "#x"},
        {"at": 2.0, "do": "move"}]}
    zoom = {"cut": "scale-zoom", "shows": {"place": "alpha"}, "seconds": 9.0,
            "legs": [{"layer": "world", "seconds": 4}, {"layer": "setting", "seconds": 4},
                     {"layer": "attic", "seconds": 1}]}
    found = script.faults(a_script([take, zoom, {"cut": "title", "pip": {"corner": "middle"}}]))
    assert any("segment 1 step 1: refused" in fault for fault in found)
    assert "segment 1 step 2: typing never presses Enter (it could send a form)" in found
    assert "segment 1 step 3: no step 'spin'" in found and "segment 1 step 4: move names the element it is `on`" in found
    assert any(fault.startswith("segment 2: a scale zoom goes down through the layers") for fault in found)
    assert "segment 2: no layer 'attic'" in found
    assert any(fault.startswith("segment 3: a picture-in-picture") for fault in found)
    for word in ("Draw fresh", "Pick", "Buy", "Keep", "Make plan", "Unlock", "EUR 0.15"):
        assert takes.SPEND.search(word), word
    assert not takes.SPEND.search("hub, picked") and not takes.SPEND.search("Places")


def test_recorded_cuts_are_free_but_a_zoom_into_finished_places_is_film_frames():
    film = a_script([{"cut": "screen-take", "shows": {"page": "/"}},
                     {"cut": "setting-animation", "shows": {"world": "world1"}},
                     {"cut": "scale-zoom", "shows": {"place": "hub"}, "seconds": 10,
                      "legs": [{"layer": "setting", "seconds": 3}, {"layer": "world", "seconds": 2},
                               {"layer": "place", "seconds": 2}, {"layer": "room", "seconds": 3}]},
                     {"cut": "scale-zoom", "shows": {"place": "hub"}, "seconds": 5,
                      "legs": [{"layer": "setting", "seconds": 3}, {"layer": "world", "seconds": 2}]}])
    items = render.items(film, {})
    assert [item["how"] for item in items] == ["free", "free", "new", "free"]
    assert items[2]["frames"] == 120 and items[2]["euros"] == round(120 * render.FILM_FRAME_EUROS["hub"], 2)


def test_the_preview_joins_on_the_scripts_own_clock():
    from score.dashboard.films.preview import make
    film = a_script([{"cut": "title", "transition": "fade-through-black", "seconds": 4},
                     {"cut": "text", "transition": "fade-through-black", "seconds": 3},
                     {"cut": "text", "transition": "cross-fade", "seconds": 3},
                     {"cut": "text", "transition": "push", "seconds": 2}])
    joined, made, total = make.joined_filter(film, [4, 3, 3, 2])
    assert total == script.total_seconds(film) == 11.0 and made == "j3"
    assert "transition=fade:duration=0.5:offset=6.500" in joined and "transition=slideleft" in joined
    assert "concat=n=2" in joined and "fade=t=out:st=3.750" in joined


def test_the_bed_is_the_sound_stages_of_the_first_place_shown_and_silence_while_none_is_made(monkeypatch):
    """The bed comes from the sound stage's output (the state's sound_beds), never a library name; none made, none."""
    from score.dashboard.films.preview import make
    from score.dashboard import state as dashboard_state

    class Blobs:
        @staticmethod
        def blob_path(sha):
            return f"blobs/{sha}"

    monkeypatch.setattr(dashboard_state, "source", lambda: Blobs)
    film = {"segments": [{"shows": {"world": "w"}}, {"shows": {"place": "hub"}}, {"shows": {"place": "base"}}]}
    beds = {"base": [{"sha": "b1"}], "hub": [], "lab": [{"sha": "l1"}]}
    assert make.bed_sound(film, {"sound_beds": beds}) == ("base", "blobs/b1")
    assert make.bed_sound({"segments": []}, {"sound_beds": beds}) == ("base", "blobs/b1")  # else the first with one
    assert make.bed_sound(film, {"sound_beds": {}}) == (None, None)
    assert make.record_of({"film": "f", "segments": []}, 1.0, None, 0.0)["bed"] == make.WAITING_BED


def test_the_setting_is_drawn_from_its_own_physics_to_the_pictures_scale():
    from score.dashboard.films.preview import scenes
    from score.review import setting
    bodies = setting.now()["bodies"]
    scale = scenes.scales(bodies)
    placed = scenes.placed(bodies, 0.0, scale)
    assert placed["sun"] == [0.0, 0.0, 0.0]
    mars_far = max(sum(value * value for value in scenes.placed(bodies, day, scale)["mars"]) ** 0.5
                   for day in range(0, 700, 10))
    mars = next(body for body in bodies if body["body"] == "mars")
    assert abs(mars_far - scenes.UNITS * (1 + mars["eccentricity"])) < 0.5  # its orbit's size the scene's 100 units
    moon = [a - b for a, b in zip(placed["moon"], placed["earth"])]
    earth = next(body for body in bodies if body["body"] == "earth")
    ring = (scenes.disc_size(earth) + 22.0) * scenes.UNITS / scenes.REACH
    assert 0.9 * ring < sum(value * value for value in moon) ** 0.5 < 1.1 * ring  # enlarged as the picture draws it


@pytest.mark.django_db(transaction=True)
def test_the_film_page_plays_its_rendered_preview_and_seeks_in_it(world, tmp_path, monkeypatch):
    from score.dashboard.tests.api_test import api
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    film = a_script([{"cut": "title"}, {"cut": "screen-take", "shows": {"page": "/"}, "seconds": 2}])
    script.save(settings.SCORE_HOME, film)
    video, record = script.preview_files(settings.SCORE_HOME, False, "trailer")
    video.parent.mkdir(parents=True)
    video.write_bytes(bytes(range(256)) * 40)
    record.write_text(json.dumps({"made_at": "2026-10-21T12:00:00+00:00", "seconds": 5.5, "script": film,
                                  "segments": [{"index": 1, "start": 0.0}, {"index": 2, "start": 3.5}]}))
    client = api()
    editor = editor_of(client.get("/film/trailer/").text)
    assert editor["preview"]["url"].startswith("/film-preview/trailer.mp4") and "screen-take" in editor["recorded"]
    part = client.get("/film-preview/trailer.mp4", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and part.content == (bytes(range(256)) * 40)[100:200]
    assert client.get("/film-preview/other.mp4").status_code == 404


def test_environment_1_demo_is_its_complete_default():
    """env1_demo is environment 1's default film, complete (owner, 2026-10-21): every segment names a real scene, the
    physics animation long enough to see an orbit, every zoom followed by a walk through its scenes (owner, 2026-10-24:
    "scale zoom after scale zoom and no walkthroughs in between"), inside its target."""
    film, origin = script.read(settings.SCORE_REPO, "/nonexistent", "env1_demo")
    assert origin == "starter" and film["default"] is True
    # the docking airlock: a scene added in the app on his kept Hangar plan, which the test's store does not hold
    assert script.faults(film, design_scenes() | {"docking_airlock"}) == []
    assert script.total_seconds(film) <= film["target_seconds"]
    animation = next(segment for segment in film["segments"] if segment["cut"] == "setting-animation")
    assert animation["seconds"] * animation["days_per_second"] >= 300  # Earth goes most of the way round the Sun
    cuts = [segment["cut"] for segment in film["segments"]]
    assert all(cuts[number + 1] == "walk-through" for number, cut in enumerate(cuts) if cut == "scale-zoom")
    walks = {segment["shows"]["place"] for segment in film["segments"] if segment["cut"] == "walk-through"}
    assert set(next(segment for segment in film["segments"] if segment["cut"] == "scale-zoom")["legs"][-1]["rooms"]) < walks


def locking(client, film, body):
    return client.post(f"/film/{film}/lock/", json.dumps(body), content_type="application/json")


def test_a_lock_is_kept_where_the_film_row_reads_it_and_stands_once_a_batch_bought_on_it(world, tmp_path, monkeypatch):
    """The Film step's Lock: the script as the editor shows it saved and locked in the cockpit's home (what the
    environment-film row reads), nothing saved over it while locked, Unlock until a batch buys a film row on it."""
    from score.dashboard.pages.models import Checkout
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    film = a_script([{"cut": "walk-through", "shows": {"place": "alpha"}}])
    owner = signed_in()
    assert locking(signed_in("other"), "trailer", film).status_code == 403
    assert locking(owner, "trailer", {**film, "film": "other"}).status_code == 409
    answer = locking(owner, "trailer", film)
    assert answer.status_code == 200 and answer.json() == {"said": "locked trailer", "locked": True}
    assert script.locked(settings.SCORE_HOME, "trailer") == film == script.read(tmp_path / "repo", settings.SCORE_HOME,
                                                                              "trailer")[0]
    assert script.locked_films(settings.SCORE_HOME, "world1") == ["trailer"]
    refused = owner.post("/film/trailer/save/", json.dumps(film), content_type="application/json")
    assert refused.status_code == 409 and refused.json()["faults"] == ["it is locked: unlock it to change it"]
    assert editor_of(owner.get("/film/trailer/").text)["locked"] is True
    assert locking(owner, "trailer", {}).json() == {"said": "unlocked trailer", "locked": False}
    assert script.locked(settings.SCORE_HOME, "trailer") is None
    locking(owner, "trailer", film)
    Checkout.objects.create(key="k" * 32, by="joey", state="launched",
                            items=[{"id": "beta-films", "nodes": {"demo-film@beta": {}}}])
    stands = locking(owner, "trailer", {})
    assert stands.status_code == 409 and "bought its film rows on this lock" in stands.json()["faults"][0]
    assert script.locked(settings.SCORE_HOME, "trailer") == film


def test_buy_leaves_out_the_film_rows_until_a_film_script_is_locked(world, tmp_path, monkeypatch):
    """Buy waits for the Film step as it waits for a scene's design: an item holding a film row is not bought, and
    the checkout refuses one, while no film script is locked."""
    import shutil
    from score.dashboard.checkout import flow
    from score.dashboard.state import screens
    shutil.rmtree(settings.SCORE_HOME / script.LOCKED_FOLDER, ignore_errors=True)  # the home is the session's
    price = {"likely_euros": 1.0, "high_euros": 2.0, "runs": 1}
    items = [{"id": f"alpha-{layer}", "place": "alpha", "layers": [layer], "places": ["alpha"],
              "nodes": {node: price}, "missing": []}
             for layer, node in (("stage", "assembly@alpha"), ("films", "demo-film@alpha"))]
    assert screens.film_waits() == "film script not locked"
    assert [item["id"] for item in screens.now_items(items, ["alpha"])] == ["alpha-stage"]
    assert any("film script not locked" in refusal for refusal in flow.item_refusals(items))
    html = signed_in().get("/buy/").content.decode()
    assert "film script not locked" in html and 'href="/film/"' in html
    script.lock(settings.SCORE_HOME, a_script([{"cut": "walk-through", "shows": {"place": "alpha"}}]))
    assert screens.film_waits() == ""
    assert [item["id"] for item in screens.now_items(items, ["alpha"])] == ["alpha-stage", "alpha-films"]
    assert not any("film" in refusal for refusal in flow.item_refusals(items))


SETTING = {"bodies": [{"body": "sun", "kelvin": 5772}, {"body": "kepler", "reference": "kepler", "radius_km": 2000.0},
                      {"body": "tess", "reference": "tess", "radius_km": 1000.0}]}
# Its plan: the body without the top scene first, so the journey's order (the top scene's body first) is the film's.
PLAN = {"maps": [{"on": "kepler", "sites": [{"place": "camp", "name": "Camp"}]},
                 {"on": "tess", "distances": [{"from": "pier", "to": "port", "metres": 80.0}],
                  "sites": [{"place": "port", "name": "Port"}, {"place": "pier", "name": "Pier",
                            "sky": {"worlds": [{"world": "kepler", "across": 2 * math.degrees(math.atan(0.02))}]}}]}]}


def test_an_environments_default_film_is_the_owners_structure_filled_from_its_own_scenes():
    """The owner's script for environment 1 as every environment's default (2026-10-21): the app's steps, then one
    shot from the setting down into the top scene's rooms, then on to every other top scene, body by body, every zoom
    followed by a walk through its scene (not a shell) and every scene it holds, parent before child (2026-10-24),
    here an environment that shares no name with his."""
    from score.dashboard.films import default
    within = {"dock": "port", "bar": "port", "bunk": "deck", "hold": "port", "deck": "port", "tent": "camp"}
    facts = default.facts_of("world7", "Environment 7", SETTING, PLAN, within, {"port": "The Port"},
                             {"tess": "tess_dust"})
    assert facts["top"] == "port" and [room for room, _ in facts["rooms"]] == ["dock", "bar", "hold"]
    assert [stop["place"] for stop in facts["stops"]] == ["port", "pier", "camp"]
    film = default.built("world7-film", facts)
    assert script.faults(film, {"port", "pier", "camp", "dock", "bar", "hold", "deck", "bunk", "tent"}) == []
    assert [segment["cut"] for segment in film["segments"]] == [
        "title", "screen-take", "setting-animation", "screen-take", "screen-take", "screen-take", "scale-zoom",
        *["walk-through"] * 5, "scale-zoom", "walk-through", "scale-zoom", "walk-through", "walk-through"]
    assert [segment["shows"]["place"] for segment in film["segments"][7:]] == [
        "dock", "bar", "hold", "deck", "bunk", "pier", "pier", "camp", "camp", "tent"]
    assert [segment["line"] for segment in film["segments"][-4::2]] == ["Outside", "Outside"]
    assert film["segments"][-1]["line"] == "Inside"
    assert script.total_seconds(film) <= film["target_seconds"] < script.total_seconds(film) + 5
    assert film["segments"][2]["seconds"] == 12.0
    pages = [segment["shows"].get("page") for segment in film["segments"] if segment["cut"] == "screen-take"]
    assert pages == ["/environments/world7/", "/environments/world7/", "/concept/dock/", "/concept/port/"]
    zoom = film["segments"][6]
    assert zoom["legs"][-1]["rooms"] == ["dock", "bar", "hold"] and zoom["legs"][3]["into"] == "dock"
    assert zoom["surfaces"] == {"tess": "tess_dust", "ground": "tess_dust"} and "kepler" in zoom["waiting"]
    pier, camp = film["segments"][-5], film["segments"][-3]
    assert [leg["layer"] for leg in pier["legs"]] == ["site", "place"] and pier["legs"][0]["from_place"] == "port"
    assert "Pier, 80 m from The Port" in json.dumps(pier) and pier["pip"]["concept"] == "pier"
    assert [leg["layer"] for leg in camp["legs"]] == ["world", "setting", "world", "site", "place", "room"]
    assert camp["legs"][0]["place"] == "pier" and camp["legs"][1]["from_body"] == "tess"
    assert "Kepler, 100,000 km away" in json.dumps(camp) and camp["legs"][-1]["rooms"] == ["tent"]
    assert camp["pip"]["to"] - camp["pip"]["from"] >= 3 and all(3 <= shown["seconds"] <= 20 for shown in (pier, camp))
    assert ".sp-card:nth-child(3)" in json.dumps(film["segments"][1]) and "world1" not in json.dumps(film)
    assert default.facts_of("world7", "E", {"bodies": []}, {"maps": []}, within, {}, {}) is None


def test_the_film_step_opens_on_the_environments_own_film(world, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    assert signed_in().get("/film/")["Location"] == "/film/world1-film/"
    script.save(settings.SCORE_HOME, {**a_script([]), "film": "mine", "default": True})
    assert signed_in("other").get("/film/")["Location"] == "/film/mine/"
    # the hosted home of 2026-10-21: a saved world1-film marked default and a saved copy of the starter without the
    # mark; the starter marked default still opens
    (tmp_path / "repo/data/films").mkdir(parents=True)
    (tmp_path / "repo/data/films/zz_demo.json").write_text(json.dumps({**a_script([]), "film": "zz_demo",
                                                                        "default": True}))
    script.save(settings.SCORE_HOME, {**a_script([]), "film": "zz_demo"})
    assert signed_in("third").get("/film/")["Location"] == "/film/zz_demo/"


def test_the_bed_starts_where_its_beats_fall_on_the_cuts_and_a_hum_at_its_start():
    from score.dashboard.films.preview import make
    import numpy
    rises = numpy.zeros(240)
    rises[[10, 58, 106, 154, 202]] = 5.0  # a beat every 2 s at 24 a second, the first 10 frames in
    assert make.beat_offset(rises, [4.0, 6.0], 24) == round(10 / 24, 3)
    assert make.beat_offset(numpy.full(240, 0.1), [4.0, 6.0], 24) == 0.0
    film = a_script([{"cut": "title", "transition": "fade-through-black", "seconds": 4},
                     {"cut": "text", "transition": "cross-fade", "seconds": 3},
                     {"cut": "text", "transition": "fade-through-black", "seconds": 3}])
    assert make.cut_moments(film) == [3.75, 6.5]


def test_a_scale_zoom_arrives_where_its_site_is_lit_unless_the_script_names_a_time():
    """#51: the Square's site at its scene time is on Earth's night side; the zoom lands at the first lit hour."""
    from score.dashboard.films.preview import scenes
    from score.review import setting
    night = "2099-10-01T14:00:00Z"
    site = {"place": "square", "name": "Square", "latitude": 22.28, "longitude": 114.16, "time": night}
    state = {"environment_concept": {"concept": {"setting": setting.now()}},
             "environment_plan": {"plan": {"time": night, "maps": [{"on": "earth", "sites": [site]}]}}}
    dark = scenes.day_of(night)
    assert scenes.sky_at(state, "square", dark)["sun"]["altitude"] < 0
    day, sky = scenes.arrival(state, "square")
    assert sky["sun"]["altitude"] >= scenes.LIT_DEGREES and 0 < day - dark < 1
    assert scenes.arrival(state, "square", night) == (dark, scenes.sky_at(state, "square", dark))


def test_a_body_is_drawn_in_the_face_its_row_made_else_a_plain_colour_said_waiting():
    """A body's face is its body-face row's (the state's body_faces), never a library name; while that row has not
    run the body is a plain colour of its own and the leg's tag says it waits."""
    from score.dashboard.films.preview import scenes
    from score.review import setting
    site = {"place": "square", "name": "Square", "latitude": 22.28, "longitude": 114.16}
    state = {"environment_concept": {"concept": {"setting": setting.now()}}, "body_faces": {"earth": {"hex": "#336699"}},
             "environment_plan": {"plan": {"time": "2099-10-01T14:00:00Z",
                                           "maps": [{"on": "earth", "name": "Earth", "sites": [site]}]}}}
    assert scenes.face_colour(state, "earth") == [0.2, 0.4, 0.6]
    assert scenes.face_colour(state, "moon") == scenes.face_colour({}, "moon") != scenes.face_colour({}, "mars")
    zoom = {"cut": "scale-zoom", "shows": {"place": "square"}, "seconds": 8,
            "legs": [{"layer": "setting", "seconds": 4}, {"layer": "world", "seconds": 4, "tag": "Plan"}]}
    setting_leg, world_leg = scenes.scene_for(state, zoom, 2)["legs"]
    assert setting_leg["tag"] == f"Moon, Mars: {scenes.WAITING}" and "waits" not in setting_leg
    assert world_leg["tag"] == "Plan" and world_leg["color"] == [0.2, 0.4, 0.6]


def test_the_state_knows_a_designed_bed_by_the_sound_stages_own_words():
    """local.DESIGNED_BED is the word the sound stage writes on a bed its design decided (an older bed is none)."""
    from score.dashboard.state import local
    assert f'"from": "{local.DESIGNED_BED}"' in (settings.SCORE_REPO / "score/stages/sound/__init__.py").read_text()
