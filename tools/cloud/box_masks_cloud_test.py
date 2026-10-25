"""Checks for SAM 3's masks on a rented card, renting nothing: a set-up or a job that failed (a gap in spread) stops
`mask` with its folder, never a return with no masks written (crops-concept read a missing instances.json,
2026-10-24).

Run: .venv/bin/python tools/cloud/box_masks_cloud_test.py   (make tests runs it)
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import box_masks_cloud  # noqa: E402
import ledger  # noqa: E402
import spread  # noqa: E402


def faked(folder, set_up_works):
    """Every cloud call of `mask` faked; spread's machine sets up (and writes the masks) only when `set_up_works`."""
    recorded = []
    batch.BATCHES = pathlib.Path(folder) / "batches"
    box_masks_cloud.cloud.account = lambda: "account"
    box_masks_cloud.cloud.allow_key = lambda *args: None
    batch.sweep = lambda account: None
    batch.ssh_key = lambda: "ssh-ed25519 test"
    batch.stop_on_signals = lambda: None
    batch.delete_machine = lambda machine: None
    box_masks_cloud.price = lambda jobs, account: ([], 30)
    ledger.machines_record = lambda machines, attempts, started: {"euros": 0.0}
    ledger.record = recorded.append

    def on_machines(run, account, found, count, kind, shares, prepare, do):
        machine = {"folder": run.folder}
        run.machines.append(machine)
        if set_up_works:
            share = shares.take()
            do(machine, share, 0)
            shares.finished(share)

    spread.on_machines = on_machines
    box_masks_cloud.run_jobs = lambda machine, share, card, jobs, out: out.write_text("[]")
    return recorded


def jobs_file(folder):
    path = pathlib.Path(folder) / "jobs.json"
    path.write_text(json.dumps([{"picture": "concept.png", "rows": []}]))
    return path


def test_a_failed_set_up_stops_the_masks():
    with tempfile.TemporaryDirectory() as folder:
        recorded = faked(folder, set_up_works=False)
        out = pathlib.Path(folder) / "instances.json"
        try:
            box_masks_cloud.mask(jobs_file(folder), out)
        except SystemExit as stopped:
            assert "were not made" in str(stopped), stopped
        else:
            raise AssertionError("mask returned with no masks written")
        assert not out.exists() and len(recorded) == 1  # the machine's ledger line is still written


def test_masks_made_return_the_ledger_entry():
    with tempfile.TemporaryDirectory() as folder:
        faked(folder, set_up_works=True)
        out = pathlib.Path(folder) / "instances.json"
        entry = box_masks_cloud.mask(jobs_file(folder), out)
        assert out.read_text() == "[]" and entry["pictures"] == 1


def sent_and_run(set_up):
    """What a runner's set_up copies to the card ([(source, destination)]) and the scripts it runs there."""
    sent, ran = [], []
    real = batch.remote, batch.copy
    batch.remote = lambda folder, host, command, **keywords: ran.append(command)
    batch.copy = lambda folder, sources, destination, *extra: sent.extend((source, destination) for source in sources)
    try:
        set_up()
    finally:
        batch.remote, batch.copy = real
    return sent, [word for command in ran for word in command.split() if word.endswith(".sh")]


def test_every_set_up_script_a_runner_runs_is_sent_with_it():
    """crops-concept, try 4 of 2026-10-25: the runners moved to tools/cloud (80fab258) and their set-ups still sent
    only tools/props, so bash found no box_masks_setup.sh and every SAM 3 set-up failed; closeups and scene the same."""
    import closeups_cloud
    import scene
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        runs = {"box masks": lambda: box_masks_cloud.set_up({"folder": folder, "host": "card"}),
                "closeups": lambda: closeups_cloud.set_up({"folder": folder, "host": "card"}, folder / "splats.ply"),
                "scene": lambda: scene.set_up(folder, "card", {"room": "toy"})}
        for name, run in runs.items():
            sent, scripts = sent_and_run(run)
            assert scripts, name
            for script in scripts:
                there = pathlib.PurePosixPath(script)
                assert any(pathlib.Path(source).name == there.name and pathlib.Path(source).is_file()
                           and destination.endswith(f"{there.parent}/") for source, destination in sent), (name, script)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("box_masks_cloud_test: ok")
