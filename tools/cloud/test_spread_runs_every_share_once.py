"""Invariant of spread.py and the claim its slots make (batch.claim): a batch spread over machines runs every share
once (a batch, CONTEXT.md, owner 2026-10-20): a share whose command failed, or whose machine broke under it, is a
gap and never handed to another machine; a share cut off by the machine (signal 9 at its memory cap, a card that
would not open) runs again once; a broken machine takes nothing more; a machine that fails its set-up has none
rented in its place; each card runs its kind's measured runs at once; machines claimed side by side spread over the
zones; an open queue waits for work until it is closed; on this PC's one machine a claim's wait and its set-up are
not the work's time, a claim refused as too big ends the spread, and a shared claim gives way to one that waits for
the machine alone; and a slot that finds no stock asks again until its work is gone, its deadline passes or a stop
comes (2026-10-09: six of seven slots gave up on their first round and one L4 did all the work).

Renting, arming, beating and deleting are stand-ins that rent nothing. One rented world (three machines claimed
through the real batch.claim, an open queue holding every kind of fault) drives spread.on_machines once; a table of
this PC's claims drives it once a row; a table of stock rounds drives batch.claim once a row; a table of machines
reads spread.slots. The break that turns each red (applied once, seen red, reverted):

- in `Shares.failed_job`, `self.failed.append(item)` -> `self.waiting.append(item)` (the rented world's "plain"
  runs again).
- in `Shares.close`, `self.open = False` -> `pass` (the open queue's last slot waits out its idle time).
- in `slots`, `range(capacity.runs_at_once(kind, machine["class"]))` -> `range(1)` (the slots table).
- in `work_slot`, the broken machine's `shares.failed_job(share)` (before "its share is a gap") ->
  `shares.put(share)`; or drop `broken.set()` (m2 takes more after it broke).
- in `one_machine`, `if not (machine.get("pool") or machine.get("yielded")) or shares.queued() <= 0:` -> `if
  shares.queued() <= 0:` (m1, whose set-up fails, is rented again). Or in `tend`, drop
  `off_zone_mirror(folder, host)` (the set-up script runs with apt still on Scaleway's zone mirror, Buy 91); or in
  APT_MIRROR, `archive.ubuntu.com#g` -> `security.ubuntu.com#g`.
- in batch.py `claim_from`, `capacity.next_offer(remaining, run.machines + pending, kind)` ->
  `capacity.next_offer(remaining, run.machines, kind)` (the rented world's three machines in one zone).
- in batch.py `claim_rounds`, `while machine is None and still_wanted(run, wanted):` -> `while machine is None and
  still_wanted(run, wanted) and rounds < 1:` (one more round only: the stock row "keeps asking").
- in batch.py `still_wanted`, `return wanted is None or bool(wanted())` -> `return True` (the stock row "work gone").
- in batch.py `still_wanted`, drop `or time.time() >= run.deadline` (the stock row "deadline passed").
- in `this_pc_waited`, drop `run.deadline += waited` (the share is never run); or `return waited >=
  THIS_PC_WAIT_SECONDS` -> `return False` (the slot gives up); or in `on_machines`, drop `raise run.cloud_only` (a
  claim refused as too big: the spread returns, nothing raised); or in `tend`, drop the `this_pc_set_up(...)` call
  (this PC's set-up past the deadline: the share is never taken). The this-PC table's rows.
- in `work_slot`, `if shares.again(share):` -> `if False:` (a killed share is a gap at once); or in `raise_for`, drop
  `or killed` (a step killed inside is a plain failure). The rented world's "killed-*" rows.
- in `work_slot`, `except (MemoryKilled, CardLost)` -> `except MemoryKilled`; or in `raise_for`, `if returncode and
  card_lost:` -> `if False:`. The rented world's "card-*" rows.
- in `work_slot`, drop the `provider.cloud.wanted_elsewhere()` check (m1 runs all three); or in `one_machine`, drop
  `or machine.get("yielded")` (two and three stay waiting). The this-PC table's shared-claim row.
"""
import pathlib
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402


@pytest.fixture(autouse=True)
def cleared(monkeypatch):
    """The parts kind cleans up (park.CLEANUPS), so a claim first looks for a parked machine, which asks for a cleared
    run; renting is faked here and the sandbox has none parked. No warm pool, no stop."""
    monkeypatch.setattr(batch.compute, "require_cleared", lambda what, store=None: {"node": "test"})
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)  # preflight.declare_deadline keeps nothing outside one
    batch.STOPPING.clear()
    yield
    batch.STOPPING.clear()


def offer(machine_class, zone, stock=0):
    return provider.Offer(0.01, stock, f"{machine_class}-type", zone, 0.01, machine_class, 0, "available")


def a_machine(run, name, machine_class, zone):
    """A rented machine's record, as batch.rent and batch.boot leave it."""
    return {"folder": run.folder / name, "host": "host", "class": machine_class, "type": "L4", "zone": zone,
            "created": time.time(), "ready": time.time(), "deleted": None}


def until(condition, seconds=5.0):
    """Whether `condition()` came true within `seconds`."""
    give_up = time.time() + seconds
    while not condition() and time.time() < give_up:
        time.sleep(0.01)
    return condition()


# The rented world's shares: what each one's command exits with on its first tries (returncode, killed, card_lost),
# every later try succeeding, and how it ends with how many tries. m2 breaks under its first share, "one".
FAULTS = {
    "one": ([], "gap", 1),  # m2 broke under it: a gap, never handed on
    "two": ([], "done", 1),
    "three": ([], "done", 1),
    "plain": ([(1, False, False)], "gap", 1),  # its own command failed: a gap, not tried again
    "killed-exit": ([(spread.KILLED, False, False)], "done", 2),  # killed by signal 9: run again once
    "killed-step": ([(1, True, False)], "done", 2),  # a step inside it killed: the same
    "killed-twice": ([(1, True, False)] * 2, "gap", 2),  # killed again: a gap
    "card-once": ([(1, False, True)], "done", 2),  # its card would not open: run again once
    "card-twice": ([(1, False, True)] * 2, "gap", 2),
    "late": ([], "done", 1),  # put on the open queue after it ran dry
}

# This PC's claims, one on_machines a row: the backend, the claim's behaviour (`wait_first`: the first claim waits
# out the run's deadline behind the run's own jobs and gets nothing; `here`: the machine is this PC's own; `turns`:
# a claim on its shared machine; `refuse`: too big for this PC's card), the set-up's seconds, the run's deadline
# from now, and what ran (machine, share), how many claims were made and whether the deadline moved on.
THIS_PC = [
    SimpleNamespace(row="a claim that waited out the deadline on this PC asks again and the deadline moves on",
                    backend="local", kind="blender", shares=["one"], count=1, setup=0.0, deadline=0.3,
                    wait_first=True, done=[("m1", "one")], claims=2, moved=True),
    SimpleNamespace(row="a rented backend's claim that waited gives up and nothing moves",
                    backend="scaleway", kind="blender", shares=["two"], count=1, setup=0.0, deadline=0.3,
                    wait_first=True, done=[], claims=1, moved=False),
    # 2026-11-10, sound@habitat: 10.2 min of MOSS set-up past a 9-min limit, the take never asked
    SimpleNamespace(row="a set-up on this PC's machine past the deadline is not the work's time",
                    backend="scaleway", kind="moss-sound", shares=["three"], count=1, setup=0.4, deadline=0.2,
                    here=True, done=[("m1", "three")], claims=1, moved=True),
    SimpleNamespace(row="a rented machine's set-up past the deadline stays in its minutes: the share is a gap",
                    backend="scaleway", kind="moss-sound", shares=["three"], count=1, setup=0.4, deadline=0.2,
                    here=False, done=[], claims=1, moved=False),
    # round 46, 2026-11-02: meshparts' 24 GB claim died in its thread and the tool ended "no card could be rented"
    SimpleNamespace(row="a claim this PC refuses as too big ends the spread on the refusal",
                    backend="scaleway", kind="meshparts", shares=["one", "two"], count=2, setup=0.0, deadline=60,
                    refuse="a meshparts job needs about 24 GB of card and this PC has 16 GB", raised="24 GB",
                    done=[], claims=2),
    # env1, 2026-10-29: straight-masks@lab waited 20 min while base's bake kept taking all three turns
    SimpleNamespace(row="a shared claim gives way to one that waits for the machine alone, each share once",
                    backend="local", kind="blender", shares=["one", "two", "three"], count=1, setup=0.0, deadline=60,
                    turns=True, elsewhere=[False, True], done=[("m1", "one"), ("m2", "two"), ("m2", "three")],
                    claims=2),
]

# Stock rounds, one batch.claim a row: the reads of the backend's offers after which stock comes up, the caller's
# `wanted` answers, the deadline from now, a stop signal; whether a machine came, how many reads were made and the
# classes the first read asked for.
STOCK = [
    SimpleNamespace(row="keeps asking until stock comes up", rounds=3, wanted=None, deadline=60, stopping=False,
                    classes=("gpu-24gb", "gpu-80gb"), machine=True, reads=3, first=["gpu-24gb", "gpu-80gb"]),
    SimpleNamespace(row="stops asking when its work is gone", rounds=99, wanted=[True, True, False], deadline=60,
                    stopping=False, classes=("gpu-24gb",), machine=False, reads=1, first=["gpu-24gb"]),
    SimpleNamespace(row="stops asking once its deadline passed", rounds=99, wanted=None, deadline=-1, stopping=False,
                    classes=("gpu-24gb",), machine=False, reads=0, first=None),
    SimpleNamespace(row="stops asking on a stop signal", rounds=99, wanted=None, deadline=60, stopping=True,
                    classes=("gpu-24gb",), machine=False, reads=0, first=None),
]

# A machine's slots: the kind, its class, the runner's `at_once`, and the card each slot runs on.
SLOTS = [
    ("pixal", "gpu-80gb", None, [0] * 10),  # three runs per 24 GB: ten on 80 GB
    ("judge", "gpu-80gb-x2", None, [0, 1]),
    ("blender", "cpu-32c-128gb", None, [None]),
    (None, "cpu-32c-128gb", 4, [None] * 4),
]


def test_spread_runs_every_share_once(monkeypatch, tmp_path):
    sent, reads, stock, real_claim = [], [], {"rounds": 0, "pause": 0.0}, batch.claim

    def rent(run, account, chosen, number, disk_gb):
        time.sleep(stock["pause"])  # claims side by side overlap while they rent
        if len(reads) < stock["rounds"]:
            return None
        return a_machine(run, f"m{number}", chosen.machine_class, chosen.zone)

    def read(classes):
        reads.append(sorted(classes))
        return [offer(machine_class, zone) for machine_class in classes for zone in ("zone-a", "zone-b")]
    monkeypatch.setattr(batch, "rent", rent)
    monkeypatch.setattr(batch, "boot", lambda machine: machine["host"])
    monkeypatch.setattr(batch.cloud, "offers", read)
    monkeypatch.setattr(batch, "STOCK_RETRY_MINUTES", 0)
    monkeypatch.setattr(batch, "arm_self_delete", lambda *arguments: None)
    monkeypatch.setattr(batch, "remote", lambda folder, host, command, **keywords: sent.append((folder.name, command)))
    monkeypatch.setattr(batch, "delete_machine", lambda machine: machine.update(deleted=time.time()))
    monkeypatch.setattr(batch, "say", lambda line: None)
    monkeypatch.setattr(pictures, "keep_beating", lambda folder, host, stop: None)

    # The rented world: three machines claimed side by side through batch.claim; m1 fails its set-up, m2 breaks
    # under its first share, m3 (set up a moment later) works the rest from an open queue.
    stock["pause"] = 0.1
    run = pictures.Run(tmp_path / "rented", time.time() + 60)
    tries, events, mirrored = {}, [], []

    def prepare(machine):
        mirrored.append((machine["folder"].name, spread.APT_MIRROR) in sent)  # apt moved before the set-up
        if machine["folder"].name == "m1":
            raise RuntimeError("a package mirror was mid-sync")
        if machine["folder"].name == "m3":
            time.sleep(0.2)

    def do(machine, share, card):
        tries[share] = tries.get(share, 0) + 1
        events.append((machine["folder"].name, share))
        if machine["folder"].name == "m2":
            raise ConnectionError("lost")
        exits = FAULTS[share][0]
        if tries[share] <= len(exits):
            returncode, killed, card_lost = exits[tries[share] - 1]
            spread.raise_for(returncode, f"job {share}", killed=killed, card_lost=card_lost)
        time.sleep(0.05)
    first = [share for share in FAULTS if share != "late"]
    shares = spread.Shares(first, open_queue=True, idle=5)
    offers = [offer("gpu-24gb", zone) for zone in ("zone-a", "zone-b", "zone-c")]
    spreading = threading.Thread(target=spread.on_machines, args=(run, None, offers, 3, "parts", shares, prepare, do))
    spreading.start()
    assert until(lambda: len(shares.done) + len(shares.failed) == len(first) and shares.queued() == -1), \
        ("the open queue's last slot never came to wait for work", shares.done, shares.failed, shares.queued())
    shares.put("late")
    assert until(lambda: "late" in shares.done), shares.waiting
    began = time.time()
    shares.close()
    spreading.join(3)
    assert not spreading.is_alive() and time.time() - began < 3, "a closed queue's slot waited out its idle time"
    assert [share for name, share in events if name == "m2"] == ["one"], events  # the broken machine took no more
    ended = {share: ("done" if share in shares.done else "gap" if share in shares.failed else "waiting", tries[share])
             for share in tries}
    assert ended == {share: (end, count) for share, (_, end, count) in FAULTS.items()}, ended
    assert sorted(shares.done + shares.failed) == sorted(set(shares.done + shares.failed)) and not shares.waiting
    # no machine rented in place of the one whose set-up failed, each deleted, one a zone
    assert sorted(machine["folder"].name for machine in run.machines) == ["m1", "m2", "m3"], run.machines
    assert all(machine["deleted"] for machine in run.machines)
    assert sorted(machine["zone"] for machine in run.machines) == ["zone-a", "zone-b", "zone-c"], run.machines
    # each machine's apt was moved off Scaleway's zone mirror before its set-up ran, security.ubuntu.com left alone
    assert mirrored == [True] * 3 and sorted(sent) == [(f"m{n}", spread.APT_MIRROR) for n in (1, 2, 3)], sent
    apt = tmp_path / "etc/apt"
    (apt / "sources.list.d").mkdir(parents=True)
    classic = "deb http://fr-par-2.clouds.archive.ubuntu.com/ubuntu noble main\n" \
              "deb http://security.ubuntu.com/ubuntu noble-security main\n"
    deb822 = "Types: deb\nURIs: https://nl-ams-2.clouds.archive.ubuntu.com/ubuntu/\nSuites: noble\n\n" \
             "Types: deb\nURIs: http://security.ubuntu.com/ubuntu/\nSuites: noble-security\n"
    (apt / "sources.list").write_text(classic)
    (apt / "sources.list.d/ubuntu.sources").write_text(deb822)
    subprocess.run(["bash", "-c", sent[0][1].replace("/etc/apt", str(apt))], check=True)
    assert (apt / "sources.list").read_text() == classic.replace("fr-par-2.clouds.archive", "archive")
    assert (apt / "sources.list.d/ubuntu.sources").read_text() == deb822.replace("nl-ams-2.clouds.archive", "archive")
    assert (apt / "apt.conf.d/80score-retries").read_text() == 'Acquire::Retries "3";\nAcquire::http::Timeout "30";\n'

    # This PC's claims, one spread a row.
    monkeypatch.setattr(spread, "THIS_PC_WAIT_SECONDS", 0.2)
    monkeypatch.setattr(spread.provider.cloud, "let_go_turn", lambda machine_id: None, raising=False)
    for case in THIS_PC:
        calls, ran, numbers, raised = [], [], iter(range(1, 100)), None
        elsewhere = iter(getattr(case, "elsewhere", []))

        def claim(run, account, found, number, kind, disk_gb, wanted=None, case=case, calls=calls, numbers=numbers):
            calls.append(time.time())
            if getattr(case, "refuse", None):
                raise batch.compute.CloudOnly(case.refuse)
            if getattr(case, "wait_first", False) and len(calls) == 1:  # busy with the run's jobs past the deadline
                time.sleep(max(0.0, run.deadline - time.time()) + 0.05)
                return None
            machine = {**a_machine(run, f"m{next(numbers)}", "gpu-24gb", "zone-a"),
                       "here": getattr(case, "here", False)}
            if getattr(case, "turns", False):
                machine.update(turns=1, id="this-pc")
            run.machines.append(machine)
            return machine
        monkeypatch.setattr(batch, "claim", claim)
        monkeypatch.setattr(spread.provider.cloud, "NAME", case.backend)
        monkeypatch.setattr(spread.provider.cloud, "wanted_elsewhere",
                            lambda elsewhere=elsewhere: next(elsewhere, False), raising=False)
        run = pictures.Run(tmp_path / case.row.replace(" ", "-").replace("'", ""), time.time() + case.deadline)
        before = run.deadline
        shares = spread.Shares(case.shares, deadline=run.deadline)
        try:
            spread.on_machines(run, None, [], case.count, case.kind, shares,
                               lambda machine, case=case: time.sleep(case.setup),
                               lambda machine, share, card, ran=ran: ran.append((machine["folder"].name, share)))
        except batch.compute.CloudOnly as refusal:
            raised = str(refusal)
        assert ran == case.done and len(calls) == case.claims, (case.row, ran, calls)
        assert (raised is not None and getattr(case, "raised", "") in raised) == hasattr(case, "raised"), \
            (case.row, raised)
        if getattr(case, "moved", None) is True:
            assert min(run.deadline, shares.deadline) > max(before, calls[-1]), (case.row, run.deadline, before)
        if getattr(case, "moved", None) is False:
            assert run.deadline == before, (case.row, run.deadline, before)
    monkeypatch.setattr(batch, "claim", real_claim)  # the stock rows ask the real claim

    # Stock rounds, one claim a row: renting is out of stock until the offers were read `rounds` times.
    stock.update(pause=0.0)
    for case in STOCK:
        batch.STOPPING.clear()
        reads.clear()
        stock["rounds"] = case.rounds
        run = pictures.Run(tmp_path / case.row.replace(" ", "-").replace("'", ""), time.time() + case.deadline)
        if case.stopping:
            batch.STOPPING.set()
        answers = list(case.wanted) if case.wanted else None
        found = [offer(machine_class, zone) for machine_class, zone in zip(case.classes, ("zone-a", "zone-b"))]
        machine = batch.claim(run, "account", found, 1, "parts", wanted=answers and (lambda: answers.pop(0)))
        assert (machine is not None) == case.machine and len(reads) == case.reads, (case.row, machine, reads)
        assert (reads[0] if reads else None) == case.first, (case.row, reads)  # every class the job fits, read again

    for kind, machine_class, at_once, cards in SLOTS:
        assert spread.slots(kind, {"class": machine_class}, at_once=at_once) == cards, (kind, machine_class)
