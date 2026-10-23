"""The environment's plan (score/review/environment_plan.py): its grounds and sites from the environment concept's
setting, each site's footprint, size and blocks its top scene's own plan (never written here), the written answer kept
under the fixed facts, what each site sees overhead worked out from it, his edit kept, and a plan made under another
version of the concept out of date. Two settings: environment 1's (the Sun, Earth, the Moon and Mars) and a single
house on a flat plot (its sun a light)."""
import json

import pytest

from score.review import environment_concept, environment_plan, plans
from score.review.setting_test import HOUSE
from score.store import Store

# the Base's plan laying out two of its modules in its rows' items, the hangar's the tallest
BASE = {"w": 60.0, "d": 50.0, "items": [["CENTRAL HUB", 20.0, 20.0, 18.0, 18.0, "", "item"],
                                        ["LARGE HANGAR", 0.0, 0.0, 16.0, 12.0, "", "item"],
                                        ["RADIO MAST", 50.0, 40.0, 1.0, 1.0, "", "item"],
                                        ["TYRE TRACKS", 0.0, 45.0, 30.0, 2.0, "", "item"]],
        "rows": {"CENTRAL HUB": ["central_hub"], "LARGE HANGAR": ["large_hangar"]},
        "shapes": {"CENTRAL HUB": {"shape": "circle", "tall": 6.0}, "LARGE HANGAR": {"tall": 15.0},
                   "RADIO MAST": {"tall": 12.0}, "TYRE TRACKS": {"tall": 0.0}},
        "holds": [{"place": "hub", "row": "central_hub", "x": 20.0, "y": 20.0, "w": 18.0, "d": 18.0},
                  {"place": "hangar", "row": "large_hangar", "x": 0.0, "y": 0.0, "w": 16.0, "d": 12.0}]}


@pytest.fixture()
def store(tmp_path):
    return Store.in_folder(tmp_path)


@pytest.fixture()
def scene_plans(monkeypatch):
    """Each top scene's plan as its plan page shows it (plans.current): the Base's above, the others 20 m squares."""
    shown = {place: {"w": 20.0, "d": 20.0} for place in ("square", "wreck", "old_station", "campgrounds")}
    shown["base"] = BASE
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": shown[place]} if place in shown else None)
    return shown


def sites_of(plan):
    return {world["on"]: [site["place"] for site in world["sites"]] for world in plan["maps"]}


def site_in(plan, place):
    return next(site for world in plan["maps"] for site in world["sites"] if site["place"] == place)


def kept_setting(store, setting, locked=True):
    concept = environment_concept.prefilled([])
    return environment_concept.saved(store, environment_plan.world_name(), {**concept, "setting": setting}, locked,
                                     "joey")


def test_each_top_scene_stands_where_the_setting_puts_it_shaped_by_its_own_plan(store, scene_plans):
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"earth": ["square"], "moon": ["wreck", "old_station", "base"], "mars": ["campgrounds"]}
    moon = next(world for world in plan["maps"] if world["on"] == "moon")
    assert moon["radius_m"] == 1737400.0  # the Moon's true radius, never the game's 220 m ball
    apart = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert apart[("old_station", "base")] == pytest.approx(62.5, abs=0.5) and len(apart) == 3
    base = site_in(plan, "base")
    assert base["size"] == [60.0, 50.0, 15.0]  # its plan's wide and deep, its tallest thing
    assert base["footprint"] == [[-30.0, -25.0], [30.0, -25.0], [30.0, 25.0], [-30.0, 25.0]]  # about its middle
    blocks = {block["name"]: block for block in base["blocks"]}
    assert set(blocks) == {"hub", "hangar", "RADIO MAST"}  # its child scenes by place, a standing thing; no tracks
    assert blocks["hangar"]["tall"] == 15.0 and blocks["hub"]["roof"] == "dome"
    assert blocks["hub"]["points"][0] == [-10.0, -5.0]  # at its hold, in site metres
    assert (base["latitude"], base["longitude"]) == (55.0, 0.0) and base["overhead"] is None  # no scene time yet: a gap
    assert min(spot[2] for spot in base["terrain"]["spots"]) > -0.02  # 100 m on the Moon: all but flat
    assert "Base: no scene time" in plan["gaps"] and not any("place on its ground" in gap for gap in plan["gaps"])
    assert {body["body"] for body in plan["setting"]["bodies"]} == {"sun", "earth", "moon", "mars"}


def test_a_site_without_a_plan_is_a_gap(store, scene_plans):
    del scene_plans["wreck"]
    plan = environment_plan.derived(store)
    assert site_in(plan, "wreck")["size"] is None and "Wreck: no plan yet" in plan["gaps"]


def bearing_from(plan, still, mover):
    """(east, south) unit bearing of `mover` from `still` on the plan's map."""
    one, two = site_in(plan, still)["at"], site_in(plan, mover)["at"]
    east, south = two[0] - one[0], two[1] - one[1]
    return east / (east ** 2 + south ** 2) ** 0.5, south / (east ** 2 + south ** 2) ** 0.5


def test_sites_that_would_overlap_are_moved_clear_along_their_own_bearings(store, scene_plans):
    before = environment_plan.derived(store)
    scene_plans["base"] = {"w": 110.0, "d": 110.0}  # its true plan: wider than the 57 m to the wreck
    plan = environment_plan.derived(store)
    assert not any("overlap" in gap for gap in plan["gaps"])
    base = site_in(plan, "base")
    assert (base["latitude"], base["longitude"]) == (55.0, 0.0)  # the larger stands where the physics puts it
    for mover in ("wreck", "old_station"):
        assert bearing_from(plan, "base", mover) == pytest.approx(bearing_from(before, "base", mover), abs=1e-3)
        apart = [abs(site_in(plan, mover)["at"][axis] - base["at"][axis]) for axis in (0, 1)]
        assert max(apart) == pytest.approx(55.0 + 10.0 + environment_plan.CLEAR_M, abs=0.05)  # just clear, no more
    moon = next(world for world in plan["maps"] if world["on"] == "moon")
    found = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert found[("wreck", "base")] > 75.0  # the page's distances follow


def test_a_site_the_creator_placed_himself_stays_and_two_of_his_stay_a_gap(store, scene_plans):
    scene_plans["base"] = {"w": 110.0, "d": 110.0}
    setting = environment_concept.setting_of(store)
    kept_setting(store, setting)  # his first: the physics' proposal, cleared like any
    assert not any("overlap" in gap for gap in environment_plan.derived(store)["gaps"])
    his = [{**site, "longitude": 0.0005} if site["place"] == "old_station" else site for site in setting["sites"]]
    kept_setting(store, {**setting, "sites": his})  # his own move of the old station, 34 m south of the base
    plan = environment_plan.derived(store)
    old = site_in(plan, "old_station")
    assert (old["latitude"], old["longitude"]) == (54.999165, 0.0005)
    assert site_in(plan, "base")["latitude"] != 55.0 and not any("overlap" in gap for gap in plan["gaps"])
    both = [{**site, "latitude": 55.0, "longitude": 0.0005} if site["place"] == "base" else site for site in his]
    kept_setting(store, {**setting, "sites": both})
    assert "Old station and Base overlap on Moon: move one in the physics" in environment_plan.derived(store)["gaps"]


NEW = "a-new-environment"  # no world of the repository's: any environment's setting and plans


def test_a_new_environment_on_one_plot_places_by_physics_until_plans_land_then_clears(store, monkeypatch):
    shown = {"house": {"w": 12.0, "d": 9.0}}
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": shown[place]} if place in shown else None)
    farm = {**HOUSE, "sites": [*HOUSE["sites"], {"place": "shed", "on": "meadow", "x": 8.0, "y": 0.0, "height_m": 0}]}
    environment_concept.saved(store, NEW, {**environment_concept.prefilled([]), "setting": farm}, True, "joey")
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "shed")["at"] == [8.0, 0.0] and "Shed: no plan yet" in plan["gaps"]  # the physics' spot
    shown["shed"] = {"w": 4.0, "d": 4.0}  # its plan lands: 8 m from a 12 m house, so it would overlap
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "house")["at"] == [0.0, 0.0]
    assert site_in(plan, "shed")["at"] == [6.0 + 2.0 + environment_plan.CLEAR_M, 0.0] and plan["gaps"] == [
        "House: no scene time", "Shed: no scene time"]
    his = {**farm, "sites": [farm["sites"][0], {**farm["sites"][1], "x": 5.0}]}  # he moves the shed himself
    environment_concept.saved(store, NEW, {**environment_concept.prefilled([]), "setting": his}, True, "joey")
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "shed")["at"] == [5.0, 0.0]  # his spot wins; the house steps aside along its bearing
    assert site_in(plan, "house")["at"] == [5.0 - 6.0 - 2.0 - environment_plan.CLEAR_M, 0.0]


def test_sites_on_different_grounds_are_never_compared(store, monkeypatch):
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": {"w": 30.0, "d": 30.0}})
    two = {**HOUSE, "plots": [*HOUSE["plots"], {"name": "Yard", "gravity": 9.81}],
           "sites": [*HOUSE["sites"], {"place": "barn", "on": "yard", "x": 0.0, "y": 0.0, "height_m": 0}]}
    environment_concept.saved(store, NEW, {**environment_concept.prefilled([]), "setting": two}, True, "joey")
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "house")["at"] == site_in(plan, "barn")["at"] == [0.0, 0.0]
    assert not any("overlap" in gap or "one spot" in gap for gap in plan["gaps"])


def test_sites_on_a_plot_are_moved_clear_across_it():
    sites = [{"place": "barn", "x": 0.0, "y": 0.0, "footprint": [[-20, -10], [20, -10], [20, 10], [-20, 10]]},
             {"place": "shed", "x": 0.0, "y": 15.0, "footprint": [[-2, -2], [2, -2], [2, 2], [-2, 2]]}]
    barn, shed = environment_plan.cleared(sites, None)
    assert barn == sites[0] and shed["x"] == 0.0 and shed["y"] == 10.0 + 2.0 + environment_plan.CLEAR_M


def test_sites_kilometres_apart_on_the_moon_are_that_far_on_its_map(store, scene_plans):
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
    """A written answer: a time for every site, and a latitude, size, outline and block it may not take."""
    return {"time": "2099-06-01T12:00:00Z", "maps": [
        {"on": world["on"], "ground": "grey dust", "sites": [
            {"place": site["place"], "time": "2099-06-01T13:00:00Z", "latitude": 10.0, "longitude": 10.0,
             "size": [120.0, 110.0, 18.0], "footprint": [[0, 0], [120, 0], [120, 110]],
             "blocks": [{"name": "a tower", "points": [[0, 0], [5, 0], [5, 5]], "tall": 30}],
             "terrain": {"spots": [[50, 0, -3.5]]}} for site in world["sites"]]} for world in plan["maps"]]}


def test_a_written_plan_keeps_the_fixed_facts_and_works_out_what_each_site_sees_overhead(store, scene_plans):
    free = environment_plan.derived(store)
    plan = environment_plan.plan_from(answer_of(free), free, store)
    assert plan["gaps"] == [] and plan["time"] == "2099-06-01T12:00:00Z"
    base, square, wreck = site_in(plan, "base"), site_in(plan, "square"), site_in(plan, "wreck")
    assert base["size"] == [60.0, 50.0, 15.0] and base["latitude"] == 55.0  # its plan's shape, the setting's place
    assert square["size"] == [20.0, 20.0, 0.0] and square["blocks"] == []  # a written size or block never stands
    earth = next(body for body in base["overhead"]["bodies"] if body["body"] == "earth")
    assert 1.75 < earth["across"] < 2.05 and earth["altitude"] > 0  # seen from the Moon's near side: about 1.9 degrees
    assert [50.0, 0.0, -3.5] in wreck["terrain"]["spots"]


def test_a_sites_shape_follows_its_scenes_plan_after_the_writing(store, scene_plans):
    free = environment_plan.derived(store)
    environment_plan.edited(store, environment_plan.plan_from(answer_of(free), free, store), "joey")
    scene_plans["square"] = {"w": 29.0, "d": 29.0, "shapes": {"FLOODLIGHT TOWER": {"tall": 18.0}}}
    assert environment_plan.site_of(store, "square")["size"] == [29.0, 29.0, 18.0]  # read again, never kept apart


def test_his_edit_is_kept_and_settled_again(store, scene_plans):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site.update({"time": "2099-06-01T20:00:00Z", "latitude": 1.0, "size": [1.0, 1.0, 1.0]})
    record = environment_plan.edited(store, plan, "joey")
    shown = environment_plan.current(store)
    assert shown["how"] == "edited" and shown["plan"] == record["plan"] and shown["plan"]["gaps"] == []
    square = environment_plan.site_of(store, "square")
    assert square["on"] == "earth" and square["latitude"] == 22.28  # where it stands is the setting's
    assert square["size"] == [20.0, 20.0, 0.0]  # its size its plan's
    assert square["overhead"]["lights"][0]["altitude"] < 0  # 4 in the morning in Hong Kong
    with pytest.raises(environment_plan.Refused):
        environment_plan.edited(store, {"maps": "none"}, "joey")


def test_a_plan_made_under_another_concept_is_out_of_date(store, scene_plans):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site["time"] = "2099-06-01T20:00:00Z"
    environment_plan.edited(store, plan, "joey")
    assert environment_plan.current(store)["how"] == "edited"
    kept_setting(store, environment_concept.setting_of(store), locked=False)  # unlocked: a new version
    assert environment_plan.current(store)["how"] == "derived"


def test_a_house_on_a_plot_stands_on_flat_ground_under_its_sun_light(store, monkeypatch):
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": {"w": 12.0, "d": 9.0}})
    kept_setting(store, HOUSE)
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"meadow": ["house"]} and plan["maps"][0]["radius_m"] is None
    house = plan["maps"][0]["sites"][0]
    assert house["at"] == [0.0, 0.0] and {spot[2] for spot in house["terrain"]["spots"]} == {0.0}
    house["time"] = "2024-03-20T12:00:00Z"
    edited = environment_plan.edited(store, plan, "joey")["plan"]
    seen = edited["maps"][0]["sites"][0]["overhead"]
    assert seen["bodies"] == [] and seen["lights"][0]["altitude"] == pytest.approx(38.0, abs=0.01)


def test_the_plan_writer_writes_it_under_the_allowance_and_a_refused_answer_is_no_plan(store, monkeypatch, scene_plans):
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
    assert record["euros"] == 0.07 and '"radius m": 1737400.0' in told
    assert environment_plan.current(store)["how"] == "written" and record["plan"]["gaps"] == []
    bad = environment_plan.write(store, "the allowance", ask=lambda body: ({"candidates": []}, 1.0), clear=clear)
    assert bad["refused"] and environment_plan.current(store)["how"] == "written"


def test_no_two_sites_on_one_body_share_a_spot_unless_the_setting_puts_them_there(store, scene_plans):
    plan = environment_plan.derived(store)
    for world in plan["maps"]:
        assert all(found["metres"] >= environment_plan.SAME_SPOT for found in world["distances"]), world["on"]
    assert not any("one spot" in gap for gap in plan["gaps"])
    setting = environment_concept.setting_of(store)
    stacked = [{**site, "latitude": 55.0, "longitude": 0.0} if site["place"] == "old_station" else site
               for site in setting["sites"]]
    kept_setting(store, {**setting, "sites": stacked})  # the creator's own setting: kept, and named as a gap
    assert "Old station and Base stand on one spot of Moon" in environment_plan.derived(store)["gaps"]
