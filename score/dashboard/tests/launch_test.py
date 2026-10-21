"""The launch basket's plan and guard: money and time priced by the runner (the backend's price), every refusal
in words, the local backend's command line and environment, its price through `score price` and its ledger read
by node (subprocess replaced), and its result line read into states."""
import datetime
import pathlib
import subprocess
import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from score.dashboard.launch import guard, localrun
from score.dashboard.launch.backend import LaunchHandle, RunGroup
from score.dashboard.pages.models import BasketItem, Launch, Plan
from score.dashboard.state import costs
from score.dashboard.tests.fixture import FakeBackend

pytestmark = pytest.mark.django_db


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


def test_every_refusal_in_words(settings):
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
    assert costs.hours(125) == "2 h 05 min" and costs.hours(14) == "14 min"


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
    seen = {}

    def run(command, **options):
        seen.update(command=command, env=options["env"], cwd=options["cwd"])
        return subprocess.CompletedProcess(command, 0, "paid rows ...\ndetached: started pid=4242 log=/tmp/x.log\n", "")
    handle = localrun.LocalBackend(run=run).launch(RunGroup(("alpha", "beta"), ("closeup",)), 4, "lamp changed")
    assert seen["command"][1:] == ["-m", "score", "run", "world1", "--place", "alpha", "--place", "beta", "--stage",
                                   "closeup", "--jobs", "4", "--detach", "--rebuy-reason", "lamp changed"]
    assert "SCORE_DASHBOARD_SECRET_KEY" not in seen["env"] and "SCORE_SYNC_TOKEN" not in seen["env"]
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
    paid: the backend reads its start line, sees it running or ended, and ends on its result line."""
    import time
    backend = localrun.LocalBackend()
    handle = backend.launch(RunGroup(("camp",), ("terrain",)), 1, None)
    assert handle.refused is None and handle.pid and pathlib.Path(handle.log).is_file(), handle
    deadline = time.time() + 120
    while (found := backend.poll(handle)).state == "running" and time.time() < deadline:
        time.sleep(1)
    assert found.state == "done" and found.result.startswith("detached: ok exit=0"), found
