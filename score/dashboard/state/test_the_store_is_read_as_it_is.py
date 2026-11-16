"""Invariant: the dashboard reads the store and the runner's figures as they are: the places grouped by the look rule
and each stage by the stage table's reads (never a hand list), the month's money a total that is never whole while a
line is partial or unread with no stop or cost set here, and the plan showing what the accepted assembly laid.

Breaks that turn test_the_store_is_read_as_it_is red (each applied once and seen red, then reverted):
- groups.look_of: drop the `prologue_<place>` name (`(f"prologue_{place}", place)` -> `(place,)`) -> LOOK_OF row beta
- groups.label: drop the PEOPLE prefix branch -> LABELS row people-dress-nev-work
- groups.layers: drop the `reads_assembly` shortcut (`row.name == "assembly" or reads_assembly(...)` ->
  `row.name == "assembly"`) -> the made-up stage table's layers
- groups.short_name: `len(style.places) == 1` -> `>= 1` -> the short names of the launch, camp and old station
- money.total: `whole=not gaps` -> `whole=True` -> MONEY row "a partial line"
- money.with_bill_days: `{**days.get(today, {}), **read}` -> `read` -> the second read of the month keeps its day
- groups.LAYER_OF_INPUT: surfaces-bake as "base" -> the made-up stage table's layers (closeup, surfaces-bake)
- money.view: `stop=None` -> MONEY row "the runner's whole lines"
- costs.hours: `{minutes % 60:02d}` -> `{minutes % 60}` -> HOURS row 125
- local.laid_on_plan: `corner, east, south = frame_of(plan)` -> `corner, east, south = np.zeros(3), np.array([1.0,
  0.0, 0.0]), np.array([0.0, 0.0, 1.0])` (the place's frame shown as the plan's) -> LAID_ON_PLAN row hut
"""
import datetime
import json
import pathlib
import types

import pytest

from score import stages
from score.dashboard.state import costs, groups, money
from score.dashboard.state.models import CostLine, PlaceCard, Spend, StyleGroup

pytestmark = pytest.mark.django_db(transaction=True)
MONTH = "2026-10"
LOOKS = {"shared": {"is": "rules"},
         "camp_look": {"scenes": ["alpha"], "style": {}},
         "prologue_beta": {"scenes": [], "style": {}},
         "gamma": {"scenes": [], "style": {}}}
LOOK_OF = [("alpha", "camp_look"),  # its scenes list it
           ("beta", "prologue_beta"),  # prologue_<place>
           ("gamma", "gamma"),  # its own name
           ("delta", groups.UNASSIGNED),
           ("shared", groups.UNASSIGNED)]  # a rules entry with no style is no look
LABELS = [("people-dress-nev-work", "dressed body of the nev-work look"),
          ("people-body-crowd_far", "body of the crowd far look"),
          ("no-such-stage", "no-such-stage")]  # never a made-up name
HOURS = [(125, "2 h 05 min"), (14, "14 min")]
# the real stage table: a place stage's layer as the stage table's reads give it
REAL_LAYERS = [("closeup", "pieces"), ("pixal", "pieces"), ("surfaces-paint", "pieces"), ("light-passes", "light"),
               ("cast", "characters"), ("plan", "base")]
# a 20 x 12 m plan with no frame stands its middle on the place's origin: place (x, z) is plan (x + 10, z + 6)
LAID_ON_PLAN = [("hut", [{"name": "garage_door_1", "row": "garage_door", "box": [12.0, 9.4, 18.0, 9.9],
                          "fitted": "laid face: moved 1.70 m"},
                         {"name": "crate_1", "row": "crate", "box": [9.0, 5.0, 10.0, 6.0], "fitted": None}]),
                ("shed", [])]  # no accepted assembly: nothing laid


def row(name, after=(), grain="place"):
    return types.SimpleNamespace(name=name, grain=grain, after={read: None for read in after}, beside={})


def cloud():
    return CostLine(source="cloud", label="Cloud compute", euros=2117.93, origin="the cloud bill")


def measured(models, stop=None):
    """A Spend as the store's machine reads it: the cloud bill whole beside `models`, the runner's figures with `stop`."""
    return Spend(spent=None if stop is None else 120.0, reserved=None if stop is None else 30.0, ceiling=stop,
                 world="world1", month=MONTH, note="" if stop else "world1: no stop set, paid launches refused",
                 lines=[cloud(), models])


MONEY = [  # (case, the Spend read, what the cockpit shows of it)
    ("a partial line", measured(CostLine(source="models", label="Model calls", euros=400.0, partial=True,
                                         origin="the call ledger")),
     {"sources": ["cloud", "models"], "whole": False, "gaps": ["Model calls"], "euros": 2517.93, "stop": None}),
    ("an unread line", Spend(world="world1", month=MONTH, lines=[
        cloud(), CostLine(source="models", label="Model calls", euros=None, partial=True,
                          origin="the export holds no rows")]),
     {"models": None, "whole": False, "euros": 2117.93}),
    ("nothing read", Spend(note="spend not read"), {"sources": ["cloud", "models"], "whole": False}),
    ("the runner's whole lines", measured(CostLine(source="models", label="Model calls", euros=1012.5,
                                                   origin="the billing export"), stop=900.0),
     {"whole": True, "euros": 3130.43, "stop": 900.0, "world_spent": 120.0, "in_flight": 30.0}),
]


def shown_as(spend):
    shown = money.view(spend)
    return {"sources": [line.source for line in shown.lines], "whole": shown.total.whole, "gaps": shown.total.gaps,
            "euros": shown.total.euros, "stop": shown.stop, "world_spent": shown.world_spent,
            "in_flight": shown.in_flight, "models": shown.lines[1].euros if len(shown.lines) > 1 else "absent"}


def laid_source(tmp_path):
    """An accepted assembly of `hut` whose LAID file holds a garage door (fitted) and a crate laid as drawn."""
    laid = {"objects": [{"name": "garage_door_1", "row": "garage_door", "low": [2.0, 0.0, 3.4], "high": [8.0, 8.0, 3.9]},
                        {"name": "crate_1", "row": "crate", "low": [-1.0, 0.0, -1.0], "high": [0.0, 1.0, 0.0]}],
            "fitted": [{"name": "garage_door_1", "words": "laid face: moved 1.70 m"}]}
    (tmp_path / "laid").write_text(json.dumps(laid))
    return types.SimpleNamespace(listing=lambda output: {"laid.json": "laid"} if output else {},
                                 accepted_output=lambda node: "out" if node == "assembly@hut" else None,
                                 blob_path=lambda sha: tmp_path / sha)


def test_the_store_is_read_as_it_is(world, settings, tmp_path):
    from score.dashboard.state.local import LocalSource

    # the look rule, a step's words and the minutes, as tables of input and the answer
    for place, look in LOOK_OF:
        assert groups.look_of(place, LOOKS) == look, place
    found = groups.styles(["delta", "gamma", "alpha", "beta"], LOOKS)
    assert list(found) == ["camp_look", "prologue_beta", "gamma", groups.UNASSIGNED]  # place.json's order
    assert sorted(place for places in found.values() for place in places) == ["alpha", "beta", "delta", "gamma"]
    for stage, words in LABELS:
        assert groups.label(stage) == words, stage
    for minutes, words in HOURS:
        assert costs.hours(minutes) == words, minutes

    # each place stage's layer by what its readers reach: what reads the assembly is the stage and films, never base
    # (complete reads the scene record too); a stage read by no assembly input takes what it reads; a world stage is
    # on the environment line, not here
    found = groups.layers([row("plan"), row("scene-record", ["plan"]), row("closeup"),
                           row("surfaces-bake", ["closeup"]), row("surfaces-check", ["surfaces-bake"]),
                           row("assembly", ["scene-record", "surfaces-bake"]),
                           row("complete", ["assembly", "surfaces-check", "scene-record"]),
                           row("demo-film", ["complete"]), row("terrain", grain="world")])
    assert found == {"plan": "base", "scene-record": "base", "closeup": "pieces", "surfaces-bake": "pieces",
                     "surfaces-check": "pieces", "assembly": groups.STAGE_AND_FILMS,
                     "complete": groups.STAGE_AND_FILMS, "demo-film": groups.STAGE_AND_FILMS}, found
    found = groups.layers(stages.STAGES)
    assert {item.name for item in stages.STAGES if item.grain == "place"} == set(found)
    assert set(found.values()) <= set(groups.LAYER_ORDER)
    for stage, layer in REAL_LAYERS:
        assert found[stage] == layer, stage

    # a place is said by its short name once: its look's when the look is its alone, else its own words
    launch = StyleGroup(look="prologue_launch", label="the launch view across the harbour", short="Launch",
                        places=[PlaceCard(place="launch", status="")])
    shared = StyleGroup(look="camp_look", label="camp", short="Camp",
                        places=[PlaceCard(place="north_camp", status=""), PlaceCard(place="south_camp", status="")])
    unassigned = StyleGroup(look=groups.UNASSIGNED, label="unassigned",
                            places=[PlaceCard(place="old_station", status="")])
    engines = types.SimpleNamespace(engines=[types.SimpleNamespace(styles=[launch, shared, unassigned])])
    assert groups.short_names(engines) == {"launch": "Launch", "north_camp": "North camp",
                                           "south_camp": "South camp", "old_station": "Old station"}
    # owner rule (the cards' short names, data/definitions/place.json): every place's look has its short name
    looks = json.loads((pathlib.Path(__file__).parents[3] / "data/definitions/place.json").read_text())
    places = [look for look, entry in looks.items() if isinstance(entry, dict) and entry.get("scenes")
              and look != "people"]
    assert places and all(looks[look].get("short") for look in places)

    # the month's money: never whole while a line is partial or unread; whole against the last batch's stop
    for case, spend, expected in MONEY:
        shown = shown_as(spend)
        assert {key: shown[key] for key in expected} == expected, case
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    read = Spend(month=today[:7], lines=[
        CostLine(source="cloud", label="Cloud compute", euros=2118.87, origin="the cloud bill"),
        CostLine(source="models", label="Model calls", euros=None, partial=True, origin="no rows yet")])
    first = money.with_bill_days(read, tmp_path / "bill")
    assert first.bill_days == [{"day": today, "cloud": 2118.87, "models": None}]
    unread = read.model_copy(update={"lines": []})
    assert money.with_bill_days(unread, tmp_path / "bill").bill_days == first.bill_days  # a line not read keeps it

    # Issue #72: the plan shows what the accepted assembly laid, in the plan's metres, named with how it was fitted
    source = laid_source(tmp_path)
    for place, laid in LAID_ON_PLAN:
        assert LocalSource.laid_on_plan(source, place, {"w": 20.0, "d": 12.0}) == laid, place
