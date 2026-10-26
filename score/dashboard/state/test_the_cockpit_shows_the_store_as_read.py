"""Invariant: what the cockpit reads is the store and the runner's figures as they are, to the signed-in only: the
places grouped by the look rule and each stage by the stage table's reads (never a hand list), the month's money a
total that is never whole while a line is partial or unread with no stop or cost set from the cockpit, a file served
only when a page listed it, every route closed without a session, the owner's routes to the owner, every write
behind the CSRF header and an Origin, and the owner's decisions through the same gate as the review page.

Breaks that turn this red (each applied once and seen red, then reverted):
- groups.look_of: drop the `prologue_<place>` name (`(f"prologue_{place}", place)` -> `(place,)`) -> test_the_style_rule
- groups.label: drop the PEOPLE prefix branch -> test_a_persons_step_is_said_by_its_step_and_look
- groups.layers: drop the `reads_assembly` shortcut (`row.name == "assembly" or reads_assembly(...)` ->
  `row.name == "assembly"`) -> test_the_layer_walks_readers_forward_to_the_assembly
- groups.short_name: `len(style.places) == 1` -> `>= 1` -> test_a_place_is_said_by_its_short_name_once
- money.total: `whole=not gaps` -> `whole=True` -> test_a_partial_line_is_never_the_total
- money.with_bill_days: `{**days.get(today, {}), **read}` -> `read` -> test_each_read_of_the_month_keeps_its_day
- groups.LAYER_OF_INPUT: surfaces-bake as "base" -> test_the_real_table_maps_every_place_stage_to_a_known_layer
- money.view: `stop=None` -> test_the_runners_whole_lines_make_the_month_whole_against_the_last_batchs_stop
- api/routes.place_detail: the unknown-place 404 dropped -> test_reads_answer_from_the_fixture_and_unknowns_are_404
- api/routes.healthz: `"commit": None` -> test_healthz_reports_the_commit_the_image_was_built_at
- api/routes: a `/money/stop` route added -> test_no_stop_or_cost_is_set_from_the_cockpit
- api/routes.basket_remove: nothing deleted -> test_a_change_request_and_the_basket_round_trip
- api/routes.decision: a missing worse_reason filled in -> test_a_worse_output_is_accepted_only_with_a_reason
- api/routes.advance: a refused advance answered 200 -> test_an_advance_is_kept_only_for_a_known_node_and_output
- api/routes.on_its_way: without `no-store` -> test_a_hosted_picture_not_yet_up_is_a_stand_in_never_a_broken_image
- costs.hours: `{minutes % 60:02d}` -> `{minutes % 60}` -> test_minutes_are_said_in_hours_and_minutes
- api/deps.py: the session check (401) dropped -> test_without_a_session_every_route_is_401
- api/deps.py: the owner check dropped -> test_owner_routes_refuse_a_non_owner
- api/deps.py: the Origin check dropped -> test_writes_need_the_csrf_header_and_an_origin
- api/routes.file: `state.source().file(sha)` -> `... or ("x.png", store_root / "objects/blobs" / sha)` (any stored
  sha served) -> test_files_are_served_only_when_listed
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


def test_the_style_rule():
    assert groups.look_of("alpha", LOOKS) == "camp_look"  # its scenes list it
    assert groups.look_of("beta", LOOKS) == "prologue_beta"  # prologue_<place>
    assert groups.look_of("gamma", LOOKS) == "gamma"  # its own name
    assert groups.look_of("delta", LOOKS) == groups.UNASSIGNED
    assert groups.look_of("shared", LOOKS) == groups.UNASSIGNED  # a rules entry with no style is no look
    found = groups.styles(["delta", "gamma", "alpha", "beta"], LOOKS)
    assert list(found) == ["camp_look", "prologue_beta", "gamma", groups.UNASSIGNED]  # place.json's order
    assert sorted(place for places in found.values() for place in places) == ["alpha", "beta", "delta", "gamma"]


def test_a_persons_step_is_said_by_its_step_and_look():
    assert groups.label("people-dress-nev-work") == "dressed body of the nev-work look"
    assert groups.label("people-body-crowd_far") == "body of the crowd far look"
    assert groups.label("no-such-stage") == "no-such-stage"  # never a made-up name


def row(name, after=(), grain="place"):
    return types.SimpleNamespace(name=name, grain=grain, after={read: None for read in after}, beside={})


def test_the_layer_walks_readers_forward_to_the_assembly():
    rows = [row("plan"), row("scene-record", ["plan"]), row("closeup"), row("surfaces-bake", ["closeup"]),
            row("surfaces-check", ["surfaces-bake"]), row("assembly", ["scene-record", "surfaces-bake"]),
            row("complete", ["assembly", "surfaces-check", "scene-record"]), row("demo-film", ["complete"]),
            row("terrain", grain="world")]
    found = groups.layers(rows)
    assert found["plan"] == found["scene-record"] == "base"
    assert found["closeup"] == found["surfaces-bake"] == "pieces"
    assert found["surfaces-check"] == "pieces"  # read by no assembly input: what it reads
    # complete reads the scene record too, but what reads the assembly is the stage and films, never base
    assert found["assembly"] == found["complete"] == found["demo-film"] == groups.STAGE_AND_FILMS
    assert "terrain" not in found  # an environment stage is on the environment line


def test_the_real_table_maps_every_place_stage_to_a_known_layer():
    found = groups.layers(stages.STAGES)
    assert set(found.values()) <= set(groups.LAYER_ORDER)
    assert found["closeup"] == found["pixal"] == found["surfaces-paint"] == "pieces"
    assert found["light-passes"] == "light" and found["cast"] == "characters" and found["plan"] == "base"
    assert found["crops-layer"] == "crops"
    assert {item.name for item in stages.STAGES if item.grain == "place"} == set(found)


def test_a_place_is_said_by_its_short_name_once():
    launch = StyleGroup(look="prologue_launch", label="the launch view across the harbour", short="Launch",
                        places=[PlaceCard(place="launch", status="")])
    shared = StyleGroup(look="camp_look", label="camp", short="Camp",
                        places=[PlaceCard(place="north_camp", status=""), PlaceCard(place="south_camp", status="")])
    unassigned = StyleGroup(look=groups.UNASSIGNED, label="unassigned",
                            places=[PlaceCard(place="old_station", status="")])
    world = types.SimpleNamespace(engines=[types.SimpleNamespace(styles=[launch, shared, unassigned])])
    assert groups.short_names(world) == {"launch": "Launch", "north_camp": "North camp", "south_camp": "South camp",
                                         "old_station": "Old station"}
    # owner rule (the cards' short names, data/definitions/place.json): every place's look has its short name
    looks = json.loads((pathlib.Path(__file__).parents[3] / "data/definitions/place.json").read_text())
    places = [look for look, entry in looks.items() if isinstance(entry, dict) and entry.get("scenes")
              and look != "people"]
    assert places and all(looks[look].get("short") for look in places)


def measured(stop=None):
    """A Spend as the store's machine reads it: the cloud bill whole, the model call ledger partial."""
    return Spend(spent=None if stop is None else 120.0, reserved=None if stop is None else 30.0, ceiling=stop,
                 world="world1", month=MONTH, note="" if stop else "world1: no stop set, paid launches refused",
                 lines=[CostLine(source="cloud", label="Cloud compute", euros=2117.93, origin="the cloud bill"),
                        CostLine(source="models", label="Model calls", euros=400.0, partial=True,
                                 origin="the call ledger")])


def test_a_partial_line_is_never_the_total():
    shown = money.view(measured())
    assert [line.source for line in shown.lines] == ["cloud", "models"]
    assert not shown.total.whole and shown.total.gaps == ["Model calls"]
    assert shown.total.euros == 2517.93  # 2117.93 + 400.00
    assert shown.stop is None
    unread = Spend(world="world1", month=MONTH, lines=[
        CostLine(source="cloud", label="Cloud compute", euros=2117.93, origin="the cloud bill"),
        CostLine(source="models", label="Model calls", euros=None, partial=True, origin="the export holds no rows")])
    shown = money.view(unread)
    assert shown.lines[1].euros is None and not shown.total.whole and shown.total.euros == 2117.93
    nothing = money.view(Spend(note="spend not read"))
    assert [line.source for line in nothing.lines] == ["cloud", "models"] and not nothing.total.whole


def test_the_runners_whole_lines_make_the_month_whole_against_the_last_batchs_stop():
    whole = measured(stop=900.0)
    whole.lines[1] = CostLine(source="models", label="Model calls", euros=1012.5, origin="the billing export")
    shown = money.view(whole)
    assert shown.total.whole and shown.total.euros == 3130.43  # 2117.93 + 1012.50
    assert (shown.stop, shown.world_spent, shown.in_flight) == (900.0, 120.0, 30.0)


def test_each_read_of_the_month_keeps_its_day(tmp_path):
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    read = Spend(month=today[:7], lines=[
        CostLine(source="cloud", label="Cloud compute", euros=2118.87, origin="the cloud bill"),
        CostLine(source="models", label="Model calls", euros=None, partial=True, origin="no rows yet")])
    first = money.with_bill_days(read, tmp_path)
    assert first.bill_days == [{"day": today, "cloud": 2118.87, "models": None}]
    unread = read.model_copy(update={"lines": []})
    assert money.with_bill_days(unread, tmp_path).bill_days == first.bill_days  # a line not read keeps the day's


def test_minutes_are_said_in_hours_and_minutes():
    assert costs.hours(125) == "2 h 05 min" and costs.hours(14) == "14 min"


def test_reads_answer_from_the_fixture_and_unknowns_are_404(world):
    client = api()
    for path in ("/api/state", "/api/places/alpha", "/api/places/alpha/steps/closeup", "/api/world/steps/terrain",
                 "/api/spend", "/api/money"):
        assert client.get(path).status_code == 200, path
    assert client.get("/api/places/nowhere").status_code == 404
    assert client.get("/api/places/alpha/steps/nothing").status_code == 404
    assert client.get("/api/launches").json() == []
    assert client.get("/healthz").json() == {"ok": True, "mode": "local", "commit": None}


def test_healthz_reports_the_commit_the_image_was_built_at(settings):
    """The hosted image's SCORE_COMMIT, the pin the conductor's score-update timer follows; open to anyone."""
    from score.dashboard.site.asgi import app
    settings.SCORE_COMMIT = "a" * 40
    answer = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000)).get("/healthz")
    assert answer.status_code == 200 and answer.json()["commit"] == "a" * 40


def test_without_a_session_every_route_is_401():
    from score.dashboard.site.asgi import app
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    for path in ("/api/state", "/api/spend", "/api/money", "/api/requests", "/files/" + "0" * 64, "/api/docs"):
        assert client.get(path).status_code == 401, path


def test_owner_routes_refuse_a_non_owner(world):
    client = api("guest")
    assert client.get("/api/basket/items").status_code == 403
    assert client.post("/api/basket/items", json={"place": "alpha", "stage": "plan"}).status_code == 403
    assert client.post("/api/decisions", json={"node": "closeup@alpha", "output": "x",
                                               "decision": "accept"}).status_code == 403
    assert client.post("/api/launches", json={"plan_id": 1, "confirm": True}).status_code == 403
    output = world.outputs["assembly@alpha"]
    assert client.post("/api/advances", json={"node": "assembly@alpha", "output": output}).status_code == 403


def test_no_stop_or_cost_is_set_from_the_cockpit(world):
    # owner rule (2026-10-20): no stop he sets, no month's stop; the Buy's yes writes the batch's stop
    owner = api("joey")
    for route in ("/api/money/owner-costs", "/api/money/stop", "/api/money/month"):
        assert owner.post(route, json={"euros": 5}).status_code in (404, 405)


def test_writes_need_the_csrf_header_and_an_origin(world):
    client = api()
    body = {"place": "alpha", "stage": "closeup", "words": "redder"}
    assert client.post("/api/requests", json=body, headers={"X-CSRFToken": ""}).status_code == 403
    client.headers.pop("Origin")
    assert client.post("/api/requests", json=body).status_code == 403
    from score.dashboard.pages.models import ChangeRequest
    assert not ChangeRequest.objects.exists()


def test_a_change_request_and_the_basket_round_trip(world):
    client = api()
    made = client.post("/api/requests", json={"place": "alpha", "stage": "closeup", "words": "redder"})
    assert made.status_code == 200 and made.json()["node"] == "closeup@alpha"
    assert [item["words"] for item in client.get("/api/requests").json()] == ["redder"]
    listed = client.post("/api/basket/items", json={"place": "alpha", "stage": "closeup"}).json()
    assert [(item["place"], item["stage"]) for item in listed] == [("alpha", "closeup")]
    assert client.delete(f"/api/basket/items/{listed[0]['id']}").json() == []


def test_a_worse_output_is_accepted_only_with_a_reason(world):
    client = api()
    waiting = world.outputs["closeup@alpha waiting"]  # the fixture's close-up with one more fault than the accepted
    before = world.store.accepted("closeup@alpha")
    refused = client.post("/api/decisions", json={"node": "closeup@alpha", "output": waiting, "decision": "accept"})
    assert refused.status_code == 409 and world.store.accepted("closeup@alpha") == before
    taken = client.post("/api/decisions", json={"node": "closeup@alpha", "output": waiting, "decision": "accept",
                                                "worse_reason": "fine"})
    assert taken.status_code == 200 and world.store.accepted("closeup@alpha") == waiting


def test_an_advance_is_kept_only_for_a_known_node_and_output(world):
    from score.dashboard.pages import seen
    output = world.outputs["assembly@alpha"]
    client = api()
    answer = client.post("/api/advances", json={"node": "assembly@alpha", "output": output})
    assert answer.status_code == 200, answer.text
    assert seen.advanced("assembly@alpha", output)
    assert client.post("/api/advances", json={"node": "nothing@alpha", "output": output}).status_code == 404
    assert client.post("/api/advances", json={"node": "assembly@alpha", "output": ""}).status_code == 409


def test_files_are_served_only_when_listed(world):
    client = api()
    detail = client.get("/api/places/alpha/steps/closeup").json()
    picture = next(item for item in detail["files"] if item["kind"] == "image")
    assert client.get(picture["url"]).headers["content-type"] == "image/png"
    assert client.get(picture["thumb_url"]).headers["content-type"] == "image/jpeg"
    secret = b"in the store, but no listing names it"
    unlisted = hashlib.sha256(secret).hexdigest()
    (world.root / "store/objects/blobs" / unlisted).write_bytes(secret)
    assert client.get(f"/files/{unlisted}").status_code == 404
    assert client.get("/files/" + "f" * 64).status_code == 404
    assert client.get("/files/../etc").status_code == 404
    assert client.get(f"/thumbs/{'b' * 64}.jpg").status_code == 404  # local: a missing picture stays a 404


@override_settings(SCORE_MODE="hosted")
def test_a_hosted_picture_not_yet_up_is_a_stand_in_never_a_broken_image(world):
    sha, owner = "a" * 64, api("joey")
    for path in (f"/files/{sha}", f"/thumbs/{sha}.jpg"):
        answer = owner.get(path)
        assert answer.status_code == 200 and answer.headers["content-type"].startswith("image/svg+xml")
        assert answer.headers["cache-control"] == "no-store"  # fetched again once the picture is up
    assert owner.get("/files/not-a-sha").status_code == 404
