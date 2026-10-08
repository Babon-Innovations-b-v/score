"""Checks for spreading a batch over many machines, without renting anything: how many machines a batch gets, the
caps, the queue of shares, machines claimed side by side spreading over the zones, a failed machine's share going to
another.

Run: .venv/bin/python tools/props/cloud/spread_test.py   (make tests runs it)
"""
import os
import pathlib
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402


def offer(machine_class, zone, stock=0):
    return provider.Offer(0.01, stock, f"{machine_class}-type", zone, 0.01, machine_class, 0, "available")


def with_caps(value, check):
    kept = os.environ.get("SCORE_MAX_MACHINES")
    os.environ["SCORE_MAX_MACHINES"] = value
    try:
        check()
    finally:
        if kept is None:
            del os.environ["SCORE_MAX_MACHINES"]
        else:
            os.environ["SCORE_MAX_MACHINES"] = kept


def test_a_small_batch_keeps_one_machine():
    assert capacity.machines_for(1, 10, 8) == 1
    assert capacity.machines_for(30, 0.15, 8) == 1  # 30 pictures of 9 s: less work than one setup
    assert capacity.machines_for(0, 1, 8) == 1


def test_a_big_batch_ends_in_about_the_setup_and_one_job():
    # Ten Blender jobs of 15 min: one a machine, all done in about the setup and 15 min.
    assert capacity.machines_for(10, 15, 8) == 10
    # 60 close-ups of 82 s on 10 min setup: each machine draws about a setup's worth.
    count = capacity.machines_for(60, 82 / 60, 10)
    assert count == 9 and capacity.spread_minutes(60, 82 / 60, 10, count) < 2 * 10 + 82 / 60
    # A machine that runs ten at once needs a tenth as many.
    assert capacity.machines_for(100, 5, 5, slots=10) == 10
    # Never more machines than jobs to share.
    assert capacity.machines_for(3, 60, 8) == 3


def test_the_caps_follow_the_quotas_and_the_environment():
    assert capacity.max_machines("gpu-80gb") == provider.cloud.QUOTAS["gpu-80gb"]
    assert capacity.max_machines("cpu-32c-128gb") == capacity.OTHER_MACHINES
    assert capacity.machines_for(500, 60, 8) == capacity.RUN_MACHINES

    def capped():
        assert capacity.max_machines("gpu-80gb") == 2 and capacity.run_cap() == 3
        assert capacity.machines_for(500, 60, 8) == 3
        offers = [offer("gpu-80gb", "zone-a"), offer("gpu-48gb", "zone-b", stock=1)]
        two = [{"zone": "zone-a", "class": "gpu-80gb"}] * 2
        assert capacity.next_offer(offers, two, "judge").machine_class == "gpu-48gb"
        assert capacity.next_offer(offers, two + [{"zone": "zone-b", "class": "gpu-48gb"}], "judge") is None
    with_caps("gpu-80gb=2, all=3", capped)
    try:
        with_caps("gpu-80gb", capacity.caps)
    except SystemExit as refused:
        assert "SCORE_MAX_MACHINES" in str(refused)
    else:
        raise AssertionError("a cap without a number was taken")


def test_a_share_goes_back_once():
    shares = spread.Shares(["a", "b"])
    assert shares.take() == "a"
    assert shares.give_back("a") and shares.take() == "b" and shares.take() == "a"
    assert not shares.give_back("a") and shares.failed == ["a"] and shares.take() is None


def test_an_open_queue_waits_for_work_until_idle_or_closed():
    shares = spread.Shares(open_queue=True, idle=5)
    taken = []
    taker = threading.Thread(target=lambda: taken.append(shares.take()))
    taker.start()
    time.sleep(0.2)
    assert shares.queued() == -1  # one machine waiting
    shares.put("job")
    taker.join(2)
    assert taken == ["job"]
    began = time.time()
    closer = threading.Timer(0.2, shares.close)
    closer.start()
    assert shares.take() is None and time.time() - began < 3


def test_a_machine_runs_its_kinds_measured_runs_on_each_card():
    assert spread.slots("pixal", {"class": "gpu-80gb"}) == [0] * 10
    assert spread.slots("judge", {"class": "gpu-80gb-x2"}) == [0, 1]
    assert spread.slots("blender", {"class": "cpu-32c-128gb"}) == [None]
    assert spread.slots(None, {"class": "cpu-32c-128gb"}, at_once=4) == [None] * 4


def fake_machines(check):
    """Run `check` with claiming, arming, beating and deleting replaced by stand-ins that rent nothing."""
    kept = batch.claim, batch.arm_self_delete, batch.delete_machine, pictures.keep_beating
    numbers = iter(range(1, 100))

    def claim(run, account, found, number, kind, disk_gb):
        machine = {"folder": run.folder / f"m{next(numbers)}", "host": "host", "class": "gpu-24gb", "type": "L4",
                   "zone": "zone-a", "created": time.time(), "ready": time.time(), "deleted": None}
        run.machines.append(machine)
        return machine
    batch.claim, batch.arm_self_delete = claim, lambda *arguments: None
    batch.delete_machine = lambda machine: machine.update(deleted=time.time())
    pictures.keep_beating = lambda folder, host, stop: None
    try:
        with tempfile.TemporaryDirectory() as folder:
            check(pictures.Run(pathlib.Path(folder), time.time() + 60))
    finally:
        batch.claim, batch.arm_self_delete, batch.delete_machine, pictures.keep_beating = kept


def test_the_machines_share_the_work_and_a_failed_machine_hands_its_share_on():
    def check(run):
        done, broken = [], []

        def do(machine, share, card):
            if share == "bad":
                raise spread.JobFailed("its script failed")
            if machine["folder"].name == "m1" and not broken:
                broken.append(share)
                raise ConnectionError("lost")
            time.sleep(0.05)
            done.append((machine["folder"].name, share))
        shares = spread.Shares(["one", "two", "three", "four", "bad"])
        spread.on_machines(run, None, [], 3, "parts", shares, lambda machine: None, do)
        assert sorted(share for _, share in done) == ["four", "one", "three", "two"]
        assert "m1" not in {name for name, _ in done}  # the broken machine took nothing after
        assert shares.failed == ["bad"] and not shares.waiting
        assert all(machine["deleted"] for machine in run.machines) and len(run.machines) == 3
    fake_machines(check)


def test_a_machine_that_fails_its_setup_is_replaced():
    def check(run):
        done = []

        def prepare(machine):
            if machine["folder"].name == "m1":
                raise RuntimeError("a package mirror was mid-sync")
        shares = spread.Shares(["one", "two"])
        spread.on_machines(run, None, [], 1, "parts", shares, prepare,
                           lambda machine, share, card: done.append((machine["folder"].name, share)))
        assert done == [("m2", "one"), ("m2", "two")] and len(run.machines) == 2
    fake_machines(check)


def test_machines_claimed_side_by_side_spread_over_the_zones():
    kept_rent, kept_boot = batch.rent, batch.boot

    def rent(run, account, chosen, number, disk_gb):
        time.sleep(0.1)
        return {"zone": chosen.zone, "class": chosen.machine_class, "deleted": None}
    batch.rent, batch.boot = rent, lambda machine: "host"
    try:
        with tempfile.TemporaryDirectory() as folder:
            run = pictures.Run(pathlib.Path(folder), time.time() + 60)
            offers = [offer("gpu-24gb", zone) for zone in ("zone-a", "zone-b", "zone-c")]
            claims = [threading.Thread(target=batch.claim, args=(run, None, offers, number, "parts"))
                      for number in range(3)]
            for claim in claims:
                claim.start()
            for claim in claims:
                claim.join()
            assert sorted(machine["zone"] for machine in run.machines) == ["zone-a", "zone-b", "zone-c"]
    finally:
        batch.rent, batch.boot = kept_rent, kept_boot


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("spread_test: ok")
