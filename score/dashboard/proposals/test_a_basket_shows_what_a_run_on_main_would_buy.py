"""Invariant: the basket shows what a run on main would buy and writes nothing into the real store: the plan's buys
grouped into items by place and what they change (joined with what they wait for, a declared item taking its own),
each item's version moving with its nodes and reasons only; the records read back by item, names with a path
refused; the Benchmarks item only while one can run.

Breaks that turn this red (each applied once and seen red, then reverted); all in the one test, by its part:
- records.checked: the name check dropped -> the kept basket's refused names
- make.joined: `for read in waits_for(...)` -> `for read in []` -> the plan's items ("dock-pieces" joined)
- make.declared_buys: a pattern compared whole -> the plan's items ("ship-room-concepts")
- make.version: the reasons left out -> the remade plan's versions
- benchmarks.item: `if not listed:` -> the plan's items (no "benchmarks") and benchmarks.put's words
"""
import json
import types

import pytest

from score.dashboard.proposals import benchmarks, make, records


PRICE = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "runs": 4,
         "guess_euros": None, "cards": 1}
LAYERS = {"pixal": "pieces", "surfaces-bake": "pieces", "light-passes": "light"}


def buy(node, why="code changed", again=True):
    return {"node": node, "why": why, "again": again, "price": PRICE}


def planner(buys, missing):
    """The runner's plan stand-in: these buys, these missing inputs, its refusal."""
    class Planned:
        def plan(self, group):
            return types.SimpleNamespace(buys=buys, missing=missing, refusal="refused: these inputs are missing")
    return Planned()


BENCHMARK_GAP = {"id": "batch-direct", "what": "batch against direct", "gap": "no paid path asks a finish list direct"}


@pytest.mark.django_db(transaction=True)
def test_a_basket_shows_what_a_run_on_main_would_buy(tmp_path):
    # The kept basket: read back by item, names with a path refused.
    root = tmp_path / "kept" / "proposals"
    item = make.finished("hangar-pieces", make.entry_of(
        [{"node": "surfaces-bake@hangar", "why": "code changed", "again": True, "price": PRICE}], {}))
    records.put_index(root, {"made_at": "2026-10-19T08:00:00Z", "items": [item]})
    assert records.item(root, "hangar-pieces")["version"] == item["version"]
    for bad in ("..", "../x", "a/b", ".hidden"):
        with pytest.raises(records.BadName):
            records.folder(root, bad)

    # The plan's buys made into items: declared items first, the rest by place and
    # what they change, joined with what they wait for; the benchmarks item only while one can run.
    home = tmp_path / "plan"
    (home / "data").mkdir(parents=True)
    (home / "data" / "views.json").write_text(
        '{"views": [{"id": "ship46_cockpit", "wording": "The cockpit, 7.8 m wide."}]}')
    (home / "data" / "boxes.json").write_text('{"boxes": [[0, 0, 1]]}')
    (home / "data" / "brief.txt").write_text("A crate of tools.")
    records.put_declared(home / "proposals", "ship-room-concepts", {
        "title": "Ship room concepts", "nodes": ["concept-views", "pixal@ship-*"],
        "files": [str(home / "data" / name) for name in ("views.json", "boxes.json", "brief.txt")]})
    records.put_declared(home / "proposals", "waiting-trial", {"title": "The prop trial", "nodes": ["prop-trial*"]})
    (home / benchmarks.RECORD).parent.mkdir(parents=True)
    (home / benchmarks.RECORD).write_text(json.dumps({"benchmarks": {"listed": [BENCHMARK_GAP]}}))
    buys = [buy("concept-views"), buy("pixal@ship-cockpit"), buy("pixal@ship-galley"), buy("pixal@hangar"),
            buy("surfaces-bake@hangar", "reads pixal@hangar"), buy("light-passes@hangar"), buy("light-passes@garage"),
            buy("pixal@dock"), buy("light-passes@dock", "reads pixal@dock"),
            buy("people-body-bram-work"), buy("people-body-nev-work"), buy("people-lists")]
    missing = ["surfaces-bake@hangar: bake job (/x/job.json)", "cast@cockpit: scene (data/scene/cockpit.json)"]
    index = make.make(home, home / "store", chosen=planner(buys, missing), layer_of=LAYERS)
    assert index["missing"] == missing
    found = {item["id"]: item for item in index["items"]}
    assert {ident: sorted(item["nodes"]) for ident, item in found.items()} == {
        "ship-room-concepts": ["concept-views", "pixal@ship-cockpit", "pixal@ship-galley"], "waiting-trial": [],
        "hangar-pieces": ["pixal@hangar", "surfaces-bake@hangar"], "hangar-light": ["light-passes@hangar"],
        "garage-light": ["light-passes@garage"], "dock-pieces": ["light-passes@dock", "pixal@dock"],
        "environment-people-body": ["people-body-bram-work", "people-body-nev-work"],
        "environment-people-lists": ["people-lists"]}
    assert list(found)[:2] == ["ship-room-concepts", "waiting-trial"]
    assert records.items(home / "proposals") == index["items"]
    ship, waiting, pieces = found["ship-room-concepts"], found["waiting-trial"], found["hangar-pieces"]
    assert ship["title"] == "Ship room concepts" and ship["declared"]
    assert ship["places"] == ["ship-cockpit", "ship-galley"] and ship["place"] is None
    assert waiting["nodes"] == {} and waiting["totals"]["nodes"] == 0
    assert pieces["place"] == "hangar" and pieces["places"] == ["hangar"] and pieces["missing"] == missing[:1]
    assert pieces["totals"]["likely_euros"] == 4.0 and pieces["totals"]["high_euros"] == 6.0
    assert found["environment-people-body"]["place"] is None and found["environment-people-body"]["places"] == []
    assert not any(item["missing"] for ident, item in found.items() if ident != "hangar-pieces")
    assert benchmarks.put(home / "proposals", home) == "benchmarks: none listed"
    assert records.item(home / "proposals", "benchmarks") is None
    # an item's version moves with its nodes and reasons only
    again = make.make(home, home / "store", chosen=planner([*buys[:3], buy("pixal@hangar", "never ran"), *buys[4:]],
                                                            missing), layer_of=LAYERS)
    moved = {item["id"]: item["version"] != found[item["id"]]["version"] for item in again["items"]}
    assert moved == {ident: ident == "hangar-pieces" for ident in found}
