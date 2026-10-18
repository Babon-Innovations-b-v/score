"""The launch basket's plan and guard: money and time from measured runs, every refusal in words, the local backend's
command line and environment (subprocess replaced), and its result line read into states."""
import datetime
import subprocess
import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.utils import timezone

from score.dashboard.launch import guard, localrun
from score.dashboard.launch.backend import LaunchHandle, MeasuredRun, RunGroup
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


def test_money_likely_is_the_ledger_median_times_the_bill_factor_and_high_the_estimates():
    buys = [{"node": "closeup@alpha", "euros": 13.67}, {"node": "pixal@alpha", "euros": 20.0}]
    found = costs.money(buys, [MeasuredRun("closeup", 10.0, 30), MeasuredRun("closeup", 12.0, 40)], 1.21)
    assert found["high"] == 33.67
    assert found["likely"] == round(11.0 * 1.21 + 20.0, 2)  # pixal has no measured run: its estimate
    assert found["not_measured"] == ["pixal"]


def test_time_is_the_longest_line_or_the_total_over_jobs():
    per_stage = {"closeup": [10.0, 20.0, 30.0], "plan": [1.0]}
    nodes = ["closeup@alpha", "plan@alpha", "closeup@beta", "closeup@gamma"]
    found = costs.time_of(nodes, per_stage, jobs=1)
    assert found["likely_minutes"] == 20.0 + 1.0 + 20.0 + 20.0  # one job: the total
    assert costs.time_of(nodes, per_stage, jobs=8)["likely_minutes"] == 21.0  # the longest line
    assert costs.time_of(nodes, per_stage, jobs=8)["high_minutes"] == 31.0
    assert costs.hours(125) == "2 h 05 min" and costs.hours(14) == "14 min"


def test_finish_records_carried_or_without_minutes_are_left_out():
    found = costs.stage_minutes([{"node": "plan@a", "stage": "plan", "minutes": 2.0},
                                 {"node": "plan@b", "stage": "plan", "minutes": 9.0, "carried": {"reason": "x"}},
                                 {"node": "plan@c", "stage": "plan"}])
    assert found == {"plan": [2.0]}


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
    settings.SCORE_MONTH_EUROS = None
    assert any("stop is not set" in why for why in refused(plan))
    settings.SCORE_MONTH_EUROS = "250"
    settings.SCORE_STORE_WRITABLE = False
    assert any("read-only" in why for why in refused(plan))


def test_the_plan_is_worked_out_from_the_backend(world, settings):
    settings.SCORE_LEDGER_FILES = [world.ledger]
    items = [item("alpha", "closeup"), item("beta", "closeup")]
    plan = Plan.objects.create(basket_hash=guard.basket_hash(items), made_by="joey", body={"jobs": 4})
    guard.work_out(plan, items, world.source.stage_records, FakeBackend())
    plan.refresh_from_db()
    assert plan.state == "ready", plan.error
    money = plan.body["money"]
    assert money["high"] == round(2 * 13.67, 2) and money["likely"] == round(2 * 11.0 * 1.21, 2)
    assert money["room"] == 250.0 - 100.0 - 10.0
    assert plan.body["time"]["likely_minutes"] > 0


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
    settings.SCORE_MONTH_EUROS = "250"
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
    assert seen["env"]["SCORE_MONTH_EUROS"] == "250" and seen["cwd"] == settings.SCORE_REPO
    assert handle.pid == 4242 and handle.log == "/tmp/x.log" and handle.refused is None


def test_a_runner_refusal_before_detaching_is_refused_by_the_guard():
    def run(command, **options):
        return subprocess.CompletedProcess(command, 1, "refused: this run would buy accepted outputs again", "")
    handle = localrun.LocalBackend(run=run).launch(RunGroup(("alpha",), ("closeup",)), 8, None)
    assert "refused" in handle.refused
    assert localrun.LocalBackend().poll(handle).state == "refused"


def test_the_result_line_gives_the_state(tmp_path):
    backend = localrun.LocalBackend()
    for line, state in (("detached: ok exit=0 minutes=3 log=x", "done"), ("detached: failed exit=1", "failed"),
                        ("detached: stopped by signal 15 exit=143", "stopped")):
        log = tmp_path / f"{state}.log"
        log.write_text(f"working\n{line}\n")
        assert backend.poll(LaunchHandle(command=[], pid=None, log=str(log))).state == state
    log = tmp_path / "going.log"
    log.write_text("working\n")
    import os
    assert backend.poll(LaunchHandle(command=[], pid=os.getpid(), log=str(log))).state == "running"
    assert backend.poll(LaunchHandle(command=[], pid=None, log=str(log))).state == "failed"


@override_settings(SCORE_LEDGER_FILES=[])
def test_measured_runs_come_from_the_ledgers_tickets(tmp_path, settings):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"ticket": "closeup@alpha k", "euros": 9.5, "wall_minutes": 12}\n'
                      '{"ticket": null, "euros": 3}\n{"ticket": "terrain k2", "euros": 4.0, "minutes": 7}\n')
    settings.SCORE_LEDGER_FILES = [ledger]
    found = list(localrun.LocalBackend().measured())
    assert found == [MeasuredRun("closeup", 9.5, 12), MeasuredRun("terrain", 4.0, 7)]
