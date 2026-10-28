"""The sound stage's paid part: MOSS-SoundEffect v2.0 takes for the briefs no world file answers yet, made in the moss
image (tools/cloud/images/moss, the image the images world rebuilt and proved) on one rented card through
tools/cloud/images/prove.py's runner, each take scored against its prompt with CLAP up there (moss_generate.py).

A take is named by its sound, its prompt's and length's hash and its seed, and kept in TAKES with its CLAP score: the
same prompt, length, seed and weights make the same take, so a take made once is never paid for again (a rerun of
the row, or another place's line asking the same brief). Each take is locked while its batch runs (`held`), so two
places' lines side by side make a shared brief (crew_talk) on one card, the other line waiting and reading it (#29).
A take its batch asked for and did not get (lost, failed, no card) is a named failure and a gap on every place that
plays it: a waiting line never asks for it again (`asked_here`); new spend on it is a new batch, another run (#29).

The takes are one batch (#21, #29): one job a sound, its brief's first prompt at seed 1, made once; the likeness gate
sorts each take by its CLAP score against gates.CLAP_FLOOR into a pass or a gap, and a new take (another seed, the
brief's next prompt) is a new batch.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import pathlib
import shutil
import sys
import time

from score import graph

REPO = pathlib.Path(__file__).resolve().parents[3]
TAKES = pathlib.Path.home() / ".cache/farm-factory/sound-picker/moss/stage"
SCORES = "scores.json"
TIMINGS = "timings"  # each batch's moss_generate timings (its takes' work seconds on the card), kept beside the takes
WHO = "score runner, sound stage"
KIND = "moss"
MODEL_PAGE = "https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect-v2.0"
MODELS = ["moss-soundeffect-v2", "clap-larger-general"]
# Measured on the moss image's proof (images.json, an L4): about 30 s a 15 s take once MOSS is loaded, and 2 to 7 min
# from the card answering to the first result.
MINUTES_A_TAKE = 0.6
FIRST_RESULT_MINUTES = 8
REMOTE = "/root/sfx"
ASKED = "asked"  # each take's last ask: the batch (the score run, else the process) that paid for it
RUN_ID = "SCORE_RUN_ID"  # the run's id; every node of a score run inherits it (score/__main__.py)
# The repo's moss-run, sent with the code: the image's own copy names the path moss_generate.py had when it was built
# (tools/props/cloud, moved 2026-10-24), so every take of Batch 1 failed with "can't open file" (exit 2).
RUN_SCRIPT = "tools/cloud/images/moss/run.sh"
SEED = 1  # one take a sound (#29): a take under the floor is a gap, never another seed inside the batch


def take_file(name, prompt, seconds, seed, weights):
    """A take's file name: its sound, the hash of what made it, its seed."""
    made_of = hashlib.sha256(json.dumps([prompt, seconds, weights]).encode()).hexdigest()[:10]
    return f"{name}__{made_of}__s{seed}.wav"


def jobs_for(name, brief, weights):
    """The one take a brief asks for: its first prompt at SEED, its length."""
    seconds, prompt = int(brief.get("seconds", 8)), brief["prompts"][0]
    return [{"file": take_file(name, prompt, seconds, SEED, weights), "sound": name, "prompt": prompt,
             "seconds": seconds, "seed": SEED}]


def scores():
    path = TAKES / SCORES
    return json.loads(path.read_text()) if path.exists() else {}


def missing(jobs):
    """The jobs whose take or score is not kept yet."""
    known = scores()
    return [job for job in jobs if not (TAKES / job["file"]).exists() or job["file"] not in known]


def plan_for(jobs_file, out, minutes, takes):
    """prove.py's plan: the jobs on one card of the moss-sound classes, the takes back into `out`; the ledger line
    names its `takes` (tools/costs/per_unit.py prices a take by them)."""
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import capacity
    return {"classes": list(capacity.classes_for("moss-sound")), "minutes": minutes, "disk_gb": 200,
            "ledger": {"takes": takes},
            "runs": [{"kind": KIND, "code": ["tools/cloud/moss_generate.py", RUN_SCRIPT],
                      "inputs": [{"from": str(jobs_file), "path": f"{REMOTE}/jobs-0.json"}],
                      "jobs": [{"name": "takes", "cache": "a", "models": MODELS, "minutes": minutes,
                                "command": ["bash", f"/work/repo/{RUN_SCRIPT}", f"{REMOTE}/jobs-0.json", "0"],
                                "outputs": [{"path": f"{REMOTE}/out", "to": str(out)}]}]}]}


def prove_tool():
    """tools/cloud/images/prove.py, loaded only when takes are made."""
    folder = str(REPO / "tools/cloud/images")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import prove
    return prove


def on_card(plan):
    """The plan on one card (#21): a card of the run's warm pool, else one rented, the claim waiting for stock while
    the card's deadline is ahead (no stock never makes a gap: owner, 2026-10-23); no card had by then is Blocked, a
    new batch asks again. On this PC (SCORE_CLOUD=local, no image registry) the same jobs go through moss_sound.py's
    machine path instead, MOSS a model at a time on its 16 GB card."""
    if graph.on_this_pc():
        on_this_pc(plan)
        return
    prove = prove_tool()
    from provider import cloud  # prove.py put it on the path
    account = cloud.account()
    prove.batch.sweep(account)
    cloud.allow_key(account, "farm-factory-batch", prove.batch.ssh_key())
    registry, store_spec = cloud.registry(), cloud.object_store()
    results = {}
    if not prove.one_attempt(plan, account, registry, store_spec, WHO, results):
        raise graph.Blocked(f"no card of {', '.join(plan['classes'])} was had before the deadline: the takes are "
                            "gaps, a new batch asks again")
    failed = [job for numbers in results.get(KIND, []) for job in numbers["jobs"].values() if job.get("failed")]
    if failed:  # its takes are gaps (made says which), never asked again inside the batch
        print(f"the moss job failed on its card: {failed}", flush=True)


def on_this_pc(plan):
    """The plan's takes on this PC's card through tools/cloud/moss_sound.py, back where the plan's output names."""
    folder = str(REPO / "tools/cloud")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import moss_sound
    run = plan["runs"][0]
    jobs = json.loads(pathlib.Path(run["inputs"][0]["from"]).read_text())
    moss_sound.on_this_pc(jobs, pathlib.Path(run["jobs"][0]["outputs"][0]["to"]), plan["minutes"])


@contextlib.contextmanager
def held(jobs):
    """Each job's take locked, in name order so two lines never wait on each other: a take another place's batch is
    making is waited for and then read, never made on a second card (#29)."""
    (TAKES / "locks").mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        for name in sorted({job["file"] for job in jobs}):
            lock = stack.enter_context((TAKES / "locks" / name).open("w"))
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def batch_id():
    """This batch: the score run every place's line belongs to, else this process."""
    return os.environ.get(RUN_ID) or f"process-{os.getpid()}"


def asked_here(job):
    """Whether this batch asked for the job's take already."""
    path = TAKES / ASKED / f"{job['file']}.json"
    return path.exists() and json.loads(path.read_text())["batch"] == batch_id()


def mark_asked(jobs):
    """Each job's take recorded as asked by this batch, before the card is asked for."""
    (TAKES / ASKED).mkdir(parents=True, exist_ok=True)
    for job in jobs:
        (TAKES / ASKED / f"{job['file']}.json").write_text(json.dumps({"batch": batch_id()}))


def made(jobs, work):
    """Every job's take made (on a card for those not kept yet; `work`, a folder in the output, carries the jobs up
    and the takes back, and is removed after) and kept in TAKES; {file: CLAP score} of the takes there, a take that
    did not come back left out (a gap: its sound has no take, which the sources gate names). A take this batch asked
    for already and did not get (another place's line, #29) is never asked again: a named failure, a gap here too."""
    with held(jobs):
        wanted = missing(jobs)
        lost_before = [job for job in wanted if asked_here(job)]
        if lost_before:
            print(f"{len(lost_before)} shared takes failed in this batch ({batch_id()}), gaps, not asked again: "
                  f"{[job['file'] for job in lost_before][:5]}", flush=True)
        wanted = [job for job in wanted if job not in lost_before]
        mark_asked(wanted)
        bought(wanted, work)
    lost = missing(jobs)
    if lost:
        print(f"{len(lost)} takes did not come back, gaps: {[job['file'] for job in lost][:5]}", flush=True)
    known = scores()
    return {job["file"]: known[job["file"]] for job in jobs if job not in lost}


def bought(wanted, work):
    """The wanted takes made on one card and kept in TAKES with their scores and the batch's timings."""
    if wanted:
        TAKES.mkdir(parents=True, exist_ok=True)
        back = work / "back"
        back.mkdir(parents=True)
        (work / "jobs.json").write_text(json.dumps(wanted, indent=1))
        on_card(plan_for(work / "jobs.json", back, round(FIRST_RESULT_MINUTES + MINUTES_A_TAKE * len(wanted)),
                         len(wanted)))
        for job in wanted:
            if (back / job["file"]).exists():
                shutil.copy2(back / job["file"], TAKES / job["file"])
        if (back / "timings-0.json").exists():  # each take's warm seconds, what the per-unit price reads (#29)
            (TAKES / TIMINGS).mkdir(exist_ok=True)
            shutil.copy2(back / "timings-0.json", TAKES / TIMINGS / f"{time.strftime('%Y%m%dT%H%M%S')}.json")
        with (TAKES / "scores.lock").open("w") as lock:  # places' lines run side by side: no score is lost
            fcntl.flock(lock, fcntl.LOCK_EX)
            kept = scores()
            if (back / "scores-0.json").exists():
                kept.update(json.loads((back / "scores-0.json").read_text()))
            (TAKES / SCORES).write_text(json.dumps(kept, indent=1))
        shutil.rmtree(work)
