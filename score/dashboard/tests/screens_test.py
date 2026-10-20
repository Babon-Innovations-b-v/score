"""Each cockpit screen's JSON (state/screens.py, GET /api/screens/...), on the fixture environment with its holes
priced by the runner, a prepare record shaped like the real one (takes by status, those waiting on lost inputs
counted in its figure), the month's spend as `score spend` writes it and a tiny library: the remake is prepare's
figure plus the holes price off the prop route, the ETA a range only when both parts have one, a place's picture
from the store else the library, the model calls' month None when not read, the basket's stop its high plus 10%, and the
library's counts by kind."""
import json

import pytest

from score.dashboard.pages.models import BasketChoice
from score.dashboard.proposals import records
from score.dashboard.state import local, screens
from score.dashboard.state.models import CostLine, Spend, WorldState
from score.dashboard.tests.library_test import api, shelf  # noqa: F401  (a pytest fixture)
from score.dashboard.tests.pages_test import MEASURED, a_holes_finding, a_holes_price

pytestmark = pytest.mark.django_db(transaction=True)
SETTLE = {**MEASURED, "basis": "measured runs"}  # a paid step off the prop route, measured
MONTH = Spend(spent=120.0, reserved=30.0, ceiling=900.0, world="world1", month="2026-10", days=[
    {"day": "2026-10-19", "cloud": 4.5, "models": 0.0}, {"day": "2026-10-20", "cloud": 1.25, "models": 0.4}], lines=[
    CostLine(source="cloud", label="Cloud compute", euros=2118.87, origin="the cloud bill"),
    CostLine(source="models", label="Model calls", euros=None, partial=True, origin="no rows yet")])


def take(place, status, lost=True):
    return {"place": place, "take": f"{place}_{status}", "status": status,
            "inputs": ["view v1's picture is not in the work folder"] if lost else []}


def a_remake(world, priced_on=None):
    """Prepare's record (WORK/checks/prepare/remake.json) as the real one is shaped: alpha's three takes, two bought
    waiting on a lost input and one a predicted hole, priced EUR 10 to 12 with the likeness calibration unpriced."""
    folder = world.root / "props/work/checks/prepare"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "remake.json").write_text(json.dumps({
        "made_at": "2026-10-20T11:19:22+00:00",
        "priced_on": priced_on or {**local.priced_here(), "uncommitted": False},
        "takes": [take("alpha", "bought"), take("alpha", "bought"), take("alpha", "predicted hole")],
        "layers": {"closeup": {"takes": 2, "price": {"likely_euros": 10.0, "high_euros": 12.0}},
                   "likeness-calibration": {"takes": 2, "price": {"likely_euros": None, "high_euros": None}}},
        "totals": {"likely_euros": 10.0, "high_euros": 12.0, "unpriced": ["likeness-calibration"]},
        "eta": {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "path": [],
                "unknown": [{"node": "closeup"}, {"node": "pixal"}]}}))


@pytest.fixture
def month_read():
    """The routes read the month through their FastAPI dependency (actions' reader): MONTH in its place."""
    from score.dashboard.pages import actions
    from score.dashboard.site.asgi import inner
    inner.dependency_overrides[actions.spend] = lambda: MONTH
    yield MONTH
    inner.dependency_overrides.clear()


@pytest.fixture
def cockpit(world, settings, tmp_path):
    """The fixture environment with alpha's holes priced (the close-up on the prop route, settle off it and measured,
    the sound guessed), prepare's record, and the basket made."""
    items = a_holes_finding(world, settings, tmp_path)
    a_holes_price(world, nodes={"closeup@alpha": {**MEASURED, "basis": "per unit × forecast"},
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
    from score.dashboard.state import library
    found = screens.environment(cockpit.source, MONTH, library.library())
    remake = found["remake"]
    assert remake["route"]["likely"] == 10.0 and remake["route"]["blocked"] == 2
    assert remake["route"]["predicted_holes"] == 1
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
    assert all(place["picture"] for place in found["places"])  # the store's, else the library's
    assert found["gaps"] == {"missing": 2, "gate": 1, "route": 1}


def test_a_place_with_no_stored_picture_takes_the_librarys_and_none_without_a_library(cockpit, shelf):  # noqa: F811
    from score.dashboard.state import library
    shown = library.library()
    place_entry = shown.entry("place/alpha@1")
    assert screens.library_picture(shown, "alpha") == f"/library-files/thumbs/{place_entry.picture}.jpg"
    assert screens.library_picture(None, "alpha") is None
    card = next(card for card in screens.cards(cockpit.source.world_state()) if card.place == "alpha")
    bare = card.model_copy(update={"hero": None, "still": None})
    assert screens.picture_of(bare, shown) == (f"/library-files/thumbs/{place_entry.picture}.jpg", "library")


def test_a_remake_priced_on_code_not_committed_says_it_is_stale(cockpit):
    a_remake(cockpit, priced_on={"commit": "6cdf4d40", "uncommitted": True, "per_unit_sha256": "x"})
    cockpit.source.refresh()
    assert screens.remake_money(cockpit.source.world_state())["stale"] == ["it was made on code not committed"]


def test_the_place_screen_lists_its_holes_as_items_and_each_chain_priced_once(cockpit):
    found = screens.place(cockpit.source, "alpha", None)
    assert [item["kind"] for item in found["items"]] == ["missing", "missing", "gate", "route"]
    assert found["items"][0]["prim"] == "/alpha/Holes/lamp_1" and found["items"][0]["node"] == "closeup@alpha"
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


def test_the_batch_is_the_whole_remake_by_layer_its_estimate_apart_and_a_step_with_no_price_unknown(cockpit):
    found = screens.batch(cockpit.source.world_state())
    assert found["total"] == {"likely": 12.0, "high": 15.0}  # the remake: prepare's 10 to 12 plus settle's 2 to 3
    assert found["estimated"] == {"likely": 10.0, "high": 12.0}  # prepare's per unit x count; settle is measured
    assert (found["jobs"], found["unpriced"]) == (6, 3)  # two close-ups, two calibrations unpriced, settle, sound
    models, motion, sound = found["layers"]
    assert (models["layer"], models["likely"], models["high"], models["jobs"], models["unpriced"]) == (
        "models", 10.0, 12.0, 4, 2)
    assert models["places"] == [{"place": "alpha", "jobs": 4, "likely": None, "high": None}]
    assert (motion["layer"], motion["likely"], motion["high"], motion["estimated"]) == (
        "motion", 2.0, 3.0, {"likely": 0.0, "high": 0.0})
    assert motion["places"] == [{"place": "alpha", "jobs": 1, "likely": 2.0, "high": 3.0}]
    assert (sound["layer"], sound["likely"], sound["unpriced"]) == ("sound", None, 1)  # a guess is never a price


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
    assert found["total"] == 14 and kinds["model"]["count"] == 3 and kinds["model"]["locked"] == 1
    assert kinds["place"]["count"] == 1 and kinds["model"]["pictured"] == 3 and kinds["model"]["scored"] == 2
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
