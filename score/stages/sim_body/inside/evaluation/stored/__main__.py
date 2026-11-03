"""Keep in SCORE's store what level 1 made before its pieces were kept there (#70, 2026-11-03).

    <python> score/stages/sim_body/inside/evaluation/stored import <seeds root> --src <the run's frozen src> \
        --cases <cases.json> [--start <the run's table.json> --python <Newton's or any Python with numpy>]
    <python> score/stages/sim_body/inside/evaluation/stored checkpoint <run dir> --src <src> [--every 3] [--card] [--exact]

`import` keeps each case of a seeds root (`evaluation.measured` at level 1's start, a seed_run.py) that holds
measures.json and m.json as a `cpu` piece: its point read from the root's own table.json, weights.json and rest.json,
its code from --src's inside/ (the code that made it), its files copied (the root is only read). With --start the
point is checked against level 1's start (`tuning.applied` at zero unknowns of that table, in --src's code) and
refused on any difference. It prints how many cases this tree's own code finds after it: a seed this tree would key
differently is said, never kept under this tree's key. `checkpoint` keeps a run folder's checkpoint.jsonl lines under
its run key as --src's level1.py computes it. Both may run again: a kept piece stays as it stands."""
import argparse
import json
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(INSIDE))
import evaluation  # noqa: E402
from evaluation import stored  # noqa: E402

START = """import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import landmarks, tuning
import numpy as np
table = json.loads(pathlib.Path(sys.argv[2]).read_text())
starts = {name: row["link"] for name, row in table.items()}
entries = tuning.layout(table, held=landmarks.HELD, joints=set())
rows, weights = tuning.applied(np.zeros(len(entries)), entries, starts, table, {"marker goal": 1.0, "end weight": 1.0})
print(json.dumps({"rows": rows, "weights": weights}))
"""


def start_point(python, inside, table):
    """(rows, weights) of level 1's start in `inside`'s own code (JSON round-tripped, as set_written writes them)."""
    done = subprocess.run([python, "-B", "-c", START, str(inside), str(table)], capture_output=True, text=True,
                          check=True)
    found = json.loads(done.stdout.strip().splitlines()[-1])
    return found["rows"], found["weights"]


def imported(store, root, inside, cases, start=None, python=None):
    """Each finished case of the seeds root kept as a `cpu` piece; {"kept", "skipped", "found here"}."""
    rows = json.loads((root / "table.json").read_text())
    weights = json.loads((root / "weights.json").read_text())
    rest = json.loads((root / "rest.json").read_text())
    if start is not None and json.loads(json.dumps(start_point(python, inside, start))) != [rows, weights]:
        raise SystemExit(f"{root}: its table.json or weights.json is not level 1's start of {start}: nothing kept")
    bodies = evaluation.by_body(cases)
    worker = inside / "evaluation" / "_case.py"
    keys = stored.keys(store, "cpu", worker, bodies, (rows, weights, rest), inside=inside)
    kept, skipped = [], []
    for case, key in sorted(keys.items()):
        folder = root / case
        if not ((folder / stored.SOLVED).is_file() and (folder / "m.json").is_file()):
            skipped.append(case)
            continue
        stored.kept(store, "cpu", key, folder, stored.made(imported_from=str(root), code_from=str(inside)),
                    case=case, body=evaluation.body_of(case), worker=worker.name)
        kept.append(case)
    here = stored.keys(store, "cpu", evaluation.WORKER, bodies, (rows, weights, rest))
    found_here = sum(stored.found(store, "cpu", key) is not None for key in here.values())
    return {"kept": len(kept), "skipped": skipped, "found here": found_here, "cases": len(cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    seeds = commands.add_parser("import")
    seeds.add_argument("root", type=pathlib.Path)
    seeds.add_argument("--src", type=pathlib.Path, required=True)
    seeds.add_argument("--cases", type=pathlib.Path, required=True)
    seeds.add_argument("--start", type=pathlib.Path)
    seeds.add_argument("--python", default=sys.executable)
    lines = commands.add_parser("checkpoint")
    lines.add_argument("run", type=pathlib.Path)
    lines.add_argument("--src", type=pathlib.Path, required=True)
    lines.add_argument("--every", type=int, default=3)
    lines.add_argument("--card", action="store_true")
    lines.add_argument("--exact", action="store_true")
    given = parser.parse_args()
    store = stored.default_store()
    inside = (given.src / "score/stages/sim_body/inside").resolve()
    if given.command == "import":
        cases = json.loads(given.cases.read_text())
        print(json.dumps(imported(store, given.root.resolve(), inside, cases, given.start, given.python)))
        return
    run = given.run.resolve()
    key = stored.run_key(inside / "evaluation" / "level1.py", json.loads((run / "table.json").read_text()),
                         json.loads((run / "split.json").read_text()), json.loads((run / "cases.json").read_text()),
                         run / "rig.npz", {"every": given.every, "card": given.card, "exact": given.exact},
                         inside=inside)
    print(json.dumps({"run": key, "lines": stored.lines_kept(store, key, run / "checkpoint.jsonl")}))


if __name__ == "__main__":
    main()
