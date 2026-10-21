"""The environment's plan (score/review/environment_plan.py): its grounds and sites from the environment concept's
setting at true sizes, the written answer kept under the fixed facts, what each site sees overhead worked out from
it, his edit kept, and a plan made under another version of the concept out of date. Two settings: environment 1's
(the Sun, Earth, the Moon and Mars) and a single house on a flat plot (its sun a light)."""
import json

import pytest

from score.review import environment_concept, environment_plan
from score.review.setting_test import HOUSE
from score.store import Store


@pytest.fixture()
def store(tmp_path):
    return Store.in_folder(tmp_path)


def sites_of(plan):
    return {world["on"]: [site["place"] for site in world["sites"]] for world in plan["maps"]}


def kept_setting(store, setting, locked=True):
    concept = environment_concept.prefilled([])
    return environment_concept.saved(store, environment_plan.world_name(), {**concept, "setting": setting}, locked,
                                     "joey")


def test_each_top_place_stands_where_the_setting_puts_it_at_true_size(store):
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"earth": ["square"], "moon": ["wreck", "old_station", "base"], "mars": ["campgrounds"]}
    moon = next(world for world in plan["maps"] if world["on"] == "moon")
    assert moon["radius_m"] == 1737400.0  # the Moon's true radius, never the game's 220 m ball
    apart = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert apart[("old_station", "base")] == pytest.approx(62.5, abs=0.5) and len(apart) == 3
    base = next(site for site in moon["sites"] if site["place"] == "base")
    assert len(base["blocks"]) == 12 and base["size"][2] == pytest.approx(15.0)  # its modules; the hangar's walls
    assert (base["latitude"], base["longitude"]) == (55.0, 0.0) and base["overhead"] is None  # no scene time yet: a gap
    assert min(spot[2] for spot in base["terrain"]["spots"]) > -0.02  # 100 m on the Moon: all but flat
    assert "Base: no scene time" in plan["gaps"] and not any("place on its ground" in gap for gap in plan["gaps"])
    assert {body["body"] for body in plan["setting"]["bodies"]} == {"sun", "earth", "moon", "mars"}


def test_sites_kilometres_apart_on_the_moon_are_that_far_on_its_map(store):
    setting = environment_concept.setting_of(store)
    moved = [{**site, "latitude": 55.0, "longitude": 0.1} if site["place"] == "old_station" else site
             for site in setting["sites"]]
    kept_setting(store, {**setting, "sites": moved})
    moon = next(world for world in environment_plan.derived(store)["maps"] if world["on"] == "moon")
    apart = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert apart[("old_station", "base")] == pytest.approx(1737400 * 0.1 * 0.01745329 * 0.573576, rel=1e-3)  # ~1.7 km
    old = next(site for site in moon["sites"] if site["place"] == "old_station")
    base = next(site for site in moon["sites"] if site["place"] == "base")
    assert old["at"][0] - base["at"][0] == pytest.approx(apart[("old_station", "base")], rel=1e-3)  # due east


def answer_of(plan):
    """A written answer: a time for every site, a latitude it may not take, a block the base must not take."""
    return {"time": "2099-06-01T12:00:00Z", "maps": [
        {"on": world["on"], "ground": "grey dust", "sites": [
            {"place": site["place"], "time": "2099-06-01T13:00:00Z", "latitude": 10.0, "longitude": 10.0,
             "blocks": [{"name": "a tower", "points": [[0, 0], [5, 0], [5, 5]], "tall": 30}],
             "terrain": {"spots": [[50, 0, -3.5]]}} for site in world["sites"]]} for world in plan["maps"]]}


def test_a_written_plan_keeps_the_fixed_facts_and_works_out_what_each_site_sees_overhead(store):
    free = environment_plan.derived(store)
    plan = environment_plan.plan_from(answer_of(free), free, store)
    assert plan["gaps"] == [] and plan["time"] == "2099-06-01T12:00:00Z"
    sites = {site["place"]: site for world in plan["maps"] for site in world["sites"]}
    base, square, wreck = sites["base"], sites["square"], sites["wreck"]
    assert len(base["blocks"]) == 12 and base["latitude"] == 55.0  # its parts and the setting's place stand
    assert square["latitude"] == 22.28 and square["blocks"][0]["name"] == "a tower"  # written where data says nothing
    earth = next(body for body in base["overhead"]["bodies"] if body["body"] == "earth")
    assert 1.75 < earth["across"] < 2.05 and earth["altitude"] > 0  # seen from the Moon's near side: about 1.9 degrees
    assert [50.0, 0.0, -3.5] in wreck["terrain"]["spots"]


def test_his_edit_is_kept_and_settled_again(store):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site.update({"time": "2099-06-01T20:00:00Z", "latitude": 1.0})
    record = environment_plan.edited(store, plan, "joey")
    shown = environment_plan.current(store)
    assert shown["how"] == "edited" and shown["plan"] == record["plan"] and shown["plan"]["gaps"] == []
    square = environment_plan.site_of(store, "square")
    assert square["on"] == "earth" and square["latitude"] == 22.28  # where it stands is the setting's
    assert square["overhead"]["lights"][0]["altitude"] < 0  # 4 in the morning in Hong Kong
    with pytest.raises(environment_plan.Refused):
        environment_plan.edited(store, {"maps": "none"}, "joey")


def test_a_plan_made_under_another_concept_is_out_of_date(store):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site["time"] = "2099-06-01T20:00:00Z"
    environment_plan.edited(store, plan, "joey")
    assert environment_plan.current(store)["how"] == "edited"
    kept_setting(store, environment_concept.setting_of(store), locked=False)  # unlocked: a new version
    assert environment_plan.current(store)["how"] == "derived"


def test_a_house_on_a_plot_stands_on_flat_ground_under_its_sun_light(store):
    kept_setting(store, HOUSE)
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"meadow": ["house"]} and plan["maps"][0]["radius_m"] is None
    house = plan["maps"][0]["sites"][0]
    assert house["at"] == [0.0, 0.0] and {spot[2] for spot in house["terrain"]["spots"]} == {0.0}
    house["time"] = "2024-03-20T12:00:00Z"
    edited = environment_plan.edited(store, plan, "joey")["plan"]
    seen = edited["maps"][0]["sites"][0]["overhead"]
    assert seen["bodies"] == [] and seen["lights"][0]["altitude"] == pytest.approx(38.0, abs=0.01)


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
    told = asked[0]["contents"][0]["parts"][0]["text"]
    assert record["euros"] == 0.07 and '"ball fall spots"' in told and '"radius m": 1737400.0' in told
    assert environment_plan.current(store)["how"] == "written" and record["plan"]["gaps"] == []
    bad = environment_plan.write(store, "the allowance", ask=lambda body: ({"candidates": []}, 1.0), clear=clear)
    assert bad["refused"] and environment_plan.current(store)["how"] == "written"
