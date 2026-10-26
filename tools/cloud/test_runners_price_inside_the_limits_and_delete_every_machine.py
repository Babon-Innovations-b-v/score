"""Invariant of the runners' shared steps (batch.priced and spread.tended/tend, as every runner calls them): each
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
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
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
import provider  # noqa: E402
import scene  # noqa: E402
import segment  # noqa: E402
import similar  # noqa: E402
import spread  # noqa: E402
import unirig  # noqa: E402


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
