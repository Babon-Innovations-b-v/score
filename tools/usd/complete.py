"""The completion gate: a place is complete only when its evidence says so, never because an agent says so.

    .venv/bin/python tools/usd/complete.py check <place> [--stage <stage.usda> | --work-stage] [--only rows,...]
    .venv/bin/python tools/usd/complete.py done <place> [--stage <stage.usda> | --work-stage] [--review <folder>]

The stage judged by default is the store copy of the place's accepted assembled stage (WORK/review-store/<place>/stage,
made by tools/review/store_page.py); --work-stage judges the old export at WORK/usd/<place>.

`check` runs the place's checks on its OpenUSD stage and writes each result beside the stage
(`<stage folder>/checks/<check>.json`); `done` reads them and writes the place's manifest (`<stage folder>/manifest.json`)
saying, requirement by requirement, whether the place is complete, and its status (CONTEXT.md): "complete" when
every requirement passes; "complete apart from accepted gaps (N)" when the accepted gaps requirement is the only one that
does not, every gap listed with its numbers and who decided it (overseer, 2026-10-15); else "NOT complete". It exits 0
on the first two. The
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
    reach         the reach check (reach.py): a walker on the place's floor reaches a standing spot in front of every
                  row's object (the automatic playtest; the interact press waits for interactable assets).
                  Experimental (EXPERIMENTAL says why): its faults are shown, not counted; what counts is that it was
                  recorded on this stage as it is now
    people, effects, motion, crops, likeness, painted, light, sound, neighbours, game
                  the contents checks (contents.py, its docstring has each): what the place holds, against its cast,
                  its expected effects and motions, its crops, its close-ups, its paint, its light and sound layers,
                  the places it shows, and no record citing the game. The runner's complete stage
                  (score/stages/complete) runs these same checks, and every one above but resting (the assembly's
                  gate judges it on its drop run), on the place's assembled stage: one gate, two ways in
    accepted gaps    as the runner's complete row: a check's faults a dated decision in data/checks/gaps/<place>.json
                  names (score/stages/gaps.py, a gate of GAP_GATES["complete"]) pass that check, said by name, and
                  this requirement fails every accepted gap by name; any fault no gap names still fails its check
    current       every check result was made on this stage as it is now (the same fingerprint) and none is unknown
    review        the review page (tools/review/page.py) was built, and its scene rendered, from this stage as it is now

The fingerprint of a stage is the size and time of every file of it (the root, its layers, its assets) and the content
of every input export.py recorded: an export, an edit in the creator's layer or a changed input all change it.
This module reads only JSON and file times at the top, so the hook can import it without OpenUSD; the checks load
OpenUSD when they run.
"""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools/props"))
sys.path.insert(0, str(HERE))
from paths import WORK  # noqa: E402
from stage_inputs import (INPUTS, INVENTORIES, KITS, file_hash, input_name, inventory_path, model_hash,  # noqa: E402,F401
                          now, record_inputs, recorded_inventory)
import contents  # noqa: E402

STAGES = WORK / "usd"
REVIEWS = WORK / "review"
CHECKS = ("rows", "made_only", "placeholders", "resting", "picks", "boxes", "reach", *contents.JUDGES)
# Checks whose faults are shown on the manifest but not counted, each unproven on its end-result fault (docs/bible.md,
# architecture/experimental): what would prove it. That such a check was recorded on the stage as it is now counts.
EXPERIMENTAL = {
    "reach": "it fails backdrop rows nobody walks to (far city towers, masts) and has caught no real unreachable row "
             "that was then fixed; counted once the owner's scenery rule is set and it has",
}
PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
# The verdict of a place whose only failing requirement is its accepted gaps (overseer, 2026-10-15): done passes for the
# run and says so. ACCEPTED_GAPS is that requirement's name, the runner's complete row's check (graph.GAPPED).
GAPPED, ACCEPTED_GAPS = "gapped", "accepted gaps"
# What done says of each verdict (CONTEXT.md: complete, complete apart from accepted gaps, not complete).
STATUS = {PASS: "complete", GAPPED: "complete apart from accepted gaps"}
NOT_COMPLETE = "NOT complete"
# What of a stage's folder is the stage: its root file, its layers and its assets (not the checks, the manifest, the
# inputs record or a settle run kept beside it).
STAGE_PARTS = ("layers", "assets")
REVIEW_STAMP = "review.json"
# The owner reviews a place in the browser viewer from its store page (tools/review/store_page.py, owner 2026-10-11:
# no renders); page.py's rendered page is for films and figures. Either page's stamp answers the review requirement.
STORE_REVIEWS = WORK / "review-store"
# The marker store_page.py writes beside a stage it copied out of the store: the accepted output it is.
STORE_OUTPUT = "output.txt"


# --- where things are ---------------------------------------------------------------------------------------------

def stage_path(place, stage=None, work=False):
    """The place's stage file: the one given; else the store copy of its accepted assembled stage
    (WORK/review-store/<place>/stage/<place>.usda, made by tools/review/store_page.py), the framework's one source;
    with `work`, the old export's (WORK/usd/<place>/<place>.usda)."""
    if stage:
        return pathlib.Path(stage)
    return STAGES / place / f"{place}.usda" if work else STORE_REVIEWS / place / "stage" / f"{place}.usda"


def assembled_node(place):
    """The node whose accepted output is the place's assembled stage, the one the runner's complete row judges
    (score/stages/complete assembled_stage): neighbours@<place> where the place shows others, else assembly@<place>."""
    sys.path.insert(0, str(REPO))
    from score.stages.assembly import neighbours
    return f"{'neighbours' if neighbours.applies(place) else 'assembly'}@{place}"



# --- the fingerprint ----------------------------------------------------------------------------------------------

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

def unlaid_rows(inventory, laid):
    """Each inventory row not among the laid rows and with no written drop reason: [{row, why}]."""
    held_back = {row["id"] for row in inventory.get("held_back", []) if row.get("why_code") or row.get("why")}
    return [{"row": row["id"], "why": f"no object of this row on the stage ({row.get('made') or row.get('kind', 'no kind')}) and no "
                                      "written drop reason (`dropped`)"}
            for row in inventory["rows"]
            if row["id"] not in laid and not str(row.get("dropped", "")).strip() and row["id"] not in held_back]


def rows_faults(stage_file, inventory, place):
    """Each inventory row with no object of the place's own on the stage (a shown place's never counts) and no
    written drop reason: [{row, why}]."""
    from pxr import Usd
    return unlaid_rows(inventory, contents.laid_rows(Usd.Stage.Open(str(stage_file)), place))


def host_of(place):
    """The place a part belongs to (contents.json `part_of`: the garage's and the hangar's door leaves), or None."""
    return (contents.expected(place) or {}).get("part_of")


def part_rows(place):
    """The inventory rows a part's own kit lays (a kind's row, as export.kind_row names it: the kind without its
    room's or the part's name), the only rows a part answers for; the rest are its host's."""
    kit = json.loads((KITS / f"{place}.json").read_text())
    prefixes = [f"{name}_" for name in (kit.get("room", ""), place) if name]
    return {laid.get("row") or next((laid["kind"].removeprefix(prefix) for prefix in prefixes
                                     if laid["kind"].startswith(prefix)), laid["kind"]) for laid in kit["pieces"]}


def own_inventory(place, stage):
    """The inventory the stage was laid from; for a part of another place, only the rows its own kit lays."""
    inventory = json.loads(recorded_inventory(place, stage).read_text())
    if not host_of(place):
        return inventory
    rows = part_rows(place)
    return {**inventory, "rows": [row for row in inventory["rows"] if row["id"] in rows],
            "held_back": [row for row in inventory.get("held_back", []) if row.get("id") in rows]}


def rows_check(place, stage):
    """Every inventory row made or dropped with a reason (a part's: its own kit's rows)."""
    faults = rows_faults(stage, own_inventory(place, stage), place)
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
    run's drop (SAGE's rule) when one lies beside the stage (settle/settled.json, newer than the stage). A store copy
    is judged as the runner judges it: by its assembly's own resting gate (assembly_resting)."""
    if (pathlib.Path(stage).parent / STORE_OUTPUT).exists():
        return assembly_resting(place, stage)
    import triage
    settled_file = pathlib.Path(stage).parent / "settle/settled.json"
    fresh = settled_file.exists() and settled_file.stat().st_mtime_ns >= pathlib.Path(stage).stat().st_mtime_ns
    found = triage.triage(stage, json.loads(settled_file.read_text()) if fresh else None)
    real = [fault for fault in found["faults"] if fault["real"]]
    note = (f"{found['real_objects']} objects with real faults, {found['false_objects']} false alarms"
            + ("" if fresh else "; no drop run on this stage (settle.py --dry-run)"))
    return result("resting", FAIL if real else PASS, stage, real, note)


def assembly_resting(place, stage):
    """The resting requirement of a store copy as the runner has it: its complete row leaves resting to the assembly's
    gate, judged on the drop run the assembly gathered with the place's accepted gaps moved, so this is that gate's
    verdict on the accepted assembly@<place> output (its newest judgement in the store)."""
    sys.path.insert(0, str(REPO))
    from score import review
    from score.store import Store
    store, node = Store.default(), f"assembly@{place}"
    output = store.accepted(node)
    record = review.record_of(store, node, output) if output else None
    judgement = review.newest_judgement(store, record) if record else None
    verdict = (judgement or {}).get("verdicts", {}).get("resting")
    if verdict is None:
        return result("resting", UNKNOWN, stage, note=f"no judged resting gate on {node}'s chosen output")
    return result("resting", verdict["answer"], stage, list(verdict.get("findings") or ()),
                  f"{node}'s resting gate on its drop run ({output[:12]}): {verdict['reason']}")


def picks_check(place, stage):
    """The pick lock (picks.py): every object of a picked row still the model the owner picked."""
    import picks
    faults, locked = picks.check(stage, own_inventory(place, stage))
    return result("picks", FAIL if faults else PASS, stage, faults, f"{locked} rows locked to an owner's pick")


def boxes_check(place, stage):
    """The box gate (props/scene/box_check.py gate()) on the inventory the stage was laid from: every box measured
    from SAM's proposals and checked on that box; a typed box fails, an unmeasured one is unknown."""
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import box_check
    found = own_inventory(place, stage)
    verdict = box_check.gate(found["scene"], found)
    faults = [{"row": row, "result": entry["result"], "why": entry["why"]}
              for row, entry in verdict["rows"].items() if entry["result"] != box_check.PASS]
    faults += [{"row": None, "result": FAIL, "why": problem} for problem in verdict["views"]]
    counts = {name: sum(entry["result"] == name for entry in verdict["rows"].values()) for name in (PASS, FAIL, UNKNOWN)}
    return result("boxes", verdict["result"], stage, faults,
                  f"{counts[PASS]} boxes pass, {counts[FAIL]} fail, {counts[UNKNOWN]} unknown")


def reach_check(place, stage):
    """The reach check (reach.py) on the inventory the stage was laid from: every row a walker on the floor cannot
    reach is a fault; a row with no object is unknown."""
    import reach
    if host_of(place):  # a part's rows are walked to on its host's stage, where it stands
        return result("reach", PASS, stage, note=f"a part of {host_of(place)}: judged on {host_of(place)}'s stage")
    overall, rows, note = reach.check(stage, place, json.loads(recorded_inventory(place, stage).read_text()))
    return result("reach", overall, stage, [row for row in rows if row["result"] != PASS], note)


def stored_outputs(place):
    """{stage: its accepted output's folder for the place, or None} of the outputs the contents checks read, from
    the framework's store."""
    sys.path.insert(0, str(REPO))
    from score.store import Store
    store = Store.default()
    accepted = {name: store.accepted(f"{name}@{place}") for name in contents.OUTPUTS}
    accepted.update({node: store.accepted(node) for node in complete_besides(place)})
    return {name: store.checkout(output) if output else None for name, output in accepted.items()}


def complete_besides(place):
    """The other places' nodes the runner's complete row reads beside for the place (its `beside` over its
    `neighbours`: a ship place's likeness@<the place whose bake lays its made piece>, 7caacee2), by node name."""
    from score import stages
    row = next(row for row in stages.STAGES if row.name == "complete")
    others = row.neighbours(place) if row.neighbours else []
    return [f"{before}@{other}" for other in others for before in row.beside]


def contents_check(check, place, stage, outputs=None):
    """A contents check (contents.py) on the stage, reading the given stage outputs or else the store's accepted."""
    from pxr import Usd
    opened = Usd.Stage.Open(str(stage))
    inventory = json.loads(recorded_inventory(place, stage).read_text())
    verdict, faults, note = contents.JUDGES[check](opened, place, inventory,
                                                   stored_outputs(place) if outputs is None else outputs)
    return result(check, verdict, stage, faults, note)


RUNNERS = {"rows": rows_check, "made_only": made_only_check, "placeholders": placeholders_check,
           "resting": resting_check, "picks": picks_check, "boxes": boxes_check, "reach": reach_check}


def run_check(check, place, stage, outputs=None):
    """One check's result; unknown, with why, when it cannot run (a missing stage, a broken file). A contents check
    reads `outputs` ({stage: accepted output folder or None}) when given, else the store's."""
    if not pathlib.Path(stage).exists():
        return result(check, UNKNOWN, stage, note=f"no stage at {stage}")
    try:
        if check in contents.JUDGES:
            return contents_check(check, place, stage, outputs)
        return RUNNERS[check](place, stage)
    except Exception as error:  # the check could not judge: its result is unknown, and unknown blocks
        return result(check, UNKNOWN, stage, note=f"{type(error).__name__}: {error}")


def recorded(verdict, why):
    """An experimental check's requirement: recorded (pass) when it judged this stage, its faults shown not counted;
    unknown when it did not."""
    return (PASS, f"recorded, {verdict}: {why}") if verdict in (PASS, FAIL) else (verdict, why)


# --- the requirements ---------------------------------------------------------------------------------------------

def stage_requirement(stage, place=None):
    """Whether the stage is current: a copy of the store's assembly (STORE_OUTPUT beside it) is judged by the runner's
    key, the accepted assembly output on the current key of every input; a work stage by whether it was exported
    after the last change to every input export.py recorded."""
    record = pathlib.Path(stage).parent / INPUTS
    if not pathlib.Path(stage).exists():
        return UNKNOWN, f"no stage at {stage}"
    marker = pathlib.Path(stage).parent / STORE_OUTPUT
    if marker.exists():
        return store_stage_requirement(place or pathlib.Path(stage).stem, marker.read_text().strip())
    if not record.exists():
        return UNKNOWN, "the stage has no inputs record (exported before export.py wrote one): export it again"
    changed = [name for name, hashed in json.loads(record.read_text())["inputs"].items()
               if not (REPO / name).exists() or file_hash(REPO / name) != hashed]
    changed += [name for name, seen in json.loads(record.read_text()).get("models", {}).items()
                if not pathlib.Path(seen["file"]).exists() or pathlib.Path(seen["file"]).stat().st_mtime_ns != seen["mtime"]]
    if changed:
        return FAIL, "changed since the stage was exported: " + ", ".join(sorted(changed)) + "; export it again"
    return PASS, "exported after the last change to its inputs"


def store_stage_requirement(place, output):
    """Whether `output` is the place's assembled node's accepted output on the key its inputs give now (the
    runner's)."""
    sys.path.insert(0, str(REPO))
    from score import graph, stages
    runner = stages.runner()
    node = assembled_node(place)
    try:
        key = runner.key(runner.stages[node.partition("@")[0]], place)["key"]
    except graph.Blocked as block:
        return UNKNOWN, f"{node}'s current key cannot be worked out: {block}"
    record = runner.store.record(node, key)
    if record is None:
        return FAIL, f"{node} has not run on its current inputs: this stage ({output[:12]}) is out of date"
    if record["output"] != output:
        return FAIL, f"this stage ({output[:12]}) is not {node}'s output on the current key ({record['output'][:12]})"
    if runner.store.accepted(node) != output:
        return FAIL, f"this stage ({output[:12]}) is {node}'s output on the current key but not accepted"
    return PASS, f"{node}'s accepted output on the current key ({key[:12]})"


def gap_inputs(place):
    """The place's gaps file as the runner's complete row declares it (score/stages/gaps.py files, row None), its
    pattern filled from the data folder the gaps live in: {"gaps": path}, or {} for a place without one."""
    sys.path.insert(0, str(REPO))
    from score.stages import gaps
    return {name: pattern.format(place=place, data=gaps.FOLDER.parents[1])
            for name, pattern in gaps.files(place).items()}


def gap_moved(check, place, found):
    """A check's saved result with the place's accepted gaps moved as the runner's complete row moves them
    (score/stages gap_moved over score/stages/complete gate_check's verdict): (answer, why moved, or None). Only a
    gate of GAP_GATES["complete"] moves, and only when every fault is an accepted gap's; anything else stands as saved."""
    from score.stages import gaps
    entries = gaps.entries(gap_inputs(place), "complete", check)
    if not entries:
        return found["result"], None
    from score import checks, stages
    if check not in stages.GAP_GATES["complete"]:
        return found["result"], None
    faults = found.get("faults", [])
    why = found.get("note") or found["result"]
    verdict = checks.Verdict(check, found["result"], f"{len(faults)} faults: {why}" if faults else why, {}, {},
                             tuple(fault if isinstance(fault, str) else json.dumps(fault) for fault in faults))
    moved = gaps.moved(verdict, entries)
    return moved.answer, moved.reason if moved is not verdict else None


def gap_list(place):
    """Every accepted gap of the place, as the runner's complete row reads them (gaps.entries)."""
    sys.path.insert(0, str(REPO))
    from score.stages import gaps
    return gaps.entries(gap_inputs(place))


def accepted_gaps_requirement(place):
    """The completion gate's own accepted gaps check (score/stages/gaps.py judge_accepted): every gap fails by name."""
    sys.path.insert(0, str(REPO))
    from score.stages import gaps
    verdict = gaps.judge_accepted(None, gap_inputs(place), None)
    return verdict.answer, verdict.reason


def check_requirement(check, stage, current, place=None):
    """A check's requirement: its last result, unless it is missing or was made on another stage (unknown); a fault
    of the place's accepted gaps moved as the runner's complete row moves it."""
    found = load(check, stage)
    if found is None:
        return UNKNOWN, "never run: complete.py check runs it"
    if found["fingerprint"] != current:
        return UNKNOWN, f"stale: made at {found['at']} on an earlier stage; run it again"
    answer, moved = gap_moved(check, place or pathlib.Path(stage).stem, found)
    if moved:
        return answer, moved
    faults = found.get("faults", [])
    if found["result"] == FAIL:
        return FAIL, f"{len(faults)} faults" + (f" ({found['note']})" if found.get("note") else "")
    if found["result"] == UNKNOWN:
        return UNKNOWN, found.get("note") or "the check could not judge"
    return PASS, found.get("note") or "passed"


def review_requirement(place, stage, review, current):
    """Whether the place's review page was built from the stage as it is now: its store page (STORE_REVIEWS, what
    the owner reviews), or page.py's page with its scene rendered from it."""
    shown = STORE_REVIEWS / place / REVIEW_STAMP
    if review is None and shown.exists():
        built = json.loads(shown.read_text())
        if built.get("fingerprint") != current:
            return FAIL, f"the store page was built at {built.get('at')} from an earlier stage: build it again"
        return PASS, f"store page built at {built.get('at')}"
    stamp = pathlib.Path(review or REVIEWS / place) / REVIEW_STAMP
    if not stamp.exists():
        return UNKNOWN, f"no review page: neither a store page (store_page.py) at {shown.parent} nor page.py's at " \
                        f"{stamp.parent}"
    built = json.loads(stamp.read_text())
    if built.get("fingerprint") != current:
        return FAIL, f"the review page was built at {built.get('at')} from an earlier stage: build it again"
    if built.get("rendered") != current:
        return FAIL, "the review page's scene was rendered from an earlier stage: render it again (not --no-render)"
    return PASS, f"built at {built.get('at')}"


def requirements(place, stage, review=None):
    """Every requirement of a complete place: [{name, result, why}], in order."""
    current = fingerprint(stage)
    found = [("stage", *stage_requirement(stage, place))]
    found += [(check, *(recorded(*check_requirement(check, stage, current)) if check in EXPERIMENTAL
                        else check_requirement(check, stage, current, place))) for check in CHECKS]
    stale = [name for name, verdict, _ in found[1:] if verdict == UNKNOWN]
    found.append((ACCEPTED_GAPS, *accepted_gaps_requirement(place)))
    found.append(("current", UNKNOWN if stale else PASS,
                  f"not current or unknown: {', '.join(stale)}" if stale else "every result is on this stage"))
    found.append(("review", *review_requirement(place, stage, review, current)))
    return [{"name": name, "result": verdict, "why": why, **({"experimental": EXPERIMENTAL[name]}
                                                             if name in EXPERIMENTAL else {})}
            for name, verdict, why in found]


def verdict_of(found):
    """The place's verdict: pass when every requirement passes; gapped when the accepted gaps requirement is the only one
    that does not; else fail when any fails, else unknown. An experimental requirement passes once recorded on this
    stage (its faults shown, not counted)."""
    results = {requirement["result"] for requirement in found}
    others = {requirement["result"] for requirement in found if requirement["name"] != ACCEPTED_GAPS}
    if results == {PASS}:
        return PASS
    if others == {PASS}:
        return GAPPED
    return FAIL if FAIL in results else UNKNOWN


def status_of(verdict):
    """What done says of a verdict: complete, complete apart from accepted gaps, or NOT complete."""
    return STATUS.get(verdict, NOT_COMPLETE)


def manifest(place, stage, review=None):
    """The place's manifest, written beside its stage: every requirement and the verdict."""
    found = requirements(place, stage, review)
    verdict = verdict_of(found)
    written = {"place": place, "stage": str(stage), "fingerprint": fingerprint(stage), "at": now(),
               "verdict": verdict, "status": status_of(verdict), "requirements": found,
               "accepted_gaps": [{key: entry[key] for key in ("name", "decided", "faults")} for entry in gap_list(place)]}
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


def done_line(place, written):
    """done's last words on the place: its status, and for one complete apart from accepted gaps every gap with its
    numbers and who decided it."""
    if written["verdict"] != GAPPED:
        return f"{place}: {written['status']} ({written['verdict']})"
    lines = [f"{place}: {written['status']} ({len(written['accepted_gaps'])})"]
    for entry in written["accepted_gaps"]:
        lines.append(f"  {entry['name']} (decided: {entry['decided']})")
        lines += [f"    {fault}" for fault in entry["faults"]]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("check", "done"))
    parser.add_argument("place")
    parser.add_argument("--stage", type=pathlib.Path,
                        help="the stage to judge; default the store copy store_page.py makes of the accepted assembly")
    parser.add_argument("--work-stage", action="store_true",
                        help="judge the old export at WORK/usd/<place> instead of the store copy")
    parser.add_argument("--review", type=pathlib.Path, help="the review page's folder (WORK/review/<place>)")
    parser.add_argument("--only", help="the checks to run, comma separated: " + ",".join(CHECKS))
    options = parser.parse_args()
    stage = stage_path(options.place, options.stage, options.work_stage)
    if options.command == "check":
        for outcome in run_checks(options.place, stage, options.only.split(",") if options.only else CHECKS):
            print(f"{outcome['check']}: {outcome['result']}: {len(outcome['faults'])} faults {outcome['note']}".rstrip())
        return
    written = manifest(options.place, stage, options.review)
    for requirement in written["requirements"]:
        counted = " (experimental: its faults not counted)" if "experimental" in requirement else ""
        print(f"{requirement['name']:13} {requirement['result']:8} {requirement['why']}{counted}")
    print(done_line(options.place, written))
    sys.exit(0 if written["verdict"] in STATUS else 1)


if __name__ == "__main__":
    main()
