"""Run a scene's model steps on one rented cloud card, bring the room's folder back, then build
its objects as one batch.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/scene.py <plan.json> --who "<session>" [--dry-run]

No model runs on this PC (owner, 2026-10-03; local_models.py), so the scene tools that load one,
target.py (FLUX.2 klein), cutout.py (SAM 3), depth.py (MoGe-2) and redraw.py (FLUX.2 klein), run up
there, the same scripts with the same arguments, on a copy of the room's folder. The plan names
what to run, in this order:

    {"room": "lab",
     "inventory": "data/inventory/lab.json",
     "target":  {"shot": "inside", "refs": ["~/ref.png"], "takes": 4, "refs_on": 2},
     "view":    {"picture": "<plan view .png>", "out": "<folder inside the room's folder>"},
     "names":   ["bench", "desk@0.4"],
     "depth":   true,
     "objects": ["bench-1:bench", "desk-2:desk"],
     "seeds": "7", "side": 1536,
     "build":   {"prefix": "lab-", "faces": 40000, "options": {"bench": "--feet"}}}

Nothing runs without the scene's inventory approved by the owner (page A, the scene workflow of
2026-10-04, #121; inventory.py) and its place's style text (place.json, place.py): the target and
every redraw are worded from the place, never from words in the plan, so a target carries no
sentence of its own, and an object with no cut-out ("none:...") is refused, since every object is
a row boxed on the plan.

Every key but "room" and "inventory" is optional. "target" draws takes for the owner to pick from, so it runs alone:
the pick (<room>-target.png) comes before the rest. "view" is a plan view (planview.py) used in
place of the target by "names" and "objects". "build" sends every object redraw.py kept to the
cloud batch runner (batch.py) as one batch once the pictures are back, so a whole room's objects go
up together and come back finished; it needs a single seed, since several are for choosing.
Renting, the owner's limits, the self-delete and deleting are batch.py's; one card does it all. Under
SCORE_CLOUD=k8s the steps run as one Kubernetes Job of the sam image (tools/cloud/k8s/cluster_jobs.py); the machine
stays the default.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "scene"))

import batch  # noqa: E402
import capacity  # noqa: E402
import inventory as inventories  # noqa: E402
import ledger  # noqa: E402
import place  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402
from local_models import ALLOW  # noqa: E402
from paths import HOME, REPO, VENV_PYTHON, WORK  # noqa: E402

REMOTE_REPO = pathlib.PurePosixPath("/root/repo")
REMOTE_HOME = pathlib.PurePosixPath("/root/props")
REMOTE_INPUTS = REMOTE_HOME / "inputs"
# The SAM 3 weights this box's cut-outs were made with (2026-10-02): the gated facebook/sam3 is not
# open to the account. SAM3_WEIGHTS here names another, as for cutout.py.
SAM3_WEIGHTS = os.environ.get("SAM3_WEIGHTS", "jetjodh/sam3")
# First guesses until a scene is measured: renting and installing torch plus 15 GB of weights, then
# each step on an L4.
SETUP_MINUTES = 15
STEP_MINUTES = {"target": 3, "cutout": 3, "depth": 2, "redraw": 1}


def local_room(room):
    """The room's folder on this PC, as target.folder names it (without importing torch)."""
    return WORK / "scene" / room


def remote_room(room):
    return REMOTE_HOME / "work" / "scene" / room


def inside_room(room, path):
    """`path`, which must lie in the room's folder here, at its place in the machine's copy."""
    relative = pathlib.Path(path).expanduser().resolve().relative_to(local_room(room).resolve())
    return remote_room(room) / relative


def input_name(number, path):
    """Where an input from outside the room's folder lands on the machine."""
    return REMOTE_INPUTS / f"{number}-{pathlib.Path(path).name}"


def check(plan):
    """Refuse a plan that cannot run as asked, before anything is rented."""
    if "room" not in plan:
        raise SystemExit("the plan needs a room")
    if "target" in plan and set(plan) & {"names", "depth", "objects", "view"}:
        raise SystemExit("a plan with a target only draws takes: pick one as <room>-target.png, "
                         "then plan the rest")
    if "build" in plan and "," in str(plan.get("seeds", "7")):
        raise SystemExit("build needs a single seed; several seeds are for choosing first")
    if "build" in plan and "objects" not in plan:
        raise SystemExit("build needs objects to redraw")
    if "sentence" in plan.get("target", {}):
        raise SystemExit("a target's words come from its place's style text (place.json), not from the plan")
    if any(item.startswith("none:") for item in plan.get("objects", [])):
        raise SystemExit("an object with no cut-out is refused: no box, no row (inventory.py)")
    place.style_text(place_of(plan))


def place_of(plan):
    """The place of the scene the plan builds, from its approved inventory; refused without one."""
    if "inventory" not in plan:
        raise SystemExit("the plan names its scene's approved inventory: \"inventory\": \"data/inventory/<scene>.json\"")
    return inventories.approved_inventory(REPO / plan["inventory"])["place"]


def uploads(plan):
    """Every input from outside the room's folder, as (here, on the machine), in a fixed order."""
    paths = list(plan.get("target", {}).get("refs", []))
    view = plan.get("view")
    if view:
        paths.append(view["picture"])
    return [(pathlib.Path(path).expanduser(), input_name(number, path))
            for number, path in enumerate(paths, 1)]


def view_arguments(plan, placed):
    """--picture and --out for a plan view, or nothing when the target is used."""
    view = plan.get("view")
    if not view:
        return []
    return ["--picture", str(placed[pathlib.Path(view["picture"]).expanduser()]),
            "--out", str(inside_room(plan["room"], view["out"]))]


def steps(plan):
    """The scene tools to run on the machine, in order, as (step, script and arguments)."""
    check(plan)
    room = plan["room"]
    placed = dict(uploads(plan))
    found = []
    if "target" in plan:
        target = plan["target"]
        found.append(("target", ["tools/props/scene/target.py", "--list", str(REMOTE_INPUTS / "targets.json"),
                                 "--takes", str(target.get("takes", 4)),
                                 "--refs-on", str(target.get("refs_on", 2))]))
    if plan.get("names"):
        found.append(("cutout", ["tools/props/scene/cutout.py", room, *plan["names"],
                                 *view_arguments(plan, placed)]))
    if plan.get("depth"):
        found.append(("depth", ["tools/props/scene/depth.py", room]))
    if plan.get("objects"):
        found.append(("redraw", ["tools/props/scene/redraw.py", room, *plan["objects"],
                                 "--place", place_of(plan), "--seeds", str(plan.get("seeds", "7")),
                                 "--side", str(plan.get("side", 1536)), *view_arguments(plan, placed)]))
    return found


def target_jobs(plan):
    """target.py's --list for the plan's target, its references at their places on the machine."""
    target = plan["target"]
    placed = dict(uploads(plan))
    return [{"scene": plan["room"], "sentence": place.style_text(place_of(plan)), "shot": target.get("shot", "inside"),
             "refs": [str(placed[pathlib.Path(ref).expanduser()]) for ref in target.get("refs", [])]}]


def redraw_folder(plan):
    """Where redraw.py writes on this PC: the view's folder, or the room's."""
    view = plan.get("view")
    return pathlib.Path(view["out"]).expanduser() if view else local_room(plan["room"])


def batch_lines(plan, report):
    """batch.py's list for every model redraw.py kept (report.json's build list), one a line."""
    build = plan["build"]
    prefix = build.get("prefix", f"{plan['room']}-")
    options = build.get("options", {})
    folder = redraw_folder(plan) / "redraw"
    return [shlex.join([f"{prefix}{model}", str(folder / f"{model}.png"),
                        "--faces", str(build.get("faces", 40000)), *shlex.split(options.get(model, ""))])
            for model in report["build"]]


def environment():
    """What every step is run with on the machine: models allowed there, and its own homes."""
    return {ALLOW: "1", "PROPS_HOME": str(REMOTE_HOME), "SAM3_WEIGHTS": SAM3_WEIGHTS,
            "PYTHONUNBUFFERED": "1"}


def command(step):
    """One step as the shell line the machine runs."""
    settings = " ".join(f"{key}={shlex.quote(value)}" for key, value in environment().items())
    return f"cd {REMOTE_REPO} && env {settings} /root/venv/bin/python {shlex.join(step)}"


# The machine.

def price(plan, account):
    """Print the estimate and refuse what passes the owner's limits; the offers and allowed minutes."""
    found = batch.offers(list(capacity.classes_for("scene")))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    minutes = SETUP_MINUTES + sum(STEP_MINUTES[step] for step, _ in steps(plan))
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{plan['room']}: {', '.join(step for step, _ in steps(plan))} on one card, about "
              f"{minutes:.0f} min, €{ledger.cost(minutes, dearest):.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def set_up(folder, host, plan):
    """The scripts, the room's folder, the inputs and MoGe-2's code on the machine, and its Python."""
    room = plan["room"]
    batch.remote(folder, host, f"mkdir -p {REMOTE_REPO}/tools {REMOTE_INPUTS} {remote_room(room)}", check=True)
    batch.copy(folder, [REPO / "tools" / "props"], f"root@{host}:{REMOTE_REPO}/tools/", "--exclude", "__pycache__")
    if local_room(room).is_dir():
        batch.copy(folder, [f"{local_room(room)}/"], f"root@{host}:{remote_room(room)}/")
    for here, there in uploads(plan):
        batch.copy(folder, [here], f"root@{host}:{there}")
    if "target" in plan:
        (folder / "targets.json").write_text(json.dumps(target_jobs(plan)))
        batch.copy(folder, [folder / "targets.json"], f"root@{host}:{REMOTE_INPUTS}/")
    if plan.get("depth"):
        batch.copy(folder, [HOME / "moge", HOME / "utils3d-moge"], f"root@{host}:{REMOTE_HOME}/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, f"bash {REMOTE_REPO}/tools/props/cloud/scene_setup.sh", check=True,
                     stdout=log, stderr=subprocess.STDOUT)


def run_steps(folder, host, plan):
    """Each step on the machine in order, its output in its own log; stops at the first failure."""
    for step, arguments in steps(plan):
        batch.say(f"{plan['room']}: {step}")
        with (folder / f"{step}.log").open("w") as log:
            batch.remote(folder, host, command(arguments), check=True, stdout=log, stderr=subprocess.STDOUT)


def work_on(run, machine, plan):
    """One machine from boot to delete: set it up, run the steps, bring the room's folder back."""
    folder = machine["folder"]
    with spread.tended(run, machine) as host:
        set_up(folder, host, plan)
        batch.say(f"{folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        try:
            run_steps(folder, host, plan)
        finally:
            local_room(plan["room"]).mkdir(parents=True, exist_ok=True)
            batch.copy(folder, [f"root@{host}:{remote_room(plan['room'])}/"], f"{local_room(plan['room'])}/")


def record(run, machines, plan, started):
    """Write the scene's run to the ledger and say what it cost."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
             "batch": run.folder.name, "kind": "scene", "room": plan["room"],
             "steps": [step for step, _ in steps(plan)], **ledger.machines_record(machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"{plan['room']}: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machine, "
              f"€{entry['euros']:.2f}")


def build(plan, who, folder):
    """Every kept object through the cloud batch runner as one batch."""
    report = json.loads((redraw_folder(plan) / "redraw" / "report.json").read_text())
    lines = batch_lines(plan, report)
    if not lines:
        batch.say("redraw kept no object to build")
        return
    listing = folder / "build.txt"
    listing.write_text("\n".join(lines) + "\n")
    batch.say(f"{len(lines)} objects to the batch runner: {listing}")
    subprocess.run([str(VENV_PYTHON), str(HERE / "batch.py"), str(listing), "--who", who,
                    "--inventory", str(REPO / plan["inventory"])], check=True)


# The Kubernetes path (SCORE_CLOUD=k8s): the steps in turn as one Kubernetes Job of the sam image
# (tools/cloud/images/sam/: SAM 3, MoGe-2 and FLUX.2 klein from the node cache through sam-run), through
# tools/cloud/k8s/cluster_jobs.py, on a copy of the room's folder at the machine's paths, which comes back here.
CLUSTER_MODELS = {"target": ["flux2-klein-4b"], "cutout": ["sam3", "birefnet-general-lite"],
                  "depth": ["moge-2-vitl-normal"], "redraw": ["flux2-klein-4b"]}


def cluster_job(plan, targets_file):
    """The plan's steps as one cluster job: the room's folder, the plan's inputs and target list (written to
    `targets_file` here) at the machine's paths, each step through sam-run, the room's folder back."""
    room = plan["room"]
    settings = {ALLOW: "1", "PROPS_HOME": str(REMOTE_HOME), "PYTHONUNBUFFERED": "1"}
    lines = [f"sam-run {shlex.join(arguments)}" for _, arguments in steps(plan)]
    inputs = [{"local": str(here.resolve()), "path": str(there)} for here, there in uploads(plan)]
    if local_room(room).is_dir():
        inputs.append({"local": str(local_room(room).resolve()), "path": str(remote_room(room))})
    if "target" in plan:
        targets_file.write_text(json.dumps(target_jobs(plan)))
        inputs.append({"local": str(targets_file), "path": str(REMOTE_INPUTS / "targets.json")})
    return {"command": ["bash", "-c", f"mkdir -p {remote_room(room)} && " + " && ".join(lines)],
            "code": ["tools/props"], "env": settings, "inputs": inputs,
            "models": sorted({model for step, _ in steps(plan) for model in CLUSTER_MODELS[step]}),
            "outputs": [{"path": str(remote_room(room)), "local": str(local_room(room))}],
            "minutes": SETUP_MINUTES + sum(STEP_MINUTES[step] for step, _ in steps(plan)) * 2}


def main_on_cluster(plan, options):
    """main() under SCORE_CLOUD=k8s: the steps as one job on the scene kind's classes in its order (capacity.py),
    then the build as today."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    if options.dry_run:
        return
    folder = batch.BATCHES / time.strftime(f"scene-k8s-{plan['room']}-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    if cluster_jobs.run("scene", [cluster_job(plan, folder / "targets.json")], options.who, image="sam"):
        raise SystemExit(f"{plan['room']}: the scene's steps failed on the cluster")
    if "build" in plan:
        build(plan, options.who, folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plan", type=pathlib.Path)
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    plan = json.loads(options.plan.read_text())
    for step, arguments in steps(plan):
        print(f"{step}: {shlex.join(arguments)}")
    if provider.on_cluster():
        main_on_cluster(plan, options)
        return
    account = cloud.account()
    batch.sweep(account)
    found, allowed_minutes = price(plan, account)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures  # its picture module loads torch, which the gate's plain python lacks
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"scene-{plan['room']}-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = pictures.Run(folder, started + allowed_minutes * 60)
    try:
        machines = pictures.rent_machines(run, account, found, 1)
        if not machines:
            raise SystemExit("no card could be rented")
        work_on(run, machines[0], plan)
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        record(run, run.machines, plan, started)
    if "build" in plan:
        build(plan, options.who, folder)


if __name__ == "__main__":
    main()
