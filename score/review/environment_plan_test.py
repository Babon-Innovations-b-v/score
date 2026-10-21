"""The environment's plan (score/review/environment_plan.py): its worlds and sites from data, the written answer kept
under the fixed facts, each site's sky worked out from the physics, his edit kept."""
import json

import pytest

from score.review import environment_plan
from score.store import Store


@pytest.fixture()
def store(tmp_path):
    return Store.in_folder(tmp_path)


def sites_of(plan):
    return {world["world"]: [site["place"] for site in world["sites"]] for world in plan["maps"]}


def test_each_top_place_stands_on_the_world_its_ground_plan_seats_it_on(store):
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"earth": ["square"], "moon": ["wreck", "old_station", "base"], "mars": ["campgrounds"]}
    moon = next(world for world in plan["maps"] if world["world"] == "moon")
    apart = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert 40 < apart[("old_station", "base")] < 90 and len(apart) == 3
    base = next(site for site in moon["sites"] if site["place"] == "base")
    assert len(base["blocks"]) == 12 and base["size"][2] == pytest.approx(15.0)  # its modules; the hangar's walls
    assert base["latitude"] is not None and base["sky"] is None  # no scene time yet: a gap
    assert "Base: no scene time" in plan["gaps"] and "Square: no latitude and longitude" in plan["gaps"]
    assert set(plan["bodies"]["worlds"]) == {"earth", "moon", "mars"}  # the physics state rides with it


def answer_of(plan):
    """A written answer: a time for every site, the Square's real place, a block the base must not take."""
    return {"time": "2099-06-01T12:00:00Z", "maps": [
        {"world": world["world"], "ground": "grey dust", "sites": [
            {"place": site["place"], "time": "2099-06-01T13:00:00Z", "latitude": 22.29, "longitude": 114.17,
             "blocks": [{"name": "a tower", "points": [[0, 0], [5, 0], [5, 5]], "tall": 30}],
             "terrain": {"spots": [[50, 0, -3.5]]}} for site in world["sites"]]} for world in plan["maps"]]}


def test_a_written_plan_keeps_the_fixed_facts_and_works_out_each_sky(store):
    free = environment_plan.derived(store)
    facts = environment_plan.facts_of(store)
    plan = environment_plan.plan_from(answer_of(free), free, facts)
    assert plan["gaps"] == [] and plan["time"] == "2099-06-01T12:00:00Z"
    sites = {site["place"]: site for world in plan["maps"] for site in world["sites"]}
    base, square, wreck = sites["base"], sites["square"], sites["wreck"]
    assert len(base["blocks"]) == 12 and base["latitude"] != 22.29  # its parts and the game's Moon frame stand
    assert square["latitude"] == 22.29 and square["blocks"][0]["name"] == "a tower"  # written where data says nothing
    earth = next(world for world in base["sky"]["worlds"] if world["world"] == "earth")
    assert 1.75 < earth["across"] < 2.05 and earth["altitude"] > 0  # seen from the Moon's near side
    assert [50.0, 0.0, -3.5] in wreck["terrain"]["spots"]
    assert environment_plan.distances([{"place": "a", "at": [0, 0]}, {"place": "b", "at": [3, 4]}]) == [
        {"from": "a", "to": "b", "metres": 5.0}]


def test_his_edit_is_kept_and_settled_again(store):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site.update({"time": "2099-06-01T20:00:00Z", "latitude": site["latitude"] or 22.29,
                         "longitude": site["longitude"] or 114.17})
    record = environment_plan.edited(store, plan, "joey")
    shown = environment_plan.current(store)
    assert shown["how"] == "edited" and shown["plan"] == record["plan"] and shown["plan"]["gaps"] == []
    square = environment_plan.site_of(store, "square")
    assert square["world"] == "earth" and square["sky"]["sun"]["altitude"] < 0  # 4 in the morning in Hong Kong
    with pytest.raises(environment_plan.Refused):
        environment_plan.edited(store, {"maps": "none"}, "joey")


def test_the_plan_writer_writes_it_under_the_allowance_and_a_refused_answer_is_no_plan(store, monkeypatch):
    from score.adapters import compute
    from score.review import plan_writing
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.07)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    free, asked, clears = environment_plan.derived(store), [], []

    def ask(body):
        asked.append(body)
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(answer_of(free))}]}}]}, 2.0

    def clear(store, places, euros, node):
        clears.append((node, places))
        return compute.reading_clearance(store, places, euros, node=node)
    record = environment_plan.write(store, "the allowance", ask=ask, clear=clear)
    assert clears == [(compute.PLAN_WRITING, [f"environment-{environment_plan.world_name()}"])]
    assert record["euros"] == 0.07 and '"ball fall spots"' in asked[0]["contents"][0]["parts"][0]["text"]
    assert environment_plan.current(store)["how"] == "written" and record["plan"]["gaps"] == []
    bad = environment_plan.write(store, "the allowance", ask=lambda body: ({"candidates": []}, 1.0), clear=clear)
    assert bad["refused"] and environment_plan.current(store)["how"] == "written"
