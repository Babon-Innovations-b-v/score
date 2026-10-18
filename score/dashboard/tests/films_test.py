"""The FILM pages and the film script (score/dashboard/films): a script's clock and checks, its render items priced
from measured frames only, the page with its free preview's data, saving to the cockpit's home only, the basket taking
only rows that exist, and world 1's starter script."""
import json
import re

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from score.dashboard.films import render, script
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
    assert script.timeline(film) == [(0.0, 4.0), (3.5, 3.5), (6.5, 2.0), (8.5, 3.0)]
    assert script.total_seconds(film) == 11.5
    film["defaults"] = {"walk-through": 5.0}
    assert script.total_seconds(film) == 13.0


def test_a_script_says_what_is_wrong_in_words():
    film = a_script([{"cut": "spin"}, {"cut": "isolate", "shows": {"place": "alpha"}},
                     {"cut": "step-card", "shows": {"place": "alpha", "step": "paint"}},
                     {"cut": "orbit", "shows": {"place": "gamma"}, "seconds": 99, "transition": "wipe"}])
    found = script.faults(film, {"alpha", "beta"})
    assert "segment 1: no cut type 'spin'" in found
    assert "segment 2 (Isolate a part) names no part" in found
    assert "segment 3: no framework step 'paint'" in found
    assert "segment 4: no transition 'wipe'" in found and any("99" in fault for fault in found)
    assert "segment 4: no place 'gamma'" in found
    assert script.faults({**film, "film": "Bad Name"}) and script.faults({"format": "other"})


def test_render_items_reuse_films_and_price_new_frames_from_measured_frames_only():
    media = {"alpha": {"film": {"url": "/files/a"}, "hero": {"url": "/files/h"}, "extras": {}},
             "beta": {"film": None, "hero": None, "extras": {}}}
    film = a_script([{"cut": "title"},
                     {"cut": "walk-through", "shows": {"place": "alpha"}},
                     {"cut": "walk-through", "shows": {"place": "alpha"}, "seconds": 7},
                     {"cut": "walk-through", "shows": {"place": "beta"}},
                     {"cut": "hero-still", "shows": {"place": "alpha"}},
                     {"cut": "exploded", "shows": {"place": "alpha"}},
                     {"cut": "step-card", "shows": {"place": "alpha", "step": "plan"}}])
    items = render.items(film, media)
    assert [item["how"] for item in items] == ["free", "reuse", "new", "basket", "reuse", "new", "free"]
    per_frame = render.MEASURED["look"]["euros"]
    assert items[2]["frames"] == 168 and items[2]["euros"] == round(168 * per_frame, 2)
    assert items[3]["node"] == "demo-film@beta" and items[3]["frames"] == render.FILM_FRAMES
    assert items[5]["frames"] == 144 and items[5]["euros"] is None  # an exploded view was never rendered on a card
    totals = render.totals(items)
    assert totals["unmeasured"] == ["exploded"] and totals["unmeasured_frames"] == 144
    assert totals["basket"] == ["demo-film@beta"] and totals["reused"] == 2 and totals["free"] == 2
    assert totals["euros"] == round(items[2]["euros"] + items[3]["euros"], 2)


def test_the_film_shot_matches_the_demo_film_rows():
    from score.stages import demo_film
    assert script.FILM_SHOT_SECONDS == demo_film.SECONDS - script.TRANSITION_SECONDS
    assert render.FILM_FRAMES == round(demo_film.SECONDS * 24) and script.FILM_SHOT_FROM == 2.0


def test_world1_starter_is_sound_and_gives_the_places_the_time():
    from score import stages
    film, origin = script.read(settings.SCORE_REPO, "/nonexistent", "k9")
    assert origin == "starter" and script.faults(film, set(stages.places(stages.world1()))) == []
    lengths = dict(zip(range(len(film["segments"])), script.timeline(film)))
    walks = sum(lengths[index][1] for index, segment in enumerate(film["segments"]) if segment["cut"] == "walk-through")
    assert walks > script.total_seconds(film) / 2
    cards = [segment for segment in film["segments"] if segment["cut"] == "step-card"]
    assert [card["shows"]["step"] for card in cards] == list(script.STEPS)  # the chain once
    assert len({card["shows"]["place"] for card in cards}) == 1
    assert script.total_seconds(film) <= film["target_seconds"]


def test_the_film_pages_render_with_the_preview_data(world, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    script.save(settings.SCORE_HOME, a_script([
        {"cut": "title", "text": "A trailer"},
        {"cut": "walk-through", "shows": {"place": "alpha"}, "text": "Alpha"},
        {"cut": "layer-split", "shows": {"place": "alpha"}}]))
    client = signed_in()
    listing = client.get("/film/").content.decode()
    assert "/film/trailer/" in listing and "A trailer" in listing
    html = client.get("/film/trailer/").content.decode()
    assert "/static/pages/film.js" in html and "importmap" in html and "What it costs to render" in html
    editor = editor_of(html)
    assert editor["origin"] == "saved" and editor["places"]["alpha"]["film"]["url"].startswith("/files/")
    assert set(editor["cuts"]) >= {"walk-through", "orbit", "hero-still", "exploded", "isolate", "layer-focus",
                                   "layer-split", "step-card", "before-after", "title", "text"}
    assert [item["how"] for item in editor["answer"]["items"]] == ["free", "reuse", "new"]
    assert editor["answer"]["totals"]["unmeasured"] == ["layer-split"]
    from score.dashboard.tests.pages_test import NODE, outside_details
    assert NODE.search(outside_details(html)) is None
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
    assert refused.status_code == 400 and "segment 1: no place 'nowhere'" in refused.json()["faults"]
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
