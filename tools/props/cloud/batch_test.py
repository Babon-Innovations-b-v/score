"""Checks for the cloud batch runner's limits, list, inventory refusal and sweep, without renting anything."""
import json
import os
import pathlib
import socket
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import batch  # noqa: E402
import ledger  # noqa: E402

L4 = 0.013125


def test_limits():
    assert ledger.refusal(90, L4) is None
    assert "4 h" in ledger.refusal(241, L4)
    assert "€60" in ledger.refusal(210, 0.3)
    assert ledger.minutes_allowed(L4) == 240
    assert round(ledger.minutes_allowed(0.3)) == 200
    assert ledger.cost(1.2, L4) == 2 * L4


def test_month_total():
    batches = [{"started": "2026-09-29T10:00:00Z", "euros": 1.5},
               {"started": "2026-08-31T23:00:00Z", "euros": 9.0}]
    assert ledger.month_total("2026-09", batches) == 1.5


NOW = 1_760_000_000.0  # a fixed now for the open-machine checks; started lines are written relative to it
MONTH = "2025-10"  # NOW's month (2025-10-09 UTC)


def started_line(name, minutes_ago, deadline_in=None, price=0.02):
    """A rent-started line for machine `name` of run `pixal-7`, ordered `minutes_ago` before NOW."""
    import time

    line = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - minutes_ago * 60)),
            "batch": f"rent-{name}", "kind": ledger.RENT_STARTED, "state": "started", "run": "pixal-7", "name": name,
            "price": price, "euros": 0.0}
    if deadline_in is not None:
        line["deadline"] = NOW + deadline_in * 60
    return line


def test_a_running_machine_counts_in_the_month_before_its_run_row():
    """Fault (review of C1, 2026-10-17): the started line held 0 euros and month_total ignored it, so the guard did
    not count a machine running and not yet billed. It counts at its price from its order until now."""
    lines = [started_line("pixal-7-1", 60, deadline_in=120)]
    assert round(ledger.month_total(MONTH, lines, now=NOW), 2) == 1.2
    assert ledger.open_rents(lines, NOW) == lines


def test_a_machine_whose_run_died_counts_until_its_deadline():
    """A run that died leaves no row; its machine is deleted by its watchdog at the deadline, so it counts until
    then and no longer."""
    lines = [started_line("pixal-7-1", 600, deadline_in=-360)]
    assert round(ledger.month_total(MONTH, lines, now=NOW), 2) == 4.8


def test_a_started_line_closes_with_its_run_row_its_delete_or_its_refusal():
    """A started line is open only until its run's row, its machine's disk-and-address row (written at delete) or
    its refused line: refused orders are told apart from orphaned machines."""
    started = [started_line("pixal-7-1", 60, 120), started_line("pixal-7-2", 60, 120), started_line("other-1", 60, 120)]
    started[2]["run"] = "other"
    closing = [{"started": started[0]["started"], "batch": "pixal-7", "kind": "pixal", "euros": 1.5},
               {"started": started[0]["started"], "batch": "disk-and-address-s1", "kind": "disk-and-address",
                "name": "other-1", "euros": 0.1},
               {"started": started[0]["started"], "batch": "rent-pixal-7-2", "kind": ledger.RENT_REFUSED,
                "name": "pixal-7-2", "euros": 0.0}]
    assert ledger.open_rents(started + closing, NOW) == []
    assert ledger.open_rents(started + closing[2:], NOW) == [started[0], started[2]]
    assert round(ledger.month_total(MONTH, started + closing, now=NOW), 2) == 1.6


def test_list():
    with tempfile.TemporaryDirectory() as folder:
        picture = pathlib.Path(folder) / "crate.png"
        picture.write_bytes(b"")
        listing = pathlib.Path(folder) / "list.txt"
        listing.write_text(f"# approved 2026-09-29\ncrate {picture} --faces 12000 --feet\n\n"
                           f"barrel {picture}  # the tall one\n")
        models = batch.read_list(listing)
        assert [model.name for model in models] == ["crate", "barrel"]
        assert models[0].faces == 12000 and models[0].feet and not models[1].feet
        listing.write_text(f"crate {picture}\ncrate {picture}\n")
        try:
            batch.read_list(listing)
        except SystemExit as refused:
            assert "twice" in str(refused)
        else:
            raise AssertionError("a repeated name was accepted")


def test_fleet_size():
    # 229 models at 3.95 card minutes each, 3 at once, in an hour: 5 min setup and a 12 min last run.
    assert batch.cards_needed(229, 3, 60, 3.95) == 21
    assert round(batch.expected_minutes(229, 21, 3, 3.95)) == 60
    assert batch.cards_needed(5, 3, 60, 3.95) == 1
    try:
        batch.cards_needed(10, 6, 20, 3.95)
    except SystemExit as refused:
        assert "too short" in str(refused)
    else:
        raise AssertionError("a target shorter than one run was accepted")


def test_a_capped_batch_aims_for_what_its_cards_can_do():
    """A one-card take of 3 models at 18.7 card minutes each, 3 at once, cannot finish in 60 min (5 setup, 56.1 for
    the run's last share): it aims for the 117 its one card takes and rents that card, rather than refusing."""
    aim = batch.aimed_minutes(3, 1, 3, 18.7, 60)
    assert round(aim, 1) == 117.2
    assert min(1, batch.cards_needed(3, 3, aim, 18.7)) == 1
    assert batch.aimed_minutes(5, 20, 3, 3.95, 60) == 60  # an uncapped small batch keeps its aim


def test_model_minutes_come_from_the_batch_started_last():
    # A batch stopped part way is written after a later one; its slow rate must not set the estimate.
    entries = [{"started": "2026-09-30T17:56:47Z", "models_done": 5, "card_minutes": 25},
               {"started": "2026-09-30T17:35:47Z", "models_done": 3, "card_minutes": 380}]
    kept, ledger.entries = ledger.entries, lambda: entries
    try:
        assert batch.card_minutes_per_model() == 5
    finally:
        ledger.entries = kept


def test_a_batch_builds_only_an_approved_inventorys_rows():
    with tempfile.TemporaryDirectory() as folder:
        picture = pathlib.Path(folder) / "locker.png"
        picture.write_bytes(b"")
        listing = pathlib.Path(folder) / "list.txt"
        listing.write_text(f"habitat-locker {picture}\nlocker-b {picture}\nr2 {picture}\n")
        models = batch.read_list(listing)
        path = pathlib.Path(folder) / "hub.json"
        rows = [{"id": "r1", "view": "v1", "box": [0, 0, 9, 9], "name": "locker", "kind": "generate",
                 "anchor": "wall", "size": [0.6, 0.5, 1.9], "count": 1, "thing": "prop:locker"},
                {"id": "r2", "view": "v1", "box": [0, 0, 9, 9], "name": "desk", "kind": "mechanic",
                 "anchor": "floor", "size": [1.6, 0.8, 0.75], "count": 1, "thing": "node:Workstation",
                 "prop": "desk"},
                {"id": "keyboard", "view": "v1", "box": [0, 0, 9, 9], "name": "keyboard", "kind": "code",
                 "anchor": "wall", "size": [0.4, 0.03, 0.15], "count": 1, "thing": "gear:keyboard"}]
        # #19: the sorter routes a row, not its own kind: hub_keyboard is a named pipeline failure, built in code
        inventory = {"scene": "hub", "place": "habitat", "plan": {"views": [{"id": "v1"}]},
                     "approved": "", "migrated": "",
                     "room": {"shell": "", "light": "place", "backdrop": "", "wall_fill": []}, "rows": rows}
        # A place named by no place.json entry builds all the same: Pixal3D is worded by nothing (place.py).
        for wanted, change in (("no inventory", None), ("not approved", {}), (None, {"approved": "2026-10-05"}),
                               (None, {"approved": "2026-10-05", "place": "no_such_place"})):
            if change is not None:
                path.write_text(json.dumps(dict(inventory, **change)))
            try:
                batch.from_the_inventory(models, [path])
            except SystemExit as refused:
                assert wanted and wanted in str(refused), refused
            else:
                assert wanted is None, f"accepted without {wanted}"
        path.write_text(json.dumps(dict(inventory, approved="2026-10-05")))
        listing.write_text(f"keyboard {picture}\n")
        try:
            batch.from_the_inventory(batch.read_list(listing), [path])
        except SystemExit as refused:
            assert "on no row" in str(refused)
        else:
            raise AssertionError("a named pipeline failure's row was sent to be generated")
        # a designed place's hand-in is approved by the creator's pick, its reading's rows taken as they stand
        designed = {**inventory, "approved": {"by": batch.DESIGNED, "concept": "c" * 64}, "room": {},
                    "rows": [{**rows[0], "anchor": "ground", "box": None}]}
        path.write_text(json.dumps(designed))
        listing.write_text(f"habitat-locker {picture}\n")
        assert batch.from_the_inventory(batch.read_list(listing), [path]) >= {"r1"}
        path.write_text(json.dumps({**designed, "scene": "lab"}))  # a hand-in under another place's name: page A's
        try:
            batch.from_the_inventory(batch.read_list(listing), [path])
        except SystemExit as refused:
            assert "not sound" in str(refused) or "not approved" in str(refused), refused
        else:
            raise AssertionError("a hand-in under another place's name was taken")


def test_a_batch_builds_a_character_only_when_its_spec_is_approved():
    with tempfile.TemporaryDirectory() as folder:
        picture = pathlib.Path(folder) / "tang.png"
        picture.write_bytes(b"")
        spec = {"name": "fish_tang", "kind": "animal", "picture": str(picture), "body": "fish"}
        path = pathlib.Path(folder) / "fish_tang.json"
        for wanted, change in (("not approved", {}), ("no picture", {"approved": "owner", "picture": None}),
                               (None, {"approved": "owner, 2026-10-09"})):
            path.write_text(json.dumps(dict(spec, **change)))
            try:
                models = batch.from_the_characters([path])
            except SystemExit as refused:
                assert wanted and wanted in str(refused), refused
            else:
                assert wanted is None, f"accepted with {wanted}"
        assert [(options.name, options.picture) for options in models] == [("fish_tang", str(picture))]
        try:
            batch.from_the_characters([path, path])
        except SystemExit as refused:
            assert "share a name" in str(refused)
        else:
            raise AssertionError("two specs of one name were both built")


def test_leftovers():
    here = socket.gethostname()
    later = 2e9
    assert batch.is_leftover([], 1e9)
    assert batch.is_leftover([f"deadline={1e9 - 1:.0f}"], 1e9)
    assert not batch.is_leftover([f"deadline={later:.0f}", f"host={here}", f"pid={os.getpid()}"], 1e9)
    assert batch.is_leftover([f"deadline={later:.0f}", f"host={here}", "pid=999999999"], 1e9)
    assert not batch.is_leftover([f"deadline={later:.0f}", "host=elsewhere", "pid=999999999"], 1e9)


def test_a_fleet_short_of_cards_rents_more_as_stock_comes_up():
    import threading
    import time
    import provider

    class Fleet:
        def __init__(self):
            self.stop, self.renting, self.deadline = threading.Event(), threading.Lock(), time.time() + 60
            self.machines, self.offers, self.work, self.lost_cards = [], [], True, 0

        def no_more_work(self):
            return not self.work
    fleet, rounds = Fleet(), []
    found = [provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")]

    def rent_fleet(fleet, cards):
        rounds.append(cards)
        if len(rounds) < 3:
            return 0  # out of stock on the first rounds
        fleet.machines.append({"cards": cards, "deleted": None})
        fleet.work = False
        fleet.machines[-1]["deleted"] = time.time()
        return cards
    kept = batch.rent_fleet, batch.cloud.offers, batch.STOCK_RETRY_MINUTES, batch.time.sleep
    batch.rent_fleet, batch.cloud.offers = rent_fleet, lambda classes: list(found)
    batch.STOCK_RETRY_MINUTES, batch.time.sleep = 0, lambda seconds: None
    try:
        batch.keep_the_fleet(fleet, found, 2)
    finally:
        batch.rent_fleet, batch.cloud.offers, batch.STOCK_RETRY_MINUTES, batch.time.sleep = kept
    assert rounds == [2, 2, 2] and fleet.offers == found


def one_shot_fleet(names):
    import types
    models = [types.SimpleNamespace(name=name, picture="/pics/p.png", seed=1) for name in names]
    return batch.Fleet(models, pathlib.Path(tempfile.mkdtemp()), None, 0, "test", finish=False), models


def test_a_failed_job_is_a_gap_and_never_sent_again():
    """A batch runs every job once (CONTEXT.md, owner 2026-10-20): retry_once sent a failed or out-of-memory job back
    for a second paid run."""
    fleet, models = one_shot_fleet(["crate", "barrel"])
    batch.queue(fleet, models)
    sent = [fleet.next_job(), fleet.next_job()]
    status = {"jobs": {"crate": {"state": "failed"}, "barrel": {"state": "running", "began": 0}}}
    over = batch.collect(fleet, fleet.folder, "host", status, set())
    assert over == {"crate"} and fleet.failed == ["crate"] and fleet.next_job() is None and len(sent) == 2
    assert not hasattr(fleet, "retry_once") and not hasattr(fleet, "give_back")


def test_a_job_past_its_deadline_is_stopped_once_and_becomes_a_gap():
    status = {"jobs": {"slow": {"state": "running", "began": 0.0}, "quick": {"state": "running", "began": 900.0},
                       "made": {"state": "done", "began": 0.0}}}
    assert batch.overdue(status, set(), 500, 1000.0) == ["slow"]
    assert batch.overdue(status, {"slow"}, 500, 1000.0) == []
    (fleet, _), commands, stopped = one_shot_fleet(["slow"]), [], set()
    fleet.job_deadline = 500
    kept = batch.remote, batch.time.time
    batch.remote, batch.time.time = lambda folder, host, command, **keywords: commands.append(command), lambda: 1000.0
    try:
        batch.stop_overdue(fleet, fleet.folder, "host", status, stopped)
        batch.stop_overdue(fleet, fleet.folder, "host", status, stopped)
    finally:
        batch.remote, batch.time.time = kept
    assert commands == ["pkill -f -- '[/]root/batch/out/slow\\.glb'"] and stopped == {"slow"}
    import re
    pattern = batch.own_pattern("/root/batch/out/slow.glb")
    assert re.search(pattern, "python scripts/pixal3d_generate.py in.png /root/batch/out/slow.glb --seed 1")
    assert not re.search(pattern, f"bash -c pkill -f -- {pattern}")


def test_a_fleet_whose_billed_machines_failed_rents_none_in_their_place():
    """A batch runs once (CONTEXT.md, owner 2026-10-20): a machine billed that did not start or broke was replaced by
    a new rental, unpriced spend inside the batch. Its cards are lost and the jobs no machine took are gaps."""
    import time
    fleet, models = one_shot_fleet(["crate", "barrel"])
    fleet.deadline = time.time() + 60
    batch.queue(fleet, models)
    fleet.lose({"cards": 1})
    rented = []
    kept = batch.rent_fleet, batch.time.sleep
    batch.rent_fleet, batch.time.sleep = lambda fleet, cards: rented.append(cards) or 0, lambda seconds: None
    try:
        batch.keep_the_fleet(fleet, [], 1)
    finally:
        batch.rent_fleet, batch.time.sleep = kept
    assert rented == [] and sorted(fleet.failed) == ["barrel", "crate"] and fleet.next_job() is None


def test_a_billed_boot_that_fails_is_a_gap_and_out_of_stock_moves_on():
    """claim_from moved to the next offer after a machine it rented (and was billed for) did not answer, renting a
    second; only an out-of-stock refusal, where no card ran, may move on."""
    import types
    import provider
    offers = [provider.Offer(0.01, 0, "L4", zone, 0.01, "gpu-24gb", 0, "available") for zone in ("zone-a", "zone-b")]
    rented, failures = [], []

    def rent(run, account, offer, number, disk_gb):
        rented.append(offer.zone)
        return {"zone": offer.zone, "type": offer.type, "class": offer.machine_class, "cards": 1,
                "folder": pathlib.Path(tempfile.mkdtemp()), "deleted": None}

    def boot(machine):
        raise failures.pop(0)
    kept = batch.rent, batch.boot, batch.delete_machine, batch.ledger.machine_row, batch.time.sleep
    batch.rent, batch.boot, batch.delete_machine = rent, boot, lambda machine: None
    batch.ledger.machine_row, batch.time.sleep = lambda machine: {}, lambda seconds: None
    try:
        run = types.SimpleNamespace(machines=[], attempts=[], deadline=0)
        failures.append(TimeoutError("did not answer"))
        assert batch.claim(run, None, offers, 1, "parts") is None and rented == ["zone-a"]
        rented.clear()
        failures.extend([batch.OutOfStock("out of stock"), TimeoutError("did not answer")])
        assert batch.claim(run, None, offers, 1, "parts") is None and rented == ["zone-a", "zone-b"]
    finally:
        batch.rent, batch.boot, batch.delete_machine, batch.ledger.machine_row, batch.time.sleep = kept


def test_the_deadline_and_the_slots_come_from_measured_numbers():
    measured = json.loads(batch.PER_UNIT.read_text())["stages"]["pixal"]["time"]["unit_seconds"]["high"]
    assert batch.job_deadline_seconds() == batch.DEADLINE_FACTOR * measured
    assert batch.capacity.runs_at_once("pixal", "gpu-24gb") == batch.PER_CARD


def test_nothing_is_rented_outside_a_cleared_run():
    """Fault (design of 2026-10-11, section 6): rent ordered a machine for any caller, so blender_cloud.py,
    detached.py, the runners and demo.py could spend without the runner's gate or the owner's yes."""
    import time
    import types
    import provider
    from score.adapters import compute

    ordered = []
    kept = batch.cloud.create, batch.month_spent, os.environ.pop(compute.TICKET, None)
    batch.cloud.create = lambda *arguments: ordered.append(arguments) or (None, "refused")
    batch.month_spent = lambda account: 0.0
    fleet = types.SimpleNamespace(folder=pathlib.Path(tempfile.mkdtemp()), deadline=time.time() + 60, attempts=[])
    offer = provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")
    try:
        batch.rent(fleet, None, offer, 0)
    except compute.Refused as refusal:
        assert "nothing rents outside a cleared run" in str(refusal)
    else:
        raise AssertionError("a machine was ordered outside a cleared run")
    finally:
        batch.cloud.create, batch.month_spent = kept[:2]
        if kept[2] is not None:
            os.environ[compute.TICKET] = kept[2]
    assert ordered == []


def test_a_rent_writes_its_started_line_before_the_order_is_sent():
    """Fault (2026-10-17, C1): the ledger had a run's row only at its end, so a machine of a run that died first was
    on the bill and nowhere in the ledger. The started line names the run and its ticket before the order goes."""
    import time
    import types
    import provider
    from score.adapters import compute

    seen = []

    def fake_scw(command, **options):
        """The backend's scw call: what the ledger held when the order went, then a refusal."""
        seen.append((command, ledger.entries()))
        return types.SimpleNamespace(returncode=1, stdout="", stderr="out of quota")
    kept = (batch.cloud.subprocess, batch.month_spent, batch.compute.require_cleared, ledger.LEDGER,
            os.environ.get(compute.TICKET))
    ledger.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    os.environ[compute.TICKET] = "run-7 surfaces-paint"
    batch.cloud.subprocess = types.SimpleNamespace(run=fake_scw)
    batch.month_spent = lambda account: 0.0
    batch.compute.require_cleared = lambda what: None
    keys = batch.KEY, batch.SELF_DELETE_KEY
    batch.KEY, batch.SELF_DELETE_KEY = (pathlib.Path(tempfile.mkdtemp()) / name for name in ("ssh_key", "self_delete.json"))
    batch.KEY.write_text("private")
    batch.SELF_DELETE_KEY.write_text("{}")
    fleet = types.SimpleNamespace(folder=pathlib.Path(tempfile.mkdtemp()) / "pixal-run-7",
                                  deadline=time.time() + 60, attempts=[])
    offer = provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")
    try:
        assert batch.rent(fleet, None, offer, 3) is None
        after = ledger.entries()
    finally:
        batch.cloud.subprocess, batch.month_spent, batch.compute.require_cleared, ledger.LEDGER = kept[:4]
        batch.KEY, batch.SELF_DELETE_KEY = keys
        os.environ.pop(compute.TICKET)
        if kept[4] is not None:
            os.environ[compute.TICKET] = kept[4]
    [(command, [line])] = seen
    assert line["deadline"] == round(fleet.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
    assert [entry["kind"] for entry in after] == [ledger.RENT_STARTED, ledger.RENT_REFUSED]
    assert after[1]["name"] == "pixal-run-7-3" and "out of quota" in after[1]["reason"]
    assert command[:4] == ["scw", "instance", "server", "create"]
    assert line["state"] == "started" and line["kind"] == ledger.RENT_STARTED and line["euros"] == 0.0
    assert line["run"] == "pixal-run-7" and line["name"] == "pixal-run-7-3"
    assert line["ticket"] == "run-7 surfaces-paint" and line["type"] == "L4" and line["zone"] == "zone-a"


# A batch holding one fake machine, deleted through batch.delete_machine as batch.run's end does; it says "ready".
FAKE_BATCH = """
import pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import batch
from provider import cloud
deletes, folder = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
cloud.delete = lambda server_id, zone: bool(deletes.open("a").write(server_id + "\\n"))
batch.stop_on_signals()
machine = {"id": "fake-machine", "zone": "zone-a", "deleted": None, "watchdog": 999999999, "folder": folder,
           "created": time.time(), "kind": None, "healthy": False}
try:
    (folder / "ready").write_text("ready")
    time.sleep(120)
finally:
    batch.delete_machine(machine)
"""
# A runner leading its process group with one node process (score.graph's watch_runner) that runs the fake batch.
RUNNER = """
import os, subprocess, sys, threading, time
sys.path.insert(0, sys.argv[1])
from score import graph
os.setpgid(0, 0)
runner = os.getpid()
if os.fork() == 0:
    threading.Thread(target=graph.watch_runner, args=(runner, 0.2), daemon=True).start()
    subprocess.run([sys.executable, "-c", sys.argv[2], *sys.argv[3:]])
    os._exit(0)
time.sleep(120)
"""


def test_a_batch_whose_runner_dies_deletes_its_machines():
    """Fault (2026-10-17): a `score run` killed outright left its batches renting with no one to stop them."""
    import signal
    import subprocess
    import time

    folder = pathlib.Path(tempfile.mkdtemp(prefix="orphan-batch-"))
    deletes = folder / "deletes.txt"
    environment = {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}
    environment.pop("SCORE_RUN_ID", None)
    runner = subprocess.Popen([sys.executable, "-c", RUNNER, str(pathlib.Path(__file__).resolve().parents[3]),
                               FAKE_BATCH, str(pathlib.Path(__file__).resolve().parent), str(deletes), str(folder)],
                              env=environment)
    deadline = time.time() + 60
    while not (folder / "ready").exists() and time.time() < deadline:
        time.sleep(0.1)
    assert (folder / "ready").exists(), "the fake batch never started"
    runner.send_signal(signal.SIGKILL)  # no stop handler runs: only the node's watch can end the batch
    runner.wait()
    while not deletes.exists() and time.time() < deadline:
        time.sleep(0.1)
    assert deletes.exists() and deletes.read_text().split() == ["fake-machine"], "the batch's machine was left"


# A batch holding three fake machines that works for argv[4] seconds, says so on its output, then deletes each
# through batch.delete_machine as batch.run's end does.
WORKING_BATCH = """
import pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import batch
from provider import cloud
deletes, folder = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
cloud.delete = lambda server_id, zone: bool(deletes.open("a").write(server_id + "\\n"))
batch.stop_on_signals()
machines = [{"id": f"machine-{number}", "zone": "zone-a", "deleted": None, "watchdog": 999999999,
             "folder": folder / f"machine-{number}", "created": time.time(), "kind": None, "healthy": False}
            for number in range(3)]
try:
    (folder / "ready").write_text("ready")
    time.sleep(float(sys.argv[4]))
    batch.say("working on")
finally:
    for machine in machines:
        batch.delete_machine(machine)
"""
# A runner that is not a group leader (compare.py, a trial, any runner but `score run`) with one node process
# (score.graph's watch_runner) that runs the batch, its output piped to the node as a stage's subprocess.run does.
FOLLOWER_RUNNER = """
import os, subprocess, sys, threading, time
sys.path.insert(0, sys.argv[1])
from score import graph
runner = os.getpid()
if os.fork() == 0:
    threading.Thread(target=graph.watch_runner, args=(runner, 0.2), daemon=True).start()
    subprocess.run([sys.executable, "-c", sys.argv[2], *sys.argv[3:]], capture_output=True)
    os._exit(0)
time.sleep(120)
"""


def test_a_node_of_a_runner_that_leads_no_group_outlives_it_so_its_batch_deletes_every_machine():
    """Review of C7 (2026-10-17): the node of a runner leading no group sent itself SIGTERM when the runner died, which
    no handler of its own caught; the batch writing to it then hit a broken pipe and deleted one machine of three."""
    import signal
    import subprocess
    import time

    folder = pathlib.Path(tempfile.mkdtemp(prefix="follower-batch-"))
    deletes = folder / "deletes.txt"
    environment = {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}
    environment.pop("SCORE_RUN_ID", None)
    runner = subprocess.Popen([sys.executable, "-c", FOLLOWER_RUNNER, str(pathlib.Path(__file__).resolve().parents[3]),
                               WORKING_BATCH, str(pathlib.Path(__file__).resolve().parent), str(deletes), str(folder),
                               "2"], env=environment)
    deadline = time.time() + 60
    while not (folder / "ready").exists() and time.time() < deadline:
        time.sleep(0.1)
    assert (folder / "ready").exists(), "the fake batch never started"
    runner.send_signal(signal.SIGKILL)
    runner.wait()
    while len(deletes.read_text().split() if deletes.exists() else []) < 3 and time.time() < deadline:
        time.sleep(0.1)
    assert deletes.read_text().split() == ["machine-0", "machine-1", "machine-2"], deletes.read_text()


# A runner leading its process group, with four node processes (score.graph's watch_runner, each its own poll) that
# take SIGTERM without ending, and a process that writes a line for every SIGTERM it gets; "ready" once all are in.
COUNTED_RUNNER = """
import os, pathlib, signal, subprocess, sys, threading, time
sys.path.insert(0, sys.argv[1])
from score import graph
folder = pathlib.Path(sys.argv[2])
os.setpgid(0, 0)
runner = os.getpid()
counter = subprocess.Popen([sys.executable, "-c", "import pathlib, signal, sys, time; "
                            "signal.signal(signal.SIGTERM, lambda *_: pathlib.Path(sys.argv[1]).open('a').write('x')); "
                            "pathlib.Path(sys.argv[2]).write_text('ready'); time.sleep(30)",
                            str(folder / "signals.txt"), str(folder / "counter-ready")])
for node in range(4):
    if os.fork() == 0:
        signal.signal(signal.SIGTERM, lambda *_: None)
        threading.Thread(target=graph.watch_runner, args=(runner, 0.05), daemon=True).start()
        time.sleep(10)
        os._exit(0)
while not (folder / "counter-ready").exists():
    time.sleep(0.05)
(folder / "ready").write_text("ready")
time.sleep(120)
"""


def test_a_dead_runners_group_is_sent_one_stop_however_many_nodes_see_it():
    """Review of C7 (2026-10-17): every node's watch could send the group its own SIGTERM within one poll, and a batch
    already deleting stops deleting at its second signal."""
    import contextlib
    import signal
    import subprocess
    import time

    folder = pathlib.Path(tempfile.mkdtemp(prefix="one-stop-"))
    runner = subprocess.Popen([sys.executable, "-c", COUNTED_RUNNER, str(pathlib.Path(__file__).resolve().parents[3]),
                               str(folder)])
    deadline = time.time() + 60
    while not (folder / "ready").exists() and time.time() < deadline:
        time.sleep(0.1)
    runner.send_signal(signal.SIGKILL)
    runner.wait()
    time.sleep(2)  # every watch has seen its runner gone by now
    signals = (folder / "signals.txt").read_text() if (folder / "signals.txt").exists() else ""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(runner.pid, signal.SIGKILL)
    assert signals == "x", f"the group was sent {len(signals)} stops"


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("batch_test: ok")


def test_cluster_groups_run_their_takes_side_by_side():
    takes = [argparse_namespace(name=f"crate-{number}", picture="/pics/crate.png", seed=number) for number in range(4)]
    groups = batch.groups_of(takes, 3)
    assert [len(group) for group in groups] == [3, 1]
    line = batch.cluster_line(groups[0])
    assert line.count("pixal-run scripts/pixal3d_generate.py /work/in/crate-") == 3
    assert "sleep 60" in line and line.rstrip().endswith("test -f /work/out/crate-2.glb")
    job = batch.cluster_job(groups[0], pathlib.Path("/w/group0/out"))
    assert job["models"] == batch.CLUSTER_MODELS and job["code"] == ["vendor/image-to-3dlab"]
    assert [entry["path"] for entry in job["inputs"]] == [f"/work/in/crate-{number}.png" for number in range(3)]
    assert job["outputs"] == [{"path": "/work/out", "local": "/w/group0/out"}] and job["minutes"] == 90


def argparse_namespace(**values):
    import argparse

    return argparse.Namespace(**values)
