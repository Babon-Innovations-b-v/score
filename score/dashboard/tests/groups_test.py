"""The groups the pages show: each place's style by the look rule, each stage's layer by the stage table's reads,
and the places from the environment's own data, never a hand list."""
import json
import pathlib
import types

from score import stages
from score.dashboard.state import groups

LOOKS = {"shared": {"is": "rules"},
         "camp_look": {"scenes": ["alpha"], "style": {}},
         "prologue_beta": {"scenes": [], "style": {}},
         "gamma": {"scenes": [], "style": {}}}


def test_the_style_rule():
    assert groups.look_of("alpha", LOOKS) == "camp_look"  # its scenes list it
    assert groups.look_of("beta", LOOKS) == "prologue_beta"  # prologue_<place>
    assert groups.look_of("gamma", LOOKS) == "gamma"  # its own name
    assert groups.look_of("delta", LOOKS) == groups.UNASSIGNED
    found = groups.styles(["delta", "gamma", "alpha", "beta"], LOOKS)
    assert list(found) == ["camp_look", "prologue_beta", "gamma", groups.UNASSIGNED]
    assert sorted(place for places in found.values() for place in places) == ["alpha", "beta", "delta", "gamma"]


def test_every_priced_step_and_kit_has_plain_words():
    assert groups.label("crops-layer") == "crops"
    assert groups.label("crops-boxes") == "crop boxes" and groups.label("crops-look") == "crop renders"
    assert groups.label("surface-tiles") == "surface tiles" and groups.label("ship_kit") == "ship kit"
    assert groups.label("people-dress-nev-work") == "dressed body of the nev-work look"


def row(name, after=(), grain="place"):
    return types.SimpleNamespace(name=name, grain=grain, after={read: None for read in after}, beside={})


def test_the_layer_walks_readers_forward_to_the_assembly():
    rows = [row("plan"), row("scene-record", ["plan"]), row("closeup"), row("surfaces-bake", ["closeup"]),
            row("surfaces-check", ["surfaces-bake"]), row("assembly", ["scene-record", "surfaces-bake"]),
            row("complete", ["assembly", "surfaces-check"]), row("demo-film", ["complete"]),
            row("terrain", grain="world")]
    found = groups.layers(rows)
    assert found["plan"] == found["scene-record"] == "base"
    assert found["closeup"] == found["surfaces-bake"] == "pieces"
    assert found["surfaces-check"] == "pieces"  # read by no assembly input: what it reads
    assert found["assembly"] == found["complete"] == found["demo-film"] == groups.STAGE_AND_FILMS
    assert "terrain" not in found  # an environment stage is on the environment line


def test_the_real_table_maps_every_place_stage_to_a_known_layer():
    found = groups.layers(stages.STAGES)
    assert set(found.values()) <= set(groups.LAYER_ORDER)
    assert found["closeup"] == found["pixal"] == found["surfaces-paint"] == "pieces"
    assert found["light-passes"] == "light" and found["cast"] == "characters" and found["plan"] == "base"
    assert found["crops-layer"] == "crops"
    assert {name for name, row in ((row.name, row) for row in stages.STAGES) if row.grain == "place"} == set(found)


def test_places_come_from_the_worlds_data(tmp_path):
    for folder, place in (("kit", "alpha"), ("plans", "beta")):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / f"{place}.json").write_text("{}")
    world = types.SimpleNamespace(roots={"data": str(tmp_path)})
    assert stages.places(world) == ["alpha", "beta"]


def test_a_place_is_said_by_its_short_name_once():
    from score.dashboard.state.models import PlaceCard, StyleGroup
    launch = StyleGroup(look="prologue_launch", label="the launch view across the harbour", short="Launch",
                        places=[PlaceCard(place="launch", status="")])
    unassigned = StyleGroup(look=groups.UNASSIGNED, label="unassigned",
                            places=[PlaceCard(place="old_station", status="")])
    world = types.SimpleNamespace(engines=[types.SimpleNamespace(styles=[launch, unassigned])])
    assert groups.short_names(world) == {"launch": "Launch", "old_station": "Old station"}
    looks = json.loads((pathlib.Path(__file__).parents[3] / "data/definitions/place.json").read_text())
    places = [look for look, entry in looks.items() if isinstance(entry, dict) and "plan" in entry and look != "people"]
    assert places and all(looks[look].get("short") for look in places)  # every place's look has its short name
