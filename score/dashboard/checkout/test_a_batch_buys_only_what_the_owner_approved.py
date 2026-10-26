"""Invariant: a batch buys only what the owner approved, at the runner's prices: his checkout (or his yes in chat)
refused in words for anything changed, waiting, unpriced, stale or not his; the runner's own plan held to what was
priced; the environment's stop line written by his name only outside an agent's process, at the batch's high plus
10% within one budget across its tries, taken back when the batch ends or is refused; ONE run command through the
backend; the results against their forecast. The launch guard (score/dashboard/launch) is this module's other way in:
its groups, its refusals in words and the local backend's command, environment, prices, ledger and result line.
Nothing launches but the real `score run --detach` of a run with nothing to make, in the sandbox home.

Breaks that turn this red (each applied once and seen red, then reverted):
- pricing.cleared_high: drop the guessed euros -> test_totals_count_each_node_once..., test_an_unmeasured_buy_...
- flow.place_refusals: `elif actions.agent_started():` -> `elif False:` -> test_every_checkout_refusal_is_in_words
- flow.bought_items: the version check -> `elif False:` -> test_an_item_changed_since_he_chose_it_...
- flow.BUFFER = 1.10 -> 1.0 -> test_the_checkout_plans_the_batch_once_writes_the_line_and_launches_one_run
- flow.refusals: `if actions.running_launch():` -> `if False:` -> test_a_press_while_a_batch_runs_is_refused_...
- guard.polled: drop "refused" from the states it reads -> test_a_checkout_whose_run_the_runner_refused_shows_...
- flow.start: the same-key early return -> `if False:` -> test_the_same_key_is_the_same_checkout
- flow.checking_out: the home's `fcntl.flock` -> `pass` -> test_a_checkout_waits_while_another_process_...
- flow.plan_refusals: `if extra:` -> `if False:` -> test_a_run_that_would_buy_more_than_was_priced_...
- flow.run: the buys-nothing check -> `if False:` -> test_a_run_that_buys_nothing_now_writes_no_line_...
- flow.room_refusals: the room check -> `if False:` -> test_a_basket_that_cannot_fit_under_the_runners_spend_...
- flow.run: `write_line` wrapped in `except PermissionError: pass` -> test_an_agents_process_writes_no_line_...
- flow.batch_groups: one RunGroup per node -> test_two_items_sharing_an_upstream_node_are_planned_once_...
- flow.stale_basket: the other-checkout check -> `if False:` -> test_a_basket_made_in_another_checkout_...
- flow.spend_now: `if books and spend.paid_refused:` -> `if False:` -> test_the_months_books_unknown_refuse_...
- flow.abandoned: `if record.pid is not None and pid_alive(...)` -> `if True:` -> test_a_checkout_left_launching_...
- flow.batches_ended: its skip -> `if True:` -> test_an_ended_batch_takes_its_line_back_once
- flow.launch: drop `record.launch = started` -> test_a_hosted_checkout_is_followed_to_its_run_with_its_stop_line
- results.billed_by_node: `(euros + line.euros, ...)` -> `(line.euros, ...)` -> test_results_show_real_cost_...
- flow.batch_groups: the Benchmarks group -> `if False:` -> test_the_benchmarks_are_one_item_on_the_buy_screen_...
- api/routes.books_figure: `user.username` -> "someone" -> test_the_google_figure_button_writes_the_owners_figure_...
- flow.by_of: `return user.username` -> test_a_buy_approved_in_chat_launches_his_checkout_once
- flow.yes_refusals: the stop check -> `if False:` -> test_a_buy_approved_in_chat_is_refused_outside_what_he_approved
- flow.batch_budget: a yes's `if used + need > total:` -> `if False:` -> test_a_batch_budget_counts_from_an_older_...
- flow.batch_budget: a retry's `return start, before` -> `before + need` -> test_a_batch_has_one_budget_across_its_tries
- flow.batch_start: `return None` for a line without batch_from -> test_a_batch_budget_counts_from_an_older_...
- guard.run_groups: the group key also takes the place -> test_groups_join_places_with_the_same_stages
- guard.refusals: the age check `> timedelta(minutes=PLAN_MINUTES)` -> `>= timedelta(0)` -> test_a_good_plan_has_...
- guard.money_refusals: the unknown-room refusal dropped -> test_every_launch_refusal_is_in_words
- guard.plan_body: room without `- spend.reserved` -> test_the_plan_is_worked_out_from_the_backend
- guard.plan_body: high `totals["high_euros"]` -> test_an_unmeasured_buy_is_held_at_its_estimate_in_the_high_only
- guard.launch: `record.state = "refused"` always -> test_a_launch_through_the_confirm_page
- localrun.run_env: `SECRETS + RUN_TAGS` -> `SECRETS` -> test_the_local_backends_command_line_and_environment
- localrun.LocalBackend.ledgered: drop the `>= since` filter -> test_the_local_backend_prices_through_score_price_...
- localrun.LocalBackend.poll: `if handle.refused is not None:` -> `if False:` -> test_a_runner_refusal_before_...
- localrun.RESULT_STATES "stopped" -> "failed" -> test_the_result_line_gives_the_state
- localrun.STARTED: `pid=(\\d+)` -> `pid=(\\d+)x` -> test_the_real_detached_start_line_is_read_and_followed_...
"""
import datetime
import os
import pathlib
import subprocess
import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from score.dashboard.checkout import flow, pricing
from score.dashboard.launch import guard, localrun
from score.dashboard.launch.backend import Billed, LaunchHandle, RunGroup
from score.dashboard.pages import basket
from score.dashboard.pages.models import BasketChoice, BasketItem, Checkout, Launch, Plan
from score.dashboard.proposals import make, records
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import FakeBackend, api
from score.store import AGENT_MARKERS

pytestmark = pytest.mark.django_db(transaction=True)
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

def test_every_checkout_refusal_is_in_words(shop, settings, monkeypatch):
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
    assert basket.batch_state(Checkout.objects.order_by("-pk").first())[0] == "running"  # the launched run's own state


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


# --- a Buy approved in chat (checkout/chat_yes.py) ----------------------------------------------------------------

QUESTION = "Batch 1: EUR 0 spent so far; this try likely EUR 20, high EUR 30, its stop EUR 33. Batch total EUR 33?"


@pytest.fixture
def chat(shop, settings, monkeypatch, tmp_path):
    """The shop as the conductor's door sees it: the owner set, the code on a pin read just now, no latch, no run, the
    agent markers set; the Buy screen's basket alpha's and beta's close-ups (high EUR 30, stop EUR 33)."""
    from score import conductor
    from score.conductor import health
    from score.dashboard.checkout import chat_yes
    from score.graph import runs
    settings.SCORE_OWNER = "joey"
    get_user_model().objects.create_user("joey", password="a long enough password")
    monkeypatch.setattr(health, "code", lambda: {"checkout": "582df3eb" * 5, "pin": "582df3eb",
                                                 "pin_at": chat_yes.now(), "matches": True})
    monkeypatch.setattr(conductor, "FREE_ONLY_LATCH", tmp_path / "free-only")
    monkeypatch.setattr(runs, "RUNS", tmp_path / "runs")
    from score.dashboard.state import screens
    monkeypatch.setattr(screens, "approved_places", lambda world: ["alpha", "beta"])
    monkeypatch.delenv("SCORE_FREE_ONLY", raising=False)
    for name in AGENT_MARKERS:
        monkeypatch.setenv(name, "1")
    return shop


def chat_buy(yes_id):
    """(Checkout or None, words or the refusal)."""
    from score.dashboard.checkout import chat_yes
    try:
        return chat_yes.buy(yes_id)
    except chat_yes.Refused as refused:
        return None, f"refused: {refused}"


def a_yes(total=33.0, high=30.0):
    from score.dashboard.checkout import chat_yes
    return chat_yes.record(total, high, "Yes, buy it", QUESTION)


def test_a_buy_approved_in_chat_launches_his_checkout_once(chat, monkeypatch):
    monkeypatch.setattr(FakeBackend, "log_folder", None)
    yes = a_yes()
    assert [item["id"] for item in yes["basket"]["items"]] == ["alpha-pieces", "beta-pieces"] and yes["by"] == "joey"
    record, said = chat_buy(yes["id"])
    assert record is not None and record.state == "launched", said
    line = stop_line(chat)
    assert line["euros"] == 100.0 + 10.0 + 33.0  # as his click: spent, in flight, the batch's high plus 10%
    assert line["by"] == record.by == f"joey, approved in chat at {yes['at']}"
    assert record.chat_yes["answer"] == "Yes, buy it" and record.chat_yes["question"] == QUESTION
    assert len(launches()) == 1 and all(os.getenv(name) == "1" for name in AGENT_MARKERS)  # back once launched
    from score.dashboard.checkout import watched
    assert watched.newest()["yes"]["answer"] == "Yes, buy it"
    # the same yes again is a retry of its batch (test_a_batch_has_one_budget_across_its_tries), never while it runs
    assert "still running" in chat_buy(yes["id"])[1] and len(launches()) == 1 and Checkout.objects.count() == 1


def test_a_buy_approved_in_chat_is_refused_outside_what_he_approved(chat, settings, monkeypatch, tmp_path):
    from score import conductor
    from score.conductor import health
    from score.dashboard.checkout import chat_yes
    from score.graph import runs
    from score.review import web

    def refused(yes_id, words):
        record, said = chat_buy(yes_id)
        assert record is None and words in said, said
        assert not web.buy_yes_used(chat.store, yes_id)  # refused before the yes was spent

    assert "above EUR 0" in str(pytest.raises(chat_yes.Refused, a_yes, total="nan").value)
    pytest.raises(chat_yes.Refused, chat_yes.record, 33, 30, "", QUESTION)
    refused("20261025T000000Z", "no quoted Buy yes")
    refused(a_yes(high=29.99)["id"], "its high is EUR 30.00, above the EUR 29.99")
    refused(a_yes(total=32.99)["id"], "its stop is EUR 33.00, above the batch total of EUR 32.99")
    older = {**a_yes(), "id": "20261025T000001Z", "stop_euros": 33.0}  # a try's stop, before batch totals
    older.pop("batch_total_euros")
    web.buy_yes_written(chat.store, older)
    refused(older["id"], "names a try's stop, not the batch total")
    code = health.code()
    monkeypatch.setattr(health, "code", lambda: {**code, "matches": False, "checkout": "0" * 40})
    refused(a_yes()["id"], "is not the cockpit's pin 582df3eb")
    monkeypatch.setattr(health, "code", lambda: {**code, "pin_at": "2026-10-01T00:00:00+00:00"})
    refused(a_yes()["id"], "not in the last 30 minutes")
    monkeypatch.setattr(health, "code", lambda: code)
    conductor.FREE_ONLY_LATCH.write_text("")
    refused(a_yes()["id"], "latched off")
    conductor.FREE_ONLY_LATCH.unlink()
    monkeypatch.setenv("SCORE_FREE_ONLY", "1")
    refused(a_yes()["id"], "latched off")
    monkeypatch.delenv("SCORE_FREE_ONLY")
    assert runs.claim("abc", ["closeup@alpha"], os.getpid(), folder=tmp_path / "runs") is None
    refused(a_yes()["id"], "a run is active")
    runs.unclaim(os.getpid(), folder=tmp_path / "runs")
    changed = a_yes()["id"]
    chat.items = a_basket(settings, ["closeup@alpha"])
    refused(changed, "the basket changed since he approved it")
    assert not Checkout.objects.exists() and not launches() and stop_line(chat) is None


def test_a_batch_has_one_budget_across_its_tries(chat, monkeypatch, tmp_path):
    """His yes is the batch's budget (owner, 2026-10-26: "those budget asks should become per batch tho, not per
    try"): the stop line is the batch's start plus it, a retry under the same yes that fits what is left needs no
    new ask and keeps the budget, one that does not fit is refused; a click over it raises it."""
    monkeypatch.setattr(FakeBackend, "log_folder", tmp_path)  # each run writes its result line: done
    yes = a_yes(total=100.0)
    first, said = chat_buy(yes["id"])
    assert first is not None and first.state == "launched", said
    assert stop_line(chat)["euros"] == 110.0 + 100.0  # the batch's start, spent and in flight, plus his budget
    assert (first.stop_line["batch_budget"], first.stop_line["batch_used"]) == (100.0, 0.0)
    monkeypatch.setattr(FakeBackend, "spent", 120.0)  # the first try spent 20
    again, said = chat_buy(yes["id"])
    assert again is not None and again.state == "launched" and again.key.endswith("-retry-1"), said
    assert stop_line(chat)["euros"] == 210.0  # the same budget: 80 left, not a new 100 on top
    assert (again.stop_line["batch_budget"], again.stop_line["batch_used"]) == (100.0, 20.0)
    from score.dashboard.checkout import watched
    money = watched.newest(reading=FakeBackend().spend)["money"]  # the guard's measure: 120 spent, 10 in flight
    assert (money["budget"], money["spent"], money["in_flight"], money["left"]) == (100.0, 10.0, 10.0, 80.0)
    from score.dashboard.checkout import chat_yes
    found = chat_yes.figures(FakeBackend().spend)  # what the next question names: the batch's total, not the try's
    assert (found["batch"], found["tries"], found["retry"], found["try"]["stop"]) == (1, 2, True, 33.0)
    assert (found["fits"], found["click"]) == (53.0, 100.0) and found["money"] == money
    monkeypatch.setattr(FakeBackend, "spent", 190.0)  # 90 spent with what is in flight: 10 left, a try needs 33
    record, said = chat_buy(yes["id"])
    assert "over the batch budget: EUR 90.00 spent of EUR 100.00" in said and record.state == "refused", said
    assert flow.batch_budget([first, again, record], 200.0, 33.0, None) == (110.0, 123.0)  # a click raises it


def test_a_batch_budget_counts_from_an_older_first_try_line():
    """A batch whose first try wrote its line before budgets (Batch 1) counts from what that line was written over;
    his new yes is the batch total, refused when the batch's spend so far plus this try's stop does not fit it."""
    older = Checkout(stop_line={"euros": 596.76, "spent": 300.0, "reserved": 0.0, "high": 100.0})
    this = Checkout(stop_line={})
    assert flow.batch_budget([older, this], 710.0, 250.0, {"batch_total_euros": 740.0}) == (300.0, 740.0)
    with pytest.raises(flow.Refused, match="over the batch total he approved: EUR 410.00 spent"):
        flow.batch_budget([older, this], 710.0, 250.0, {"batch_total_euros": 659.99})
    assert flow.batch_budget([this], 710.0, 33.0, None) == (710.0, 33.0)  # a new batch: its own stop


# --- the launch guard and the local backend ----------------------------------------------------------------------

def item(place, stage):
    return types.SimpleNamespace(place=place, stage=stage)


def test_groups_join_places_with_the_same_stages():
    groups = guard.run_groups([item("alpha", "closeup"), item("beta", "closeup"), item("beta", "plan"),
                               item("", "terrain")])
    assert RunGroup(places=("alpha",), stages=("closeup",)) in groups
    assert RunGroup(places=("beta",), stages=("closeup", "plan")) in groups
    assert RunGroup(places=(), stages=("terrain",)) in groups


def ready_plan(**money):
    body = {"groups": [{"places": ["alpha"], "stages": ["closeup"], "missing": [], "buys": [], "refusal": None,
                        "to_run": {}, "blocked": {}}], "buys": [], "jobs": 8, "rebuys": 0.0, "nodes": [],
            "money": {"high": 13.67, "likely": 13.31, "spent": 100.0, "reserved": 10.0, "ceiling": 250.0,
                      "room": 140.0, "note": "", **money}, "time": {"likely_minutes": 10, "high_minutes": 20}}
    return Plan.objects.create(basket_hash="h", made_by="joey", state="ready", body=body, finished=timezone.now())


def refused(plan, **given):
    arguments = {"user_is_owner": True, "current_hash": "h", "running": False, "confirmed": True,
                 "rebuy_reason": None, **given}
    return guard.refusals(plan, **arguments)


def test_a_good_plan_has_no_refusal():
    assert refused(ready_plan()) == []


def test_every_launch_refusal_is_in_words(settings):
    plan = ready_plan()
    assert "only the owner launches" in refused(plan, user_is_owner=False)
    assert any("basket changed" in why for why in refused(plan, current_hash="other"))
    assert any("still running" in why for why in refused(plan, running=True))
    assert any("I launch this" in why for why in refused(plan, confirmed=False))
    assert any("cannot finish under the stop: high EUR 200.00, room EUR 140.00" in why
               for why in refused(ready_plan(high=200.0)))
    assert any("no room under a stop is known: no bill" in why for why in refused(ready_plan(room=None, note="no bill")))
    stale = ready_plan()
    stale.finished = timezone.now() - datetime.timedelta(minutes=16)
    assert any("older than 15 minutes" in why for why in refused(stale))
    missing = ready_plan()
    missing.body["groups"][0]["missing"] = ["data/kit/alpha.json"]
    assert any("inputs are missing" in why for why in refused(missing))
    rebuy = ready_plan()
    rebuy.body["groups"][0]["refusal"] = "refused: re-buys"
    rebuy.body["rebuys"] = 9.0
    assert any("write the reason" in why for why in refused(rebuy))
    assert not any("write the reason" in why for why in refused(rebuy, rebuy_reason="the lamp changed"))
    settings.SCORE_STORE_WRITABLE = False
    assert any("read-only" in why for why in refused(plan))


def test_the_plan_is_worked_out_from_the_backend(world, settings):
    settings.SCORE_LEDGER_FILES = [world.ledger]
    items = [item("alpha", "closeup"), item("beta", "closeup")]
    plan = Plan.objects.create(basket_hash=guard.basket_hash(items), made_by="joey", body={"jobs": 4})
    FakeBackend.calls.clear()
    guard.work_out(plan, items, FakeBackend())
    plan.refresh_from_db()
    assert plan.state == "ready", plan.error
    assert ("price", "world1", ("closeup@alpha", "closeup@beta")) in FakeBackend.calls  # the runner prices, not us
    money = plan.body["money"]
    assert money["high"] == 2 * 15.0 and money["likely"] == 2 * 10.0, money
    assert money["room"] == 250.0 - 100.0 - 10.0
    assert plan.body["time"] == {"likely_minutes": 30.0, "high_minutes": 45.0}  # one line each, 4 jobs at once


def test_an_unmeasured_buy_is_held_at_its_estimate_in_the_high_only(world, settings):
    items = [item("alpha", "closeup")]
    plan = Plan.objects.create(basket_hash=guard.basket_hash(items), made_by="joey", body={})
    unmeasured = FakeBackend()
    unmeasured.price_of = {"likely_euros": None, "high_euros": None, "guess_euros": 7.5, "runs": 0}
    guard.work_out(plan, items, unmeasured)
    plan.refresh_from_db()
    money = plan.body["money"]
    assert (money["high"], money["likely"], money["not_measured"]) == (7.5, 0.0, ["closeup@alpha"]), money


def test_a_launch_through_the_confirm_page(world, settings, tmp_path):
    FakeBackend.log_folder = str(tmp_path)
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    client = Client()
    client.force_login(user)
    BasketItem.objects.create(place="alpha", stage="closeup", added_by="joey")
    plan = ready_plan()
    plan.basket_hash = guard.basket_hash(BasketItem.objects.all())
    plan.save()
    assert client.post(f"/basket/confirm/{plan.pk}/", {}).status_code == 200  # not ticked
    assert not Launch.objects.exists()
    monkey = guard.launch_soon
    guard.launch_soon = lambda record, chosen_plan: guard.launch(record, chosen_plan, FakeBackend())
    try:
        answer = client.post(f"/basket/confirm/{plan.pk}/", {"confirm": "yes"})
    finally:
        guard.launch_soon = monkey
    launched = Launch.objects.get()
    assert answer.status_code == 302 and launched.state == "running"
    assert guard.polled(launched, FakeBackend()).state == "done"
    assert ("launch", RunGroup(places=("alpha",), stages=("closeup",)), 8, None) in FakeBackend.calls


def test_the_local_backends_command_line_and_environment(monkeypatch, settings):
    monkeypatch.setenv("SCORE_DASHBOARD_SECRET_KEY", "secret")
    monkeypatch.setenv("SCORE_SYNC_TOKEN", "token")
    for tag in localrun.RUN_TAGS:  # a grant or cap in the sync service's environment never reaches the owner's batch
        monkeypatch.setenv(tag, "inherited")
    seen = {}

    def run(command, **options):
        seen.update(command=command, env=options["env"], cwd=options["cwd"])
        return subprocess.CompletedProcess(command, 0, "paid rows ...\ndetached: started pid=4242 log=/tmp/x.log\n", "")
    handle = localrun.LocalBackend(run=run).launch(RunGroup(("alpha", "beta"), ("closeup",)), 4, "lamp changed")
    assert seen["command"][1:] == ["-m", "score", "run", "world1", "--place", "alpha", "--place", "beta", "--stage",
                                   "closeup", "--jobs", "4", "--detach", "--rebuy-reason", "lamp changed"]
    assert "SCORE_DASHBOARD_SECRET_KEY" not in seen["env"] and "SCORE_SYNC_TOKEN" not in seen["env"]
    assert not set(localrun.RUN_TAGS) & set(seen["env"])
    assert seen["cwd"] == settings.SCORE_REPO
    assert handle.pid == 4242 and handle.log == "/tmp/x.log" and handle.refused is None


def test_the_local_backend_prices_through_score_price_and_reads_the_ledger_by_node(settings, tmp_path):
    import json
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


def test_a_runner_refusal_before_detaching_is_refused_by_the_guard():
    def run(command, **options):
        return subprocess.CompletedProcess(command, 1, "refused: this run would buy accepted outputs again", "")
    handle = localrun.LocalBackend(run=run).launch(RunGroup(("alpha",), ("closeup",)), 8, None)
    assert "refused" in handle.refused
    assert localrun.LocalBackend().poll(handle).state == "refused"


def test_the_result_line_gives_the_state(tmp_path):
    backend = localrun.LocalBackend()
    for line, state in (("detached: ok exit=0 minutes=3 log=x", "done"), ("detached: failed exit=1", "failed"),
                        ("detached: stopped by signal 15 exit=143", "stopped"),
                        ("detached: refused: another run holds the store exit=1", "refused")):
        log = tmp_path / f"{state}.log"
        log.write_text(f"working\n{line}\n")
        assert backend.poll(LaunchHandle(command=[], pid=None, log=str(log))).state == state
    log = tmp_path / "going.log"
    log.write_text("working\n")
    import os
    assert backend.poll(LaunchHandle(command=[], pid=os.getpid(), log=str(log))).state == "running"
    assert backend.poll(LaunchHandle(command=[], pid=None, log=str(log))).state == "failed"


def test_the_real_detached_start_line_is_read_and_followed_to_its_result_line():
    """The real `score run --detach` in this test's own PROPS_HOME (conftest), a run with nothing to make and nothing
    paid: the backend reads its start line, sees it running or ended, and ends on its result line. The camp's
    physics layer: a stage for the places with physics data only (the habitat), so the run holds no node at all
    (terrain, an empty store's first row, builds the grounds for minutes)."""
    import time
    backend = localrun.LocalBackend()
    handle = backend.launch(RunGroup(("camp",), ("physics-layer",)), 1, None)
    assert handle.refused is None and handle.pid and pathlib.Path(handle.log).is_file(), handle
    deadline = time.time() + 60
    while (found := backend.poll(handle)).state == "running" and time.time() < deadline:
        time.sleep(1)
    assert found.state == "done" and found.result.startswith("detached: ok exit=0"), found
