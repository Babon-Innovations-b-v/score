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
from score.dashboard.state import batch_run, plain
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


def a_batch(world, log=LOG, state="launched", pool=True, key="a"):
    """A checkout launched one run whose log is `log`; closeup@alpha's own log written since (it runs now)."""
    props, store = world.source.props_home, world.source.store_root
    (props / "logs").mkdir(parents=True, exist_ok=True)
    path = props / "logs" / "score-run-1.log"
    path.write_text(log.format(run=RUN))
    plan = Plan.objects.create(basket_hash=f"checkout-{key}", made_by="joey", state="ready", body=PLAN)
    launch = Launch.objects.create(plan=plan, by="joey", state="running", handles=[
        {"command": ["score", "run"], "pid": None, "log": str(path), "refused": None}])
    record = Checkout.objects.create(key=key * 32, by="joey", state=state, totals=TOTALS, launch=launch,
                                     items=[{"nodes": {"closeup@alpha": {}, "closeup@beta": {}}}],
                                     stop_line={"euros": 516.44, "spent": 120.0, "reserved": 0.0,
                                                "at": "2026-10-24T11:08:38+00:00"})
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
    assert run["money"]["spent"] == 3.21 and run["money"]["line"] == 516.44
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


def test_a_relaunch_goes_on_where_the_checkout_was(world):
    """A second run of the same checkout plans only what is not accepted yet: the monitor still counts every row the
    checkout planned, the ones accepted since as done, and this run's failures from its own log."""
    record = a_batch(world)
    first = record.launch.plan
    first.body = {**PLAN, "checkout": record.pk}
    first.save()
    rest = {"groups": [{"places": ["alpha", "beta"], "to_run": {}, "blocked": {"assembly@alpha": "waits"},
                        "buys": [{"node": "closeup@alpha"}, {"node": "closeup@beta"}]}], "checkout": record.pk}
    again = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready", body=rest)
    Launch.objects.filter(pk=record.launch.pk).update(plan=again)
    after = (record.at + datetime.timedelta(minutes=5)).isoformat()
    accepts = {"terrain": after, "plan@alpha": after, "assembly@beta": after,
               "assembly@alpha": (record.at - datetime.timedelta(days=1)).isoformat()}  # stale: made again
    found = batch_run.gathered(batch_run_input(), world.source.props_home, world.source.store_root,
                               accepted_at=accepts.get)
    assert found["rows"] == {"total": 6, "done": 3, "failed": 1, "not_run": 0, "running": 1, "queued": 1}
    scenes = {scene["place"]: (scene["done"], scene["total"]) for scene in found["scenes"]}
    assert scenes == {"": (1, 1), "alpha": (1, 3), "beta": (1, 2)}
    assert [problem["node"] for problem in found["problems"]] == ["closeup@beta"]


def test_a_relaunch_adds_the_first_runs_money_and_clock_and_parked_machines_show(world):
    """Fault of 2026-10-24: after a relaunch the monitor's spend began again at EUR 0 and its clock at the relaunch,
    and once the pool was released its 13 parked machines billed with nothing on the page."""
    record = a_batch(world)
    first_log = world.source.props_home / "logs" / "score-run-0.log"
    first_log.write_text("[cloud] 12:00:00 pool of 2 gpu-24gb opened for run old-run until 16:00\n"
                         "heartbeat 2026-10-24T10:30:00+00:00: rows done 1, running 0, queued 5; this run's rows: "
                         "paid runs open 0, EUR 1.18 in the ledger since the run started\n")
    plan = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready",
                               body={**PLAN, "checkout": record.pk})
    earlier = Launch.objects.create(plan=plan, by="joey", state="stopped", handles=[
        {"command": ["score", "run"], "pid": None, "log": str(first_log), "refused": None}])
    began = record.launch.at - datetime.timedelta(minutes=45)
    Launch.objects.filter(pk=earlier.pk).update(at=began)
    parked = world.source.props_home / "cloud" / "parked"
    parked.mkdir(parents=True)
    for number, pool in enumerate(["old-run", RUN, RUN, "someone-else"]):
        (parked / f"m-{number}.json").write_text(json.dumps({"id": f"m-{number}", "pool": pool}))
    (world.source.props_home / "cloud" / "pools" / RUN / "closed").write_text("")
    found = batch_run.gathered(batch_run_input(), world.source.props_home, world.source.store_root)
    assert found["money"]["spent"] == 4.39, found["money"]  # 1.18 before the relaunch, 3.21 since
    assert found["started"] == began.isoformat(timespec="seconds") and found["eta"]["elapsed"] >= 45
    assert not found["pool"]["open"] and found["pool"]["renting"] == 3, found["pool"]
    html = signed_in().get("/buy/run/").content.decode()
    assert "3 still renting" in html and len(prose(html)) <= 60, prose(html)


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


def test_the_money_is_this_batchs_high_and_room_on_its_own_spends_scale(world):
    """High is what the runner clears (the guesses in it, as the Buy showed), Stop this batch's room under the line:
    the line less the spend before it, so its high plus 10%."""
    a_batch(world)
    money = world.source.batch_run()["money"]
    assert money["high"] == round(327.24 + 33.16, 2) == 360.40
    assert money["stop"] == round(516.44 - 120.0, 2) == round(360.40 * 1.1, 2)
    assert not run_monitor.money_bar({**money, "spent": 340.0})["over"]  # inside the high he approved
    assert batch_run.own_stop({"euros": 396.44}) is None  # a line without what it was written over: no room shown


def test_a_failed_run_is_finished_only_when_its_drive_ended_with_lines_stopped():
    def said(log):
        return batch_run.overall({"state": "launched", "launch": {}}, batch_run.read_log(log.splitlines(), set()),
                                 False, None)
    assert said("exit: stopped, 3 of 4 lines done, 1 stopped\ndetached: failed exit=1 minutes=80.0") == (
        "finished", "some scenes' lines stopped")
    assert said("refused: these inputs are missing, so the rows ...\n  /x/a.json\nexit: exited, exit 1\n"
                "detached: failed exit=1 minutes=0.3") == (
        "stopped", "refused: these inputs are missing, so the rows ...")
    assert said("exit: error: KeyError: 'x'\ndetached: failed exit=1 minutes=2.0") == ("stopped", "error: KeyError: 'x'")
    assert said("Traceback\ndetached: failed exit=1 minutes=0.1")[0] == "stopped"


def test_a_refused_run_shows_stopped_with_its_problem(world):
    a_batch(world, log="refused: these inputs are missing\nexit: exited, exit 1\n"
                       "detached: failed exit=1 minutes=0.3 log=x outputs=y\n", pool=False)
    Launch.objects.update(state="failed")
    run = world.source.batch_run()
    assert run["state"] == "stopped" and run["problems"][0]["kind"] == "run"
    html = signed_in().get("/buy/run/").content.decode()
    assert "Stopped" in html and "Finished" not in html


def test_no_warm_card_while_stock_is_short_is_waiting_for_machines():
    pool = {"open": True, "cards": {"warm": 0, "short": 2}}
    nothing = batch_run.read_log([], set())
    assert batch_run.overall({"state": "launched", "launch": {}}, nothing, True, pool)[0] == "waiting"
    pool["cards"]["warm"] = 1
    assert batch_run.overall({"state": "launched", "launch": {}}, nothing, True, pool)[0] == "running"
    assert batch_run.overall({"state": "launched", "launch": {}}, nothing, False, None) == (
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
    assert 'data-url="/api/machine/stop-batch"' in html and "Paid work stays allowed" in html
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


def test_a_fault_is_said_as_a_short_plain_cause():
    cloud = ("error: CalledProcessError: Command '['/home/score/tools/cloud/blender_cloud.py', '--scene', 'x']' "
             "returned non-zero exit status 1.")
    assert plain.step_cause(cloud, "  | no card could be rented") == "no cloud machine could be rented"
    assert plain.step_cause(cloud, "") == "its run on a cloud machine failed"
    assert plain.step_cause("error: RuntimeError: light@a: an input changed while it ran; nothing is stored") == \
        "an input file changed while it ran"
    assert plain.step_cause("error: RuntimeError: the finish call failed (exit 1) and brought no take back") == \
        "the model's finishing step on a cloud machine failed"
    assert plain.step_cause("error: OSError: Insufficient permissions for /a/b.usd") == "a file could not be saved"
    assert plain.step_cause("made: fail") == "it was made but failed its check"
    assert plain.step_cause("error: ValueError: need at least one array to concatenate") == \
        "need at least one array to concatenate"
    said = plain.step_cause("error: KeyError: " + "word " * 40 + "/home/score/deep/file.json")
    assert len(said) <= 103 and "/home" not in said


def test_failed_rows_sharing_a_cause_are_one_problem_with_their_raw_words(tmp_path):
    report = tmp_path / "faults.txt"
    report.write_text("  | no card could be rented\n")
    fault = (f"error: CalledProcessError: Command '['/x/blender_cloud.py']' returned non-zero exit status 1; "
             f"fault report {report}")
    rows = {f"light@{place}": ("failed", fault, "2026-10-24T11:09:00+00:00") for place in ("a", "b", "c")}
    rows["film@a"] = ("not_run", "not run: its line stopped at light@a", None)
    [problem] = batch_run.failures(rows)
    assert problem["places"] == ["a", "b", "c"] and problem["place"] == ""
    assert problem["words"].endswith("stopped in 3 places: no cloud machine could be rented. 1 later step waits on them.")
    assert len(problem["raw"]) == 3 and "blender_cloud.py" in problem["raw"][0]


def test_the_next_buy_says_what_it_makes_again_first_and_keeps():
    run = {"checkout": 3, "batch": 1, "at": "2026-10-25T09:10:00+00:00", "state": "finished", "design_at": None,
           "nodes": {"planned": ["a", "b", "c", "d"], "made": ["a", "b"], "failed": ["c"]}}
    assert batch_run.next_buy(run, ["c", "d", "e"]) == (
        "Retry Batch 1: makes again the 1 step that failed and the 1 that never ran; makes 1 step for the "
        "first time; keeps the 2 already made.")
    changed = {**run, "design_at": "2026-10-25T10:00:00Z"}
    assert batch_run.next_buy(changed, ["c"]).startswith("Batch 2, after Batch 1: makes again the 1 step")
    assert batch_run.next_buy({**run, "state": "running"}, ["c"]) is None
    assert batch_run.next_buy({"checkout": 1, "state": "finished"}, ["c"]) is None


def test_a_buy_while_the_batch_is_unfinished_is_its_next_try(world):
    """Owner, 2026-10-25: "its the same batch, ur just retrying a failed part of it"."""
    first = a_batch(world)
    retry = a_batch(world, key="b")
    retry.at = first.at + datetime.timedelta(hours=1)
    retry.save()
    found = world.source.batch_run()
    assert (found["batch"], found["tries"], found["checkout"]) == (1, 2, retry.pk)
    assert found["rows"]["failed"] == 1 and found["money"]["spent"] is not None
    redesigned = a_batch(world, key="c")
    redesigned.at, redesigned.design_at = retry.at + datetime.timedelta(hours=1), \
        (retry.at + datetime.timedelta(minutes=5)).isoformat()
    redesigned.save()
    assert (world.source.batch_run()["batch"], world.source.batch_run()["tries"]) == (2, 1)


def test_a_try_that_wrote_no_line_yet_shows_its_buys_stop_and_spends_nothing(world):
    record = a_batch(world, log="paid rows this run would buy: 2\n", state="launching")
    record.stop_line = {}
    record.save()
    money = world.source.batch_run()["money"]
    assert money["spent"] == 0.0 and money["stop"] == round(money["high"] * batch_run.BUFFER, 2)


TRY_ONE = """heartbeat 2026-10-24T23:05:00+00:00: rows done 0, running 2, queued 3; this run's rows: paid runs open 1, EUR 2.00 in the ledger since the run started
terrain: made: pass, accepted automatically
light@alpha: error: RuntimeError: boom; fault report /x/faults/light@alpha.txt
closeup@beta: error: RuntimeError: no card; fault report /x/faults/closeup@beta.txt
assembly@beta: not run: its line stopped at closeup@beta
detached: failed
"""


def two_tries(tmp_path, try_log=None):
    """Batch 1 of two tries: the first failed light@alpha and closeup@beta; the second buys closeup@beta and
    assembly@beta again, launching (no log) or ended with `try_log`."""
    first, second = tmp_path / "try1.log", tmp_path / "try2.log"
    first.write_text(TRY_ONE)
    one = {"at": "2026-10-24T23:00:00+00:00", "logs": [str(first)]}
    two = {"at": "2026-10-25T09:00:00+00:00", "logs": [str(second)]}
    if try_log:
        second.write_text(try_log)
    return {"checkout": 2, "at": "2026-10-25T08:59:00+00:00", "state": "launched" if try_log else "launching",
            "totals": TOTALS, "stop_line": {}, "batch": 1, "tries": 2, "first_at": "2026-10-24T22:59:00+00:00",
            "launch": {"at": two["at"], "state": "done", "result": "failed", "logs": two["logs"]} if try_log else None,
            "runs": [one, two] if try_log else [one], "try_runs": [two] if try_log else [],
            "nodes": ["terrain", "light@alpha", "closeup@beta", "assembly@beta"],
            "try_nodes": ["closeup@beta", "assembly@beta"]}


def test_a_try_shows_what_it_makes_again_as_waiting_not_as_an_earlier_tries_failure(tmp_path):
    """Owner, 2026-10-25: "and it still shows all failed etc"."""
    accepted = {"terrain": "2026-10-24T23:04:00+00:00"}.get
    run = batch_run.gathered(two_tries(tmp_path), tmp_path, tmp_path, accepted_at=accepted,
                             now=datetime.datetime(2026, 10, 25, 9, 1, tzinfo=datetime.timezone.utc))
    scenes = {scene["place"]: scene["state"] for scene in run["scenes"]}
    assert run["state"] == "starting" and scenes == {"": "done", "alpha": "failed", "beta": "waiting"}
    assert (run["rows"]["done"], run["rows"]["failed"], run["rows"]["not_run"]) == (1, 1, 0)
    assert [problem["node"] for problem in run["problems"]] == ["light@alpha"] and run["retried"] == 1
    assert run["started"].startswith("2026-10-24T23:00") and run["try_started"].startswith("2026-10-25T08:59")
    clock = run_monitor.clock(run)
    assert clock["started"] == "08:59" and clock["batch_started"] == "24 Oct 23:00"

    again = TRY_ONE.splitlines()[0] + "\ncloseup@beta: error: RuntimeError: no card again; fault report /x/f.txt\n" \
        "assembly@beta: not run: its line stopped at closeup@beta\ndetached: failed\nexit: stopped, 1 line\n"
    ended = batch_run.gathered(two_tries(tmp_path, again), tmp_path, tmp_path, accepted_at=accepted)
    assert ended["state"] == "finished" and ended["retried"] == 0
    assert {problem["node"] for problem in ended["problems"]} == {"light@alpha", "closeup@beta"}
    assert "no card again" in next(problem["tip"] for problem in ended["problems"] if problem["node"] == "closeup@beta")
