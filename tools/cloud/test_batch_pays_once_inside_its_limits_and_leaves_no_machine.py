"""Invariant of batch.py (with the ledger it writes): a batch rents only inside a cleared run and the owner's limits
(4 h and EUR 60), builds only approved rows and specs, orders nothing the stock read says is out, writes a machine's
started line before its order so the month counts it until it is closed, runs every job once (a failed, overdue,
unsent or broken-machine job is a gap with its reason; a job lost while this PC slept is not a gap), rents no machine
in the place of a billed one that failed, and leaves no machine running however its runner or node ends.

No machine is rented: the backend, ssh and the clock are stand-ins, and the dying-runner checks run real processes.
Expected numbers are worked out by hand in the tests. The break that turns each red (applied once, seen red,
reverted):

- test_a_batch_past_the_owners_limits_is_refused_and_the_dearest_cards_left_out: in ledger.py `refusal`,
  `estimated_minutes > BATCH_HOURS * 60` -> `estimated_minutes > BATCH_HOURS * 600`; or in `affordable`, `found =
  [offer for offer in found if offer.per_card < dearest]` -> `break`.
- test_the_month_counts_a_running_machine_until_its_run_row_delete_or_refusal: in ledger.py `month_total`, the `+
  sum(open_euros(line, now) ...)` term -> `+ 0`; or in `open_rents`, `("disk-and-address", RENT_REFUSED)` ->
  `("disk-and-address",)`.
- test_a_list_names_each_model_once_with_its_options: in `read_list`, `if len(set(names)) != len(names):` -> `if
  False:`.
- test_the_fleet_is_sized_to_end_in_its_aim_and_a_capped_one_aims_for_what_it_can: in `cards_needed`, `working =
  minutes - SETUP_MINUTES - per_model * per_card` -> `working = minutes - SETUP_MINUTES`; or in `aimed_minutes`,
  `max(` -> `min(`.
- test_model_minutes_come_from_the_batch_started_last: in `card_minutes_per_model`, `reverse=True` -> `reverse=False`.
- test_a_batch_builds_only_an_approved_inventorys_rows: in `from_the_inventory`, `if strays:` -> `if False:`.
- test_a_batch_builds_a_character_only_when_its_spec_is_approved: in `from_the_characters`, `if not
  spec.get("approved"):` -> `if False:`.
- test_a_machine_is_left_over_once_past_its_deadline_or_its_process_is_gone: in `is_leftover`, `and not (pid and
  process_alive(int(pid)))` -> `and False`.
- test_a_short_fleet_rents_more_as_stock_comes_up: in `keep_the_fleet`, `if short > 0 and not fleet.no_more_work() and`
  -> `if False and` (a short fleet never asks again).
- test_a_fleet_waits_out_an_open_pool_but_never_a_closed_one: in `keep_the_fleet`, `if alive or not pool_open() or
  pool_closed():` -> `if alive or not pool_open():`.
- test_nothing_is_ordered_while_the_backend_says_there_is_no_stock: in `rent`, `if offer.stock_word in NO_STOCK:` ->
  `if False:`.
- test_the_wait_for_stock_doubles_up_to_half_an_hour_and_never_past_the_deadline: in `claim_rounds`, `min(stock_wait_
  minutes(rounds) * 60, max(0.0, run.deadline - time.time()))` -> `stock_wait_minutes(rounds) * 60`.
- test_a_runs_rent_fees_are_its_machines_disk_and_address_lines_failed_rents_included: in ledger.py
  `machines_record`, drop `names |= {row["name"] for row in attempts if row.get("name")}`.
- test_a_pool_card_is_replaced_only_when_it_died_and_only_once_in_set_up: in `Fleet.replaces`, `return
  self.setup_deaths == 1` -> `return True`.
- test_a_failed_job_is_a_gap_and_never_sent_again: in `collect`, `fleet.gaps(failed, ...)` -> `fleet.again([{"name":
  name} for name in failed])`.
- test_a_job_past_its_deadline_is_stopped_once_and_becomes_a_gap: in `stop_overdue`, `stopped.add(name)` -> `pass`.
- test_a_fleet_whose_billed_machines_failed_rents_none_in_their_place: in `keep_the_fleet`, `short = cards -
  fleet.lost_cards - sum(` -> `short = cards - sum(`.
- test_a_fleets_leftover_jobs_at_its_deadline_are_gaps_with_a_reason: in `Fleet.gaps`, `self.why.setdefault(name,
  why)` -> `pass`.
- test_jobs_lost_while_this_pc_slept_are_not_gaps_and_the_batch_stops: in `Fleet.woke`, `QUIET_MINUTES * 60` ->
  `QUIET_MINUTES * 6000`.
- test_a_billed_boot_that_fails_is_a_gap_and_out_of_stock_moves_on: in `claim_from`, `if not isinstance(error,
  OutOfStock):` -> `if False:`.
- test_a_jobs_deadline_comes_from_its_measured_high_seconds: in `job_deadline_seconds`, `["high"]` -> `["median"]`.
- test_nothing_is_rented_outside_a_cleared_run: in `rent`, drop `compute.require_cleared(f"a {machine_type} in
  {zone}")`.
- test_a_rent_writes_its_started_line_before_the_order_is_sent: in backends/scaleway.py `create`, drop the
  `ledger.rent_started(...)` call before the order.
- test_a_batch_whose_runner_dies_deletes_its_machines: in score/graph's `watch_runner`, `os.killpg(runner_pid,
  signal.SIGTERM)` -> `pass` (the batch rents on).
- test_a_node_of_a_runner_that_leads_no_group_outlives_it_so_its_batch_deletes_every_machine: the fault's two halves
  together (each alone is covered by the other): in score/graph's `watch_runner`, the node sends itself SIGTERM when
  its runner is gone, and in `say`, `except BrokenPipeError:` -> `except ZeroDivisionError:`.
- test_a_node_killed_alone_while_its_run_lives_has_its_batch_delete_every_machine: in `stop_on_signals`, `if
  os.environ.get("SCORE_RUN_ID"):` -> `if False:`.
- test_a_dead_runners_group_is_sent_one_stop_however_many_nodes_see_it: in score/graph's `watch_runner`, drop `and
  stopped.claim_stop(mark)`.
- test_cluster_groups_run_their_takes_side_by_side: in `cluster_line`, `" || ".join(` -> `" && ".join(`.

The runners' shared steps (batch.priced and spread.tended/tend, as every runner calls them): each
runner says its estimate before it rents, the euros it says are its machines at the dearest offer it may take for
the minutes it says, it refuses a batch past the owner's limits (4 h, EUR 60) and never on the month's total (owner,
2026-10-20: no month's ceiling); and a machine a runner tends itself is armed to delete itself, hears the heartbeat
and is deleted whatever happens, a failed set-up included (#21: never held to mend).

The estimates are each runner's on a fixed list, as recorded from the code before the shared estimate (a separate
implementation), and their euros are checked against count x minutes x price worked out here. No machine is rented.
The break that turns each red (applied once, seen red, reverted):

- test_each_runner_says_and_returns_its_estimate: in batch.py `priced`, `ledger.cost(minutes, dearest) * count` ->
  `ledger.cost(minutes, dearest)`; or `dearest = max(` -> `dearest = min(`.
- test_every_runner_refuses_a_batch_past_the_owners_limits: in ledger.py `refusal`, `if euros > BATCH_EUROS:` -> `if
  False:`.
- test_no_runner_refuses_on_the_months_total: in batch.py `priced`, `refused = ledger.refusal(minutes, dearest *
  count)` -> `refused = ledger.refusal(minutes, dearest * count) or (spent > 1000 and "the month")`.
- test_a_scene_machine_is_armed_and_deleted_also_when_a_step_fails: in spread.py `tended`, move
  `batch.delete_machine(machine)` from the `finally` to after the `yield` (deleted only when the block ends well).
- test_a_held_character_machine_is_armed_with_the_grace_and_deleted: in spread.py `tended`, `run.deadline +
  batch.WATCHDOG_GRACE_MINUTES * 60` -> `run.deadline`.
- test_a_character_machine_whose_set_up_failed_is_deleted_not_held_to_mend: in characters.py `held`, the set-up
  failure's `raise SystemExit(...)` -> `pass`.
- test_a_served_blender_machine_runs_the_queue_on_its_card_and_is_deleted: in blender_cloud.py `serve`, `card =
  machine.get("class", "").startswith("gpu")` -> `card = False`.
- test_a_spread_machine_is_armed_and_deleted: in spread.py `tend`, drop `batch.delete_machine(machine)` from its
  `finally`.
"""
import json
import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import batch  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
from score.adapters import compute  # noqa: E402
import blender_cloud  # noqa: E402
import box_masks_cloud  # noqa: E402
import characters  # noqa: E402
import closeups_cloud  # noqa: E402
import delight  # noqa: E402
import finish_masks  # noqa: E402
import judge  # noqa: E402
import library_bake  # noqa: E402
import meshparts  # noqa: E402
import parts  # noqa: E402
import pictures  # noqa: E402
import scene  # noqa: E402
import segment  # noqa: E402
import similar  # noqa: E402
import spread  # noqa: E402
import unirig  # noqa: E402

L4 = 0.013125
NOW = 1_760_000_000.0  # a fixed now for the open-machine checks (2025-10-09 UTC)
MONTH = "2025-10"
REAL_SLEEP = time.sleep


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    """No line printed, no warm pool, no stop left over from another test."""
    monkeypatch.setattr(batch, "say", lambda line: None)
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)
    batch.STOPPING.clear()
    yield
    batch.STOPPING.clear()


def l4(zone="zone-a", stock_word="available"):
    return provider.Offer(0.01, 0, "L4", zone, 0.01, "gpu-24gb", 0, stock_word)


def refusal_of(call, *arguments):
    try:
        call(*arguments)
    except SystemExit as refused:
        return str(refused)
    return None


def test_a_batch_past_the_owners_limits_is_refused_and_the_dearest_cards_left_out():
    assert ledger.refusal(90, L4) is None
    assert "4 h" in ledger.refusal(241, L4)
    assert "€60" in ledger.refusal(210, 0.3)  # EUR 63
    assert ledger.minutes_allowed(L4) == 240 and round(ledger.minutes_allowed(0.3)) == 200
    assert ledger.cost(1.2, L4) == 2 * L4  # billed by the started minute
    found = [provider.Offer(L4, 1, "L4", "zone-a", L4, "gpu-24gb", 0, "scarce"),
             provider.Offer(0.047775, 2, "H100", "zone-b", 0.047775, "gpu-80gb", 0, "shortage")]
    # 20 H100s for 180 min is EUR 172; 20 L4s EUR 47: the H100 is left out
    assert [offer.machine_class for offer in batch.affordable(found, minutes=180, cards=20)] == ["gpu-24gb"]
    assert batch.affordable(found, minutes=30, cards=2) == found


def started_line(name, minutes_ago, deadline_in=None, price=0.02, run="pixal-7"):
    """A rent-started line for machine `name` of `run`, ordered `minutes_ago` before NOW."""
    line = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - minutes_ago * 60)),
            "batch": f"rent-{name}", "kind": ledger.RENT_STARTED, "state": "started", "run": run, "name": name,
            "price": price, "euros": 0.0}
    if deadline_in is not None:
        line["deadline"] = NOW + deadline_in * 60
    return line


def test_the_month_counts_a_running_machine_until_its_run_row_delete_or_refusal():
    """Fault (review of C1, 2026-10-17): a started line held 0 euros and the month ignored it, so the guard did not
    count a machine running and not yet billed."""
    batches = [{"started": "2026-09-29T10:00:00Z", "euros": 1.5}, {"started": "2026-08-31T23:00:00Z", "euros": 9.0}]
    assert ledger.month_total("2026-09", batches) == 1.5
    running = [started_line("pixal-7-1", 60, deadline_in=120)]  # an hour at EUR 0.02 a minute
    assert round(ledger.month_total(MONTH, running, now=NOW), 2) == 1.2 and ledger.open_rents(running, NOW) == running
    died = [started_line("pixal-7-1", 600, deadline_in=-360)]  # its run died: counted to its deadline, 4 h
    assert round(ledger.month_total(MONTH, died, now=NOW), 2) == 4.8
    started = [started_line("pixal-7-1", 60, 120), started_line("pixal-7-2", 60, 120),
               started_line("other-1", 60, 120, run="other")]
    closing = [{"started": started[0]["started"], "batch": "pixal-7", "kind": "pixal", "euros": 1.5},
               {"started": started[0]["started"], "batch": "disk-and-address-s1", "kind": "disk-and-address",
                "name": "other-1", "euros": 0.1},
               {"started": started[0]["started"], "batch": "rent-pixal-7-2", "kind": ledger.RENT_REFUSED,
                "name": "pixal-7-2", "euros": 0.0}]
    assert ledger.open_rents(started + closing, NOW) == []
    assert ledger.open_rents(started + closing[2:], NOW) == [started[0], started[2]]  # the refusal closes only its own
    assert round(ledger.month_total(MONTH, started + closing, now=NOW), 2) == 1.6


def test_a_list_names_each_model_once_with_its_options(tmp_path):
    picture = tmp_path / "crate.png"
    picture.write_bytes(b"")
    listing = tmp_path / "list.txt"
    listing.write_text(f"# approved 2026-09-29\ncrate {picture} --faces 12000 --feet\n\nbarrel {picture}  # tall\n")
    models = batch.read_list(listing)
    assert [model.name for model in models] == ["crate", "barrel"]
    assert models[0].faces == 12000 and models[0].feet and not models[1].feet
    listing.write_text(f"crate {picture}\ncrate {picture}\n")
    assert "twice" in refusal_of(batch.read_list, listing)


def test_the_fleet_is_sized_to_end_in_its_aim_and_a_capped_one_aims_for_what_it_can():
    # 229 models at 3.95 card minutes each, 3 at once, in an hour: 5 min set-up and an 11.85 min last run leave
    # 43.15 min of work for 904.55 card minutes, 21 cards; 5 + 229 * 3.95 / 21 + 11.85 = 59.9 min
    assert batch.cards_needed(229, 3, 60, 3.95) == 21
    assert round(batch.expected_minutes(229, 21, 3, 3.95)) == 60
    assert batch.cards_needed(5, 3, 60, 3.95) == 1
    assert "too short" in refusal_of(batch.cards_needed, 10, 6, 20, 3.95)  # 5 + 23.7 for one run: over 20
    # one card, 3 models at 18.7 card minutes, 3 at once: 5 + 56.1 + 56.1 = 117.2 min, aimed for, not refused
    assert round(batch.aimed_minutes(3, 1, 3, 18.7, 60), 1) == 117.2
    assert batch.aimed_minutes(5, 20, 3, 3.95, 60) == 60  # an uncapped small batch keeps its aim


def test_model_minutes_come_from_the_batch_started_last(monkeypatch):
    """A batch stopped part way is written after a later one; its slow rate must not set the estimate."""
    monkeypatch.setattr(ledger, "entries", lambda: [
        {"started": "2026-09-30T17:56:47Z", "models_done": 5, "card_minutes": 25},
        {"started": "2026-09-30T17:35:47Z", "models_done": 3, "card_minutes": 380}])
    assert batch.card_minutes_per_model() == 5


def test_a_batch_builds_only_an_approved_inventorys_rows(tmp_path):
    picture = tmp_path / "locker.png"
    picture.write_bytes(b"")
    listing = tmp_path / "list.txt"
    listing.write_text(f"habitat-locker {picture}\nlocker-b {picture}\nr2 {picture}\n")
    models = batch.read_list(listing)
    path = tmp_path / "hub.json"
    rows = [{"id": "r1", "view": "v1", "box": [0, 0, 9, 9], "name": "locker", "kind": "generate", "anchor": "wall",
             "size": [0.6, 0.5, 1.9], "count": 1, "thing": "prop:locker"},
            {"id": "r2", "view": "v1", "box": [0, 0, 9, 9], "name": "desk", "kind": "mechanic", "anchor": "floor",
             "size": [1.6, 0.8, 0.75], "count": 1, "thing": "node:Workstation", "prop": "desk"},
            {"id": "keyboard", "view": "v1", "box": [0, 0, 9, 9], "name": "keyboard", "kind": "code",
             "anchor": "wall", "size": [0.4, 0.03, 0.15], "count": 1, "thing": "gear:keyboard"}]
    inventory = {"scene": "hub", "place": "habitat", "plan": {"views": [{"id": "v1"}]}, "approved": "", "migrated": "",
                 "room": {"shell": "", "light": "place", "backdrop": "", "wall_fill": []}, "rows": rows}
    assert "no inventory" in refusal_of(batch.from_the_inventory, models, [path])
    path.write_text(json.dumps(inventory))
    assert "not approved" in refusal_of(batch.from_the_inventory, models, [path])
    # approved, a place named by no place.json entry too: Pixal3D is worded by nothing
    for place in ("habitat", "no_such_place"):
        path.write_text(json.dumps(dict(inventory, approved="2026-10-05", place=place)))
        assert batch.from_the_inventory(models, [path]) >= {"r1", "locker", "r2", "desk"}
    listing.write_text(f"no_such_row {picture}\n")
    assert "on no row" in refusal_of(batch.from_the_inventory, batch.read_list(listing), [path])
    # a designed place's hand-in is approved by the creator's pick, its rows taken as they stand
    designed = {**inventory, "approved": {"by": batch.DESIGNED, "concept": "c" * 64}, "room": {},
                "rows": [{**rows[0], "anchor": "ground", "box": None}]}
    path.write_text(json.dumps(designed))
    listing.write_text(f"habitat-locker {picture}\n")
    assert batch.from_the_inventory(batch.read_list(listing), [path]) >= {"r1"}
    path.write_text(json.dumps({**designed, "scene": "lab"}))  # a hand-in under another place's name: page A's rules
    refused = refusal_of(batch.from_the_inventory, batch.read_list(listing), [path])
    assert refused and ("not sound" in refused or "not approved" in refused)


def test_a_batch_builds_a_character_only_when_its_spec_is_approved(tmp_path):
    picture = tmp_path / "tang.png"
    picture.write_bytes(b"")
    spec = {"name": "fish_tang", "kind": "animal", "picture": str(picture), "body": "fish"}
    path = tmp_path / "fish_tang.json"
    path.write_text(json.dumps(spec))
    assert "not approved" in refusal_of(batch.from_the_characters, [path])
    path.write_text(json.dumps(dict(spec, approved="owner", picture=None)))
    assert "no picture" in refusal_of(batch.from_the_characters, [path])
    path.write_text(json.dumps(dict(spec, approved="owner, 2026-10-09")))
    models = batch.from_the_characters([path])
    assert [(options.name, options.picture) for options in models] == [("fish_tang", str(picture))]
    assert "share a name" in refusal_of(batch.from_the_characters, [path, path])


def test_a_machine_is_left_over_once_past_its_deadline_or_its_process_is_gone():
    here, later = socket.gethostname(), 2e9
    assert batch.is_leftover([], 1e9)
    assert batch.is_leftover([f"deadline={1e9 - 1:.0f}"], 1e9)
    assert not batch.is_leftover([f"deadline={later:.0f}", f"host={here}", f"pid={os.getpid()}"], 1e9)
    assert batch.is_leftover([f"deadline={later:.0f}", f"host={here}", "pid=999999999"], 1e9)
    assert not batch.is_leftover([f"deadline={later:.0f}", "host=elsewhere", "pid=999999999"], 1e9)


class FleetStub:
    """The parts of a Fleet keep_the_fleet reads."""

    def __init__(self, deadline, work=True):
        self.stop, self.renting, self.deadline = threading.Event(), threading.Lock(), deadline
        self.machines, self.offers, self.work, self.lost_cards = [], [], work, 0

    def no_more_work(self):
        return not self.work

    def woke(self, since):
        return False


def test_a_short_fleet_rents_more_as_stock_comes_up(monkeypatch):
    fleet, rounds = FleetStub(time.time() + 60), []
    found = [l4()]

    def rent_fleet(fleet, cards):
        rounds.append(cards)
        if len(rounds) < 3:
            return 0  # out of stock on the first rounds
        fleet.machines.append({"cards": cards, "deleted": time.time()})
        fleet.work = False
        return cards
    monkeypatch.setattr(batch, "rent_fleet", rent_fleet)
    monkeypatch.setattr(batch.cloud, "offers", lambda classes: list(found))
    monkeypatch.setattr(batch, "STOCK_RETRY_MINUTES", 0)
    monkeypatch.setattr(batch.time, "sleep", lambda seconds: None)
    batch.keep_the_fleet(fleet, found, 2)
    assert rounds == [2, 2, 2] and fleet.offers == found


def test_a_fleet_waits_out_an_open_pool_but_never_a_closed_one(monkeypatch):
    """Fault of 2026-10-26: a Pixal3D fleet with no card paused its deadline on its run's pool for as long as the pool
    had ever been opened; a closed pool holds no card for it again, so the fleet runs out its own time."""
    rounds, closed = [], [False]

    def rent_fleet(fleet, cards):
        rounds.append(cards)
        if len(rounds) >= 6:  # a fleet left waiting is stopped here
            fleet.stop.set()
        return 0
    monkeypatch.setattr(batch, "rent_fleet", rent_fleet)
    monkeypatch.setattr(batch, "pool_open", lambda: True)
    monkeypatch.setattr(batch, "pool_closed", lambda: closed[0])
    monkeypatch.setattr(batch, "ask_every", lambda rounds: 0 if not closed[0] else 3600)
    monkeypatch.setattr(batch, "fresh_offers", lambda run, found: [])
    monkeypatch.setattr(batch.time, "sleep", lambda seconds: REAL_SLEEP(0.02))
    batch.keep_the_fleet(FleetStub(time.time() + 0.05), [], 1)
    assert len(rounds) == 6  # six rounds of 0.02 s past its 0.05 s: its deadline held while the pool was open
    closed[0] = True
    fleet = FleetStub(time.time() + 0.1)
    deadline = fleet.deadline
    batch.keep_the_fleet(fleet, [], 1)
    assert fleet.deadline == deadline and time.time() >= deadline  # its own time, never stretched


def test_nothing_is_ordered_while_the_backend_says_there_is_no_stock(monkeypatch, tmp_path):
    """pixal@people, 2026-10-22: the fleet ordered at the provider's shortage every round for over an hour, each
    order a machine that never started and billed its disk and address (EUR 2.19 in all)."""
    ordered = []
    monkeypatch.setattr(batch.cloud, "create", lambda *arguments: ordered.append(arguments) or (None, "refused"))
    monkeypatch.setattr(batch.compute, "require_cleared", lambda what: None)
    fleet = types.SimpleNamespace(folder=tmp_path, deadline=time.time() + 60, attempts=[])
    for word in batch.NO_STOCK:
        assert batch.rent(fleet, "account", l4(stock_word=word), 1) is None
    assert ordered == [] and fleet.attempts == []


def test_the_wait_for_stock_doubles_up_to_half_an_hour_and_never_past_the_deadline(monkeypatch):
    assert [batch.stock_wait_minutes(rounds) for rounds in range(6)] == [3, 6, 12, 24, 30, 30]
    waits, rounds = [], []
    run = types.SimpleNamespace(deadline=time.time() + 20 * 60)
    monkeypatch.setattr(batch, "park_taken", lambda *arguments: None)
    monkeypatch.setattr(batch, "claim_round", lambda *arguments: rounds.append(1) or (
        None if len(rounds) < 5 else {"machine": 1}))
    monkeypatch.setattr(batch, "parked_within", lambda run, offers, number, kind, disk_gb, seconds: waits.append(
        seconds))
    monkeypatch.setattr(batch, "fresh_offers", lambda run, offers: offers)
    assert batch.claim_rounds(run, "account", [], 1, "pixal", 60, None) == {"machine": 1}
    assert [round(wait / 60) for wait in waits[:3]] == [3, 6, 12]
    assert 19 * 60 < waits[3] <= 20 * 60 and len(waits) == 4  # the fourth (24 min) cut to the 20 min left


def test_a_runs_rent_fees_are_its_machines_disk_and_address_lines_failed_rents_included(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    for name, euros in (("batch-1-1", 0.005), ("batch-1-1", 0.005), ("batch-1-2", 0.005), ("batch-2-1", 1.0)):
        ledger.record({"started": "2026-10-22T10:00:00Z", "batch": f"disk-and-address-{euros}", "name": name,
                       "kind": "disk-and-address", "euros": euros})
    attempts = [batch.refused_row(l4(), "out of stock", "batch-1-1"), batch.refused_row(l4(), "refused")]
    record = ledger.machines_record([], attempts, 0.0)
    # batch-1-1's two lines, not batch-1-2 (no attempt of its) nor batch-2-1; none in the run's own euros
    assert round(record["rent_fees"], 6) == 0.01 and record["euros"] == 0.0


def one_shot_fleet(names, tmp_path):
    models = [types.SimpleNamespace(name=name, picture="/pics/p.png", seed=1) for name in names]
    folder = tmp_path / f"fleet-{len(list(tmp_path.iterdir()))}"
    folder.mkdir()
    return batch.Fleet(models, folder, None, 0, "test", finish=False), models


def test_a_pool_card_is_replaced_only_when_it_died_and_only_once_in_set_up(monkeypatch, tmp_path):
    """Review of the warm pool (2026-10-23): every failure of a pool card put its jobs back and took the next card,
    so a set-up that always fails took card after card until the deadline."""
    fleet, _ = one_shot_fleet(["crate"], tmp_path)
    monkeypatch.setattr(batch, "answers", lambda machine: True)
    assert not fleet.replaces({"generating_began": 1.0})  # it answers: the fault is the job's
    monkeypatch.setattr(batch, "answers", lambda machine: False)
    assert fleet.replaces({"generating_began": 1.0})  # it died while working
    assert fleet.replaces({"generating_began": None})  # the first that died in set-up
    assert not fleet.replaces({"generating_began": None})  # a second: no more taken


def test_a_failed_job_is_a_gap_and_never_sent_again(tmp_path):
    """A batch runs every job once (CONTEXT.md, owner 2026-10-20): a failed or out-of-memory job was sent back."""
    fleet, models = one_shot_fleet(["crate", "barrel"], tmp_path)
    batch.queue(fleet, models)
    sent = [fleet.next_job()["name"], fleet.next_job()["name"]]
    status = {"jobs": {"crate": {"state": "failed"}, "barrel": {"state": "running", "began": 0}}}
    assert batch.collect(fleet, fleet.folder, "host", status, set()) == {"crate"}
    assert sent == ["crate", "barrel"] and fleet.failed == ["crate"] and fleet.next_job() is None


def test_a_job_past_its_deadline_is_stopped_once_and_becomes_a_gap(monkeypatch, tmp_path):
    status = {"jobs": {"slow": {"state": "running", "began": 0.0}, "quick": {"state": "running", "began": 900.0},
                       "made": {"state": "done", "began": 0.0}}}
    assert batch.overdue(status, set(), 500, 1000.0) == ["slow"]  # 1000 s on, 100 s on, done
    assert batch.overdue(status, {"slow"}, 500, 1000.0) == []
    (fleet, _), commands, stopped = one_shot_fleet(["slow"], tmp_path), [], set()
    fleet.job_deadline = 500
    monkeypatch.setattr(batch, "remote", lambda folder, host, command, **keywords: commands.append(command))
    monkeypatch.setattr(batch.time, "time", lambda: 1000.0)
    batch.stop_overdue(fleet, fleet.folder, "host", status, stopped)
    batch.stop_overdue(fleet, fleet.folder, "host", status, stopped)
    assert commands == ["pkill -f -- '[/]root/batch/out/slow\\.glb'"] and stopped == {"slow"}
    assert fleet.why["slow"] == "passed its 500 s deadline; stopped"
    pattern = batch.own_pattern("/root/batch/out/slow.glb")
    assert re.search(pattern, "python scripts/pixal3d_generate.py in.png /root/batch/out/slow.glb --seed 1")
    assert not re.search(pattern, f"bash -c pkill -f -- {pattern}")  # never the shell that runs pkill


def test_a_fleet_whose_billed_machines_failed_rents_none_in_their_place(monkeypatch, tmp_path):
    """A batch runs once: a billed machine that did not start or broke was replaced by a new rental, unpriced."""
    fleet, models = one_shot_fleet(["crate", "barrel"], tmp_path)
    fleet.deadline = time.time() + 60
    batch.queue(fleet, models)
    fleet.lose({"cards": 1})
    rented = []
    monkeypatch.setattr(batch, "rent_fleet", lambda fleet, cards: rented.append(cards) or 0)
    monkeypatch.setattr(batch.time, "sleep", lambda seconds: None)
    batch.keep_the_fleet(fleet, [], 1)
    assert rented == [] and sorted(fleet.failed) == ["barrel", "crate"] and fleet.next_job() is None


def tended(names, looks, poll_seconds, deadline_in, tmp_path, monkeypatch, per_card=3):
    """batch.tend on one fake machine over a fake clock that each poll's sleep moves on by `poll_seconds`: its status
    at each look is the next of `looks` (the last one kept; None: the machine is gone); the fleet."""
    fleet, models = one_shot_fleet(names, tmp_path)
    clock = [1000.0]
    fleet.deadline, fleet.per_card = clock[0] + deadline_in, per_card
    batch.queue(fleet, models)
    machine = {"adopted": True, "host": "host", "folder": fleet.folder / "m-1", "cards": 1, "class": "gpu-24gb",
               "created": clock[0], "deleted": None}
    machine["folder"].mkdir()
    looks = list(looks)

    def status(folder, host):
        look = looks.pop(0) if len(looks) > 1 else looks[0]
        if look is None:
            raise ConnectionError("the machine is gone")
        return {"finished": False, "jobs": {name: {"state": state, "began": clock[0]} for name, state in look.items()}}
    nothing = lambda *arguments, **keywords: None  # noqa: E731
    for name in ("arm_self_delete", "prepare", "send", "remote", "heartbeat", "bring_back", "delete_machine"):
        monkeypatch.setattr(batch, name, nothing)
    monkeypatch.setattr(batch, "machine_status", status)
    monkeypatch.setattr(batch, "POLL_SECONDS", poll_seconds)
    with monkeypatch.context() as clocked:
        clocked.setattr(time, "time", lambda: clock[0])
        clocked.setattr(time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
        batch.tend(fleet, machine)
    return fleet


def test_a_fleets_leftover_jobs_at_its_deadline_are_gaps_with_a_reason(tmp_path, monkeypatch):
    """Audit (2026-10-22): the jobs still running or never sent at a batch's deadline were left out of its gaps."""
    fleet = tended(["crate", "barrel", "lamp"], [{"crate": "done", "barrel": "running"}], 60, 30, tmp_path,
                   monkeypatch, per_card=1)
    assert fleet.done == ["crate"] and fleet.failed == ["barrel"]
    assert fleet.unsent_gaps("not sent before the batch's deadline") == ["lamp"]
    entry = batch.ledger_entry(fleet, list(fleet.models), 0.0)
    assert entry["gap_reasons"] == {"barrel": "still running at the batch's deadline",
                                    "lamp": "not sent before the batch's deadline"}
    broken = tended(["crate", "barrel"], [{"crate": "running", "barrel": "running"}, None], 1, 600, tmp_path,
                    monkeypatch)
    assert broken.failed == ["barrel", "crate"] and broken.why["crate"].startswith("its machine m-1 broke")


def test_jobs_lost_while_this_pc_slept_are_not_gaps_and_the_batch_stops(tmp_path, monkeypatch):
    """Audit (2026-10-22): the PC slept, the machines deleted themselves, and on waking their jobs were recorded as
    gaps, never asked again. They are lost to sleep now, for a rerun; the model already back is not among them."""
    looks = [{"crate": "done", "barrel": "running", "lamp": "running"}]
    fleet = tended(["crate", "barrel", "lamp"], looks, (batch.QUIET_MINUTES + 5) * 60, 4 * 3600, tmp_path, monkeypatch)
    assert fleet.done == ["crate"] and fleet.failed == [] and fleet.asleep == ["barrel", "lamp"]
    assert fleet.slept.is_set() and fleet.stop.is_set()
    entry = batch.ledger_entry(fleet, list(fleet.models), 0.0)
    assert entry["lost_to_sleep"] == ["barrel", "lamp"] and entry["gaps"] == []
    awake = tended(["crate", "barrel"], [{"crate": "done", "barrel": "running"}, None], 60, 4 * 3600, tmp_path,
                   monkeypatch)
    assert awake.asleep == [] and awake.failed == ["barrel"] and not awake.slept.is_set()


def test_a_billed_boot_that_fails_is_a_gap_and_out_of_stock_moves_on(monkeypatch, tmp_path):
    """claim_from moved to the next offer after a machine it rented (and was billed for) did not answer; only an
    out-of-stock refusal, where no card ran, may move on."""
    offers = [l4("zone-a"), l4("zone-b")]
    rented, failures = [], []

    def rent(run, account, offer, number, disk_gb):
        rented.append(offer.zone)
        folder = tmp_path / f"m{len(list(tmp_path.iterdir()))}"
        folder.mkdir()
        return {"zone": offer.zone, "type": offer.type, "class": offer.machine_class, "cards": 1, "folder": folder,
                "deleted": None}

    def boot(machine):
        raise failures.pop(0)
    monkeypatch.setattr(batch, "rent", rent)
    monkeypatch.setattr(batch, "boot", boot)
    monkeypatch.setattr(batch, "delete_machine", lambda machine: None)
    monkeypatch.setattr(batch.ledger, "machine_row", lambda machine: {})
    monkeypatch.setattr(batch, "park_taken", lambda *arguments: None)
    run = types.SimpleNamespace(machines=[], attempts=[], deadline=0)
    failures.append(TimeoutError("did not answer"))
    assert batch.claim(run, None, offers, 1, "parts") is None and rented == ["zone-a"]
    rented.clear()
    failures.extend([batch.OutOfStock("out of stock"), TimeoutError("did not answer")])
    assert batch.claim(run, None, offers, 1, "parts") is None and rented == ["zone-a", "zone-b"]


def test_a_jobs_deadline_comes_from_its_measured_high_seconds():
    measured = json.loads((REPO / "data" / "costs" / "per-unit.json").read_text())
    high = measured["stages"]["pixal"]["time"]["unit_seconds"]["high"]
    assert batch.job_deadline_seconds() == batch.DEADLINE_FACTOR * high


def test_nothing_is_rented_outside_a_cleared_run(monkeypatch, tmp_path):
    """Fault (design of 2026-10-11): rent ordered a machine for any caller, so the runners could spend without the
    runner's gate or the owner's yes."""
    ordered = []
    monkeypatch.setattr(batch.cloud, "create", lambda *arguments: ordered.append(arguments) or (None, "refused"))
    monkeypatch.setattr(batch, "month_spent", lambda account: 0.0)
    monkeypatch.delenv(compute.TICKET, raising=False)
    fleet = types.SimpleNamespace(folder=tmp_path, deadline=time.time() + 60, attempts=[])
    try:
        batch.rent(fleet, None, l4(), 0)
        raise AssertionError("a machine was ordered outside a cleared run")
    except compute.Refused as refusal:
        assert "nothing rents outside a cleared run" in str(refusal)
    assert ordered == []


def test_a_rent_writes_its_started_line_before_the_order_is_sent(monkeypatch, tmp_path):
    """Fault (2026-10-17, C1): a machine of a run that died first was on the bill and nowhere in the ledger. The
    started line names the run and its ticket before the order goes."""
    seen = []

    def fake_scw(command, **options):
        """The backend's scw call: what the ledger held when the order went, then a refusal; the look for a machine
        the refused order made anyway finds none."""
        if command[:4] != ["scw", "instance", "server", "create"]:
            return types.SimpleNamespace(returncode=0, stdout="[]", stderr="")
        seen.append((command, ledger.entries()))
        return types.SimpleNamespace(returncode=1, stdout="", stderr="out of quota")
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setenv(compute.TICKET, "run-7 surfaces-paint")
    monkeypatch.setattr(batch.cloud, "subprocess", types.SimpleNamespace(run=fake_scw))
    monkeypatch.setattr(batch, "month_spent", lambda account: 0.0)
    monkeypatch.setattr(batch.compute, "require_cleared", lambda what: None)
    keys = tmp_path / "keys"
    keys.mkdir()
    monkeypatch.setattr(batch, "KEY", keys / "ssh_key")
    monkeypatch.setattr(batch, "SELF_DELETE_KEY", keys / "self_delete.json")
    batch.KEY.write_text("private")
    batch.SELF_DELETE_KEY.write_text("{}")
    fleet = types.SimpleNamespace(folder=tmp_path / "pixal-run-7", deadline=time.time() + 60, attempts=[])
    assert batch.rent(fleet, None, l4(), 3) is None
    after = ledger.entries()
    [(command, [line])] = seen  # one order, and one line in the ledger as it went
    assert command[:4] == ["scw", "instance", "server", "create"]
    assert line["kind"] == ledger.RENT_STARTED and line["state"] == "started" and line["euros"] == 0.0
    assert line["deadline"] == round(fleet.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
    assert line["run"] == "pixal-run-7" and line["name"] == "pixal-run-7-3"
    assert line["ticket"] == "run-7 surfaces-paint" and line["type"] == "L4" and line["zone"] == "zone-a"
    assert [entry["kind"] for entry in after] == [ledger.RENT_STARTED, ledger.RENT_REFUSED]
    assert after[1]["name"] == "pixal-run-7-3" and "out of quota" in after[1]["reason"]


def wait_for(path, seconds=30):
    deadline = time.time() + seconds
    while not path.exists() and time.time() < deadline:
        REAL_SLEEP(0.05)
    assert path.exists(), f"{path.name} never came"


def deleted(path, count, seconds=30):
    """The machine ids written to `path`, once `count` are there or `seconds` passed."""
    deadline = time.time() + seconds
    while len(path.read_text().split() if path.exists() else []) < count and time.time() < deadline:
        REAL_SLEEP(0.05)
    return path.read_text().split() if path.exists() else []


def a_home(tmp_path, run_id=None):
    environment = {**os.environ, "PROPS_HOME": str(tmp_path), "PROPS_WORK": str(tmp_path / "work")}
    environment.pop("SCORE_RUN_ID", None)
    if run_id:
        environment["SCORE_RUN_ID"] = run_id
    return environment


# A batch holding argv[4] fake machines that works for argv[5] seconds, says so, then deletes each through
# batch.delete_machine as batch.run's end does; it writes "ready" once its signals are handled.
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
            for number in range(int(sys.argv[4]))]
try:
    (folder / "ready").write_text("ready")
    time.sleep(float(sys.argv[5]))
    batch.say("working on")
finally:
    for machine in machines:
        batch.delete_machine(machine)
"""
# A runner (argv[2] "lead": it leads its process group, as `score run` does) with one node process (score.graph's
# watch_runner) running the batch, its output piped to the node as a stage's subprocess.run does.
RUNNER = """
import os, subprocess, sys, threading, time
sys.path.insert(0, sys.argv[1])
from score import graph
if sys.argv[2] == "lead":
    os.setpgid(0, 0)
runner = os.getpid()
if os.fork() == 0:
    threading.Thread(target=graph.watch_runner, args=(runner, 0.2), daemon=True).start()
    subprocess.run([sys.executable, "-c", sys.argv[3], *sys.argv[4:]], capture_output=True)
    os._exit(0)
time.sleep(120)
"""


def test_a_batch_whose_runner_dies_deletes_its_machines(tmp_path):
    """Fault (2026-10-17): a `score run` killed outright left its batches renting with no one to stop them."""
    runner = subprocess.Popen([sys.executable, "-c", RUNNER, str(REPO), "lead", WORKING_BATCH, str(HERE),
                               str(tmp_path / "deletes.txt"), str(tmp_path), "1", "120"], env=a_home(tmp_path))
    wait_for(tmp_path / "ready")
    runner.send_signal(signal.SIGKILL)  # no stop handler runs: only the node's watch can end the batch
    runner.wait()
    assert deleted(tmp_path / "deletes.txt", 1) == ["machine-0"]


def test_a_node_of_a_runner_that_leads_no_group_outlives_it_so_its_batch_deletes_every_machine(tmp_path):
    """Review of C7 (2026-10-17): the node of a runner leading no group ended with it; the batch writing to it hit a
    broken pipe and deleted one machine of three."""
    runner = subprocess.Popen([sys.executable, "-c", RUNNER, str(REPO), "follow", WORKING_BATCH, str(HERE),
                               str(tmp_path / "deletes.txt"), str(tmp_path), "3", "2"], env=a_home(tmp_path))
    wait_for(tmp_path / "ready")
    runner.send_signal(signal.SIGKILL)
    runner.wait()
    assert deleted(tmp_path / "deletes.txt", 3) == ["machine-0", "machine-1", "machine-2"]


# A run (SCORE_RUN_ID set) whose one node runs the batch, its output piped to the node; the node's pid in node.pid.
RUN_WITH_A_NODE = """
import os, pathlib, subprocess, sys, time
folder = pathlib.Path(sys.argv[4])
if os.fork() == 0:
    (folder / "node.pid").write_text(str(os.getpid()))
    subprocess.run([sys.executable, "-c", sys.argv[1], *sys.argv[2:]], capture_output=True)
    os._exit(0)
time.sleep(120)
"""


def test_a_node_killed_alone_while_its_run_lives_has_its_batch_delete_every_machine(tmp_path):
    """Audit (2026-10-22): a node killed alone (out of memory) while its run lived got no stop, so its batch rented on
    until its deadline or the machines' self-delete."""
    run = subprocess.Popen([sys.executable, "-c", RUN_WITH_A_NODE, WORKING_BATCH, str(HERE),
                            str(tmp_path / "deletes.txt"), str(tmp_path), "3", "90"],
                           env=a_home(tmp_path, "killed-node-test"), start_new_session=True)
    try:
        wait_for(tmp_path / "ready")
        os.kill(int((tmp_path / "node.pid").read_text()), signal.SIGKILL)  # the run lives on
        assert deleted(tmp_path / "deletes.txt", 3) == ["machine-0", "machine-1", "machine-2"]
        assert run.poll() is None, "the run itself ended"
    finally:
        os.killpg(run.pid, signal.SIGKILL)
        run.wait(timeout=10)


# A runner leading its process group, with four node processes (watch_runner, each its own poll) that take SIGTERM
# without ending, and a process that writes a line for every SIGTERM it gets; "ready" once all are in.
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


def test_a_dead_runners_group_is_sent_one_stop_however_many_nodes_see_it(tmp_path):
    """Review of C7 (2026-10-17): every node's watch could send the group its own SIGTERM, and a batch already
    deleting stops deleting at its second signal."""
    runner = subprocess.Popen([sys.executable, "-c", COUNTED_RUNNER, str(REPO), str(tmp_path)])
    wait_for(tmp_path / "ready")
    runner.send_signal(signal.SIGKILL)
    runner.wait()
    REAL_SLEEP(2)  # every watch has seen its runner gone by now
    signals = (tmp_path / "signals.txt").read_text() if (tmp_path / "signals.txt").exists() else ""
    try:
        os.killpg(runner.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    assert signals == "x", f"the group was sent {len(signals)} stops"


def test_cluster_groups_run_their_takes_side_by_side():
    takes = [types.SimpleNamespace(name=f"crate-{number}", picture="/pics/crate.png", seed=number)
             for number in range(4)]
    groups = batch.groups_of(takes, 3)
    assert [[take.name for take in group] for group in groups] == [["crate-0", "crate-1", "crate-2"], ["crate-3"]]
    line = batch.cluster_line(groups[0])
    assert line.count("pixal-run scripts/pixal3d_generate.py /work/in/crate-") == 3 and line.count(") &") == 3
    # the job fails only when no take made its model
    assert line.endswith("wait; test -f /work/out/crate-0.glb || test -f /work/out/crate-1.glb || "
                         "test -f /work/out/crate-2.glb")
    job = batch.cluster_job(groups[0], pathlib.Path("/w/group0/out"))
    assert [entry["path"] for entry in job["inputs"]] == [f"/work/in/crate-{number}.png" for number in range(3)]
    assert job["outputs"] == [{"path": "/work/out", "local": "/w/group0/out"}]
    assert job["minutes"] == 3 * batch.cluster_job(groups[1], pathlib.Path("/w/group1/out"))["minutes"]


# --- the runners' shared steps: each says and keeps inside its estimate, and deletes every machine it tends ---

def offers(scale=1.0):
    """Three offers, EUR 0.02, 0.05 and 0.01 a minute (times `scale`), of three classes and stocks."""
    return [provider.Offer(0.02 * scale, 0, "small", "zone-a", 0.02 * scale, "gpu-24gb", 0, "available"),
            provider.Offer(0.05 * scale, 1, "big", "zone-b", 0.05 * scale, "gpu-80gb", 0, "scarce"),
            provider.Offer(0.01 * scale, 2, "short", "zone-c", 0.01 * scale, "cpu-32c-128gb", 0, "shortage")]


# Each runner's estimate on a fixed list, and the line it said on the code before the shared estimate.
ESTIMATES = {
    "blender_cloud": (lambda: blender_cloud.price([{"minutes": 5}, {"minutes": 20}], "acct", ["gpu-24gb"]),
                      "2 Blender jobs on 2 machines: about 28 min, €1.12"),
    "box_masks_cloud": (lambda: box_masks_cloud.price([{}] * 9, "acct"), "9 pictures on 1 card: about 13 min, €0.65"),
    "characters": (lambda: characters.price(["p1", "p2", "p3"], "acct", None),
                   "3 people on 3 machines: about 57 min, €8.55"),
    "closeups_cloud": (lambda: closeups_cloud.price(40, "acct", 20), "40 close-ups on 1 card: about 24 min, €1.20"),
    "delight": (lambda: delight.price(30, "acct"), "30 unlit copies on 2 cards: about 16 min, €1.60"),
    "finish_masks": (lambda: finish_masks.price([[]] * 7, "acct", 2),
                     "7 shares of pictures on 2 machines: about 26 min, €2.60"),
    "judge": (lambda: judge.price([{}] * 300, "acct", 1), "300 questions on 1 card: about 42 min, €2.10"),
    "library_bake": (lambda: library_bake.price([{"materials": [1] * 10}, {"chunky": [1] * 4}], "acct",
                                                ["gpu-24gb"]), "2 library jobs on 1 machine: about 17 min, €0.34"),
    "meshparts": (lambda: meshparts.price([["a"]] * 4, "acct", False),
                  "4 shares of takes on 4 machines: about 33 min, €6.60"),
    "parts": (lambda: parts.price(12, "acct"), "12 PartCrafter runs on 2 cards: about 32 min, €3.20"),
    "pictures": (lambda: pictures.price([{}] * 50, 2, "acct", "klein"), "50 pictures on 2 machines: about 12 min, €1.20"),
    "segment": (lambda: segment.price([[]] * 5, "acct"), "5 shares of pictures on 2 machines: about 22 min, €2.20"),
    "similar": (lambda: similar.price({f"p{n}": ["x", "y"] for n in range(100)}, "acct"),
                "100 pairs on one machine: about 10 min, €0.50"),
    "unirig": (lambda: unirig.price(9, "acct"), "9 models on 3 machines: about 27 min, €4.05"),
}
SAID = re.compile(r"on (\d+|one) (?:machine|card)s?: about (\d+) min, €([\d.]+); €([\d.]+) spent this month$")


def stubbed(monkeypatch, spent=100.0, scale=1.0):
    """batch's offers, month spend and say stubbed; the lines it says."""
    said = []
    monkeypatch.setattr(batch, "offers", lambda classes: offers(scale))
    monkeypatch.setattr(batch, "month_spent", lambda account: spent)
    monkeypatch.setattr(batch, "say", said.append)
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)  # no warm pool
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)  # no measured pre-flight
    return said


def test_each_runner_says_and_returns_its_estimate(monkeypatch):
    for name, (estimate, recorded) in ESTIMATES.items():
        said = stubbed(monkeypatch)
        returned = estimate()
        assert said == [f"{recorded}; €100.00 spent this month"], (name, said)
        count, minutes, euros, _ = SAID.search(said[0]).groups()
        count = 1 if count == "one" else int(count)
        dearest = max(offer.per_card for offer in returned[0])  # the dearest offer the runner may take
        # billed by the started minute: the said minutes are rounded, so the bill lies within a minute of them
        assert (int(minutes) - 0.5) * dearest * count - 0.005 <= float(euros) <= (int(minutes) + 1.5) * dearest * count
        assert returned[-1] == min(240.0, 60.0 / (dearest * count)), name  # the 4 h and EUR 60 limits


def test_every_runner_refuses_a_batch_past_the_owners_limits(monkeypatch):
    for name, (estimate, _) in ESTIMATES.items():
        stubbed(monkeypatch, scale=200.0)  # EUR 2 to 10 a minute: every batch here passes EUR 60
        try:
            estimate()
            raise AssertionError(f"{name} priced a batch past EUR 60")
        except SystemExit as refused:
            assert "refused" in str(refused) and "€60" in str(refused), (name, refused)


def test_no_runner_refuses_on_the_months_total(monkeypatch):
    for name, (estimate, recorded) in ESTIMATES.items():
        said = stubbed(monkeypatch, spent=10_000.0)
        estimate()
        assert said == [f"{recorded}; €10000.00 spent this month"], name


class Tended:
    """batch's machine steps stubbed: what was armed, beaten and deleted, in order."""

    def __init__(self, monkeypatch):
        self.done = []
        monkeypatch.setattr(batch, "arm_self_delete", lambda folder, host, deadline: self.done.append(
            ("armed", host, deadline)))
        monkeypatch.setattr(pictures, "keep_beating", lambda folder, host, stop: self.done.append(
            ("beating", host)) or stop.wait(5))
        monkeypatch.setattr(batch, "delete_machine", lambda machine: self.done.append(("deleted", machine["host"])))
        monkeypatch.setattr(batch, "say", lambda line: None)

    def armed_beaten_deleted(self, deadline):
        grace = deadline + batch.WATCHDOG_GRACE_MINUTES * 60
        return (self.done[0] == ("armed", "10.0.0.1", grace) and ("beating", "10.0.0.1") in self.done
                and self.done[-1] == ("deleted", "10.0.0.1") and self.done.count(("deleted", "10.0.0.1")) == 1)


def machine_and_run(tmp_path):
    folder = tmp_path / "machine"
    folder.mkdir()
    run = pictures.Run(folder, time.time() + 3600)
    run.started = time.time()
    return {"folder": folder, "host": "10.0.0.1", "created": 0.0, "class": "gpu-24gb", "type": "small",
            "zone": "zone-a"}, run


def test_a_scene_machine_is_armed_and_deleted_also_when_a_step_fails(tmp_path, monkeypatch):
    machine, run = machine_and_run(tmp_path)
    monkeypatch.setattr(scene, "set_up", lambda folder, host, plan: None)
    monkeypatch.setattr(scene, "run_steps", lambda folder, host, plan: (_ for _ in ()).throw(RuntimeError("failed")))
    monkeypatch.setattr(scene, "local_room", lambda room: tmp_path / "room")
    monkeypatch.setattr(batch, "copy", lambda *arguments: None)
    tended = Tended(monkeypatch)
    try:
        scene.work_on(run, machine, {"room": "lab"})
        raise AssertionError("the failed step was swallowed")
    except RuntimeError as failed:
        assert str(failed) == "failed"
    assert tended.armed_beaten_deleted(run.deadline), tended.done


def test_a_held_character_machine_is_armed_with_the_grace_and_deleted(tmp_path, monkeypatch):
    machine, run = machine_and_run(tmp_path)
    monkeypatch.setattr(characters, "set_up", lambda machine: None)
    monkeypatch.setattr(characters, "hold", lambda run, host: None)
    tended = Tended(monkeypatch)
    characters.held(run, machine, [])
    assert tended.armed_beaten_deleted(run.deadline), tended.done
    assert (run.folder / "host").read_text() == "10.0.0.1"


def test_a_character_machine_whose_set_up_failed_is_deleted_not_held_to_mend(tmp_path, monkeypatch):
    """#21: a set-up that fails ends the run with its people as gaps; the machine is never held to mend."""
    machine, run = machine_and_run(tmp_path)
    held = []

    def failed_set_up(machine):
        raise subprocess.CalledProcessError(1, "characters_setup.sh")
    monkeypatch.setattr(characters, "set_up", failed_set_up)
    monkeypatch.setattr(characters, "hold", lambda run, host: held.append(host))
    tended = Tended(monkeypatch)
    try:
        characters.held(run, machine, [pathlib.Path("/tmp/made/nev")])
        raise AssertionError("a failed set-up was held to mend")
    except SystemExit as stopped:
        assert "nev are gaps" in str(stopped)
    assert held == [] and tended.armed_beaten_deleted(run.deadline), tended.done


def test_a_served_blender_machine_runs_the_queue_on_its_card_and_is_deleted(tmp_path, monkeypatch):
    machine, run = machine_and_run(tmp_path)
    queue = tmp_path / "queue"
    queue.mkdir()
    (queue / "1.json").write_text(json.dumps({"script": "tools/blender/inside/x.py", "minutes": 1}))
    (queue / "close").write_text("")
    ran = []
    monkeypatch.setattr(blender_cloud, "set_up", lambda log_folder, host, jobs: ran.append(("set up", jobs)))
    monkeypatch.setattr(blender_cloud, "run_job", lambda log_folder, host, number, job, card: ran.append(
        (number, card)) or 1.5)
    monkeypatch.setattr(batch, "remote", lambda *arguments, **keywords: ran.append("remote"))
    monkeypatch.setattr(batch, "copy", lambda *arguments: ran.append("copy"))
    tended = Tended(monkeypatch)
    blender_cloud.serve(run, machine, queue, 1)
    assert tended.armed_beaten_deleted(run.deadline), tended.done
    assert ran == [("set up", []), "remote", "copy", (1, True)]  # its folders sent, then job 1 on the card
    assert (queue / "1.done").read_text() == "1.5" and (queue / "ready").read_text() == "gpu-24gb"
    assert machine["unit_seconds"] == [1.5]


def test_a_spread_machine_is_armed_and_deleted(tmp_path, monkeypatch):
    machine, run = machine_and_run(tmp_path)
    worked = []
    tended = Tended(monkeypatch)
    spread.tend(run, machine, "parts", spread.Shares([1, 2]), lambda machine: None,
                lambda machine, share, card: worked.append(share))
    assert tended.armed_beaten_deleted(run.deadline), tended.done
    assert sorted(worked) == [1, 2]
