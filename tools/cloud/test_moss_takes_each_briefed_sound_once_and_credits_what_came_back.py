"""moss_sound.py's invariants: a page's run asks one take of each sound briefed for that page (its first prompt, seed
1, its seconds or 8), and nothing for another page's sounds or a brief with no prompt (#29); after a run, the manifest
credits (model, code, weights, licence) exactly the takes that came back, and the picker's scores.json holds every
share's scores; a cluster share's jobs file, the one that goes up, holds exactly that share's jobs; MOSS goes to the
card a model at a time on this PC's machine only, and that measured need is one this PC's 16 GB card takes.

Break that turns it red: in `write_manifest` drop `if (out / job["file"]).exists()` (takes that never came back are
credited), or in `jobs_for` drop the `brief.get("page") == page` test (another page's sounds are paid for), or in
`here_only` drop `if machine.get("here")` (a rented card's takes made another way), or set THIS_PC_NEED's card_gb
past local.CARD_GB (this PC refuses the claim, as before), or in `make_share` drop the space after
`PYTHONUNBUFFERED=1` (the shell reads the Python as a variable and finds no moss_generate.py: every take of round 39
on this PC, 2026-10-31), or in `on_this_pc` return `[]` for its failed shares (a share that exited non-zero
passes as if it made nothing, and the sound row turns its takes into gaps instead of failing), or in `cluster_job`
run the image's `moss-run` again (its moss_generate.py path is the one before 2026-10-24: every cluster take exits 2).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import moss_sound  # noqa: E402


def test_a_page_takes_each_briefed_sound_once_and_credits_what_came_back(tmp_path, monkeypatch):
    import local
    sounds, out = tmp_path / "sounds.json", tmp_path / "out"
    sounds.write_text(json.dumps({"sounds": {
        "door": {"pick": {"page": "hub", "prompts": ["a heavy door", "a creaky door"], "seconds": 3}},
        "wind": {"pick": {"page": "hub", "prompts": ["wind over a roof"]}},
        "bird": {"pick": {"page": "camp", "prompts": ["a crow"]}},
        "hum": {"pick": {"page": "hub", "prompts": []}},
        "rain": {}}}))
    jobs = moss_sound.jobs_for("hub", sounds)
    assert jobs == [
        {"file": "door__p1__s1.wav", "sound": "door", "prompt": "a heavy door", "seconds": 3, "seed": 1},
        {"file": "wind__p1__s1.wav", "sound": "wind", "prompt": "wind over a roof", "seconds": 8, "seed": 1}]

    # The run on this PC's card: the generator exits 127 after the door's take and both shares' scores came back.
    commands, recorded = [], []

    def copy(folder, sources, destination, **options):
        if destination == f"{out}/":
            (out / "door__p1__s1.wav").write_bytes(b"RIFF")
            (out / "scores-0.json").write_text(json.dumps({"door__p1__s1.wav": 0.31}))
            (out / "scores-1.json").write_text(json.dumps({"wind__p1__s1.wav": 0.12}))

    def on_machines(run, account, found, count, kind, shares, prepare, do):
        share = shares.waiting.popleft()
        try:
            do({"folder": run.folder, "host": "172.17.0.2", "here": True}, share, 0)
        except moss_sound.spread.JobFailed:
            shares.failed_job(share)

    monkeypatch.setattr(moss_sound.cloud, "account", lambda: "account")
    monkeypatch.setattr(moss_sound.batch, "offers", lambda classes: [])
    monkeypatch.setattr(moss_sound.batch, "BATCHES", tmp_path)
    monkeypatch.setattr(moss_sound.batch, "copy", copy)
    monkeypatch.setattr(moss_sound.batch, "remote", lambda folder, host, command, **options: commands.append(command)
                        or __import__("subprocess").CompletedProcess(command, 127))
    monkeypatch.setattr(moss_sound.spread, "on_machines", on_machines)
    monkeypatch.setattr(moss_sound, "record", lambda run, machines, started, folder, made: recorded.append(made))
    failed = moss_sound.on_this_pc(jobs, out, 10)
    assert len(failed) == 1 and failed[0].startswith("share 0 ("), failed
    assert recorded == [[jobs[0]]]
    # the venv's Python runs moss_generate.py, MOSS a model at a time on this PC's card only
    words = commands[0].split()
    assert "MOSS_ONE_AT_A_TIME=1" in words and moss_sound.here_only({"host": "10.0.0.2"}) == ""
    assert "/root/venv/bin/python" in words and words[words.index("/root/venv/bin/python") + 1] == "moss_generate.py"
    assert moss_sound.THIS_PC_NEED["card_gb"] < local.TOO_BIG["moss-sound"]  # under all of MOSS on the card at once
    assert local.refusal("moss-sound", {"card_gb": moss_sound.THIS_PC_NEED["card_gb"]}) is None

    made = moss_sound.write_manifest(out, jobs)
    assert [take["file"] for take in made] == ["door__p1__s1.wav"]
    assert json.loads((out / "manifest.json").read_text()) == made
    assert made[0]["licence"] == "Apache-2.0" and made[0]["code"] and made[0]["weights"]
    moss_sound.join_scores(out)
    assert json.loads((out / "scores.json").read_text()) == {"door__p1__s1.wav": 0.31, "wind__p1__s1.wav": 0.12}

    # The same jobs as a cluster share: its jobs file goes up, the repo's run.sh (never the image's moss-run) runs.
    job = moss_sound.cluster_job(2, jobs, tmp_path / "jobs-2.json", out)
    sent = pathlib.Path(job["inputs"][0]["local"])
    assert json.loads(sent.read_text()) == jobs
    assert job["inputs"][0]["path"] == job["command"][2]
    assert moss_sound.RUN_SCRIPT in job["code"] and job["command"][1] == f"/work/repo/{moss_sound.RUN_SCRIPT}"
    assert [output["local"] for output in job["outputs"]] == [str(out)]
