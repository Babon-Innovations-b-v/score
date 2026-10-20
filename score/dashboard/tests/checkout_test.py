"""The owner's one checkout of the basket items he bought: prices on the runner's numbers, every refusal in words, an
item changed since he chose it refused, a key that makes the same checkout twice, the runner's own plan of each item
held to what was priced, the environment's stop line written by the owner's name only outside an agent's process,
ONE batch through the fake backend (a run command an item), and the results against their forecast. Nothing
launches."""
import datetime
import os

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from fastapi.testclient import TestClient

from score.dashboard.checkout import flow, pricing
from score.dashboard.launch.backend import Billed, RunGroup
from score.dashboard.pages.models import BasketChoice, Checkout
from score.dashboard.proposals import make, records
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import FakeBackend
from score.store import AGENT_MARKERS

pytestmark = pytest.mark.django_db(transaction=True)
ORIGIN = "http://127.0.0.1:8780"
BOOKS = {"month": "2026-10", "bill": 0.0, "ledger": 0.0}  # what a first line counts from (the fake spend reads none)


def a_basket(settings, buys, declared=None, missing=()):
    """The basket as make.py leaves it, its items from `buys` (priced at the fake backend's numbers)."""
    settings.SCORE_HOME.mkdir(parents=True, exist_ok=True)
    priced = [{"node": node, "why": "never ran", "again": False, "price": dict(FakeBackend.price_of)} for node in buys]
    found = make.grouped(priced, {"closeup": "pieces"}, list(missing), declared or {})
    records.put_index(settings.SCORE_HOME / "proposals", {"made_at": "2026-10-19T08:00:00Z", "items": found})
    return {item["id"]: item for item in found}


@pytest.fixture
def shop(world, settings, monkeypatch):
    """The fixture environment, a basket of alpha's and beta's close-ups, the checkout run in this thread, no agent
    marks, the owner's books."""
    monkeypatch.setattr(flow, "run_soon", lambda record: flow.run(record, FakeBackend()))
    from score.review import web
    monkeypatch.setattr(web, "books_now", lambda: dict(BOOKS))
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    FakeBackend.plan_buys, FakeBackend.bill, FakeBackend.ceiling, FakeBackend.missing = None, [], 250.0, []
    world.items = a_basket(settings, ["closeup@alpha", "closeup@beta"])
    return world


def api(name="joey"):
    """A FastAPI test client carrying a signed-in Django session and its CSRF cookie."""
    from score.dashboard.site.asgi import app
    user = get_user_model().objects.create_user(name, password="a long enough password")
    pages = Client()
    pages.force_login(user)
    pages.get("/login/")
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        client.cookies.set(cookie.key, cookie.value)
    token = pages.cookies["csrftoken"].value if "csrftoken" in pages.cookies else ""
    client.headers.update({"X-CSRFToken": token, "Origin": ORIGIN})
    return client


def bought(shop, *idents, version=None):
    """His buy of the items, as he saw them."""
    for ident in idents:
        BasketChoice.objects.create(item=ident, version=version or shop.items[ident]["version"], choice="buy",
                                    by="joey")


def checked_out(client, key, confirmed=True):
    return client.post("/api/checkout", json={"key": key * 16, "confirmed": confirmed}).json()


def launches():
    return [call for call in FakeBackend.calls if call[0] == "launch"]


def stop_line(world):
    from score.review import web
    return web.stop_line(world.store, "world1")


# --- prices ------------------------------------------------------------------------------------------------------

def test_totals_count_each_node_once_and_say_what_is_unmeasured_or_unpriced():
    """Measured nodes make the price, each once; a node not measured yet adds its stage's guess apart, never to the
    price, and the stop line holds both (what the runner's clearance reserves)."""
    measured = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "cards": 2,
                "runs": 3}
    estimate = {"likely_euros": None, "high_euros": None, "guess_euros": 5.0, "likely_minutes": None,
                "high_minutes": None, "cards": None, "runs": 0, "basis": "not measured yet"}
    items = [{"nodes": {"closeup@alpha": measured, "closeup@beta": measured}},
             {"nodes": {"closeup@beta": measured, "pixal@alpha": estimate, "odd@alpha": {"error": "not a paid row"}}}]
    found = pricing.totals(pricing.basket_prices(items), jobs=1)
    assert (found["likely_euros"], found["high_euros"], found["guessed_euros"], found["nodes"]) == (4.0, 6.0, 5.0, 4)
    assert pricing.cleared_high(found) == 11.0
    assert found["likely_minutes"] == 20.0 and found["high_minutes"] == 40.0 and found["cards"] == 4
    assert found["unmeasured"] == ["pixal@alpha"] and found["unpriced"] == ["odd@alpha"]
    assert pricing.totals(pricing.basket_prices(items), jobs=8)["likely_minutes"] == 10.0  # the longest line


# --- refusals ----------------------------------------------------------------------------------------------------

def test_every_refusal_in_words(shop, settings, monkeypatch):
    client = api()
    said = checked_out(client, "c", confirmed=False)["said"]
    assert "choose Buy on at least one item first" in said and "I buy these" in said
    bought(shop, "alpha-pieces")
    from score.dashboard.pages import actions
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    assert "started from an agent's shell" in checked_out(client, "c")["said"]
    assert not Checkout.objects.exists() and not launches()


def test_an_item_changed_since_he_chose_it_or_waiting_or_missing_inputs_is_refused(shop, settings):
    client = api()
    bought(shop, "alpha-pieces", version="0" * 16)
    assert "changed since you chose it: look again" in checked_out(client, "k")["said"]
    BasketChoice.objects.all().delete()
    items = a_basket(settings, ["closeup@alpha"], {"ship-room-concepts": {"title": "Ship room concepts",
                                                                          "nodes": ["concept-views"]}},
                     ["closeup@alpha: a bake job (/x/job.json)"])
    shop.items = items
    bought(shop, "ship-room-concepts", "alpha-pieces")
    said = checked_out(client, "k")["said"]
    assert "Ship room concepts: a run on main does not buy it yet" in said and "inputs are missing" in said
    assert not Checkout.objects.exists() and not launches()


# --- the checkout ------------------------------------------------------------------------------------------------

def test_the_checkout_plans_each_item_writes_the_line_and_launches_one_batch(shop):
    client = api()
    bought(shop, "alpha-pieces", "beta-pieces")
    record = checked_out(client, "d")["checkout"]
    assert record["state"] == "launched", record
    line = stop_line(shop)
    assert line["euros"] == 100.0 + 10.0 + 33.0 and line["by"] == "joey"  # the batch's high plus 10%
    assert "alpha: pieces, beta: pieces" in line["reason"]
    assert record["stop_line"]["high"] == 30.0
    planned = [call[1] for call in FakeBackend.calls if call[0] == "plan"]
    assert planned == [RunGroup(("alpha",), ("closeup",)), RunGroup(("beta",), ("closeup",))]
    assert [call[1] for call in launches()] == planned and "the owner's checkout" in launches()[0][3]
    assert record["launch"] is not None and [item["id"] for item in record["items"]] == ["alpha-pieces", "beta-pieces"]


def test_the_same_key_is_the_same_checkout(shop):
    client = api()
    bought(shop, "alpha-pieces")
    first = checked_out(client, "e")
    again = checked_out(client, "e")
    assert again["checkout"]["id"] == first["checkout"]["id"] and "already made with this key" in again["said"]
    assert Checkout.objects.count() == 1 and len(launches()) == 1


def test_a_run_that_would_buy_more_than_was_priced_is_refused_before_the_line(shop):
    client = api()
    bought(shop, "alpha-pieces")
    FakeBackend.plan_buys = ["closeup@alpha", "closeup@beta"]
    found = Checkout.objects.get(pk=checked_out(client, "g")["checkout"]["id"])
    assert found.state == "refused" and "would also buy closeup@beta" in found.detail
    assert stop_line(shop) is None and not launches()


def test_a_run_that_buys_nothing_now_writes_no_line_and_launches_nothing(shop):
    client = api()
    bought(shop, "alpha-pieces")
    FakeBackend.plan_buys = []
    found = Checkout.objects.get(pk=checked_out(client, "n")["checkout"]["id"])
    assert found.state == "done" and "buys nothing now" in found.detail
    assert stop_line(shop) is None and not launches()


def test_a_basket_that_cannot_fit_under_the_runners_spend_is_refused_before_start(shop):
    client = api()
    bought(shop, "alpha-pieces")
    FakeBackend.ceiling = 115.0  # the runner still reads an older, lower line: room EUR 5 for a EUR 15 high
    found = Checkout.objects.get(pk=checked_out(client, "h")["checkout"]["id"])
    assert found.state == "refused" and "cannot finish under the stop: high EUR 15.00, room EUR 5.00" in found.detail
    assert not launches()


def test_an_agents_process_writes_no_line_and_launches_nothing(shop):
    client = api()
    bought(shop, "alpha-pieces")
    os.environ[AGENT_MARKERS[0]] = "1"  # the cockpit's own check passed (patched); the guard's writer still refuses
    try:
        record = checked_out(client, "i")["checkout"]
    finally:
        os.environ.pop(AGENT_MARKERS[0])
    found = Checkout.objects.get(pk=record["id"])
    assert found.state == "failed" and "PermissionError" in found.detail
    assert stop_line(shop) is None and not launches()


# --- results -----------------------------------------------------------------------------------------------------

def test_results_show_real_cost_against_forecast_gates_and_new_outputs(shop):
    client = api()
    bought(shop, "alpha-pieces", "beta-pieces")
    record = checked_out(client, "j")["checkout"]
    found = Checkout.objects.get(pk=record["id"])
    since = found.at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    FakeBackend.bill = [Billed("closeup@alpha", 8.5, 25.0, since), Billed("closeup@alpha", 0.5, 0.0, since),
                        Billed("closeup@beta", 99.0, 5.0, "2026-01-01T00:00:00Z")]  # an older run's line
    new = fixture.made(shop.store, shop.root / "work", "closeup", "alpha", tweak=7, minutes_ago=0)
    shop.source.refresh()  # the cockpit reads the store's index again within a minute; the test at once
    shown = client.get(f"/api/checkout/{record['id']}/results").json()
    alpha, beta = shown["items"]
    assert alpha["id"] == "alpha-pieces" and alpha["euros"] == 9.0 and alpha["forecast"]["high_euros"] == 15.0
    (node,) = alpha["nodes"]
    assert node["new"] and node["output"] == new and node["minutes"] == 25.0
    assert node["verdicts"] == [{"check": "looks", "answer": "pass", "reason": "0 faults"}]
    assert beta["euros"] is None and beta["nodes"][0]["output"] is None and beta["nodes"][0]["new"] is False
    fixture.made(shop.store, shop.root / "work", "closeup", "beta", "fail", faults=4, tweak=8, minutes_ago=0)
    shop.source.refresh()
    beta = client.get(f"/api/checkout/{record['id']}/results").json()["items"][1]
    assert beta["new_outputs"] == 1 and beta["failed_gates"] == 1
    assert shown["euros"] == 9.0 and shown["forecast"]["high_euros"] == 30.0
    assert client.get("/api/checkout/999/results").status_code == 404


# --- the shipped backend's price and ledger (subprocess replaced) ------------------------------------------------

def test_the_local_backend_prices_through_score_price_and_reads_the_ledger_by_node(settings, tmp_path):
    import json
    import types
    from score.dashboard.launch import localrun
    said = []

    def run(command, **_):
        said.append(command)
        return types.SimpleNamespace(returncode=0, stderr="", stdout="reading the ledger\n" + json.dumps(
            {"world": "world1", "nodes": {"closeup@alpha": {"likely_euros": 1.0, "high_euros": 2.0}}}))
    found = localrun.LocalBackend(run=run).price("world1", ["closeup@alpha"])
    assert found == {"closeup@alpha": {"likely_euros": 1.0, "high_euros": 2.0}}
    assert said[0][1:] == ["-m", "score", "price", "world1", "--node", "closeup@alpha", "--json"]
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in (
        {"ticket": "closeup@alpha k1", "euros": 3.0, "wall_minutes": 9, "started": "2026-10-18T12:00:00Z"},
        {"ticket": "closeup@alpha k0", "euros": 7.0, "wall_minutes": 9, "started": "2026-10-17T12:00:00Z"},
        {"ticket": "closeup@beta k2", "euros": 5.0, "wall_minutes": 9, "started": "2026-10-18T12:00:00Z"})) + "\n")
    settings.SCORE_LEDGER_FILES = [ledger]
    (line,) = localrun.LocalBackend(run=run).ledgered(["closeup@alpha"], "2026-10-18T00:00:00Z")
    assert (line.node, line.euros, line.minutes) == ("closeup@alpha", 3.0, 9)
