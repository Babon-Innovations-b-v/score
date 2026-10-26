"""The plan review (pages/plans.py) on the fixture environment: a place's plan page once its scene inventory counts
(made from the pick, no Approve: the pick is the approval), its card's Plan button and design steps, his Keep kept as
his own (the plan stage then reads it), the inside places he names on the concept page, and anyone but the owner
refused. No model is called, nothing is spent."""
import contextlib
import json

import pytest

from score.dashboard.tests import fixture
from score.dashboard.tests.pages_test import signed_in
from score.review import plans

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def world(drafting):
    """The fixture environment still in design: its plans are made here."""
    return drafting


@pytest.fixture
def planned(world, monkeypatch, tmp_path):
    """alpha's concept picked and its inventory read from it, plans reading the fixture's data."""
    monkeypatch.setattr(plans, "DATA", world.data)
    monkeypatch.setattr(plans, "KEPT", tmp_path / "kept")
    monkeypatch.setattr(plans, "KEPT_INVENTORY", tmp_path / "kept-inventory")
    monkeypatch.setattr(plans, "KEPT_CONCEPT", tmp_path / "kept-concepts")
    sha = fixture.concept_of(world.store, "alpha")
    fixture.an_inventory_read(world.store, world.data, "alpha", sha)
    world.source.refresh()
    return world


def test_no_plan_page_numbers_before_the_inventory_counts(world, monkeypatch):
    monkeypatch.setattr(plans, "DATA", world.data)
    html = signed_in().get("/plan/alpha/", follow=True).content.decode()
    assert "after the inventory" in html and "plan-drawing" not in html  # owner 2026-10-20: no plan before it counts


def test_the_plan_page_shows_the_plan_made_from_the_pick_and_keeps_his_edit(planned):
    owner = signed_in()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert 'id="plan-drawing"' in html and "R1 1" in html and "Approve" not in html  # owner 2026-10-21: no Approve
    assert 'id="plan-saved"' in html and 'id="plan-keep"' not in html  # owner 2026-10-21: edits save on their own
    assert "data-v>R1 1: no size</span>" in html  # its row gives no size: a gap shown, never hidden
    card = owner.get("/places/").content.decode()
    assert 'href="/concept/alpha/#plan-part"' in card  # its card's Plan button: the design page's plan part
    plan = json.loads(html.split('<script id="plan-data" type="application/json">')[1].split("</script>")[0])
    plan["items"][0][1] = 2.5
    answer = owner.post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert answer.status_code == 200, answer.content
    assert plans.current(planned.store, "alpha")["how"] == "edited"
    assert json.loads((plans.KEPT / "alpha.json").read_text())["items"][0][1] == 2.5  # what the plan stage reads
    refused = signed_in("joey2").post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert refused.status_code == 403


def test_the_concept_page_names_inside_places_up_front(planned):
    owner = signed_in()
    answer = owner.post("/plan/alpha/named/", json.dumps({"names": ["Back Room", "loft"]}),
                        content_type="application/json")
    assert answer.status_code == 200, answer.content
    assert plans.named(planned.store, "alpha") == ["back_room", "loft"]
    holds = plans.current(planned.store, "alpha")["plan"]["holds"]
    assert [hold["place"] for hold in holds] == ["back_room", "loft"]
    planned.source.refresh()
    page = owner.get("/concept/alpha/").content.decode()
    assert '<li data-name="back_room"><span data-v>back_room</span><button type="button" class="chip-drop"' in page


def test_an_inside_place_his_kept_plan_adds_gets_a_card_and_a_concept_page(planned):
    owner = signed_in()
    owner.post("/plan/alpha/named/", json.dumps({"names": ["loft"]}), content_type="application/json")
    plan = plans.current(planned.store, "alpha")["plan"]
    answer = owner.post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert answer.status_code == 200, answer.content
    planned.source.refresh()
    assert 'href="/concept/loft/"' in signed_in("joey2").get("/places/?in=alpha").content.decode()
    assert owner.get("/concept/loft/").status_code == 200
    assert owner.get("/concept/attic/").status_code == 404


def test_a_rough_plan_offers_make_plan_and_his_click_writes_it_with_its_gaps_to_light(planned, monkeypatch):
    from score.dashboard.pages import concepts
    from score.review import plan_drawing, plan_writing, web
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)  # the thread's work, now
    # in units of its top-down drawing (100 a metre: its lamp row's metres, 6 x 0.4 m, measure it)
    fixture.an_inventory_read(planned.store, planned.data, "alpha", fixture.concept_of(planned.store, "alpha"),
                              size=[6.0, 0.4, 0.8])
    planned.source.refresh()
    answer = {"outline": [[0, 0], [600, 0], [600, 400], [0, 400]],
              "items": [{"row": "r1", "box_2d": [180, 0, 220, 600], "tall": 0.8}], "people": [[100, 100], [500, 350]],
              "openings": [{"kind": "door", "at": [300, 400], "wide": 90, "angle": 0, "swing": "left", "sill": 0.0,
                            "head": 2.1, "to": "outside"}]}  # its one door, in the south wall
    asked = []

    def written(store, place, euros, by):  # the writing's own process, its model call a stand-in
        asked.append(euros)
        finished = {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(answer)}]}}
        record, = plan_writing.write(store, [place], by, ask=lambda body: ({"candidates": [finished],
                                                                            "usageMetadata": {}}, 1.0))
        return json.loads(plan_writing.said(record))

    monkeypatch.setattr(web, "plan_write", written)
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(plan_drawing, "called", lambda wording, pictures, frame: (drawing_png(), 0.13, 1.0))
    monkeypatch.setattr(plan_writing, "cleared", lambda *found, **named: contextlib.nullcontext())
    monkeypatch.setattr("score.adapters.compute.require_cleared", lambda what, store=None: None)
    owner = signed_in()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    price = plan_writing.price(planned.store)  # the writing and its top-down drawing
    assert 'id="plan-write"' in html and f"EUR {price:.2f}" in html and "data-v>rough" in html
    sent = owner.post("/plan/alpha/write/", json.dumps({"euros": price}), content_type="application/json")
    assert sent.status_code == 200, sent.content
    assert asked == [price] and plans.current(planned.store, "alpha")["how"] == "written"
    planned.source.refresh()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert 'id="plan-write"' not in html and "data-v>written" in html and 'id="plan-section"' in html
    # r1 across the room cuts the north spot off its door: a gap, said plainly, lit on the drawing by its click
    assert "data-gap" in html and "the standing spot (north-west) cannot be reached on foot" in html
    assert 'data-at="[' in html
    assert "the concept drawn top down" in html  # the drawing it was measured from, the third picture


def drawing_png():
    import io
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (600, 600), (255, 255, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def a_draw(world, place, room):
    """A first draw of `place` in the store, its blob there, drawn on `room` (its hold on the plan above then)."""
    from score.review import concepts
    path = world.root / f"{place}-draw.png"
    path.write_bytes(fixture.picture((7, 200, 9)))
    sha = fixture.file_hash(path)
    world.store.put_blob(path, sha)
    concepts.recorded(world.store, f"concepts/{place}/draws/2026-10-21T09-00-00.json",
                      {"place": place, "sha": sha, "name": f"{place}-concept.png", "by": "joey",
                       "at": "2026-10-21T09:00:00+00:00", "room": room})
    return sha


def hosted_page(world, tmp_path, monkeypatch, settings, page):
    """(`page` as the hosted cockpit serves it from an export of the fixture's store, the export's WorldState)."""
    from score.dashboard import state
    from score.dashboard.state.exported import ExportedSource
    from score.dashboard.tests.fixture import exported
    world.source.refresh()
    exported(world, tmp_path / "export")
    source = ExportedSource(tmp_path / "export")
    monkeypatch.setattr(state, "source", lambda: source)
    settings.SCORE_MODE = "hosted"
    return signed_in("joey2").get(page).content.decode(), source.world_state()


def test_a_scene_merged_into_another_has_no_card_even_with_draws(planned, tmp_path, monkeypatch, settings):
    """Owner, 2026-10-21 ("nav again showed up here"): a scene he merged into another is no card anywhere, hosted too,
    whatever draws of it the store holds."""
    (planned.data / "places/within.json").write_text(json.dumps({
        "shells": {}, "within": {}, "merged": {"beta": {"into": "alpha"}}}))
    a_draw(planned, "beta", None)
    html, shown = hosted_page(planned, tmp_path, monkeypatch, settings, "/places/")
    assert shown.removed == ["beta"]
    assert 'href="/concept/beta/"' not in html and 'href="/place/beta/"' not in html
    # no scene of the design either, so no Draw all offers it (the old ship, 2026-10-21)
    assert "beta" not in planned.source.scenes() and "beta" not in shown.concept_undrawn


def test_a_draw_on_a_room_the_plan_above_changed_is_no_concept_on_its_card(planned, tmp_path, monkeypatch, settings):
    """Owner, 2026-10-21 ("all below would become need for redrawn"): a scene drawn on a room the plan above has
    since moved shows no picture as current and no Review; its card says the plan changed and offers the redraw."""
    (planned.data / "places/within.json").write_text(json.dumps({"shells": {}, "within": {"beta": {"within": "alpha"}}}))
    a_draw(planned, "beta", {"place": "beta", "x": 90.0, "y": 90.0, "w": 1.0, "d": 1.0})
    assert plans.room_of(planned.store, "beta") is not None  # alpha's plan lays it out, elsewhere
    html, shown = hosted_page(planned, tmp_path, monkeypatch, settings, "/places/?in=alpha")
    assert shown.plan_changed == ["beta"] and "beta" not in shown.concepts
    tile = html[html.index('href="/concept/beta/"'):].split('<div class="ptile-box">')[0]
    assert "plan changed" in tile and ">Redraw</a>" in tile and "<img" not in tile and "Review" not in tile
