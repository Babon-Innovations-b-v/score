"""Invariant: what the cockpit reads is the store and the runner's figures as they are, to the signed-in only: the
places grouped by the look rule and each stage by the stage table's reads (never a hand list), the month's money a
total that is never whole while a line is partial or unread with no stop or cost set from the cockpit, a file served
only when a page listed it, every route closed without a session, the owner's routes to the owner, every write
behind the CSRF header and an Origin, and the owner's decisions through the same gate as the review page.

Breaks that turn test_the_cockpit_shows_the_store_as_read red (each applied once and seen red, then reverted):
- groups.look_of: drop the `prologue_<place>` name (`(f"prologue_{place}", place)` -> `(place,)`) -> LOOK_OF row beta
- groups.label: drop the PEOPLE prefix branch -> LABELS row people-dress-nev-work
- groups.layers: drop the `reads_assembly` shortcut (`row.name == "assembly" or reads_assembly(...)` ->
  `row.name == "assembly"`) -> the made-up stage table's layers
- groups.short_name: `len(style.places) == 1` -> `>= 1` -> the short names of the launch, camp and old station
- money.total: `whole=not gaps` -> `whole=True` -> MONEY row "a partial line"
- money.with_bill_days: `{**days.get(today, {}), **read}` -> `read` -> the second read of the month keeps its day
- groups.LAYER_OF_INPUT: surfaces-bake as "base" -> the made-up stage table's layers (closeup, surfaces-bake)
- money.view: `stop=None` -> MONEY row "the runner's whole lines"
- api/routes.place_detail: the unknown-place 404 dropped -> route row /api/places/nowhere
- api/routes.healthz: `"commit": None` -> healthz names the commit
- api/routes: a `/money/stop` route added -> route row /api/money/stop
- api/routes.basket_remove: nothing deleted -> the basket round trip
- api/routes.decision: a missing worse_reason filled in -> the worse close-up accepted without a reason (409)
- api/routes.advance: a refused advance answered 200 -> the advance with no output (409)
- api/routes.on_its_way: without `no-store` -> the hosted stand-in's cache-control
- costs.hours: `{minutes % 60:02d}` -> `{minutes % 60}` -> HOURS row 125
- api/deps.py: the session check (401) dropped -> route rows of nobody
- api/deps.py: the owner check dropped -> route rows of the guest
- api/deps.py: the Origin check dropped -> the write without an Origin
- api/routes.file: `state.source().file(sha)` -> `... or ("x.png", store_root / "objects/blobs" / sha)` (any stored
  sha served) -> route row of the unlisted blob
- local.laid_on_plan: `corner, east, south = frame_of(plan)` -> `corner, east, south = np.zeros(3), np.array([1.0,
  0.0, 0.0]), np.array([0.0, 0.0, 1.0])` (the place's frame shown as the plan's) -> LAID_ON_PLAN row hut
"""
import datetime
import hashlib
import json
import pathlib
import types

import pytest
from django.test import override_settings
from fastapi.testclient import TestClient

from score import stages
from score.dashboard.state import costs, groups, money
from score.dashboard.state.models import CostLine, PlaceCard, Spend, StyleGroup
from score.dashboard.tests.fixture import ORIGIN, api

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
               ("cast", "characters"), ("plan", "base"), ("crops-layer", "crops")]
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


def test_the_cockpit_shows_the_store_as_read(world, settings, tmp_path):
    from score.dashboard.pages import seen
    from score.dashboard.pages.models import ChangeRequest
    from score.dashboard.site.asgi import app
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

    # the served cockpit: open to no one without a session but healthz, the owner's routes his alone
    nobody = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    owner, guest = api("joey"), api("guest")
    secret = b"in the store, but no listing names it"
    unlisted = hashlib.sha256(secret).hexdigest()
    (world.root / "store/objects/blobs" / unlisted).write_bytes(secret)
    routes = [  # (who, method, path, body, the answers allowed)
        *[("nobody", "get", path, None, {401}) for path in
          ("/api/state", "/api/spend", "/api/money", "/api/requests", "/files/" + "0" * 64, "/api/docs")],
        *[("owner", "get", path, None, {200}) for path in
          ("/api/state", "/api/places/alpha", "/api/places/alpha/steps/closeup", "/api/world/steps/terrain",
           "/api/spend", "/api/money")],
        ("owner", "get", "/api/places/nowhere", None, {404}),
        ("owner", "get", "/api/places/alpha/steps/nothing", None, {404}),
        ("guest", "get", "/api/basket/items", None, {403}),
        ("guest", "post", "/api/basket/items", {"place": "alpha", "stage": "plan"}, {403}),
        ("guest", "post", "/api/decisions", {"node": "closeup@alpha", "output": "x", "decision": "accept"}, {403}),
        ("guest", "post", "/api/launches", {"plan_id": 1, "confirm": True}, {403}),
        ("guest", "post", "/api/advances", {"node": "assembly@alpha", "output": world.outputs["assembly@alpha"]},
         {403}),
        # owner rule (2026-10-20): no stop he sets, no month's stop; the Buy's yes writes the batch's stop
        *[("owner", "post", route, {"euros": 5}, {404, 405}) for route in
          ("/api/money/owner-costs", "/api/money/stop", "/api/money/month")],
        # a file is served only when a listing names it, never a stored blob by its sha alone
        ("owner", "get", f"/files/{unlisted}", None, {404}),
        ("owner", "get", "/files/" + "f" * 64, None, {404}),
        ("owner", "get", "/files/../etc", None, {404}),
        ("owner", "get", f"/thumbs/{'b' * 64}.jpg", None, {404}),  # local: a missing picture stays a 404
    ]
    clients = {"nobody": nobody, "owner": owner, "guest": guest}
    for who, method, path, body, allowed in routes:
        answer = getattr(clients[who], method)(path, **({} if body is None else {"json": body}))
        assert answer.status_code in allowed, (who, method, path, answer.status_code)
    assert owner.get("/api/launches").json() == []
    # healthz is open to anyone and names the commit the image was built at (the score-update timer's pin)
    assert nobody.get("/healthz").json() == {"ok": True, "mode": "local", "commit": None}
    settings.SCORE_COMMIT = "a" * 40
    answer = nobody.get("/healthz")
    assert answer.status_code == 200 and answer.json()["commit"] == "a" * 40

    # the listed picture is served as its kind, its thumb as a jpeg
    detail = owner.get("/api/places/alpha/steps/closeup").json()
    picture = next(item for item in detail["files"] if item["kind"] == "image")
    assert owner.get(picture["url"]).headers["content-type"] == "image/png"
    assert owner.get(picture["thumb_url"]).headers["content-type"] == "image/jpeg"

    # a write without the CSRF header or without an Origin is refused and keeps nothing
    asked = {"place": "alpha", "stage": "closeup", "words": "redder"}
    assert owner.post("/api/requests", json=asked, headers={"X-CSRFToken": ""}).status_code == 403
    origin = owner.headers.pop("Origin")
    assert owner.post("/api/requests", json=asked).status_code == 403
    owner.headers["Origin"] = origin
    assert not ChangeRequest.objects.exists()
    # with both, a change request and the basket round trip
    made = owner.post("/api/requests", json=asked)
    assert made.status_code == 200 and made.json()["node"] == "closeup@alpha"
    assert [item["words"] for item in owner.get("/api/requests").json()] == ["redder"]
    listed = owner.post("/api/basket/items", json={"place": "alpha", "stage": "closeup"}).json()
    assert [(item["place"], item["stage"]) for item in listed] == [("alpha", "closeup")]
    assert owner.delete(f"/api/basket/items/{listed[0]['id']}").json() == []

    # a worse output (the fixture's close-up with one more fault than the accepted) is accepted only with a reason
    waiting, before = world.outputs["closeup@alpha waiting"], world.store.accepted("closeup@alpha")
    refused = owner.post("/api/decisions", json={"node": "closeup@alpha", "output": waiting, "decision": "accept"})
    assert refused.status_code == 409 and world.store.accepted("closeup@alpha") == before
    taken = owner.post("/api/decisions", json={"node": "closeup@alpha", "output": waiting, "decision": "accept",
                                               "worse_reason": "fine"})
    assert taken.status_code == 200 and world.store.accepted("closeup@alpha") == waiting

    # an advance is kept only for a known node and output
    output = world.outputs["assembly@alpha"]
    answer = owner.post("/api/advances", json={"node": "assembly@alpha", "output": output})
    assert answer.status_code == 200 and seen.advanced("assembly@alpha", output), answer.text
    assert owner.post("/api/advances", json={"node": "nothing@alpha", "output": output}).status_code == 404
    assert owner.post("/api/advances", json={"node": "assembly@alpha", "output": ""}).status_code == 409

    # hosted: a picture not yet up is a stand-in fetched again later, never a broken image
    with override_settings(SCORE_MODE="hosted"):
        for path in (f"/files/{'a' * 64}", f"/thumbs/{'a' * 64}.jpg"):
            answer = owner.get(path)
            assert answer.status_code == 200 and answer.headers["content-type"].startswith("image/svg+xml"), path
            assert answer.headers["cache-control"] == "no-store", path
        assert owner.get("/files/not-a-sha").status_code == 404
