"""Interface checks for the runners' shared steps, without renting anything: each runner's estimate (what it says,
what it returns, and its refusal past the owner's limits), and that a machine a runner tends itself is armed to delete
itself, hears the heartbeat and is deleted whatever happens.

Plain python: python3 tools/props/cloud/runners_test.py
"""
import json
import os
import pathlib
import sys
import tempfile
import time

_SANDBOX = pathlib.Path(tempfile.mkdtemp(prefix="runners-test-"))
# paths.py reads these when it is imported, so they come first.
os.environ["PROPS_HOME"] = str(_SANDBOX)
os.environ["PROPS_WORK"] = str(_SANDBOX / "work")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import blender_cloud  # noqa: E402
import box_masks_cloud  # noqa: E402
import characters  # noqa: E402
import closeups_cloud  # noqa: E402
import delight  # noqa: E402
import finish_masks  # noqa: E402
import infinigen  # noqa: E402
import judge  # noqa: E402
import library_bake  # noqa: E402
import meshparts  # noqa: E402
import parts  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
import scene  # noqa: E402
import segment  # noqa: E402
import similar  # noqa: E402
import unirig  # noqa: E402

OFFERS = [provider.Offer(0.02, 0, "small", "zone-a", 0.02, "gpu-24gb", 0, "available"),
          provider.Offer(0.05, 1, "big", "zone-b", 0.05, "gpu-80gb", 0, "scarce"),
          provider.Offer(0.01, 2, "short", "zone-c", 0.01, "cpu-32c-128gb", 0, "shortage")]


def infinigen_jobs():
    jobs = []
    for name, minutes in (("a", 30), ("b", 90)):
        job = _SANDBOX / "infinigen" / name
        job.mkdir(parents=True, exist_ok=True)
        (job / "spec.json").write_text(json.dumps({"minutes": minutes}))
        jobs.append(job)
    return jobs


# Each runner's estimate on a fixed list, and what it said and returned on the code before the shared estimate.
ESTIMATES = {
    "blender_cloud": (lambda: blender_cloud.price([{"minutes": 5}, {"minutes": 20}], "acct", ["gpu-24gb"]),
                      "2 Blender jobs on 2 machines: about 28 min, €2.80; €100.00 spent this month", (2, 2, 240.0)),
    "box_masks_cloud": (lambda: box_masks_cloud.price([{}] * 9, "acct"),
                        "9 pictures on 1 card: about 13 min, €0.65; €100.00 spent this month", (3, 240.0)),
    "characters": (lambda: characters.price(["p1", "p2", "p3"], "acct", None),
                   "3 people on 3 machines: about 100 min, €15.00; €100.00 spent this month", (3, 3, 240.0)),
    "closeups_cloud": (lambda: closeups_cloud.price(40, "acct", 20),
                       "40 close-ups on 1 card: about 24 min, €1.20; €100.00 spent this month", (3, 1, 240.0)),
    "delight": (lambda: delight.price(30, "acct"),
                "30 unlit copies on 2 cards: about 16 min, €1.60; €100.00 spent this month", (3, 2, 240.0)),
    "finish_masks": (lambda: finish_masks.price([[]] * 7, "acct", 2),
                     "7 shares of pictures on 2 machines: about 26 min, €2.60; €100.00 spent this month",
                     (3, 2, 240.0)),
    "infinigen": (lambda: infinigen.price(infinigen_jobs(), "cpu-32c-128gb", "acct", False, 4),
                  "2 Infinigen jobs on 1 cpu-32c-128gb machine: about 110 min, €5.50; €100.00 spent this month",
                  (2, 1, 240.0)),
    "judge": (lambda: judge.price([{}] * 300, "acct", 1),
              "300 questions on 1 card: about 42 min, €2.10; €100.00 spent this month", (3, 1, 240.0)),
    "library_bake": (lambda: library_bake.price([{"materials": [1] * 10}, {"chunky": [1] * 4}], "acct", False,
                                                ["gpu-24gb"]),
                     "2 library jobs on 1 machine: about 17 min, €0.85; €100.00 spent this month", (3, 1, 240.0)),
    "meshparts": (lambda: meshparts.price([["a"]] * 4, "acct", False),
                  "4 shares of takes on 4 machines: about 33 min, €6.60; €100.00 spent this month", (3, 4, 240.0)),
    "parts": (lambda: parts.price(12, "acct"),
              "12 PartCrafter runs on 2 cards: about 32 min, €3.20; €100.00 spent this month", (3, 2, 240.0)),
    "pictures": (lambda: pictures.price([{}] * 50, 2, "acct", "klein"),
                 "50 pictures on 2 machines: about 12 min, €1.20; €100.00 spent this month", (3, 240.0)),
    "segment": (lambda: segment.price([[]] * 5, "acct"),
                "5 shares of pictures on 2 machines: about 22 min, €2.20; €100.00 spent this month", (3, 2, 240.0)),
    "similar": (lambda: similar.price({"a": ["x", "y"]} | {f"p{n}": ["x", "y"] for n in range(99)}, "acct"),
                "100 pairs on one machine: about 10 min, €0.50; €100.00 spent this month", (3, 240.0)),
    "unirig": (lambda: unirig.price(9, "acct"),
               "9 models on 3 machines: about 27 min, €4.05; €100.00 spent this month", (3, 3, 240.0)),
}


class Stubbed:
    """batch's offers, month spend and say stubbed for the duration: OFFERS, `spent` euros, the lines kept."""

    def __init__(self, spent=100.0):
        self.spent, self.said = spent, []

    def __enter__(self):
        self.kept = batch.offers, batch.month_spent, batch.say
        batch.offers = lambda classes: list(OFFERS)
        batch.month_spent = lambda account: self.spent
        batch.say = self.said.append
        return self

    def __exit__(self, *_):
        batch.offers, batch.month_spent, batch.say = self.kept


def shape(returned):
    """A runner's estimate as compared: the number of offers, then the rest as returned (minutes rounded)."""
    found, *rest = returned
    return (len(found), *[round(value, 3) if isinstance(value, float) else value for value in rest])


def test_each_runner_says_and_returns_its_estimate():
    for name, (estimate, said, returned) in ESTIMATES.items():
        with Stubbed() as stubbed:
            got = shape(estimate())
        assert stubbed.said == [said], (name, stubbed.said)
        assert got == returned, (name, got)


def test_each_runner_refuses_past_the_month_s_ceiling():
    for name, (estimate, _, _) in ESTIMATES.items():
        with Stubbed(spent=batch.ledger.MONTH_EUROS) as stubbed:
            try:
                estimate()
            except SystemExit as refused:
                assert str(refused).startswith("refused: "), (name, refused)
            else:
                raise AssertionError(f"{name} was not refused at the month's ceiling")
        assert len(stubbed.said) == 1, (name, stubbed.said)


def test_the_minutes_allowed_follow_the_month_s_remainder():
    with Stubbed(spent=batch.ledger.MONTH_EUROS - 5):
        assert shape(unirig.price(9, "acct")) == (3, 3, round(5 / (0.05 * 3), 3))


class Tended:
    """batch's machine steps stubbed: what was armed, beaten and deleted, in order."""

    def __init__(self):
        self.done = []

    def __enter__(self):
        self.kept = batch.arm_self_delete, pictures.keep_beating, batch.delete_machine, batch.say
        batch.arm_self_delete = lambda folder, host, deadline: self.done.append(("armed", host, deadline))
        pictures.keep_beating = lambda folder, host, stop: self.done.append(("beating", host)) or stop.wait(5)
        batch.delete_machine = lambda machine: self.done.append(("deleted", machine["host"]))
        batch.say = lambda line: None
        return self

    def __exit__(self, *_):
        batch.arm_self_delete, pictures.keep_beating, batch.delete_machine, batch.say = self.kept


DEADLINE = time.time() + 3600


def machine_and_run():
    folder = pathlib.Path(tempfile.mkdtemp(prefix="machine-", dir=_SANDBOX))
    run = pictures.Run(folder, DEADLINE)
    run.started = time.time()
    return {"folder": folder, "host": "10.0.0.1", "created": 0.0, "class": "gpu-24gb", "type": "small",
            "zone": "zone-a"}, run


def armed_beaten_deleted(done):
    deadline = DEADLINE + batch.WATCHDOG_GRACE_MINUTES * 60
    return (done[0] == ("armed", "10.0.0.1", deadline) and ("beating", "10.0.0.1") in done
            and done[-1] == ("deleted", "10.0.0.1") and done.count(("deleted", "10.0.0.1")) == 1)


def test_a_scene_machine_is_armed_and_deleted_also_when_a_step_fails():
    machine, run = machine_and_run()
    kept = scene.set_up, scene.run_steps, batch.copy
    scene.set_up = lambda folder, host, plan: None
    scene.run_steps = lambda folder, host, plan: (_ for _ in ()).throw(RuntimeError("a step failed"))
    batch.copy = lambda *arguments: None
    try:
        with Tended() as tended:
            try:
                scene.work_on(run, machine, {"room": "lab"})
            except RuntimeError:
                pass
            else:
                raise AssertionError("the failed step was swallowed")
        assert armed_beaten_deleted(tended.done), tended.done
    finally:
        scene.set_up, scene.run_steps, batch.copy = kept


def test_a_held_character_machine_is_armed_and_deleted():
    machine, run = machine_and_run()
    kept = characters.set_up, characters.hold
    characters.set_up = lambda machine: None
    characters.hold = lambda run, host: None
    try:
        with Tended() as tended:
            characters.held(run, machine, [])
        assert armed_beaten_deleted(tended.done), tended.done
        assert (run.folder / "host").read_text() == "10.0.0.1"
    finally:
        characters.set_up, characters.hold = kept


def test_an_infinigen_machine_is_armed_and_deleted_with_the_jobs_codes():
    machine, run = machine_and_run()
    kept = infinigen.set_up, infinigen.run_jobs
    infinigen.set_up = lambda folder, host: None
    infinigen.run_jobs = lambda run, folder, host, jobs, at_once: {"a": 0}
    try:
        with Tended() as tended:
            assert infinigen.work_on(run, machine, [], False, 4) == {"a": 0}
        assert armed_beaten_deleted(tended.done), tended.done
    finally:
        infinigen.set_up, infinigen.run_jobs = kept


def test_a_served_blender_machine_runs_the_queue_and_is_deleted():
    machine, run = machine_and_run()
    queue = pathlib.Path(tempfile.mkdtemp(prefix="queue-", dir=_SANDBOX))
    (queue / "1.json").write_text(json.dumps({"script": "tools/blender/inside/x.py", "minutes": 1}))
    (queue / "close").write_text("")
    ran = []
    kept = blender_cloud.set_up, blender_cloud.run_job, batch.remote, batch.copy
    blender_cloud.set_up = lambda log_folder, host, jobs: ran.append(("set up", jobs))
    blender_cloud.run_job = lambda log_folder, host, number, job, card: ran.append((number, card)) or 1.5
    batch.remote = lambda *arguments, **keywords: ran.append("remote")
    batch.copy = lambda *arguments: ran.append("copy")
    try:
        with Tended() as tended:
            blender_cloud.serve(run, machine, queue, 1)
        assert armed_beaten_deleted(tended.done), tended.done
        assert ran == [("set up", []), "remote", "copy", (1, True)], ran
        assert (queue / "1.done").read_text() == "1.5" and (queue / "ready").read_text() == "gpu-24gb"
        assert machine["unit_seconds"] == [1.5]
    finally:
        blender_cloud.set_up, blender_cloud.run_job, batch.remote, batch.copy = kept


def test_the_spread_runner_s_machine_is_armed_and_deleted():
    import spread

    machine, run = machine_and_run()
    shares = spread.Shares([1, 2])
    worked = []
    with Tended() as tended:
        assert spread.tend(run, machine, "parts", shares, lambda machine: None,
                           lambda machine, share, card: worked.append(share)) is True
    assert armed_beaten_deleted(tended.done), tended.done
    assert sorted(worked) == [1, 2]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("runners_test: ok")
