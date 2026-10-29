"""Invariant of park.py (and the batch steps that park and take): a healthy machine of a kind that cleans up is parked
instead of deleted only while that pays off (an hourly machine until 5 min before its paid hour ends; a card for its
kind's measured cold start, at most 10 min, and only while a claim waits for one); the next claim takes it within
its cleared run and its cap, pays only what it adds and runs on the newest set-up; one nobody took is deleted at its
time with its idle minutes in the ledger, by its --expire process or its ended run's releaser; and nothing parked is
ever deleted early by a sweep or an older expirer (owner, 2026-10-12: no new machine while one is idle; #45: three
L4s stayed parked past their time).

The cloud, ssh and process calls are recorded instead of made; the clean-up commands run in a scratch folder. The
break that turns each red (applied once, seen red, reverted):

- test_only_a_healthy_machine_of_a_cleaned_kind_with_time_left_is_parked: in `parkable`, drop
  `bool(machine.get("healthy")) and `.
- test_a_parked_machine_must_go_before_its_paid_hour_ends: in `leaves_at`, `paid_until(machine, now) - MARGIN_MINUTES
  * 60` -> `paid_until(machine, now)`.
- test_the_next_run_of_the_kind_takes_it_and_pays_only_what_it_adds: in ledger.py `machine_row`, drop `-
  machine.get("paid_minutes", 0.0) * machine["price"]`; or in `take`, `(record.get("disk_gb") or 0) >= disk_gb` ->
  `True`.
- test_another_cleaned_kind_takes_a_parked_machine_when_its_own_kind_has_none: in `take`, `record["kind"] == kind` ->
  `False`.
- test_a_machine_not_worth_parking_or_of_a_stopping_run_is_deleted: in `parkable`, drop `not
  batch.STOPPING.is_set() and ` (its first occurrence).
- test_expire_deletes_a_machine_nobody_took_and_spares_one_taken_or_reparked: the token checked nowhere (each alone
  is covered by the other): in `release`, `mine = record.get("token") == token` -> `mine = bool(record)`, and in
  `listed`, `path.exists() and json.loads(path.read_text()).get("token") == token` -> `path.exists()`.
- test_an_expirer_ends_once_its_machine_is_no_longer_parked_under_its_token: in `expire`, `while listed(server_id,
  token):` -> `while True:`.
- test_a_watchdog_deletes_its_machine_at_once_when_its_renter_is_gone: in batch.py `watchdog`, drop `and
  os.getppid() == holder`.
- test_a_parked_machine_that_does_not_answer_is_deleted_and_none_taken: in `adopt`, the failure's
  `batch.delete_machine(machine)\n            continue` -> `return machine`.
- test_a_card_waits_its_kinds_measured_cold_start_at_most_the_cap: in `idle_minutes`, `min(IDLE_CAP_MINUTES,
  statistics.median(starts))` -> `statistics.median(starts)`.
- test_a_card_with_no_claim_waiting_is_released_not_parked: in `parkable`, `(not card or queued())` -> `True`.
- test_a_card_nobody_took_is_deleted_at_its_time_and_its_idle_minutes_charged: in `release`, `if
  record["unit_minutes"] == 1:` -> `if False:`.
- test_an_ended_run_releases_its_parked_machines_at_their_time: in `outlive`, `if record["until"] <= now or` -> `if
  True or`.
- test_a_taken_card_skips_its_cold_start_and_pays_its_idle_and_work: in `taken_machine`, `"ready": now` -> `"ready":
  None`.
- test_a_claim_waiting_on_its_kinds_queue_takes_a_card_parked_meanwhile: in `waiting`, `count += 1` -> `pass`.
- test_taking_a_parked_machine_needs_a_cleared_run: in `adopt`, drop `batch.compute.require_cleared(f"a parked machine
  of {kind}")`.
- test_a_sweep_leaves_a_parked_machine_alone_until_its_time: in batch.py `run_tags`, `f"deadline={deadline:.0f}"` ->
  `"deadline=0"`.
- test_a_run_at_its_cap_leaves_another_runs_parked_machine_listed: in `adopt`, `if not
  capacity.reserve_run_slot(len(live_of(run))):` -> `if False:`.
- test_each_kinds_clean_up_removes_its_runs_files_and_keeps_its_set_up: `CLEANUPS["pixal"]`'s `rm -rf in out queue
  logs closed status.json run.log` -> `rm -rf /root/batch`.
- test_a_taken_machine_keeps_only_its_newest_set_up_mark: `STALE_MARKS`, `tail -n +2` -> `tail -n +1`.
- test_this_pcs_card_is_taken_free_one_claim_at_a_time_and_never_parked: in `adopt`, drop `if hasattr(cloud,
  "take"): return here(...)` -> the claim asks a clearance and finds nothing parked; or in `park`, drop `if
  machine.get("here"): return False` -> the PC's machine is listed as parked; or in `here`, `f"{own_set_up(kind)};
  {cleanup_of(machine)}"` -> `own_set_up(kind)` (a last claim's `closed` ends the next worker at once).
- test_each_kind_on_this_pcs_card_keeps_its_own_set_up: in `own_set_up`, drop `if [ -e {KINDS}/{kind}/venv ]; then mv
  {KINDS}/{kind}/venv venv; fi && ` (a kind's venv never comes back); or `ALL_MARKS` -> `"rm -f /root/.*-setup-*"`
  (moss' set-up wipes the other kinds' marks there).
- test_a_pixal_fleet_takes_a_parked_card_before_it_orders_one: in batch.py `rent_fleet`, `machine =
  park_taken(fleet, fleet.offers, len(fleet.machines) + 1, "pixal", DISK_GB)` -> `machine = None`.
"""
import json
import os
import pathlib
import shlex
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "park-test"
OTHER = "park-test-other"  # a kind whose claim waits, so cards of KIND park
HOUR_PRICE = 1.2 / 60  # euros a minute of a machine billed by the hour
CARD_PRICE = 0.8 / 60  # euros a minute of a card, billed by the minute
OFFERS = [provider.Offer(HOUR_PRICE, 0, "cpu-type", "zone-a", HOUR_PRICE, "cpu-32c-128gb", 0, "available")]
CARD_OFFERS = [provider.Offer(CARD_PRICE, 1, "card-type", "zone-a", CARD_PRICE, "gpu-24gb", 0, "available")]
CLEAN = "rm -rf /root/lib/out"


class Calls:
    """The cloud, ssh and process calls park.py makes, recorded instead of made."""

    def __init__(self, monkeypatch):
        self.remote, self.retagged, self.deleted, self.armed = [], [], [], []
        monkeypatch.setattr(batch, "remote", lambda folder, host, command, **_: self.remote.append(command))
        monkeypatch.setattr(batch, "arm_self_delete", lambda folder, host, deadline, quiet_minutes=0: self.armed.append(
            deadline))
        monkeypatch.setattr(batch, "start_watchdog", lambda server_id, zone, deadline, folder: os.getpid() + 10 ** 6)
        monkeypatch.setattr(batch, "say", lambda line: None)
        monkeypatch.setattr(cloud, "retag", lambda server_id, zone, tags: self.retagged.append((server_id, tags)))
        monkeypatch.setattr(cloud, "delete", lambda server_id, zone: self.deleted.append(server_id) or True)
        monkeypatch.setattr(park.subprocess, "Popen", lambda *_, **__: type("Expirer", (), {"pid": os.getpid()})())
        monkeypatch.setattr(batch.compute, "require_cleared", lambda what, store=None: {"node": "test"})
        monkeypatch.setitem(park.CLEANUPS, KIND, lambda _machine: CLEAN)
        monkeypatch.setitem(park.CLEANUPS, OTHER, lambda _machine: CLEAN)


@pytest.fixture
def calls(monkeypatch):
    """A sandbox with nothing parked, an empty ledger and no run; the recorded calls."""
    for name in ("SCORE_RUN_ID", "SCORE_MAX_MACHINES", "SCORE_SPEND_TICKET"):
        monkeypatch.delenv(name, raising=False)
    found = Calls(monkeypatch)
    for path in park.PARKED.glob("*.json") if park.PARKED.exists() else ():
        path.unlink()
    ledger.LEDGER.unlink(missing_ok=True)
    batch.STOPPING.clear()
    return found


def machine(minutes_ago, unit_minutes=60, healthy=True, kind=KIND, server_id="m1"):
    folder = pathlib.Path(os.environ["PROPS_HOME"]) / "runs" / server_id
    folder.mkdir(parents=True, exist_ok=True)
    card = unit_minutes == 1
    return {"id": server_id, "zone": "zone-a", "type": "card-type" if card else "cpu-type",
            "class": "gpu-24gb" if card else "cpu-32c-128gb", "cards": 1 if card else 0,
            "price": CARD_PRICE if card else HOUR_PRICE, "unit_minutes": unit_minutes,
            "created": time.time() - minutes_ago * 60, "host": "192.0.2.1", "kind": kind, "disk_gb": 60,
            "folder": folder, "deleted": None, "ready": time.time() - minutes_ago * 60 + 60, "healthy": healthy,
            "watchdog": os.getpid() + 10 ** 6}


def card(server_id, minutes_ago=20, kind=KIND):
    return machine(minutes_ago, unit_minutes=1, kind=kind, server_id=server_id)


def run_of(name):
    folder = pathlib.Path(os.environ["PROPS_HOME"]) / "runs" / name
    folder.mkdir(parents=True, exist_ok=True)
    return pictures.Run(folder, time.time() + 3600)


def parked(held):
    """A card's run ends while a claim of another kind waits, so it is parked rather than deleted."""
    with park.wanting(OTHER):
        batch.delete_machine(held)


def token_of(server_id):
    return json.loads((park.PARKED / f"{server_id}.json").read_text())["token"]


def cold_card_runs(*cold_starts):
    """Ledger entries of KIND, one fresh card each, that took these minutes from order to first job."""
    for minutes in cold_starts:
        ledger.record({"started": "2026-10-11T10:00:00Z", "kind": KIND, "euros": 0.1, "machines": [
            {"type": "card-type", "zone": "zone-a", "cards": 1, "started": True, "start_wait_minutes": 0.5,
             "setup_minutes": minutes - 0.5, "work_minutes": 5.0, "minutes": minutes + 4.5, "euros": 0.1}]})


def test_only_a_healthy_machine_of_a_cleaned_kind_with_time_left_is_parked(calls):
    now = time.time()
    assert park.parkable(machine(20), now)  # 35 min of its paid hour left
    assert not park.parkable(machine(20, healthy=False), now)
    assert not park.parkable(machine(20, kind="unregistered"), now)
    assert not park.parkable(machine(53), now)  # 2 min before it must go
    assert park.parkable(machine(70), now)  # in its second paid hour, 45 min left of it
    assert not park.parkable(card("c"), now)  # a card with no claim waiting is released
    with park.wanting(KIND):
        assert park.parkable(card("c"), now)


def test_a_parked_machine_must_go_before_its_paid_hour_ends():
    held = {"created": 1000.0, "unit_minutes": 60}
    assert park.leaves_at(held, 1000.0 + 20 * 60) == 1000.0 + 55 * 60
    assert park.leaves_at(held, 1000.0 + 61 * 60) == 1000.0 + 115 * 60


def test_the_next_run_of_the_kind_takes_it_and_pays_only_what_it_adds(calls):
    first = machine(20)
    batch.delete_machine(first)
    assert first["parked"] and not calls.deleted and calls.remote == [CLEAN]  # its run's files gone first
    assert abs(ledger.machine_row(first)["euros"] - 60 * HOUR_PRICE) < 1e-9  # the first run pays its whole hour
    expirer_tags = calls.retagged[-1][1]
    assert expirer_tags[0] == f"pid={os.getpid()}" and expirer_tags[2].startswith("deadline=")
    other = run_of("other-kind")
    assert batch.park_taken(other, OFFERS, 1, "blender-other", 60) is None  # a kind without a clean-up never takes it
    assert batch.park_taken(other, OFFERS, 1, KIND, 200) is None  # nor a run wanting a bigger disk
    assert batch.park_taken(other, [OFFERS[0]._replace(zone="zone-b")], 1, KIND, 60) is None  # nor one elsewhere
    second = run_of("second")
    taken = batch.park_taken(second, OFFERS, 1, KIND, 60)
    assert taken["id"] == "m1" and taken in second.machines
    assert calls.retagged[-1][1][2] == f"deadline={second.deadline + batch.WATCHDOG_GRACE_MINUTES * 60:.0f}"
    assert batch.park_taken(run_of("third"), OFFERS, 1, KIND, 60) is None  # taken once
    taken["deleted"] = taken["adopted"] + 10 * 60  # ten minutes of work, inside the paid hour
    assert ledger.machine_row(taken)["euros"] == 0.0
    taken["deleted"] = taken["created"] + 70 * 60  # into a second hour: that hour is this run's
    assert abs(ledger.machine_row(taken)["euros"] - 60 * HOUR_PRICE) < 1e-9


def test_another_cleaned_kind_takes_a_parked_machine_when_its_own_kind_has_none(calls, monkeypatch):
    monkeypatch.setitem(park.CLEANUPS, "park-other", lambda _machine: "rm -rf /root/other/out")
    for server_id, kind in (("m-own", KIND), ("m-other", "park-other")):  # its own kind's parked first: less time
        batch.delete_machine(machine(20, kind=kind, server_id=server_id))
    own = batch.park_taken(run_of("own"), OFFERS, 1, KIND, 60)
    assert own["id"] == "m-own" and own["kind"] == KIND  # its own kind's machine first
    taken = batch.park_taken(run_of("cross"), OFFERS, 1, KIND, 60)
    assert taken["id"] == "m-other" and taken["kind"] == KIND  # then the other kind's, now this kind's
    assert not calls.deleted


def test_a_machine_not_worth_parking_or_of_a_stopping_run_is_deleted(calls):
    late = machine(54, server_id="m2")
    batch.delete_machine(late)
    assert calls.deleted == ["m2"] and not late.get("parked")
    batch.STOPPING.set()
    try:
        batch.delete_machine(machine(10, server_id="m3"))
    finally:
        batch.STOPPING.clear()
    assert calls.deleted == ["m2", "m3"]


def test_expire_deletes_a_machine_nobody_took_and_spares_one_taken_or_reparked(calls):
    batch.delete_machine(machine(20, server_id="m4"))
    park.expire("m4", "zone-a", "another-parking", time.time())  # an older expirer of the same machine
    assert calls.deleted == [] and (park.PARKED / "m4.json").exists()
    park.expire("m4", "zone-a", token_of("m4"), time.time())
    assert calls.deleted == ["m4"] and not (park.PARKED / "m4.json").exists()
    batch.delete_machine(machine(20, server_id="m5"))
    token = token_of("m5")
    assert batch.park_taken(run_of("taker"), OFFERS, 1, KIND, 60)["id"] == "m5"
    park.expire("m5", "zone-a", token, time.time())
    assert calls.deleted == ["m4"]


def test_an_expirer_ends_once_its_machine_is_no_longer_parked_under_its_token(calls):
    """2026-10-26: a pool card's expirer slept to the pool's end after its card was taken or released."""
    batch.delete_machine(machine(20, server_id="m7"))
    expirer = threading.Thread(target=park.expire, args=("m7", "zone-a", token_of("m7"), time.time() + 3600, 0.02),
                               daemon=True)
    expirer.start()
    time.sleep(0.1)
    assert expirer.is_alive()
    (park.PARKED / "m7.json").unlink()  # taken, or released by a pool's close
    expirer.join(2)
    assert not expirer.is_alive() and calls.deleted == []


def test_a_watchdog_deletes_its_machine_at_once_when_its_renter_is_gone(calls, monkeypatch):
    """Killed before its own delete, the renter left the machine billing and its watchdog asleep to the deadline."""
    parents = iter([4242, 4242, 1])
    monkeypatch.setattr(os, "getppid", lambda: next(parents, 1))
    started = time.time()
    batch.watchdog("m8", "zone-a", time.time() + 20, poll=0.01)
    assert calls.deleted == ["m8"] and time.time() - started < 5


def test_a_parked_machine_that_does_not_answer_is_deleted_and_none_taken(calls, monkeypatch):
    batch.delete_machine(machine(20, server_id="m6"))

    def no_answer(folder, host, command, **_):
        raise OSError("connection refused")
    monkeypatch.setattr(batch, "remote", no_answer)
    assert batch.park_taken(run_of("unlucky"), OFFERS, 1, KIND, 60) is None
    assert calls.deleted == ["m6"]


def test_a_card_waits_its_kinds_measured_cold_start_at_most_the_cap(calls):
    assert park.idle_minutes(KIND) == park.IDLE_DEFAULT_MINUTES  # never measured
    cold_card_runs(4.0, 6.0, 5.0)
    ledger.record({"started": "2026-10-11T10:00:00Z", "kind": KIND, "euros": 1.0, "machines": [
        {"cards": 0, "started": True, "start_wait_minutes": 0.5, "minutes": 50}]})  # a processor machine: no card
    assert park.idle_minutes(KIND) == 5.0
    cold_card_runs(30.0, 40.0, 50.0, 60.0)  # median 30: never an hour, however long a set-up took
    assert park.idle_minutes(KIND) == park.IDLE_CAP_MINUTES == 10
    now = time.time()
    assert abs(park.leaves_at(card("c"), now) - (now + 10 * 60)) < 1e-6
    ledger.LEDGER.unlink()
    cold_card_runs(0.6, 0.7, 0.8)
    with park.wanting(KIND):  # a claim waits: a short cold start still parks the card LEAST_MINUTES for it
        now = time.time()
        assert park.parkable(card("c"), now)
        assert abs(park.leaves_at(card("c"), now) - (now + park.LEAST_MINUTES * 60)) < 1e-6


def test_a_card_with_no_claim_waiting_is_released_not_parked(calls):
    """2026-10-22: an H100 sat parked for the next Pixal3D run after a one-model batch, and none came."""
    cold_card_runs(4.0)
    idle = card("c-idle")
    batch.delete_machine(idle)
    assert not idle.get("parked") and calls.deleted == ["c-idle"] and not (park.PARKED / "c-idle.json").exists()


def test_a_card_nobody_took_is_deleted_at_its_time_and_its_idle_minutes_charged(calls):
    cold_card_runs(4.0)
    held = card("c1")
    parked(held)
    assert held["parked"] and not calls.deleted
    assert abs(calls.armed[-1] - (time.time() + 4 * 60)) < 5  # its own self-delete armed for its idle time
    park.expire("c1", "zone-a", token_of("c1"), time.time())
    assert calls.deleted == ["c1"]
    idle = ledger.entries()[-1]
    assert idle["kind"] == KIND and idle["machines"][0]["parked_idle"] and idle["euros"] >= 0.0
    assert park.idle_minutes(KIND) == 4.0  # an idle row is not a cold start


def test_an_ended_run_releases_its_parked_machines_at_their_time(calls, monkeypatch):
    """#45: three L4s of an ended run stayed parked past their time. The run's releaser deletes each of its own still
    listed at its time, leaves another run's alone and returns once none is listed."""
    cold_card_runs(4.0)
    monkeypatch.setenv("SCORE_RUN_ID", "ended-run")
    for server_id in ("e1", "e2"):
        parked(card(server_id))
    monkeypatch.setenv("SCORE_RUN_ID", "another-run")
    parked(card("o1"))
    monkeypatch.delenv("SCORE_RUN_ID")
    for server_id, seconds in (("e1", 0.2), ("e2", 0.4)):
        path = park.PARKED / f"{server_id}.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), "until": time.time() + seconds}))
    assert sorted(record["id"] for record in park.parked_by("ended-run")) == ["e1", "e2"]
    started = time.time()
    park.outlive("ended-run", poll=0.05)
    assert sorted(calls.deleted) == ["e1", "e2"] and time.time() - started >= 0.4  # each at its time, not before
    assert park.parked_by("ended-run") == [] and (park.PARKED / "o1.json").exists()
    assert sum(1 for entry in ledger.entries() if entry.get("batch", "").startswith("parked-e")) == 2  # idle charged
    park.outlive("ended-run", poll=0.05)  # nothing left: returns at once
    assert sorted(calls.deleted) == ["e1", "e2"]


def test_a_taken_card_skips_its_cold_start_and_pays_its_idle_and_work(calls):
    held = card("c2")
    parked(held)
    assert abs(ledger.machine_row(held)["euros"] - 21 * CARD_PRICE) < 1e-9  # 20 min and a started one
    taken = batch.park_taken(run_of("next-card"), CARD_OFFERS, 1, KIND, 60)
    assert taken["id"] == "c2" and taken["ready"] == taken["adopted"]  # no wait to answer, no set-up again
    taken["deleted"] = taken["adopted"] + 3 * 60
    assert abs(ledger.machine_row(taken)["euros"] - 3 * CARD_PRICE) < 0.02 * CARD_PRICE + 1e-9


def test_a_claim_waiting_on_its_kinds_queue_takes_a_card_parked_meanwhile(calls, monkeypatch):
    monkeypatch.setattr(park, "PARKED_POLL_SECONDS", 0.05)
    found = []
    with park.wanting(KIND):
        assert park.waiting(KIND) == 1
        waiter = threading.Thread(target=lambda: found.append(
            batch.parked_within(run_of("waiter"), CARD_OFFERS, 1, KIND, 60, 5.0)))
        waiter.start()
        time.sleep(0.2)
        batch.delete_machine(card("c3"))
        waiter.join()
    assert found[0]["id"] == "c3" and park.waiting(KIND) == 0


def test_taking_a_parked_machine_needs_a_cleared_run(calls, monkeypatch):
    parked(card("c4"))

    def refuse(what, store=None):
        raise batch.compute.Refused(what)
    monkeypatch.setattr(batch.compute, "require_cleared", refuse)
    try:
        batch.park_taken(run_of("uncleared"), CARD_OFFERS, 1, KIND, 60)
        raise AssertionError("a parked card was taken outside a cleared run")
    except batch.compute.Refused:
        pass
    assert (park.PARKED / "c4.json").exists()  # still there for a cleared run


def test_a_sweep_leaves_a_parked_machine_alone_until_its_time():
    until = time.time() + 30 * 60
    tags = batch.run_tags(os.getpid(), until)
    assert not batch.is_leftover(tags, time.time())
    assert batch.is_leftover(tags, until + 1)
    assert batch.is_leftover(batch.run_tags(999999999, until), time.time())  # its expirer gone


def test_a_run_at_its_cap_leaves_another_runs_parked_machine_listed(calls, monkeypatch):
    monkeypatch.setenv("SCORE_RUN_ID", "another-park-test-run")
    monkeypatch.setenv("SCORE_MAX_MACHINES", "all=1")
    parked(card("c9"))  # parked by another run
    assert json.loads((park.PARKED / "c9.json").read_text())["run"] == "another-park-test-run"
    monkeypatch.setenv("SCORE_RUN_ID", "park-test-run")
    held = run_of("at-cap")
    held.machines.append({"id": "busy", "zone": "zone-a", "class": "gpu-24gb", "deleted": None})
    assert park.adopt(held, CARD_OFFERS, 1, KIND, 60) is None  # this run holds its cap of one: none taken
    assert (park.PARKED / "c9.json").exists()
    held.machines[0]["deleted"] = time.time()
    assert park.adopt(held, CARD_OFFERS, 1, KIND, 60)["id"] == "c9"  # parked to live: the count stays one


def on_the_machine(command, root):
    """Run a machine's shell command with /root as `root`, as the machine runs it."""
    assert os.system(f"bash -c {shlex.quote(command.replace('/root', str(root)))}") == 0


def test_each_kinds_clean_up_removes_its_runs_files_and_keeps_its_set_up(tmp_path):
    """#20: one warm queue per step: Pixal3D, finish-masks, segment and meshparts clean up beside the others; each
    removes its run's inputs and outputs and keeps the set-up, and Pixal3D's keeps its watcher and key."""
    import finish_masks
    import segment
    layouts = {"pixal": ("batch", ["in", "out", "queue", "logs", "closed", "status.json", "run.log"],
                         ["self_delete.py", "heartbeat", "machine_run.py"]),
               segment.KIND: ("seg", ["in", "out"], ["sam2"]), finish_masks.KIND: ("finish", ["in", "out"], ["venv"]),
               "meshparts": ("mp", ["in", "out"], ["SegviGen"])}
    for kind, (folder, removed, kept) in layouts.items():
        root = tmp_path / kind
        for name in removed + kept:
            (root / folder / name).mkdir(parents=True)
        on_the_machine(park.CLEANUPS[kind](machine(20, unit_minutes=1)), root)
        assert sorted(path.name for path in (root / folder).iterdir()) == sorted(kept), kind


def test_a_taken_machine_keeps_only_its_newest_set_up_mark(calls, tmp_path):
    """Most kinds install into /root/venv: after depth set up on a parked pixal card, pixal's own older mark would
    skip a set-up whose environment is gone, so only the newest mark stays."""
    for age, name in ((300, ".pixal-setup-aaaa"), (200, ".library-setup-done"), (100, ".depth-setup-bbbb")):
        (tmp_path / name).touch()
        os.utime(tmp_path / name, (time.time() - age, time.time() - age))
    (tmp_path / "venv").mkdir()
    on_the_machine(park.STALE_MARKS, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == [".depth-setup-bbbb", "venv"]
    empty = tmp_path / "empty"
    empty.mkdir()
    on_the_machine(park.STALE_MARKS, empty)  # no mark at all: no failure
    parked(card("c-marks"))
    assert park.adopt(run_of("marks"), CARD_OFFERS, 1, KIND, 60)["id"] == "c-marks"
    assert calls.remote[-1] == park.STALE_MARKS  # run on the taken machine


def test_a_pixal_fleet_takes_a_parked_card_before_it_orders_one(calls, monkeypatch):
    parked(card("c-pixal", kind="pixal"))
    ordered, tended = [], []
    monkeypatch.setattr(batch, "rent", lambda *arguments, **_: ordered.append(arguments) or None)
    monkeypatch.setattr(batch, "tend", lambda fleet, taken: tended.append(taken["id"]))
    fleet = batch.Fleet([], run_of("pixal-fleet").folder, 3, time.time() + 3600, "park-test", False)
    fleet.offers = list(CARD_OFFERS)
    assert batch.rent_fleet(fleet, 1) == 1
    assert not ordered and [taken["id"] for taken in fleet.machines] == ["c-pixal"]  # listed once, none rented
    deadline = time.time() + 5
    while not tended and time.time() < deadline:
        time.sleep(0.05)
    assert tended == ["c-pixal"]


def test_this_pcs_card_is_taken_free_one_claim_at_a_time_and_never_parked(calls, monkeypatch):
    held = []

    def take(kind, public_key, need=None):
        if kind == "judge":
            raise ValueError("a judge job needs about 30 GB of card")
        if held:
            return None  # another claim holds this PC
        held.append(kind)
        return {"id": "score-this-pc:1", "zone": "this-pc", "type": "score-this-pc", "class": "gpu-16gb", "cards": 1,
                "price": 0.0, "unit_minutes": 1, "host": "172.17.0.2", "disk_gb": 500, "here": True}

    monkeypatch.setattr(cloud, "take", take, raising=False)
    monkeypatch.setattr(batch, "ssh_key", lambda: "ssh-ed25519 AAAA runner")
    monkeypatch.setattr(batch.compute, "require_cleared", lambda what, store=None: pytest.fail("cleared " + what))
    first = run_of("here")
    taken = batch.park_taken(first, CARD_OFFERS, 1, KIND, 60)
    assert taken["id"] == "score-this-pc:1" and taken in first.machines
    assert calls.remote == [f"{park.own_set_up(KIND)}; {CLEAN}"]  # a last claim's own files go, its set-up stays
    assert batch.park_taken(run_of("busy"), CARD_OFFERS, 1, KIND, 60) is None  # one claim at a time
    with pytest.raises(batch.compute.Refused, match="30 GB"):
        batch.park_taken(run_of("big"), CARD_OFFERS, 1, "judge", 60)
    taken["healthy"] = True
    with park.wanting(OTHER):  # a claim waits, yet this PC's card is never parked: its claim ends
        batch.delete_machine(taken)
    assert calls.deleted == ["score-this-pc:1"] and not list(park.PARKED.glob("*.json"))
    assert ledger.machine_row({**taken, "deleted": taken["adopted"] + 600})["euros"] == 0.0


def test_each_kind_on_this_pcs_card_keeps_its_own_set_up(tmp_path):
    """This PC's container is one machine kept for good (2026-10-29: a characters claim set up from scratch while
    every Blender bake waited): each kind gets its own /root/venv back at its claim, nothing a claim runs removes
    another kind's set-up mark, and the venv of no known kind found at the first claim goes once with every mark."""
    root = tmp_path / "pc"
    (root / "venv").mkdir(parents=True)
    (root / ".pixal-setup-old").touch()
    on_the_machine(park.own_set_up("pixal"), root)  # the first claim: a venv nobody can name, and marks that may lie
    assert not (root / "venv").exists() and not (root / ".pixal-setup-old").exists()
    (root / "venv" / "pixal3d").mkdir(parents=True)  # pixal's set-up: its venv, its mark, Blender's beside
    (root / ".pixal-setup-aaaa").touch()
    (root / ".library-setup-done").touch()
    on_the_machine(park.own_set_up("moss-sound"), root)
    assert not (root / "venv").exists()  # moss builds its own, never over pixal's
    (root / "venv" / "moss").mkdir(parents=True)
    (root / "sfx" / "model").mkdir(parents=True)
    (root / "sfx" / "out").mkdir()
    on_the_machine(f"{park.CLEANUPS['moss-sound']({'here': True})}; {park.ALL_MARKS}", root)  # moss_sound.set_up's
    assert sorted(path.name for path in (root / "sfx").iterdir()) == ["model"]  # its model stays for its next claim
    on_the_machine(park.own_set_up("pixal"), root)
    assert sorted(path.name for path in (root / "venv").iterdir()) == ["pixal3d"]  # pixal's own venv, back
    assert (root / ".pixal-setup-aaaa").exists() and (root / ".library-setup-done").exists()  # its set-up skips
    on_the_machine(park.own_set_up("moss-sound"), root)
    assert sorted(path.name for path in (root / "venv").iterdir()) == ["moss"]
    rented = tmp_path / "card"
    rented.mkdir()
    (rented / ".pixal-setup-aaaa").touch()
    on_the_machine(park.CLEANUPS["moss-sound"]({}), rented)  # a rented card's kinds share /root/venv: every mark goes
    assert not list(rented.iterdir())
