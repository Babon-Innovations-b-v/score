"""One batch of props through the upgraded prop route: N props in, a manifest out, a record per prop, and the cost
per prop priced before and measured after, from the ledgers' own numbers.

    python3 tools/props/cloud/prop_batch.py price <props.json> [--previous <manifest.json>] [--ledger <file> ...]
        [--out <plan.json>]                       # free: likely and high euros per step and per prop, one line out
    ~/.farm-factory-props/env/bin/python tools/props/cloud/prop_batch.py run <props.json> --yes [--folder <dir>]
        # paid: prints the price as above, then makes the batch through the real runners (prop_makers.py); refused
        # without --yes and outside a cleared run or the owner's override (SCORE_SPEND_TICKET)

props.json is a list of {"name": <take>, "place": <place>, "picture": <path or null>, "body": <body or null>,
"keep": [<step>, ...]}; a kept step (a close-up that stands, say) is neither made nor paid again for that prop.

The route (owner, PRD #10, 2026-10-18): a code-built body for the big shapes, the picture model's geometry kept for
the detail, every finish from the library. Its paid steps (STEPS) run each as one batch over every prop still in the
batch, on the step's cheapest measured card, as many props to a card as it runs at once; a free check runs before
every paid step, so a prop that fails stops there and pays nothing more. A prop whose inputs and route did not change
since the previous manifest is kept, not made again. What was dropped from today's line: the turntable, the finish
maps, SegviGen and the paint, which split a model by its picture colours; a body's parts come from its code and the
kept detail takes one library finish each (the finish pick, a text ask).

Prices come from measured numbers only: a card step from preflight.measured over its kind's machines of its card type
(the job seconds, median and high, the set-up, the euros a card-minute), a Google step from that caller's finished
calls on the Google ledger (median and high euros a call), each step's success share from its batches' made against
asked. A step with too few measured machines or calls is said as unmeasured and priced at nothing; never guessed.
The live ledger was reset on 2026-10-17, so the repo's evidence copy (paper/evidence/cloud/ledger.jsonl) is read with
it by default, and any older copy can be added with --ledger.

`run` drives the batch with the makers and checks it is given (a maker makes one step for a list of props as one
batch; `run` the command gives it prop_makers.py's, the real runners); `measured_costs` splits each paid batch's ledger euros over the
props it made, by each job's seconds where the line names them, else evenly.

Not imported by any stage, so a change here re-keys no row.
"""
import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import statistics
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capacity  # noqa: E402
import preflight  # noqa: E402
from paths import HOME  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
ROUTE_VERSION = "body-detail-library-1"
EVIDENCE_LEDGER = REPO / "paper/evidence/cloud/ledger.jsonl"
GOOGLE_LEDGER = HOME / "cloud" / "google-ledger.jsonl"
# The provider's bill over the ledger's sum for 2026-10 up to 2026-10-10 (EUR 627.74 against 547.31: disks,
# addresses, storage and registry; paper/evidence/cloud/cost-tables-2026-10.txt). Card steps are priced with it.
BILL_SHARE = 627.74 / 547.31
MEASURED_CALLS = 10  # finished Google calls of a caller before its price counts as measured
CAP = 20  # cards a step may take at once (capacity.run_cap's default)


@dataclasses.dataclass(frozen=True)
class Step:
    """One paid step of the route: `kind` is the ledger kind (a card step) or the Google caller its numbers come
    from, `card` the card type it takes, `slots` the props a card runs at once, `tries` the asks a prop may take, and
    `check` the free check that runs before it."""
    name: str
    kind: str
    google: bool = False
    card: str = ""
    slots: int = 1
    tries: int = 1
    check: str = ""


STEPS = (
    Step("closeup", "pro", google=True, tries=2, check="the box gate (props-inputs)"),
    Step("image-to-3d", "pixal", card="L4", slots=capacity.RUNS_PER_24GB["pixal"],
         check="the close-up's shape check"),
    Step("finish-pick", "finishmap-list", google=True, check="the raw model against its close-up (gates/model.py)"),
    Step("bake", "library", card="L4", check="every part named to a library surface"),
)
FINAL_CHECK = "bake_check and the library check, free"


def read_lines(path):
    """A JSON-lines file's rows, a broken line skipped ([] for no file)."""
    path = pathlib.Path(path)
    if not path.is_file():
        return []
    found = []
    for text in path.read_text().splitlines():
        try:
            found.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return found


def cloud_lines(paths):
    """The cloud ledgers' rows, each batch once however many copies hold it."""
    seen, found = set(), []
    for path in paths:
        for row in read_lines(path):
            key = (row.get("batch"), row.get("started"), row.get("kind"))
            if key not in seen:
                seen.add(key)
                found.append(row)
    return found


def card_numbers(lines, kind, card):
    """A card step's measured numbers (preflight.measured) from its kind's machines of card type `card`, or None."""
    chosen = []
    for row in lines:
        machines = [machine for machine in row.get("machines") or () if (machine.get("type") or "").startswith(card)]
        if row.get("kind") == kind and machines:
            chosen.append({**row, "machines": machines, "ticket": f"{kind}@all measured"})
    return preflight.measured(chosen, kind)


def success_share(lines, kind):
    """The share of asked jobs a kind's batches made (models_done over models), 1.0 where none says."""
    asked = sum(row["models"] for row in lines if row.get("kind") == kind and row.get("models"))
    made = sum(row.get("models_done", 0) for row in lines if row.get("kind") == kind and row.get("models"))
    return made / asked if asked else 1.0


def call_numbers(google_lines, caller):
    """A Google caller's finished calls: {calls, euros, high_euros} a call, or None under MEASURED_CALLS."""
    euros = [row["euros"] for row in google_lines
             if row.get("caller") == caller and row.get("state") in (None, "finished") and "euros" in row]
    if len(euros) < MEASURED_CALLS:
        return None
    return {"calls": len(euros), "euros": statistics.median(euros), "high_euros": preflight.quantile(euros, preflight.HIGH)}


def resolved(pattern):
    """A data file's path as a path: {home} (the props home), {data} and {repo} filled in, ~ expanded."""
    text = str(pattern).replace("{home}", str(HOME)).replace("{data}", str(REPO / "data")).replace("{repo}", str(REPO))
    return pathlib.Path(text).expanduser()


def file_hash(path):
    """A file's sha256, or None for no path or a missing file."""
    if not path or not resolved(path).is_file():
        return None
    return hashlib.sha256(resolved(path).read_bytes()).hexdigest()


def prop_key(prop):
    """What a prop is made from: its fields, its picture's bytes and the route's version."""
    text = json.dumps({**prop, "picture_hash": file_hash(prop.get("picture")), "route": ROUTE_VERSION}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()


def to_make(props, previous):
    """The props a batch makes: every one whose key is not a finished prop of the previous manifest."""
    done = {name: record["key"] for name, record in (previous or {}).get("props", {}).items()
            if record.get("status") == "done"}
    return [prop for prop in props if done.get(prop["name"]) != prop_key(prop)]


def makes_step(prop, step):
    """True when the batch makes `step` for `prop` (the prop does not keep that step's output)."""
    return step.name not in prop.get("keep", ())


def step_price(step, jobs, lines, google_lines):
    """One step's likely and high euros for `jobs` props: {likely, high, measured}; likely asks each prop's job again
    at the step's measured failure share, high asks twice that and takes the high job time (or call price)."""
    if jobs == 0:
        return {"likely": 0.0, "high": 0.0, "measured": True}
    if step.google:
        numbers = call_numbers(google_lines, step.kind)
        if numbers is None:
            return {"likely": 0.0, "high": 0.0, "measured": False}
        return {"likely": round(jobs * numbers["euros"], 4),
                "high": round(jobs * step.tries * numbers["high_euros"], 4), "measured": numbers}
    numbers = card_numbers(lines, step.kind, step.card)
    if numbers is None:
        return {"likely": 0.0, "high": 0.0, "measured": False}
    failed = 1.0 - success_share(lines, step.kind)
    likely_jobs, high_jobs = math.ceil(jobs * (1 + failed)), math.ceil(jobs * (1 + 2 * failed))
    likely = preflight.batch(likely_jobs, numbers, CAP, step.slots)
    high = preflight.batch(high_jobs, numbers, CAP, step.slots)
    return {"likely": round(likely["euros"] * BILL_SHARE, 4), "high": round(high["high_euros"] * BILL_SHARE, 4),
            "cards": likely["cards"], "minutes": likely["minutes"], "high_minutes": high["high_minutes"],
            "failed_share": round(failed, 3), "measured": numbers}


def price(props, lines, google_lines, previous=None):
    """The batch's pre-flight: the props it makes and keeps, each step's price, the per-prop and whole likely and
    high euros, and the steps still unmeasured."""
    making = to_make(props, previous)
    steps = {step.name: step_price(step, sum(makes_step(prop, step) for prop in making), lines, google_lines)
             for step in STEPS}
    likely = round(sum(step["likely"] for step in steps.values()), 2)
    high = round(sum(step["high"] for step in steps.values()), 2)
    count = max(len(making), 1)
    return {"route": ROUTE_VERSION, "props": len(props), "making": [prop["name"] for prop in making],
            "kept": len(props) - len(making), "steps": steps, "likely": likely, "high": high,
            "per_prop": {"likely": round(likely / count, 3), "high": round(high / count, 3)},
            "unmeasured": [name for name, step in steps.items() if step["measured"] is False]}


def record_path(out, name):
    return pathlib.Path(out) / "records" / f"{name}.json"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n")


def run(props, makers, checks, out, previous=None):
    """Make the batch: for each step, the free check on every prop still in it, then the step's maker once for all
    that passed (makers[name](props) -> {name: {"batch": <ledger batch>, ...}}, a prop missing from the answer
    failed). Writes out/records/<name>.json per prop and out/manifest.json, and returns the manifest."""
    manifest = {"route": ROUTE_VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "props": {}}
    making = to_make(props, previous)
    for prop in props:
        kept = prop not in making
        old = (previous or {}).get("props", {}).get(prop["name"], {})
        manifest["props"][prop["name"]] = {**old, "kept": True} if kept else {
            "key": prop_key(prop), "place": prop.get("place"), "status": "making", "steps": {}}
    alive = list(making)
    for step in STEPS:
        passed = []
        for prop in alive:
            ok, why = checks[step.name](prop)
            if ok:
                passed.append(prop)
            else:
                manifest["props"][prop["name"]].update(status="stopped", at=step.name, why=why)
        wanted = [prop for prop in passed if makes_step(prop, step)]
        made = makers[step.name](wanted) if wanted else {}
        alive = []
        for prop in passed:
            record = manifest["props"][prop["name"]]
            if not makes_step(prop, step):
                record["steps"][step.name] = {"kept": True}
                alive.append(prop)
            elif prop["name"] in made:
                record["steps"][step.name] = made[prop["name"]]
                alive.append(prop)
            else:
                record.update(status="failed", at=step.name)
    for prop in alive:
        manifest["props"][prop["name"]]["status"] = "done"
    for name, record in manifest["props"].items():
        write_json(record_path(out, name), record)
    write_json(pathlib.Path(out) / "manifest.json", manifest)
    return manifest


def batch_shares(line, names):
    """{name: share} of one ledger line's euros among the props it made: by job seconds where the line names its jobs,
    else evenly."""
    seconds = {name: line.get("job_seconds", {}).get(name) or 0 for name in names}
    total = sum(seconds.values())
    if total:
        return {name: value / total for name, value in seconds.items()}
    return {name: 1 / len(names) for name in names}


def measured_costs(manifest, lines, google_lines=()):
    """{name: {step: euros, "total": euros}}: each paid batch's ledger euros (cloud lines by batch, Google lines by
    call) split over the props that step made."""
    by_batch = {}
    for name, record in manifest["props"].items():
        for step, made in record.get("steps", {}).items():
            by_batch.setdefault(made.get("batch"), []).append((name, step))
    euros = {line.get("batch"): line.get("euros", 0.0) for line in lines}
    euros.update({line.get("call"): line.get("euros", 0.0) for line in google_lines if line.get("state") == "finished"})
    found = {name: {"total": 0.0} for name in manifest["props"]}
    for batch, takers in by_batch.items():
        if batch not in euros:
            continue
        line = next((line for line in lines if line.get("batch") == batch), {})
        shares = batch_shares(line, [name for name, _ in takers])
        for name, step in takers:
            cost = round(euros[batch] * shares[name], 4)
            found[name][step] = round(found[name].get(step, 0.0) + cost, 4)
            found[name]["total"] = round(found[name]["total"] + cost, 4)
    return found


def previous_manifest(path, folder):
    """The manifest a batch keeps from: the one named, else the batch folder's own from its last run, else None."""
    found = pathlib.Path(path) if path else folder / "manifest.json"
    return json.loads(found.read_text()) if path or found.exists() else None


def run_paid(props, previous, folder, yes):
    """The batch through the real makers (prop_makers.py), only with the owner's yes (--yes) and a cleared run or his
    override (SCORE_SPEND_TICKET); refused before any check or rent otherwise."""
    if not yes:
        raise SystemExit("not run: nothing is paid without --yes, the owner's yes to the price above")
    sys.path.insert(0, str(REPO))
    from score.adapters import compute
    compute.require_cleared("a prop batch")
    import prop_makers
    manifest = run(props, prop_makers.makers_for(folder, f"prop-batch {folder.name}"), prop_makers.checks_for(folder),
                   folder, previous)
    done = sum(record.get("status") == "done" or record.get("kept", False) for record in manifest["props"].values())
    print(f"{done} of {len(props)} props done; records and manifest in {folder}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("price", "run"))
    parser.add_argument("props")
    parser.add_argument("--previous")
    parser.add_argument("--ledger", action="append", default=[])
    parser.add_argument("--out")
    parser.add_argument("--folder", type=pathlib.Path, help="the batch's folder (default: prop-batches/<props file "
                        "name> in the props home); its manifest is the previous one unless --previous names another")
    parser.add_argument("--yes", action="store_true", help="run: the owner said yes to the price printed")
    args = parser.parse_args()
    props = json.loads(pathlib.Path(args.props).read_text())
    folder = args.folder or HOME / "prop-batches" / pathlib.Path(args.props).stem
    previous = previous_manifest(args.previous, folder)
    lines = cloud_lines([EVIDENCE_LEDGER, HOME / "cloud" / "ledger.jsonl", *args.ledger])
    plan = price(props, lines, read_lines(GOOGLE_LEDGER), previous)
    if args.out:
        write_json(pathlib.Path(args.out), plan)
    print(f"{len(plan['making'])} of {plan['props']} props to make, EUR {plan['likely']} likely, {plan['high']} high "
          f"(per prop {plan['per_prop']['likely']} / {plan['per_prop']['high']}); unmeasured: "
          f"{', '.join(plan['unmeasured']) or 'none'}" + (f"; wrote {args.out}" if args.out else ""), flush=True)
    if args.command == "run":
        run_paid(props, previous, folder, args.yes)


if __name__ == "__main__":
    main()
