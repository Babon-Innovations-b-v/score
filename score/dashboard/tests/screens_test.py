"""Each cockpit screen's JSON (state/screens.py, GET /api/screens/...), on the fixture environment with its gaps
priced by the runner, a prepare record shaped like the real one (takes by status, those waiting on lost inputs
counted in its figure), the month's spend as `score spend` writes it and a tiny library: the remake is prepare's
figure plus the gaps price off the prop route, the ETA a range only when both parts have one, a place's picture
its concept, the model calls' month None when not read, the basket's stop its high plus 10%, and the
library's counts by kind."""
import json
import os

import pytest

from score.dashboard.pages.models import BasketChoice
from score.dashboard.proposals import records
from score.dashboard.state import local, screens
from score.dashboard.state.models import CostLine, Spend, WorldState
from score.dashboard.tests.library_test import api, shelf  # noqa: F401  (a pytest fixture)
from score.dashboard.tests.pages_test import MEASURED, a_gaps_finding, a_gaps_price

pytestmark = pytest.mark.django_db(transaction=True)
SETTLE = {**MEASURED, "basis": "measured runs"}  # a paid step off the prop route, measured
MONTH = Spend(spent=120.0, reserved=30.0, ceiling=900.0, world="world1", month="2026-10", days=[
    {"day": "2026-10-19", "cloud": 4.5, "models": 0.0}, {"day": "2026-10-20", "cloud": 1.25, "models": 0.4}], lines=[
    CostLine(source="cloud", label="Cloud compute", euros=2118.87, origin="the cloud bill"),
    CostLine(source="models", label="Model calls", euros=None, partial=True, origin="no rows yet")])


def take(place, status, lost=True):
    return {"place": place, "take": f"{place}_{status}", "status": status,
            "inputs": ["view v1's picture is not in the work folder"] if lost else []}


def a_design(approved):
    """Prepare's design record (prepare/design.py): alpha's and beta's, the `approved` ones approved, the others with
    their concept missing and their plan to remake."""
    def one(place):
        if place in approved:
            return {"concept": "picked", "plan": "approved", "output": "o" * 64, "hint": "K01"}
        return {"concept": "missing", "plan": "remake", "output": None, "hint": None}
    return {"places": {place: one(place) for place in ("alpha", "beta")}, "approved": list(approved)}


def a_remake(world, priced_on=None, approved=("alpha", "beta")):
    """Prepare's record (WORK/checks/prepare/remake.json) as the real one is shaped: alpha's three takes, two bought
    waiting on a lost input and one a predicted gap, priced EUR 10 to 12 with the likeness calibration unpriced; the
    designs of `approved` approved."""
    folder = world.root / "props/work/checks/prepare"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "remake.json").write_text(json.dumps({
        "made_at": "2026-10-20T11:19:22+00:00",
        "priced_on": priced_on or {**local.priced_here(), "uncommitted": False},
        "takes": [take("alpha", "bought"), take("alpha", "bought"), take("alpha", "predicted gap")],
        "layers": {"closeup": {"takes": 2, "price": {"likely_euros": 10.0, "high_euros": 12.0}},
                   "likeness-calibration": {"takes": 2, "price": {"likely_euros": None, "high_euros": None}}},
        "totals": {"likely_euros": 10.0, "high_euros": 12.0, "unpriced": ["likeness-calibration"]},
        "eta": {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "path": [],
                "unknown": [{"node": "closeup"}, {"node": "pixal"}]}, "design": a_design(approved)}))


@pytest.fixture
def month_read():
    """The routes read the month through their FastAPI dependency (actions' reader): MONTH in its place."""
    from score.dashboard.pages import actions
    from score.dashboard.site.asgi import inner
    inner.dependency_overrides[actions.spend] = lambda: MONTH
    yield MONTH
    inner.dependency_overrides.clear()


@pytest.fixture
def cockpit(world, read, settings, tmp_path):
    """The fixture environment with alpha's gaps priced (the close-up on the prop route, settle off it and measured,
    the sound guessed), prepare's record, and the basket made."""
    items = a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, nodes={"closeup@alpha": {**MEASURED, "basis": "per unit × forecast"},
                                "settle@alpha": SETTLE, "sound@alpha": {
                                    "likely_euros": None, "high_euros": None, "guess_euros": 1.0,
                                    "basis": "not measured yet", "likely_minutes": None, "high_minutes": None}},
                  eta={"likely_minutes": None, "high_minutes": None, "at_least_minutes": 20.0,
                       "unknown": [{"node": "sound@alpha"}]})
    a_remake(world)
    world.source.refresh()
    world.items = items
    return world


def test_the_environment_shows_the_whole_remake_its_eta_floor_and_each_places_tile(cockpit, shelf):  # noqa: F811
    found = screens.environment(cockpit.source, MONTH)
    remake = found["remake"]
    assert remake["route"]["likely"] == 10.0 and remake["route"]["blocked"] == 2
    assert remake["route"]["predicted_gaps"] == 1
    assert remake["rest"] == {"likely": 2.0, "high": 3.0, "priced": 1, "unpriced": 1}  # settle; the sound guessed
    assert (remake["likely"], remake["high"], remake["unpriced"]) == (12.0, 15.0, 2)
    assert remake["eta"] == {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "untimed": 3}
    assert remake["stale"] == []
    assert found["money"] == {"month": "2026-10", "cloud": 2118.87, "models": None, "total": 2118.87,
                              "whole": False, "stop": 900.0, "against_stop": 150.0, "in_flight": 30.0,
                              "refused": False}
    alpha = next(place for place in found["places"] if place["place"] == "alpha")
    assert alpha["gaps"] == 4 and alpha["worst"] == "route" and alpha["takes"]["takes"] == 3
    assert alpha["progress"]["needed"] >= alpha["progress"]["made"] > 0
    assert [bool(place["picture"]) for place in found["places"]] == [True, False]  # alpha's concept; beta's is lost
    assert found["gaps"] == {"missing": 2, "gate": 1, "route": 1}


def test_a_places_picture_is_its_concept_and_none_when_its_concept_is_lost(cockpit, shelf):  # noqa: F811
    world = cockpit.source.world_state()
    concept = world.concepts["alpha"]
    assert screens.picture_of(world, "alpha") == (f"/thumbs/{concept.sha}.jpg", "concept")
    assert screens.picture_of(world, "beta") == (None, None)  # its store hero and library entry are no concept
    assert cockpit.source.file(concept.sha)[1].is_file()  # served from the store's blobs


def test_a_remake_priced_on_code_not_committed_says_it_is_stale(cockpit):
    a_remake(cockpit, priced_on={"commit": "6cdf4d40", "uncommitted": True, "per_unit_sha256": "x"})
    cockpit.source.refresh()
    assert screens.remake_money(cockpit.source.world_state())["stale"] == ["it was made on code not committed"]
    from score.dashboard.tests.pages_test import signed_in
    html = signed_in().get("/buy/").content.decode()
    after = html[html.index(">After design<"):html.index('<ul class="buy-layers buy-design">')]
    assert after.count(">unknown</span>") == 1 and "&ndash;" not in after.split("</div>")[1]  # never 0.00 stale
    layers = html.split('<ul class="buy-layers buy-design">')[1].split('<ul class="buy-layers">')[1]
    assert layers.count('<span class="unknown">unknown</span>') == layers.count('class="node-row buy-item"') > 0


def test_the_place_screen_lists_its_gaps_as_items_and_each_chain_priced_once(cockpit):
    found = screens.place(cockpit.source, "alpha", None)
    assert [item["kind"] for item in found["items"]] == ["missing", "missing", "gate", "route"]
    assert found["items"][0]["prim"] == "/alpha/Gaps/lamp_1" and found["items"][0]["node"] == "closeup@alpha"
    assert found["prices"]["closeup@alpha"] == {"likely": 2.0, "high": 3.0, "priced": 1, "unpriced": 1}
    assert found["prices"]["complete@alpha"] == {"likely": 0, "high": 0, "priced": 0, "unpriced": 1}
    assert found["gaps"] == {"missing": 2, "gate": 1, "route": 1} and not found["price_stale"]
    assert {step["state"] for step in found["steps"]} <= {"accepted", "waiting", "stopped", "not run"}


def test_the_buy_screen_totals_the_chosen_items_and_their_stop_is_the_high_plus_ten_percent(cockpit):
    item = cockpit.items[0]
    assert screens.buy(cockpit.items, {}, MONTH)["stop"] is None
    found = screens.buy(cockpit.items, {item["id"]: "buy"}, MONTH)
    assert found["chosen"] == 1 and found["total"]["likely"] == 2.0 and found["total"]["high"] == 3.0
    assert found["stop"] == 3.3 and found["eta"] == {"likely_minutes": 10.0, "high_minutes": 20.0, "untimed": 0}
    assert found["items"][0]["choice"] == "buy" and found["items"][0]["likely"] == 2.0


def test_the_batch_splits_into_what_buy_buys_now_and_what_waits_and_its_lines_add_up(cockpit):
    """The basket buys closeup@alpha now, so alpha's two close-up takes are made now at the basket's price, not
    prepare's; the predicted hole, settle and the sound wait; the calibration and the sound have no price."""
    found = screens.batch(cockpit.source.world_state(), cockpit.items)
    models, motion, sound = found["layers"]
    assert (models["make"], models["library"], models["waiting"], models["models"]) == (2, 0, 1, 3)
    assert models["why"] == {"predicted to fail": 1} and models["no_price"] == {"likeness calibration": 2}
    assert (models["likely"], models["high"]) == (2.0, 3.0)  # the basket's close-up; prepare's share went with it
    assert (motion["waiting"], motion["why"], motion["likely"], motion["high"]) == (
        1, {"an earlier step first": 1}, 2.0, 3.0)
    assert (sound["waiting"], sound["likely"], sound["high"], sound["guessed"]) == (1, 0.0, 0.0, 0.0)  # no guess later
    assert found["total"]["likely"] == found["now"]["likely"] + found["waiting"]["likely"] == 4.0
    assert found["total"]["high"] == found["now"]["high"] + found["waiting"]["high"] == 6.0
    assert found["total"]["measured"]["high"] + found["total"]["estimated"]["high"] == 6.0  # settle measured
    assert (found["now"]["steps"], found["now"]["places"], found["now"]["stop"]) == (1, ["alpha"], 3.3)
    assert found["waiting"]["why"] == ["an earlier step first", "predicted to fail"]
    blocked = [{**item, "missing": ["a lost input"]} for item in cockpit.items]
    waits = screens.batch(cockpit.source.world_state(), blocked)
    assert waits["now"]["steps"] == 0 and waits["now"]["stop"] is None  # Buy buys nothing that cannot run
    assert waits["layers"][0]["why"]["lost concept views"] == 2


def test_no_step_is_bought_at_a_place_whose_design_is_not_approved(cockpit):
    """Before any design is approved the batch buys nothing and is priced at nothing (the old inventories' price says
    nothing of the new designs); once alpha's is, only alpha's part is priced, with no ETA while beta is in design.
    The design names each place's concept and plan as prepare wrote them, and a place it does not name as None."""
    a_remake(cockpit, approved=())
    cockpit.source.refresh()
    world = cockpit.source.world_state()
    found = screens.batch(world, cockpit.items)
    assert found["now"]["steps"] == 0 and found["now"]["stop"] is None and found["layers"] == []
    money = screens.remake_money(world)
    assert (money["likely"], money["approved"], money["in_design"]) == (None, 0, 2)
    assert screens.now_items(cockpit.items, ["beta"]) == []  # alpha's close-up waits on alpha's design
    design = screens.design(cockpit.source, world)
    assert design["approved"] == [] and [row["design"]["plan"] for row in design["places"]] == ["remake", "remake"]
    world.remake.design = {}
    assert screens.design(cockpit.source, world)["places"][0]["design"] is None
    a_remake(cockpit, approved=("alpha",))
    cockpit.source.refresh()
    money = screens.remake_money(cockpit.source.world_state())
    assert (money["likely"], money["high"], money["in_design"]) == (12.0, 15.0, 1)  # every take is alpha's
    assert money["eta"]["at_least_minutes"] is None  # the runner times the whole remake only


def test_the_buy_route_counts_a_choice_on_another_version_as_none(cockpit, month_read):
    item = records.items(cockpit.root / "home" / "proposals")[0]
    BasketChoice.objects.create(item=item["id"], version="0" * 16, choice="buy", by="joey")
    found = api().get("/api/screens/buy").json()
    assert found["chosen"] == 0 and found["items"][0]["choice"] is None


def test_the_stats_count_measured_prices_gaps_and_places_complete(cockpit):
    found = screens.stats(cockpit.source, MONTH)
    assert found["prices"]["measured"] == 2 and found["prices"]["steps"] == 3
    assert found["days"][-1] == {"day": "2026-10-20", "cloud": 1.25, "models": 0.4}
    assert found["places"]["total"] == 2 and found["gaps"]["missing"] == 2


def test_the_library_counts_each_kind(world, shelf):  # noqa: F811
    from score.dashboard.state import library
    found = screens.library_counts(library.library())
    kinds = {row["kind"]: row for row in found["kinds"]}
    assert found["total"] == 15 and kinds["model"]["count"] == 3 and kinds["model"]["locked"] == 1
    assert kinds["place"]["count"] == 3 and kinds["model"]["pictured"] == 3 and kinds["model"]["scored"] == 2
    assert screens.library_counts(None) == {"kinds": [], "total": 0}


def test_every_screen_route_answers_json_and_the_remake_travels_in_the_export(cockpit, month_read):
    client = api()
    for path in ("environment", "place/alpha", "buy", "stats", "library"):
        assert client.get(f"/api/screens/{path}").status_code == 200, path
    assert client.get("/api/screens/place/nowhere").status_code == 404
    world = cockpit.source.world_state(MONTH)
    assert WorldState.model_validate_json(world.model_dump_json()).remake.counts["blocked"] == 2


def test_a_library_with_no_blob_folder_reads_its_pictures_from_the_store_sides_cache(shelf, tmp_path):  # noqa: F811
    from score.dashboard.state import library
    blobs, cache = shelf.parent / "blobs", tmp_path / "cache"
    alpha = library.LocalLibrary(shelf, None, tmp_path / "thumbs", cache).entry("place/alpha@1")
    bare = library.LocalLibrary(shelf, None, tmp_path / "thumbs", cache)
    assert bare.picture_path(alpha.picture, 64) is None  # neither a blob nor a cached copy yet
    kept = cache / "place" / "alpha" / "1" / alpha.picture_file
    kept.parent.mkdir(parents=True)
    kept.write_bytes((blobs / "blobs" / alpha.picture[:2] / alpha.picture).read_bytes())
    assert bare.blob(alpha.picture) == kept and bare.picture_path(alpha.picture, 64).is_file()


def test_each_read_of_the_month_keeps_its_day_so_the_stats_show_how_the_month_grew(tmp_path):
    import datetime

    from score.dashboard.state import money
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    first = money.with_bill_days(MONTH.model_copy(update={"month": today[:7]}), tmp_path)
    assert first.bill_days == [{"day": today, "cloud": 2118.87, "models": None}]
    unread = MONTH.model_copy(update={"month": today[:7], "lines": []})
    assert money.with_bill_days(unread, tmp_path).bill_days == first.bill_days  # a line not read keeps the day's


def test_a_place_shows_its_design_state_and_no_numbers_until_its_inventory_is_read_from_its_picked_concept(world):
    from score.dashboard.tests import fixture
    from score.dashboard.tests.pages_test import signed_in
    from score.review import concepts

    def alpha():
        world.source.refresh()
        return next(place for place in screens.environment(world.source, MONTH)["places"] if place["place"] == "alpha")
    shown = alpha()
    assert (shown["design"], shown["progress"], shown["gaps"]) == ("review", None, None)  # drawn, not picked
    html = signed_in().get("/places/").content.decode()
    assert "data-v>in review</span>" in html and "data-v>to draw</span>" in html and 'class="ring' not in html
    assert 'href="/place/alpha/"' not in html and 'class="ptile" href="/concept/alpha/"' in html  # no Place screen
    page = signed_in("joey2").get("/place/alpha/").content.decode()
    assert "<iframe" not in page and 'href="/concept/alpha/"' in page and "data-v>in review</span>" in page
    sha = json.loads((world.data / "places/concepts.json").read_text())["concepts"]["alpha"]["sha256"]
    fixture.an_inventory_read(world.store, world.data, "alpha", sha)
    shown = alpha()
    assert shown["design"] is None and shown["progress"]["needed"] > 0 and shown["gaps"] is not None
    assert screens.place(world.source, "alpha", None)["progress"] is not None
    findings = world.root / "props/work/checks/gaps/alpha/findings.json"
    assert not findings.exists()
    findings.parent.mkdir(parents=True)
    findings.write_text("{}")
    os.utime(findings, (1760000000, 1760000000))  # gaps checked before the pick: read from an older inventory
    assert alpha()["design"] == "check"
    findings.unlink()
    inventory = world.data / "inventory/alpha.json"
    inventory.write_text(inventory.read_text().replace(sha, "o" * 64))  # read from an older concept
    shown = alpha()
    assert (shown["design"], shown["progress"], shown["gaps"]) == ("read", None, None)
    assert screens.place(world.source, "alpha", None)["items"] == []  # no gap of it, in 3D either
    inventory.write_text(inventory.read_text().replace("o" * 64, sha))
    concepts.recorded(world.store, "concepts/alpha/picks/2026-10-20T10-00-00.json",
                      {"place": "alpha", "sha": None, "by": "joey", "at": "2026-10-20T10:00:00+00:00"})
    shown = alpha()  # unlocked: its inventory counts for nothing again
    assert (shown["design"], shown["progress"]) == ("review", None)
