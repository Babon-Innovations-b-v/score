"""The completion gate: a place is complete only when its evidence says so, never because an agent says so.

    .venv/bin/python tools/usd/complete.py check <place> [--stage <stage.usda>] [--only rows,made_only,...]
    .venv/bin/python tools/usd/complete.py done <place> [--stage <stage.usda>] [--review <the review page's folder>]

`check` runs the place's checks on its OpenUSD stage and writes each result beside the stage
(`<stage folder>/checks/<check>.json`); `done` reads them and writes the place's manifest (`<stage folder>/manifest.json`)
saying, requirement by requirement, whether the place is complete. It exits 0 only when every requirement passes. The
Stop hook (.claude/hooks/completion_guard.py) runs `done` for each place a session worked on and refuses to let the
session end on a claim that a place is done while its manifest says otherwise.

Every check answers pass, fail or unknown, and unknown blocks like fail: a check that could not run, a result that is
missing, or one made on an earlier stage proves nothing (LEGO-Anything, arXiv 2609.36380, App. G.5-G.6: hard
requirements with missing evidence block acceptance; any later change to the scene invalidates a report; hooks stop the
agent finishing while validations are stale). The requirements:

    stage         the stage was exported after the last change to its inputs (the inventory, the kit, the scene record,
                  the cast and the made models, as export.py recorded them in <stage folder>/inputs.json)
    rows          every inventory row has its made model on the stage (an object of that row), or a written drop reason
                  (the row's `dropped`, or the row listed in the inventory's `held_back`)
    made_only     every visible mesh on the stage was made by the framework: a made model, a code builder's mesh or a
                  world's own model, each saying so (score:model, score:builder or score:kind), and every object's model
                  loaded
    placeholders  the placeholder check (placeholders.py): nothing visible stands in for a made piece
    resting       the resting triage (triage.py): no real resting fault left (false alarms are listed, not counted)
    picks         the pick lock (picks.py): no object the owner picked shows another model without a written decision
    current       every check result was made on this stage as it is now (the same fingerprint) and none is unknown
    review        the review page (tools/review/page.py) was built, and its scene rendered, from this stage as it is now

The fingerprint of a stage is the size and time of every file of it (the root, its layers, its assets) and the content
of every input export.py recorded: an export, an edit in the creator's layer or a changed input all change it.
This module reads only JSON and file times at the top, so the hook can import it without OpenUSD; the checks load
OpenUSD when they run.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools/props"))
sys.path.insert(0, str(HERE))
from paths import WORK  # noqa: E402

STAGES = WORK / "usd"
REVIEWS = WORK / "review"
INVENTORIES = REPO / "data/inventory"
KITS = REPO / "data/kit"
CHECKS = ("rows", "made_only", "placeholders", "resting", "picks", "boxes")
PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
# What of a stage's folder is the stage: its root file, its layers and its assets (not the checks, the manifest, the
# inputs record or a settle run kept beside it).
STAGE_PARTS = ("layers", "assets")
INPUTS = "inputs.json"
REVIEW_STAMP = "review.json"


# --- where things are ---------------------------------------------------------------------------------------------

def stage_path(place, stage=None):
    """The place's stage file: the one given, else the work folder's (WORK/usd/<place>/<place>.usda)."""
    return pathlib.Path(stage) if stage else STAGES / place / f"{place}.usda"


def inventory_path(place):
    """The place's inventory, or that of the place its kit belongs to (a room of the flat keeps the flat's)."""
    own = INVENTORIES / f"{place}.json"
    if own.exists():
        return own
    kit = KITS / f"{place}.json"
    belongs = json.loads(kit.read_text()).get("place") if kit.exists() else None
    return INVENTORIES / f"{belongs}.json" if belongs else own


def now():
    """This moment, in UTC, as text."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# --- the fingerprint ----------------------------------------------------------------------------------------------

def file_hash(path):
    """A file's content as a sha256 hex digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def model_hash(gltf):
    """A made model's content as a sha256 hex digest: its .gltf and every buffer file it names."""
    gltf = pathlib.Path(gltf)
    digest = hashlib.sha256(gltf.read_bytes())
    for buffer in json.loads(gltf.read_text()).get("buffers", []):
        if buffer.get("uri") and not buffer["uri"].startswith("data:"):
            digest.update(file_hash(gltf.parent / buffer["uri"]).encode())
    return digest.hexdigest()


def input_name(path):
    """How an input is named in a stage's inputs record: its path in the repository, or its full path outside it."""
    resolved = pathlib.Path(path).resolve()
    return str(resolved.relative_to(REPO)) if resolved.is_relative_to(REPO) else str(resolved)


def record_inputs(out, inventory, inputs, models, hashes=None):
    """Write what a stage was exported from beside it (inputs.json): the inventory it was laid from, each input file
    by its content, and each made model (.gltf) by its content, file and time, for the gate to tell when the stage is
    older than they are. `models` is {model: its .gltf}, `hashes` their model_hash when already worked out; inputs that do
    not exist are left out."""
    hashes = hashes or {}
    written = {"at": now(), "inventory": input_name(inventory),
               "inputs": {input_name(path): file_hash(path) for path in [inventory, *inputs] if pathlib.Path(path).exists()},
               "models": {model: {"file": str(pathlib.Path(gltf).resolve()), "sha256": hashes.get(model) or model_hash(gltf),
                                  "mtime": pathlib.Path(gltf).stat().st_mtime_ns}
                          for model, gltf in sorted(models.items())}}
    (pathlib.Path(out) / INPUTS).write_text(json.dumps(written, indent=1) + "\n")
    return written


def recorded_inventory(place, stage):
    """The inventory a stage was laid from, as its inputs record names it; else the place's own."""
    record = pathlib.Path(stage).parent / INPUTS
    if record.exists():
        return REPO / json.loads(record.read_text())["inventory"]
    return inventory_path(place)


def stage_files(stage):
    """Every file of a stage: its root file and everything under its layers and assets, sorted."""
    stage = pathlib.Path(stage)
    found = [stage] if stage.exists() else []
    for part in STAGE_PARTS:
        folder = stage.parent / part
        if folder.is_dir():
            found += sorted(path for path in folder.rglob("*") if path.is_file())
    return found


def fingerprint(stage):
    """The stage as it is now: a digest of each of its files' place, size and time, and of the inputs record
    export.py wrote beside it. Any export, edit or changed input gives another."""
    stage = pathlib.Path(stage)
    digest = hashlib.sha256()
    for path in stage_files(stage):
        status = path.stat()
        digest.update(f"{path.relative_to(stage.parent)}\0{status.st_size}\0{status.st_mtime_ns}\n".encode())
    record = stage.parent / INPUTS
    if record.exists():
        digest.update(record.read_bytes())
    return digest.hexdigest()


# --- results ------------------------------------------------------------------------------------------------------

def results_folder(stage):
    """Where a stage's check results are kept."""
    return pathlib.Path(stage).parent / "checks"


def result(check, verdict, stage, faults=(), note=""):
    """One check's result on a stage as it is now."""
    return {"check": check, "result": verdict, "fingerprint": fingerprint(stage), "at": now(),
            "faults": list(faults), "note": note}


def save(found, stage):
    """Write a check's result beside the stage."""
    folder = results_folder(stage)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{found['check']}.json").write_text(json.dumps(found, indent=1) + "\n")


def load(check, stage):
    """A check's last result on a stage, or None when it never ran."""
    path = results_folder(stage) / f"{check}.json"
    return json.loads(path.read_text()) if path.exists() else None


# --- the checks ---------------------------------------------------------------------------------------------------

def rows_faults(stage_file, inventory):
    """Each inventory row with no object on the stage and no written drop reason: [{row, why}]."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_file))
    laid = {prim.GetAttribute("score:row").Get() for prim in stage.Traverse() if prim.HasAttribute("score:row")}
    held_back = {row["id"] for row in inventory.get("held_back", []) if row.get("why_code") or row.get("why")}
    return [{"row": row["id"], "why": f"no object of this row on the stage ({row.get('made') or row.get('kind', 'no kind')}) and no "
                                      "written drop reason (`dropped`)"}
            for row in inventory["rows"]
            if row["id"] not in laid and not str(row.get("dropped", "")).strip() and row["id"] not in held_back]


def rows_check(place, stage):
    """Every inventory row made or dropped with a reason."""
    faults = rows_faults(stage, json.loads(recorded_inventory(place, stage).read_text()))
    return result("rows", FAIL if faults else PASS, stage, faults)


def made_only_check(place, stage):
    """Every visible mesh made by the framework (made_only.py)."""
    import made_only
    faults = made_only.check(stage)
    return result("made_only", FAIL if faults else PASS, stage, faults)


def placeholders_check(place, stage):
    """The placeholder check (placeholders.py)."""
    import placeholders
    faults = placeholders.check(stage)
    return result("placeholders", FAIL if faults else PASS, stage, faults)


def resting_check(place, stage):
    """The resting triage's real faults (triage.py): each a fault the false-alarm guards kept, with the last settle
    run's drop (SAGE's rule) when one lies beside the stage (settle/settled.json, newer than the stage)."""
    import triage
    settled_file = pathlib.Path(stage).parent / "settle/settled.json"
    fresh = settled_file.exists() and settled_file.stat().st_mtime_ns >= pathlib.Path(stage).stat().st_mtime_ns
    found = triage.triage(stage, json.loads(settled_file.read_text()) if fresh else None)
    real = [fault for fault in found["faults"] if fault["real"]]
    note = (f"{found['real_objects']} objects with real faults, {found['false_objects']} false alarms"
            + ("" if fresh else "; no drop run on this stage (settle.py --dry-run)"))
    return result("resting", FAIL if real else PASS, stage, real, note)


def picks_check(place, stage):
    """The pick lock (picks.py): every object of a picked row still the model the owner picked."""
    import picks
    faults, locked = picks.check(stage, json.loads(recorded_inventory(place, stage).read_text()))
    return result("picks", FAIL if faults else PASS, stage, faults, f"{locked} rows locked to an owner's pick")


def boxes_check(place, stage):
    """The box gate (props/scene/box_check.py gate()) on the inventory the stage was laid from: every box measured
    from SAM's proposals and checked on that box; a typed box fails, an unmeasured one is unknown."""
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import box_check
    found = json.loads(recorded_inventory(place, stage).read_text())
    verdict = box_check.gate(found["scene"], found)
    faults = [{"row": row, "result": entry["result"], "why": entry["why"]}
              for row, entry in verdict["rows"].items() if entry["result"] != box_check.PASS]
    faults += [{"row": None, "result": FAIL, "why": problem} for problem in verdict["views"]]
    counts = {name: sum(entry["result"] == name for entry in verdict["rows"].values()) for name in (PASS, FAIL, UNKNOWN)}
    return result("boxes", verdict["result"], stage, faults,
                  f"{counts[PASS]} boxes pass, {counts[FAIL]} fail, {counts[UNKNOWN]} unknown")


RUNNERS = {"rows": rows_check, "made_only": made_only_check, "placeholders": placeholders_check,
           "resting": resting_check, "picks": picks_check, "boxes": boxes_check}


def run_check(check, place, stage):
    """One check's result; unknown, with why, when it cannot run (a missing stage, a broken file)."""
    if not pathlib.Path(stage).exists():
        return result(check, UNKNOWN, stage, note=f"no stage at {stage}")
    try:
        return RUNNERS[check](place, stage)
    except Exception as error:  # the check could not judge: its result is unknown, and unknown blocks
        return result(check, UNKNOWN, stage, note=f"{type(error).__name__}: {error}")


# --- the requirements ---------------------------------------------------------------------------------------------

def stage_requirement(stage):
    """Whether the stage was exported after the last change to every input export.py recorded."""
    record = pathlib.Path(stage).parent / INPUTS
    if not pathlib.Path(stage).exists():
        return UNKNOWN, f"no stage at {stage}"
    if not record.exists():
        return UNKNOWN, "the stage has no inputs record (exported before export.py wrote one): export it again"
    changed = [name for name, hashed in json.loads(record.read_text())["inputs"].items()
               if not (REPO / name).exists() or file_hash(REPO / name) != hashed]
    changed += [name for name, seen in json.loads(record.read_text()).get("models", {}).items()
                if not pathlib.Path(seen["file"]).exists() or pathlib.Path(seen["file"]).stat().st_mtime_ns != seen["mtime"]]
    if changed:
        return FAIL, "changed since the stage was exported: " + ", ".join(sorted(changed)) + "; export it again"
    return PASS, "exported after the last change to its inputs"


def check_requirement(check, stage, current):
    """A check's requirement: its last result, unless it is missing or was made on another stage (unknown)."""
    found = load(check, stage)
    if found is None:
        return UNKNOWN, "never run: complete.py check runs it"
    if found["fingerprint"] != current:
        return UNKNOWN, f"stale: made at {found['at']} on an earlier stage; run it again"
    faults = found.get("faults", [])
    if found["result"] == FAIL:
        return FAIL, f"{len(faults)} faults" + (f" ({found['note']})" if found.get("note") else "")
    if found["result"] == UNKNOWN:
        return UNKNOWN, found.get("note") or "the check could not judge"
    return PASS, found.get("note") or "passed"


def review_requirement(place, stage, review, current):
    """Whether the review page was built, and its scene rendered, from the stage as it is now."""
    stamp = pathlib.Path(review or REVIEWS / place) / REVIEW_STAMP
    if not stamp.exists():
        return UNKNOWN, f"no review page built by page.py at {stamp.parent}"
    built = json.loads(stamp.read_text())
    if built.get("fingerprint") != current:
        return FAIL, f"the review page was built at {built.get('at')} from an earlier stage: build it again"
    if built.get("rendered") != current:
        return FAIL, "the review page's scene was rendered from an earlier stage: render it again (not --no-render)"
    return PASS, f"built at {built.get('at')}"


def requirements(place, stage, review=None):
    """Every requirement of a complete place: [{name, result, why}], in order."""
    current = fingerprint(stage)
    found = [("stage", *stage_requirement(stage))]
    found += [(check, *check_requirement(check, stage, current)) for check in CHECKS]
    stale = [name for name, verdict, _ in found[1:] if verdict == UNKNOWN]
    found.append(("current", UNKNOWN if stale else PASS,
                  f"not current or unknown: {', '.join(stale)}" if stale else "every result is on this stage"))
    found.append(("review", *review_requirement(place, stage, review, current)))
    return [{"name": name, "result": verdict, "why": why} for name, verdict, why in found]


def verdict_of(found):
    """The place's verdict: pass when every requirement passes, fail when any fails, else unknown."""
    results = {requirement["result"] for requirement in found}
    return PASS if results == {PASS} else FAIL if FAIL in results else UNKNOWN


def manifest(place, stage, review=None):
    """The place's manifest, written beside its stage: every requirement and the verdict."""
    found = requirements(place, stage, review)
    written = {"place": place, "stage": str(stage), "fingerprint": fingerprint(stage), "at": now(),
               "verdict": verdict_of(found), "requirements": found}
    if pathlib.Path(stage).parent.is_dir():
        (pathlib.Path(stage).parent / "manifest.json").write_text(json.dumps(written, indent=1) + "\n")
    return written


# --- the way in ---------------------------------------------------------------------------------------------------

def run_checks(place, stage, only=CHECKS):
    """Run the named checks on the place's stage and save each result; the results."""
    found = []
    for check in only:
        outcome = run_check(check, place, stage)
        save(outcome, stage)
        found.append(outcome)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("check", "done"))
    parser.add_argument("place")
    parser.add_argument("--stage", type=pathlib.Path)
    parser.add_argument("--review", type=pathlib.Path, help="the review page's folder (WORK/review/<place>)")
    parser.add_argument("--only", help="the checks to run, comma separated: " + ",".join(CHECKS))
    options = parser.parse_args()
    stage = stage_path(options.place, options.stage)
    if options.command == "check":
        for outcome in run_checks(options.place, stage, options.only.split(",") if options.only else CHECKS):
            print(f"{outcome['check']}: {outcome['result']}: {len(outcome['faults'])} faults {outcome['note']}".rstrip())
        return
    written = manifest(options.place, stage, options.review)
    for requirement in written["requirements"]:
        print(f"{requirement['name']:13} {requirement['result']:8} {requirement['why']}")
    print(f"{options.place}: {'complete' if written['verdict'] == PASS else 'NOT complete'} ({written['verdict']})")
    sys.exit(0 if written["verdict"] == PASS else 1)


if __name__ == "__main__":
    main()
