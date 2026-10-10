"""Checks for parking a machine billed by the hour for the next run of its kind (park.py), without renting anything:
which machines are parked, how long, that the next run of the kind takes one and pays only what it adds, that the
--expire process deletes one nobody took and spares one that was taken, and that a sweep leaves a parked machine alone
until its time.

Run: .venv/bin/python tools/props/cloud/park_test.py   (make tests runs it)
"""
import os
import pathlib
import sys
import tempfile
import time

_SANDBOX = pathlib.Path(tempfile.mkdtemp(prefix="park-test-"))
# paths.py reads these when it is imported, so they come first.
os.environ["PROPS_HOME"] = str(_SANDBOX)
os.environ["PROPS_WORK"] = str(_SANDBOX / "work")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "park-test"
HOUR_PRICE = 1.2 / 60  # euros a minute of a machine billed by the hour


class Calls:
    """The cloud, ssh and process calls park.py makes, recorded instead of made."""

    def __init__(self):
        self.remote, self.retagged, self.deleted, self.armed = [], [], [], []

    def install(self):
        batch.remote = lambda folder, host, command, **_: self.remote.append(command)
        batch.arm_self_delete = lambda folder, host, deadline, quiet_minutes=0: self.armed.append(deadline)
        batch.start_watchdog = lambda server_id, zone, deadline, folder: os.getpid() + 10 ** 6
        cloud.retag = lambda server_id, zone, tags: self.retagged.append((server_id, tags))
        cloud.delete = lambda server_id, zone: self.deleted.append(server_id) or True
        park.subprocess.Popen = lambda *_, **__: type("Expirer", (), {"pid": os.getpid()})()


def machine(minutes_ago, unit_minutes=60, healthy=True, kind=KIND, server_id="m1"):
    folder = _SANDBOX / "runs" / server_id
    folder.mkdir(parents=True, exist_ok=True)
    return {"id": server_id, "zone": "zone-a", "type": "cpu-type", "class": "cpu-32c-128gb", "cards": 0,
            "price": HOUR_PRICE, "unit_minutes": unit_minutes, "created": time.time() - minutes_ago * 60,
            "host": "192.0.2.1", "kind": kind, "disk_gb": 60, "folder": folder, "deleted": None,
            "ready": time.time() - minutes_ago * 60 + 60, "healthy": healthy, "watchdog": os.getpid() + 10 ** 6}


def run_of(name):
    folder = _SANDBOX / "runs" / name
    folder.mkdir(parents=True, exist_ok=True)
    return pictures.Run(folder, time.time() + 3600)


OFFERS = [provider.Offer(HOUR_PRICE, 0, "cpu-type", "zone-a", HOUR_PRICE, "cpu-32c-128gb", 0, "available")]


def fresh():
    calls = Calls()
    calls.install()
    park.CLEANUPS[KIND] = lambda _machine: "rm -rf /root/lib/out"
    for path in park.PARKED.glob("*.json") if park.PARKED.exists() else ():
        path.unlink()
    return calls


def test_only_a_healthy_hourly_machine_of_a_cleaned_kind_with_time_left_is_parked():
    fresh()
    now = time.time()
    assert park.parkable(machine(20), now)
    assert not park.parkable(machine(20, unit_minutes=1), now)  # a card, billed by the minute
    assert not park.parkable(machine(20, healthy=False), now)
    assert not park.parkable(machine(20, kind="unregistered"), now)
    assert not park.parkable(machine(53), now)  # 2 min before it must go
    assert park.parkable(machine(70), now)  # in its second paid hour, 45 min left of it


def test_a_parked_machine_must_go_before_its_paid_hour_ends():
    started = 1000.0
    held = {"created": started, "unit_minutes": 60}
    assert park.leaves_at(held, started + 20 * 60) == started + 55 * 60
    assert park.leaves_at(held, started + 61 * 60) == started + 115 * 60


def test_the_next_run_of_the_kind_takes_it_and_pays_only_what_it_adds():
    calls = fresh()
    first = machine(20)
    batch.delete_machine(first)
    assert first["parked"] and not calls.deleted
    assert calls.remote == ["rm -rf /root/lib/out"]  # the run's own files gone first
    assert abs(ledger.machine_row(first)["euros"] - 60 * HOUR_PRICE) < 1e-9  # the first run pays its whole hour
    expirer_tags = calls.retagged[-1][1]
    assert expirer_tags[0] == f"pid={os.getpid()}" and expirer_tags[2].startswith("deadline=")

    other = run_of("other-kind")
    assert batch.park_taken(other, OFFERS, 1, "blender-other", 60) is None  # another kind never takes it
    assert batch.park_taken(other, OFFERS, 1, KIND, 200) is None  # nor a run wanting a bigger disk
    assert batch.park_taken(other, [OFFERS[0]._replace(zone="zone-b")], 1, KIND, 60) is None  # nor one elsewhere

    second = run_of("second")
    taken = batch.park_taken(second, OFFERS, 1, KIND, 60)
    assert taken is not None and taken["id"] == "m1" and taken in second.machines
    assert calls.retagged[-1][1][2] == f"deadline={second.deadline + batch.WATCHDOG_GRACE_MINUTES * 60:.0f}"
    assert batch.park_taken(run_of("third"), OFFERS, 1, KIND, 60) is None  # taken once
    taken["deleted"] = taken["adopted"] + 10 * 60  # ten minutes of work, inside the paid hour
    assert ledger.machine_row(taken)["euros"] == 0.0
    taken["deleted"] = taken["created"] + 70 * 60  # into a second hour: that hour is this run's
    assert abs(ledger.machine_row(taken)["euros"] - 60 * HOUR_PRICE) < 1e-9


def test_a_machine_not_worth_parking_is_deleted():
    calls = fresh()
    late = machine(54, server_id="m2")
    batch.delete_machine(late)
    assert calls.deleted == ["m2"] and not late.get("parked")
    stopping = machine(10, server_id="m3")
    batch.STOPPING.set()
    try:
        batch.delete_machine(stopping)
    finally:
        batch.STOPPING.clear()
    assert calls.deleted == ["m2", "m3"]


def test_expire_deletes_a_machine_nobody_took_and_spares_one_that_was_taken():
    calls = fresh()
    batch.delete_machine(machine(20, server_id="m4"))
    token = (park.PARKED / "m4.json").read_text().split('"token": "')[1].split('"')[0]
    park.expire("m4", "zone-a", "another-parking", time.time())
    assert calls.deleted == [] and (park.PARKED / "m4.json").exists()  # an older expirer of the same machine
    park.expire("m4", "zone-a", token, time.time())
    assert calls.deleted == ["m4"] and not (park.PARKED / "m4.json").exists()

    batch.delete_machine(machine(20, server_id="m5"))
    token = (park.PARKED / "m5.json").read_text().split('"token": "')[1].split('"')[0]
    assert batch.park_taken(run_of("taker"), OFFERS, 1, KIND, 60)["id"] == "m5"
    park.expire("m5", "zone-a", token, time.time())
    assert calls.deleted == ["m4"]


def test_a_parked_machine_that_does_not_answer_is_deleted_and_none_taken():
    calls = fresh()
    batch.delete_machine(machine(20, server_id="m6"))

    def no_answer(folder, host, command, **_):
        raise OSError("connection refused")
    batch.remote = no_answer
    assert batch.park_taken(run_of("unlucky"), OFFERS, 1, KIND, 60) is None
    assert calls.deleted == ["m6"]


def test_a_sweep_leaves_a_parked_machine_alone_until_its_time():
    until = time.time() + 30 * 60
    tags = batch.run_tags(os.getpid(), until)
    assert not batch.is_leftover(tags, time.time())
    assert batch.is_leftover(tags, until + 1)
    assert batch.is_leftover(batch.run_tags(999999999, until), time.time())  # its expirer gone


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"park: {len(tests)} checks pass")
