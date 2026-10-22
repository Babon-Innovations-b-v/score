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
from score.dashboard.pages import basket
from score.dashboard.pages.models import BasketChoice, Checkout
from score.dashboard.proposals import make, records
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import FakeBackend
from score.store import AGENT_MARKERS

pytestmark = pytest.mark.django_db(transaction=True)
ORIGIN = "http://127.0.0.1:8780"
BOOKS = {"month": "2026-10", "bill": 0.0, "ledger": 0.0}  # what a first line counts from (the fake spend reads none)


def made_now():
    """The time a basket is made, as make.py writes it."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def a_basket(settings, buys, declared=None, missing=()):
    """The basket as make.py leaves it, its items from `buys` (priced at the fake backend's numbers)."""
    settings.SCORE_HOME.mkdir(parents=True, exist_ok=True)
    priced = [{"node": node, "why": "never ran", "again": False, "price": dict(FakeBackend.price_of)} for node in buys]
    found = make.grouped(priced, {"closeup": "pieces"}, list(missing), declared or {})
    records.put_index(settings.SCORE_HOME / "proposals", {"made_at": made_now(), "checkout": str(settings.SCORE_REPO),
                                                          "items": found})
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
    FakeBackend.paid_refused = None
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

def test_the_checkout_plans_the_batch_once_writes_the_line_and_launches_one_run(shop, monkeypatch):
    monkeypatch.setattr(FakeBackend, "log_folder", None)  # its run writes no result line: still running
    client = api()
    bought(shop, "alpha-pieces", "beta-pieces")
    record = checked_out(client, "d")["checkout"]
    assert record["state"] == "launched", record
    line = stop_line(shop)
    assert line["euros"] == 100.0 + 10.0 + 33.0 and line["by"] == "joey"  # the batch's high plus 10%
    assert "alpha: pieces, beta: pieces" in line["reason"]
    assert record["stop_line"]["high"] == 30.0
    planned = [call[1] for call in FakeBackend.calls if call[0] == "plan"]
    assert planned == [RunGroup(("alpha", "beta"), ("closeup@alpha", "closeup@beta"))]
    assert [call[1] for call in launches()] == planned and "the owner's checkout" in launches()[0][3]
    assert record["launch"] is not None and [item["id"] for item in record["items"]] == ["alpha-pieces", "beta-pieces"]
    assert basket.last_batch()["state"] == "running"  # the Buy screen follows the launched run, not the checkout


def test_a_press_while_a_batch_runs_is_refused_and_launches_nothing(shop, monkeypatch):
    """Audit (2026-10-22): no test pressed Buy again while the first checkout's batch still ran."""
    monkeypatch.setattr(FakeBackend, "log_folder", None)  # its run writes no result line: still running
    client = api()
    bought(shop, "alpha-pieces")
    assert checked_out(client, "r")["checkout"]["state"] == "launched"
    said = checked_out(client, "s")["said"]
    assert "a launch from this cockpit is still running" in said, said
    assert Checkout.objects.count() == 1 and len(launches()) == 1


def test_a_checkout_whose_run_the_runner_refused_shows_refused_not_launched(shop, tmp_path, monkeypatch):
    """Audit (2026-10-22): the Basket's last checkout line read "launched" after its run's result line said refused."""
    import pathlib
    monkeypatch.setattr(FakeBackend, "log_folder", tmp_path)
    client = api()
    bought(shop, "alpha-pieces")
    record = Checkout.objects.get(pk=checked_out(client, "u")["checkout"]["id"])
    assert record.state == "launched"
    pathlib.Path(record.launch.handles[0]["log"]).write_text(
        "score run: started\ndetached: refused: the month's books are unknown\n")
    line = basket.last_checkout()
    assert line.startswith(f"Checkout {record.pk}: refused.") and "books are unknown" in line, line


def test_the_same_key_is_the_same_checkout(shop):
    client = api()
    bought(shop, "alpha-pieces")
    first = checked_out(client, "e")
    again = checked_out(client, "e")
    assert again["checkout"]["id"] == first["checkout"]["id"] and "already made with this key" in again["said"]
    assert Checkout.objects.count() == 1 and len(launches()) == 1


def test_a_checkout_waits_while_another_process_of_this_home_is_checking_out(shop, settings):
    """Audit (2026-10-22): the checkout's lock was this process's alone, so the local cockpit and a sync pass applying
    a hosted Buy could both pass "another checkout is still launching" and both launch. The other process here holds
    the home's checkout lock for 1.5 s."""
    import subprocess
    import sys
    import time
    holder = subprocess.Popen([sys.executable, "-c", "import fcntl, sys, time; held = open(sys.argv[1], 'a'); "
                               "fcntl.flock(held, fcntl.LOCK_EX); print('held', flush=True); time.sleep(1.5)",
                               str(settings.SCORE_HOME / "checkout.lock")], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        client, began = api(), time.monotonic()
        bought(shop, "alpha-pieces")
        checked_out(client, "w")
        assert time.monotonic() - began >= 1.0
        assert Checkout.objects.count() == 1 and len(launches()) == 1
    finally:
        holder.wait(timeout=10)


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
    line = stop_line(shop)  # the line its yes wrote is taken back to the spend so far plus what is in flight
    assert line["euros"] == 110.0 and line["before"] == round(110.0 + 15.0 * 1.1, 2), line
    assert found.stop_line["closed"]["euros"] == 110.0 and "refused" in line["reason"]


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


def test_two_items_sharing_an_upstream_node_are_planned_once_and_launched_as_one_run(shop, settings):
    """Two items at one place (its pieces and its stage and films) read the same upstream nodes: one runner command
    holds both, each node named, so the runner's clash check (graph/runs.py) has no second run to refuse."""
    from score.dashboard.launch import localrun
    shop.items = a_basket(settings, ["closeup@alpha", "pixal@alpha"])
    assert sorted(shop.items) == ["alpha-pieces", "alpha-stage-and-films"]
    FakeBackend.plan_buys = ["closeup@alpha", "pixal@alpha"]
    bought(shop, "alpha-pieces", "alpha-stage-and-films")
    record = checked_out(api(), "s")["checkout"]
    assert record["state"] == "launched", record
    (planned,) = [call[1] for call in FakeBackend.calls if call[0] == "plan"]
    (launched,) = launches()
    assert launched[1] == planned == RunGroup(("alpha",), ("closeup@alpha", "pixal@alpha"))
    assert localrun.run_command(launched[1], 8, None)[4:] == [
        "world1", "--place", "alpha", "--stage", "closeup@alpha", "--stage", "pixal@alpha", "--jobs", "8", "--detach"]


def test_a_basket_made_in_another_checkout_or_before_the_design_changed_is_refused(shop, settings):
    from score.review import concepts
    client = api()
    bought(shop, "alpha-pieces")
    root = settings.SCORE_HOME / "proposals"
    made = records.index(root)
    records.put_index(root, {**made, "checkout": "/home/x/score/.claude/worktrees/agent-ad171d0a"})
    said = checked_out(client, "w")["said"]
    assert "the basket was made in /home/x/score/.claude/worktrees/agent-ad171d0a, not in this cockpit's" in said
    records.put_index(root, {**made, "made_at": "2026-10-19T08:00:00Z"})
    concepts.recorded(shop.store, "concepts/alpha/picks/20261021T090000.000000+0000.json",
                      {"place": "alpha", "sha": "a" * 64, "by": "joey", "at": "2026-10-21T09:00:00+00:00"})
    said = checked_out(client, "w")["said"]
    assert "the basket was made at 2026-10-19T08:00:00Z, before the design last changed (" in said, said
    assert not Checkout.objects.exists() and not launches()
    records.put_index(root, {**made, "made_at": made_now()})  # the next pass's basket
    assert checked_out(client, "w")["checkout"]["state"] == "launched"


def test_the_months_books_unknown_refuse_before_any_line(shop):
    FakeBackend.paid_refused = "the cloud bill of 2026-10 is not read"
    client = api()
    bought(shop, "alpha-pieces")
    found = Checkout.objects.get(pk=checked_out(client, "b")["checkout"]["id"])
    assert found.state == "refused" and "the month's books are not known (the cloud bill of 2026-10 is not read)" \
        in found.detail and "press Read the bills on the Buy screen" in found.detail
    assert stop_line(shop) is None and not launches()


def test_a_checkout_left_launching_by_a_gone_process_is_failed_on_the_next_one(shop):
    import subprocess
    import sys
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    left = [Checkout.objects.create(key=key * 32, by="joey", state="launching", pid=pid)
            for key, pid in (("p", gone.pid), ("q", None))]  # None: a row from before the pid was kept
    client = api()
    bought(shop, "alpha-pieces")
    record = checked_out(client, "m")["checkout"]  # not refused as "another checkout is still launching"
    assert record["state"] == "launched", record
    for each in left:
        each.refresh_from_db()
        assert each.state == "failed" and f"(pid {each.pid}) ended before it launched" in each.detail


def test_an_ended_batch_takes_its_line_back_once(shop, tmp_path, monkeypatch):
    monkeypatch.setattr(FakeBackend, "log_folder", tmp_path)  # its run writes its result line: done
    client = api()
    bought(shop, "alpha-pieces")
    record = checked_out(client, "t")["checkout"]
    assert stop_line(shop)["euros"] == 126.5
    assert flow.tidied(FakeBackend()) == "checkouts: 0 left launching failed, 1 ended batches' lines taken back"
    line = stop_line(shop)
    assert line["euros"] == 110.0 and f"checkout {record['id']} closed: its batch ended done" in line["reason"]
    assert flow.tidied(FakeBackend()).endswith("0 ended batches' lines taken back")


def test_a_hosted_checkout_is_followed_to_its_run_with_its_stop_line(shop, monkeypatch):
    """Applied on the store's machine, a launched checkout reports running with its launch's id (the pass follows
    it to its end) and the stop line it wrote."""
    from score.dashboard.sync import applying
    seen = [{"id": "alpha-pieces", "version": shop.items["alpha-pieces"]["version"]}]
    item = {"id": 3, "kind": "checkout", "user": "joey", "payload": {"key": "h" * 32, "items": seen}}
    applied = applying.apply_checkout(item)
    found = Checkout.objects.get(key="h" * 32)
    assert applied.state == "running" and applied.launch_id == found.launch_id is not None, applied
    assert "stop line EUR 126.50" in applied.detail and "its high EUR 15.00 plus 10%" in applied.detail


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


# --- the Benchmarks item (#21) -----------------------------------------------------------------------------------

LISTED = [  # prepare's record as score/stages/complete/prepare/benchmarks.listed writes it
    {"id": "pixal-l4", "what": "Pixal3D on one L4", "likely_euros": 1.5, "high_euros": 2.81, "guess_euros": None,
     "likely_minutes": 91.3, "high_minutes": 183.3, "gap": None},
    {"id": "film", "what": "the hub's film", "likely_euros": None, "high_euros": None, "guess_euros": 3.5,
     "likely_minutes": 64.0, "high_minutes": 144.0, "gap": None},
    {"id": "batch-direct", "what": "batch against direct", "gap": "no paid path asks a finish list direct"}]


def a_prepare_record(settings, listed=LISTED):
    import json
    from score.dashboard.proposals import benchmarks
    path = settings.SCORE_PROPS_HOME / benchmarks.RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"benchmarks": {"listed": listed}}))


def test_the_benchmarks_are_one_item_on_the_buy_screen_and_one_batch_at_its_high_plus_ten_percent(shop, settings):
    from score.dashboard.launch import localrun
    from score.dashboard.proposals import benchmarks
    a_prepare_record(settings)
    said = benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME)
    assert said == "benchmarks: EUR 1.50 to 6.31, 2 to run, 1 gaps", said
    benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME)  # a second pass replaces it
    item = records.item(settings.SCORE_HOME / "proposals", "benchmarks")
    assert [each["id"] for each in records.items(settings.SCORE_HOME / "proposals")].count("benchmarks") == 1
    assert item["title"] == "Benchmarks" and item["gaps"][0]["id"] == "batch-direct"
    client = api()
    row = next(each for each in client.get("/api/screens/buy").json()["items"] if each["id"] == "benchmarks")
    assert (row["likely"], row["high"], row["guessed"], row["nodes"], row["blocked"]) == (1.5, 2.81, 3.5, 2, False)
    BasketChoice.objects.create(item="benchmarks", version=item["version"], choice="buy", by="joey")
    screen = client.get("/api/screens/buy").json()
    assert screen["stop"] == round(6.31 * 1.1, 2) and screen["eta"]["likely_minutes"] == round(91.3 + 64.0, 1)
    record = checked_out(client, "e")["checkout"]
    assert record["state"] == "launched", record
    assert stop_line(shop)["euros"] == round(100.0 + 10.0 + 6.31 * 1.1, 2)  # spent, in flight, its high plus 10%
    assert not [call for call in FakeBackend.calls if call[0] == "plan"]  # its batch plans each benchmark itself
    (launched,) = launches()
    assert launched[1] == RunGroup((), (), benchmarks=True)
    assert localrun.run_command(launched[1], 8, None)[1:] == ["-m", localrun.BENCHMARKS, "run", "--detach"]


def test_the_google_figure_button_writes_the_owners_figure_into_the_books(shop, monkeypatch):
    from score.review import web
    written = []
    monkeypatch.setattr(web, "google_month", lambda euros, by: written.append((euros, by)) or {"month": "2026-10"})
    answer = api().post("/api/money/books-figure", json={"euros": 1030})
    assert answer.status_code == 200 and "EUR 1030.00 entered by joey" in answer.json()["said"], answer.text
    assert written == [(1030.0, "joey")]


def test_no_benchmark_that_can_run_is_no_item(settings):
    from score.dashboard.proposals import benchmarks
    a_prepare_record(settings, LISTED[2:])
    assert benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME) == "benchmarks: none listed"
    assert records.item(settings.SCORE_HOME / "proposals", "benchmarks") is None
