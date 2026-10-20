"""The plan review (pages/plans.py) on the fixture environment: a place's plan page once its scene inventory counts
(made from the pick, no Approve: the pick is the approval), its card's Plan button and design steps, his Keep kept as
his own (the plan stage then reads it), the inside places he names on the concept page, and anyone but the owner
refused. No model is called, nothing is spent."""
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
    card = owner.get("/").content.decode()
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
