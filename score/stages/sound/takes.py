"""The sound stage's paid part: MOSS-SoundEffect v2.0 takes for the briefs no world file answers yet, made in the moss
image (tools/cloud/images/moss, the image the images world rebuilt and proved) on one rented card through
tools/cloud/images/prove.py's runner, each take scored against its prompt with CLAP up there (moss_generate.py).

A take is named by its sound, its prompt's and length's hash and its seed, and kept in TAKES with its CLAP score: the
same prompt, length, seed and weights make the same take, so a take made once is never paid for again (a rerun of
the row, or another place's line asking the same brief).
"""
import hashlib
import json
import pathlib
import shutil
import sys
import time

from score import graph

REPO = pathlib.Path(__file__).resolve().parents[3]
TAKES = pathlib.Path.home() / ".cache/farm-factory/sound-picker/moss/stage"
SCORES = "scores.json"
WHO = "score runner, sound stage"
KIND = "moss"
MODEL_PAGE = "https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect-v2.0"
MODELS = ["moss-soundeffect-v2", "clap-larger-general"]
# Measured on the moss image's proof (images.json, an L4): about 30 s a 15 s take once MOSS is loaded, and 2 to 7 min
# from the card answering to the first result.
MINUTES_A_TAKE = 0.6
FIRST_RESULT_MINUTES = 8
WAIT_MINUTES = 90
RETRY_SECONDS = 180
REMOTE = "/root/sfx"


def take_file(name, prompt, seconds, seed, weights):
    """A take's file name: its sound, the hash of what made it, its seed."""
    made_of = hashlib.sha256(json.dumps([prompt, seconds, weights]).encode()).hexdigest()[:10]
    return f"{name}__{made_of}__s{seed}.wav"


def jobs_for(name, brief, weights):
    """Every take a brief asks for: each prompt at each seed, its length."""
    seconds = int(brief.get("seconds", 8))
    return [{"file": take_file(name, prompt, seconds, seed, weights), "sound": name, "prompt": prompt,
             "seconds": seconds, "seed": seed}
            for prompt in brief["prompts"] for seed in range(1, int(brief.get("seeds", 2)) + 1)]


def scores():
    path = TAKES / SCORES
    return json.loads(path.read_text()) if path.exists() else {}


def missing(jobs):
    """The jobs whose take or score is not kept yet."""
    known = scores()
    return [job for job in jobs if not (TAKES / job["file"]).exists() or job["file"] not in known]


def plan_for(jobs_file, out, minutes):
    """prove.py's plan: the jobs on one card of the moss-sound classes, the takes back into `out`."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import capacity
    return {"classes": list(capacity.classes_for("moss-sound")), "minutes": minutes, "disk_gb": 200,
            "runs": [{"kind": KIND, "code": ["tools/props/cloud/moss_generate.py"],
                      "inputs": [{"from": str(jobs_file), "path": f"{REMOTE}/jobs-0.json"}],
                      "jobs": [{"name": "takes", "cache": "a", "models": MODELS, "minutes": minutes,
                                "command": ["moss-run", f"{REMOTE}/jobs-0.json", "0"],
                                "outputs": [{"path": f"{REMOTE}/out", "to": str(out)}]}]}]}


def prove_tool():
    """tools/cloud/images/prove.py, loaded only when takes are made."""
    folder = str(REPO / "tools/cloud/images")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import prove
    return prove


def on_card(plan):
    """The plan on one rented card, asking again while none is in stock; Blocked after WAIT_MINUTES."""
    prove = prove_tool()
    from provider import cloud  # prove.py put it on the path
    account = cloud.account()
    prove.batch.sweep(account)
    cloud.allow_key(account, "farm-factory-batch", prove.batch.ssh_key())
    registry, store_spec = cloud.registry(), cloud.object_store()
    results, give_up = {}, time.time() + WAIT_MINUTES * 60
    while not prove.one_attempt(plan, account, registry, store_spec, WHO, results):
        if time.time() > give_up:
            raise graph.Blocked(f"no card of {', '.join(plan['classes'])} in {WAIT_MINUTES} min")
        time.sleep(RETRY_SECONDS)
    failed = [job for numbers in results.get(KIND, []) for job in numbers["jobs"].values() if job.get("failed")]
    if failed:
        raise RuntimeError(f"the moss job failed on its card: {failed}")


def made(jobs, work):
    """Every job's take made (on a card for those not kept yet; `work`, a folder in the output, carries the jobs up
    and the takes back, and is removed after) and kept in TAKES; {file: CLAP score}."""
    wanted = missing(jobs)
    if wanted:
        TAKES.mkdir(parents=True, exist_ok=True)
        back = work / "back"
        back.mkdir(parents=True)
        (work / "jobs.json").write_text(json.dumps(wanted, indent=1))
        on_card(plan_for(work / "jobs.json", back, round(FIRST_RESULT_MINUTES + MINUTES_A_TAKE * len(wanted) * 2)))
        kept = scores()
        kept.update(json.loads((back / "scores-0.json").read_text()))
        for job in wanted:
            if (back / job["file"]).exists():
                shutil.copy2(back / job["file"], TAKES / job["file"])
        (TAKES / SCORES).write_text(json.dumps(kept, indent=1))
        shutil.rmtree(work)
    lost = missing(jobs)
    if lost:
        raise RuntimeError(f"{len(lost)} takes did not come back: {[job['file'] for job in lost][:5]}")
    known = scores()
    return {job["file"]: known[job["file"]] for job in jobs}
