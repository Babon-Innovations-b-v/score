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
def planned(world, monkeypatch, tmp_path):
    """alpha's concept picked and its inventory read from it, plans reading the fixture's data; alpha's plan."""
    monkeypatch.setattr(plans, "DATA", world.data)
    monkeypatch.setattr(plans, "KEPT", tmp_path / "kept")
    monkeypatch.setattr(plans, "KEPT_INVENTORY", tmp_path / "kept-inventory")
    monkeypatch.setattr(plans, "KEPT_CONCEPT", tmp_path / "kept-concepts")
    (world.data / "plans").mkdir(exist_ok=True)
    (world.data / "plans/alpha.json").write_text(json.dumps({
        "title": "ALPHA", "shell": "kit", "w": 6.0, "d": 4.0, "height": "ceiling 3 m",
        "doors": [["S", 3.0, 0.9, "DOOR"]], "leads": {"S": {"to": "outside", "why": "its one door"}}, "items": []}))
    sha = json.loads((world.data / "places/concepts.json").read_text())["concepts"]["alpha"]["sha256"]
    fixture.an_inventory_read(world.store, world.data, "alpha", sha)
    world.source.refresh()
    return world


def test_no_plan_page_numbers_before_the_inventory_counts(world, monkeypatch):
    monkeypatch.setattr(plans, "DATA", world.data)
    html = signed_in().get("/plan/alpha/").content.decode()
    assert "inventory to read" in html and "plan-drawing" not in html


def test_the_plan_page_shows_the_plan_made_from_the_pick_and_keeps_his_edit(planned):
    owner = signed_in()
    html = owner.get("/plan/alpha/").content.decode()
    assert 'id="plan-drawing"' in html and "R1 1" in html and "Approve" not in html and 'id="plan-keep"' in html
    assert "data-v>R1 1: no size</span>" in html  # its row gives no size: a gap shown, never hidden
    card = owner.get("/places/").content.decode()
    assert 'href="/plan/alpha/"' in card  # its card's Plan button
    plan = json.loads(html.split('<script id="plan-data" type="application/json">')[1].split("</script>")[0])
    plan["items"][0][1] = 2.5
    answer = owner.post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert answer.status_code == 200, answer.content
    assert plans.current(planned.store, "alpha")["how"] == "edited"
    assert json.loads((plans.KEPT / "alpha.json").read_text())["items"][0][1] == 2.5  # what the plan stage reads
    refused = signed_in("joey2").post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert refused.status_code == 403


def test_the_concept_page_names_inside_places_up_front(planned):
    answer = signed_in().post("/plan/alpha/named/", json.dumps({"names": ["Back Room", "loft"]}),
                              content_type="application/json")
    assert answer.status_code == 200, answer.content
    assert plans.named(planned.store, "alpha") == ["back_room", "loft"]
    holds = plans.current(planned.store, "alpha")["plan"]["holds"]
    assert [hold["place"] for hold in holds] == ["back_room", "loft"]


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
    from score.review import plan_writing, web
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)  # the thread's work, now
    answer = {"items": [{"row": "r1", "x": 3.0, "y": 2.0, "wide": 6.0, "deep": 0.4, "tall": 0.8}],
              "people": [[1.0, 1.0], [5.0, 3.5]]}
    asked = []

    def written(store, place, euros, by):  # the writing's own process, its model call a stand-in
        asked.append(euros)
        record, = plan_writing.write(store, [place], by, ask=lambda body: ({"candidates": [{"content": {"parts": [
            {"text": json.dumps(answer)}]}}], "usageMetadata": {}}, 1.0))
        return json.loads(plan_writing.said(record))

    monkeypatch.setattr(web, "plan_write", written)
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(plan_writing, "cleared", lambda *found, **named: contextlib.nullcontext())
    monkeypatch.setattr("score.adapters.compute.require_cleared", lambda what, store=None: None)
    owner = signed_in()
    html = owner.get("/plan/alpha/").content.decode()
    assert 'id="plan-write"' in html and "EUR 0.05" in html and ">rough<" in html
    sent = owner.post("/plan/alpha/write/", json.dumps({"euros": 0.05}), content_type="application/json")
    assert sent.status_code == 200, sent.content
    assert asked == [0.05] and plans.current(planned.store, "alpha")["how"] == "written"
    planned.source.refresh()
    html = owner.get("/plan/alpha/").content.decode()
    assert 'id="plan-write"' not in html and ">written<" in html and 'id="plan-section"' in html
    # r1 across the room cuts the north spot off its door: a gap, said plainly, lit on the drawing by its click
    assert "data-gap" in html and "the standing spot (north-west) cannot be reached on foot" in html
    assert 'data-at="[' in html
