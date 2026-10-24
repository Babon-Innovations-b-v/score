"""The run monitor (`/buy/run/`, pages/run_monitor.py, state/batch_run.py, checkout/watched.py): the newest Buy's batch
read from its checkout, its run's log, its rows' logs and its warm pool; its state, rows, money, scenes, machines and
problems; the page for the owner (Stop only for him, only while it lives), Home's link while it lives, the Buy's yes
opening it, and the export carrying it to the hosted cockpit, which says how fresh it is and shows a Buy sent but not
answered yet. Every file is the test's own: a fixture store, a written log and a written pool."""
import datetime
import json
import os
import re
import time

import pytest
from django.test import override_settings

from score.dashboard.pages import run_monitor
from score.dashboard.pages.models import Checkout, Launch, Plan, SyncRequest
from score.dashboard.state import batch_run
from score.dashboard.state.exported import ExportedSource
from score.dashboard.sync import building
from score.dashboard.tests.pages_test import prose, signed_in
from score.dashboard.tests.sync_test import MADE, SPEND

pytestmark = pytest.mark.django_db
RUN = "joey-1-1792840013"
TOTALS = {"likely_euros": 186.14, "high_euros": 327.24, "guessed_euros": 33.16, "likely_minutes": 121.5,
          "high_minutes": 305.3, "unmeasured": ["closeup@beta"]}
PLAN = {"groups": [{"places": ["alpha", "beta"], "to_run": {"terrain": "to run", "plan@alpha": "to run"},
                    "blocked": {"assembly@alpha": "waits", "assembly@beta": "waits"},
                    "buys": [{"node": "closeup@alpha"}, {"node": "closeup@beta"}]}]}
LOG = """paid rows this run would buy: 2, about EUR 8.33; re-buys of accepted outputs: 0, about EUR 0.00
[cloud] 13:07:00 pool of 2 gpu-24gb, 1 cpu-16c-64gb opened for run {run} until 17:07; jobs start on the first warm card
heartbeat 2026-10-24T11:09:00+00:00: rows done 0, running 2, queued 4; this run's rows: paid runs open 1, EUR 0.00 in the ledger since the run started
terrain: made: pass, accepted automatically
plan@alpha: fresh
heartbeat 2026-10-24T11:11:00+00:00: rows done 2, running 2, queued 2; this run's rows: paid runs open 1, EUR 1.20 in the ledger since the run started
closeup@beta: blocked: no card of gpu-24gb was had before the deadline: the takes are gaps; fault report /x/faults/closeup@beta.txt
assembly@beta: not run: its line stopped at closeup@beta
heartbeat 2026-10-24T11:13:00+00:00: rows done 4, running 1, queued 1; this run's rows: paid runs open 1, EUR 3.21 in the ledger since the run started
"""


def a_pool(props, short_word=True):
    """The run's warm pool: two cards and a processor machine asked, one card warm and busy, the rest not in stock."""
    folder = props / "cloud" / "pools" / RUN
    (folder / "cards").mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"sizes": {"gpu-24gb": 2, "cpu-16c-64gb": 1},
                                                  "deadline": time.time() + 3600}))
    (folder / "cards" / "m-1.json").write_text(json.dumps({"id": "m-1", "class": "gpu-24gb", "for": "gpu-24gb",
                                                           "holder": 4242}))
    said = "pool: 2 card(s) short, none in stock; asking again in 3 min" if short_word else "rented a card"
    (folder / "collector.log").write_text(f"[cloud] 13:07:13 rented a card\n{said}\n")


def a_batch(world, log=LOG, state="launched", pool=True):
    """A checkout launched one run whose log is `log`; closeup@alpha's own log written since (it runs now)."""
    props, store = world.source.props_home, world.source.store_root
    (props / "logs").mkdir(parents=True, exist_ok=True)
    path = props / "logs" / "score-run-1.log"
    path.write_text(log.format(run=RUN))
    plan = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready", body=PLAN)
    launch = Launch.objects.create(plan=plan, by="joey", state="running", handles=[
        {"command": ["score", "run"], "pid": None, "log": str(path), "refused": None}])
    record = Checkout.objects.create(key="a" * 32, by="joey", state=state, totals=TOTALS, launch=launch,
                                     items=[{"nodes": {"closeup@alpha": {}, "closeup@beta": {}}}],
                                     stop_line={"euros": 396.44, "at": "2026-10-24T11:08:38+00:00"})
    (store / "logs").mkdir(parents=True, exist_ok=True)
    row_log = store / "logs" / "closeup@alpha.log"
    row_log.write_text("drawing\n")
    later = time.time() + 5
    os.utime(row_log, (later, later))
    if pool:
        a_pool(props)
    return record


def test_the_batch_is_read_from_its_log_its_rows_and_its_pool(world):
    a_batch(world)
    run = world.source.batch_run()
    assert run["state"] == "running" and run["checkout"] == Checkout.objects.get().pk
    assert run["rows"] == {"total": 6, "done": 2, "failed": 1, "not_run": 1, "running": 1, "queued": 1}
    assert run["money"]["spent"] == 3.21 and run["money"]["stop"] == 396.44 and run["money"]["high"] == 327.24
    assert run["eta"]["likely_minutes"] == 121.5 and run["eta"]["untimed"] == 1
    scenes = {scene["place"]: scene for scene in run["scenes"]}
    assert scenes[""] == {"place": "", "total": 1, "done": 1, "failed": 0, "not_run": 0, "running": [],
                          "state": "done"}
    assert scenes["alpha"]["running"] == ["close-ups"] and scenes["alpha"]["state"] == "working"
    assert scenes["beta"]["failed"] == 1 and scenes["beta"]["not_run"] == 1 and scenes["beta"]["state"] == "failed"
    assert run["pool"]["cards"] == {"size": 2, "warm": 1, "busy": 1, "idle": 0, "short": 1}
    assert run["pool"]["processors"] == {"size": 1, "warm": 0, "busy": 0, "idle": 0, "short": 1}
    assert run["pool"]["open"] and run["pool"]["stock"]
    [problem] = run["problems"]
    assert problem["place"] == "beta" and problem["kind"] == "failed"
    assert problem["words"].startswith("The close-ups step stopped: no card of 24 GB graphics card was had") and \
        "gpu-" not in problem["words"] and "1 later step" in \
        problem["words"] and "fault report" not in problem["words"]


def test_the_state_follows_the_checkout_the_result_line_and_the_pool(world):
    record = a_batch(world, log=LOG + "detached: ok exit=0 minutes=15.6 log=x outputs=y\n")
    run = world.source.batch_run()
    assert run["state"] == "finished" and run["ended"] and run["scenes"][1]["running"] == []
    record.launch.handles[0]["log"] = str(world.source.props_home / "logs" / "gone.log")
    record.launch.state = "running"
    record.launch.save()
    (world.source.props_home / "logs" / "gone.log").write_text(
        LOG.format(run=RUN) + "detached: stopped by signal 15 exit=143 minutes=0.0 log=x outputs=y\n")
    run = world.source.batch_run()
    assert run["state"] == "stopped" and run["problems"][0]["kind"] == "run"
    Checkout.objects.update(state="launching", launch=None)
    assert world.source.batch_run()["state"] == "starting"


def test_no_warm_card_while_stock_is_short_is_waiting_for_machines():
    pool = {"open": True, "cards": {"warm": 0, "short": 2}}
    assert batch_run.overall({"state": "launched", "launch": {}}, None, True, pool)[0] == "waiting"
    pool["cards"]["warm"] = 1
    assert batch_run.overall({"state": "launched", "launch": {}}, None, True, pool)[0] == "running"
    assert batch_run.overall({"state": "launched", "launch": {}}, None, False, None) == (
        "stopped", "the run ended without its result line")


def test_a_finished_rows_batch_gaps_are_problems(world):
    a_batch(world)
    found = batch_run.gathered(batch_run_input(), world.source.props_home, world.source.store_root,
                               lambda node: [{"name": "hatch: no model"}] if node == "plan@alpha" else [])
    gaps = [problem for problem in found["problems"] if problem["kind"] == "gaps"]
    assert gaps == [{"at": "2026-10-24T11:09:00+00:00", "place": "alpha", "node": "plan@alpha", "kind": "gaps",
                     "words": "Plan left 1 thing out as gaps.", "tip": "hatch: no model"}]


def batch_run_input():
    from score.dashboard.checkout import watched
    return watched.newest()


def test_scenes_show_parent_scenes_before_their_child_scenes():
    within = {"cockpit": "ship", "galley": "ship", "ship": "hangar", "flat": "block"}
    names = {"hangar": "Hangar", "ship": "Ship", "cockpit": "Cockpit", "galley": "Galley", "flat": "Flat"}
    found = run_monitor.ordered(["galley", "flat", "hangar", "cockpit", "ship", ""], within, names)
    assert found == [("", 0), ("flat", 0), ("hangar", 0), ("ship", 1), ("cockpit", 2), ("galley", 2)]


def test_the_owner_sees_the_monitor_with_stop_and_few_words(world, settings):
    a_batch(world)
    html = signed_in().get("/buy/run/").content.decode()
    assert "Running" in html and "Batch" in html and 'data-url="/api/machine/stop"' in html
    assert re.search(r"3\.21", html) and "396.44" in html and "waiting for stock" in html
    assert 'href="/place/alpha/"' not in html  # alpha is not done: no result link yet
    assert len(prose(html)) <= 60, prose(html)
    viewer = signed_in("sam").get("/buy/run/").content.decode()
    assert "/api/machine/stop" not in viewer
    Checkout.objects.update(state="done")
    Launch.objects.update(state="done")


def test_no_batch_says_so_and_links_to_buy(world):
    html = signed_in().get("/buy/run/").content.decode()
    assert "No batch yet" in html and 'href="/buy/"' in html


def test_home_links_to_the_monitor_while_the_batch_lives_and_buy_opens_it(world):
    client = signed_in()
    assert 'href="/buy/run/"' not in client.get("/").content.decode()
    a_batch(world)
    assert 'href="/buy/run/"' in client.get("/").content.decode()
    buy = open(__file__.replace("tests/run_monitor_test.py", "pages/templates/pages/buy.html")).read()
    assert 'data-go="/buy/run/" data-url="/buy/yes/"' in buy


def test_the_export_carries_the_batch_and_the_hosted_page_says_how_fresh(world, tmp_path, monkeypatch):
    a_batch(world)
    building.build(world.source, tmp_path / "one", MADE, 50, SPEND, world.root)
    exported = ExportedSource(tmp_path / "one")
    run = exported.batch_run()
    assert run["read_at"] == MADE and run["money"]["spent"] == 3.21 and run["rows"]["done"] == 2
    from score.dashboard import state
    monkeypatch.setattr(state, "source", lambda: exported)
    with override_settings(SCORE_MODE="hosted"):
        html = signed_in().get("/buy/run/").content.decode()
        assert "min ago" in html and "live," not in html and "Buy sent" not in html
        SyncRequest.objects.create(kind="checkout", user="joey", payload={})
        SyncRequest.objects.filter(kind="checkout").update(
            created=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1))
        assert "Buy sent" in signed_in("sam").get("/buy/run/").content.decode()
