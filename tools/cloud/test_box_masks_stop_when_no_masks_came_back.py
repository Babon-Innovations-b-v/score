"""box_masks_cloud.py's invariants: a set-up or a job that failed (a gap in spread) stops `mask` with its folder,
never a return with no masks written (crops-concept read a missing instances.json, 2026-10-24), and the machine's
ledger line is written either way; and every set-up script a card runner runs there is sent with it, to the folder
it is run from (crops-concept, try 4 of 2026-10-25: the runners moved to tools/cloud in 80fab258 and their set-ups
still sent only tools/props, so bash found no box_masks_setup.sh; closeups and scene the same).

Break that turns it red: in `mask` drop the `if shares.failed or shares.waiting` stop; or in box_masks_cloud's
`set_up` leave `box_masks_setup.sh` out of what it copies.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import box_masks_cloud  # noqa: E402
import ledger  # noqa: E402
import spread  # noqa: E402


@pytest.fixture
def fake_cloud(tmp_path, monkeypatch):
    """Every cloud call of `mask` faked; returns (the ledger lines written, a switch for whether set-up works)."""
    recorded, works = [], {"set_up": True}
    monkeypatch.setattr(batch, "BATCHES", tmp_path / "batches")
    monkeypatch.setattr(box_masks_cloud.cloud, "account", lambda: "account")
    monkeypatch.setattr(box_masks_cloud.cloud, "allow_key", lambda *args: None)
    monkeypatch.setattr(batch, "sweep", lambda account: None)
    monkeypatch.setattr(batch, "ssh_key", lambda: "ssh-ed25519 test")
    monkeypatch.setattr(batch, "stop_on_signals", lambda: None)
    monkeypatch.setattr(batch, "delete_machine", lambda machine: None)
    monkeypatch.setattr(box_masks_cloud, "price", lambda jobs, account: ([], 30))
    monkeypatch.setattr(ledger, "machines_record", lambda machines, attempts, started: {"euros": 0.0})
    monkeypatch.setattr(ledger, "record", recorded.append)

    def on_machines(run, account, found, count, kind, shares, prepare, do):
        run.machines.append({"folder": run.folder})
        if works["set_up"]:
            share = shares.take()
            do(run.machines[0], share, 0)
            shares.finished(share)
    monkeypatch.setattr(spread, "on_machines", on_machines)
    monkeypatch.setattr(box_masks_cloud, "run_jobs", lambda machine, share, card, jobs, out: out.write_text("[]"))
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps([{"picture": "concept.png", "rows": []}]))
    return jobs, recorded, works


def test_a_failed_set_up_stops_the_masks_and_still_writes_the_ledger(fake_cloud, tmp_path):
    jobs, recorded, works = fake_cloud
    works["set_up"] = False
    out = tmp_path / "instances.json"
    with pytest.raises(SystemExit, match="were not made"):
        box_masks_cloud.mask(jobs, out)
    assert not out.exists() and len(recorded) == 1


def test_masks_made_return_the_ledger_entry(fake_cloud, tmp_path):
    jobs, recorded, _ = fake_cloud
    out = tmp_path / "instances.json"
    entry = box_masks_cloud.mask(jobs, out)
    assert out.read_text() == "[]" and entry["pictures"] == 1 and recorded == [entry]


def test_every_set_up_script_a_runner_runs_is_sent_with_it(tmp_path, monkeypatch):
    import closeups_cloud
    import scene
    sent, ran = [], []
    monkeypatch.setattr(batch, "remote", lambda folder, host, command, **keywords: ran.append(command))
    monkeypatch.setattr(batch, "copy", lambda folder, sources, destination, *extra:
                        sent.extend((source, destination) for source in sources))
    runs = {"box masks": lambda: box_masks_cloud.set_up({"folder": tmp_path, "host": "card"}),
            "closeups": lambda: closeups_cloud.set_up({"folder": tmp_path, "host": "card"}, tmp_path / "splats.ply"),
            "scene": lambda: scene.set_up(tmp_path, "card", {"room": "toy"})}
    for name, run in runs.items():
        sent.clear()
        ran.clear()
        run()
        scripts = [word for command in ran for word in command.split() if word.endswith(".sh")]
        assert scripts, name
        for script in scripts:
            there = pathlib.PurePosixPath(script)
            assert any(pathlib.Path(source).name == there.name and pathlib.Path(source).is_file()
                       and destination.endswith(f"{there.parent}/") for source, destination in sent), (name, script)
