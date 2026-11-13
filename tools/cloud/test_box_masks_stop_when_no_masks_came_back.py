"""box_masks_cloud.py's invariants: a set-up or a job that failed (a gap in spread) stops `mask` with its folder,
never a return with no masks written (crops-concept read a missing instances.json, 2026-10-24), and the machine's
ledger line is written either way; and every set-up script a card runner runs there is sent with it, to the folder
it is run from (crops-concept, try 4 of 2026-10-25: the runners moved to tools/cloud in 80fab258 and their set-ups
still sent only tools/props, so bash found no box_masks_setup.sh; closeups and scene the same).

One world: every cloud call faked, `mask` driven through its real set-up once with the set-up script failing and
once with it working, then the closeups and scene set-ups run on the same faked remote and copy; every script any of
them ran is checked against what was sent.

Break that turns it red: in `mask` drop the `if shares.failed or shares.waiting` stop; or in box_masks_cloud's
`set_up` leave `box_masks_setup.sh` out of what it copies.
"""
import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import box_masks_cloud  # noqa: E402
import closeups_cloud  # noqa: E402
import ledger  # noqa: E402
import scene  # noqa: E402
import spread  # noqa: E402


def test_box_masks_stop_when_no_masks_came_back(tmp_path, monkeypatch):
    recorded, sent, ran, world = [], [], [], {"set_up": True}

    def remote(folder, host, command, **keywords):
        ran.append(command)
        if not world["set_up"] and "box_masks_setup.sh" in command:
            raise subprocess.CalledProcessError(1, command)

    def on_machines(run, account, found, count, kind, shares, prepare, do):
        machine = {"folder": run.folder, "host": "card"}
        run.machines.append(machine)
        try:
            prepare(machine)
        except subprocess.CalledProcessError:
            return  # spread leaves the share waiting: a gap
        share = shares.take()
        do(machine, share, 0)
        shares.finished(share)

    monkeypatch.setattr(box_masks_cloud.cloud, "account", lambda: "account")
    monkeypatch.setattr(box_masks_cloud.cloud, "allow_key", lambda *args: None)
    monkeypatch.setattr(batch, "sweep", lambda account: None)
    monkeypatch.setattr(batch, "ssh_key", lambda: "ssh-ed25519 test")
    monkeypatch.setattr(batch, "stop_on_signals", lambda: None)
    monkeypatch.setattr(batch, "delete_machine", lambda machine: None)
    monkeypatch.setattr(batch, "remote", remote)
    monkeypatch.setattr(batch, "copy", lambda folder, sources, destination, *extra:
                        sent.extend((source, destination) for source in sources))
    monkeypatch.setattr(box_masks_cloud, "price", lambda jobs, account: ([], 30))
    monkeypatch.setattr(ledger, "machines_record", lambda machines, attempts, started: {"euros": 0.0})
    monkeypatch.setattr(ledger, "record", recorded.append)
    monkeypatch.setattr(spread, "on_machines", on_machines)
    monkeypatch.setattr(box_masks_cloud, "run_jobs", lambda machine, share, card, jobs, out: out.write_text("[]"))
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps([{"picture": "concept.png", "rows": []}]))

    # (set-up works, what `mask` must give): a failed set-up stops with no masks, a working one returns its entry
    scripts_ran = {}  # each run's (commands run, (source, destination) sent)
    for works, stops in ((False, True), (True, False)):
        world["set_up"] = works
        monkeypatch.setattr(batch, "BATCHES", tmp_path / f"batches-{works}")  # both runs fall in one second
        for seen in (recorded, sent, ran):
            seen.clear()
        out = tmp_path / f"instances-{works}.json"
        if stops:
            with pytest.raises(SystemExit, match="were not made"):
                box_masks_cloud.mask(jobs, out)
            assert not out.exists() and len(recorded) == 1, f"set-up works={works}"
        else:
            entry = box_masks_cloud.mask(jobs, out)
            assert out.read_text() == "[]" and entry["pictures"] == 1 and recorded == [entry], f"set-up works={works}"
        scripts_ran[f"box masks, set-up works={works}"] = (list(ran), list(sent))
    for name, run in {"closeups": lambda: closeups_cloud.set_up({"folder": tmp_path, "host": "card"},
                                                                 tmp_path / "splats.ply"),
                      "scene": lambda: scene.set_up(tmp_path, "card", {"room": "toy"})}.items():
        sent.clear()
        ran.clear()
        run()
        scripts_ran[name] = (list(ran), list(sent))

    for name, (commands, copied) in scripts_ran.items():
        scripts = [word for command in commands for word in command.split() if word.endswith(".sh")]
        assert scripts, name
        for script in scripts:
            there = pathlib.PurePosixPath(script)
            assert any(pathlib.Path(source).name == there.name and pathlib.Path(source).is_file()
                       and destination.endswith(f"{there.parent}/") for source, destination in copied), (name, script)
