"""Pixal3D's sampling steps by shape, settled before the batch (the owner, 2026-10-20: "lower Pixal3D settings where
the shape check allows"; #21's benchmark P2). The route is locked at LOCKED steps (#55, tools/props/pixal.py STEPS); a
shape runs at LOWER steps only when P2 measured every one of at least MIN_TAKES takes of that shape sort the same on
every check at both settings, and the owner said yes on #55 (OWNER_YES). Until both, every take runs at LOCKED: no
quality is traded on a guess.

P2, prepared here and never launched from here (benchmarks.py lists it under the EUR 20 cap):

    .venv/bin/python -m score.stages.complete.prepare.pixal_steps list <close-ups dir> <inventory.json> <out dir>
        one batch list, each chunky (solid, predict.shape_of) close-up twice, same seed: <row>-st12 and <row>-st8
    SCORE_SPEND_TICKET="override p2-steps" ~/.farm-factory-props/env/bin/python tools/props/cloud/batch.py \\
        <out dir>/list.txt --who "P2 benchmark" --inventory <inventory.json> --no-finish
        after the month's books are known and the owner's override yes (node override, key p2-steps) is given
    .venv/bin/python -m score.stages.complete.prepare.pixal_steps sort <models dir> <close-ups dir> <inventory.json>
        <out dir> [--scores likeness.json --least L]
        the free checks on both raw models of each take (shape check, outline) and pairs.json for DINOv2
        (tools/props/cloud/similar.py, paid, part of P2); with its scores and the place's least, sorted.json

Raw models on both sides (`--no-finish`): the finish is the same processor step for both, and it runs Blender here.
Each is judged in the frame the route's own check sees: a copy turned back from image-to-3dlab's +Z, stood upright and
levelled as pixal.stand_and_pad does (the shape check's spread reads the model's axis-aligned extents), against its
close-up cut as likeness_row cuts it (Pixal3D's own cut-out when the batch brought its camera folder back, else
likeness_row.cut_out; an uncut close-up dropped the engineroom core's outline from 0.76 to 0.46).

The batch runs every job once (#21 track A, landed: batch.py has no retry); a failed arm is a take P2 cannot tell,
never run again inside it.
"""
import argparse
import json
import pathlib

from score.stages.complete.prepare import predict

LOCKED = 12  # tools/props/pixal.py STEPS, the #55 lock (pixal_steps_test holds them equal)
LOWER = 8
SEED = 1
OWNER_YES = None  # the owner's dated yes on #55 to run a shape at LOWER where P2 sorted it the same; None: not given
MIN_TAKES = 3
MOST_TAKES = 6
CHUNKY = "solid"
CHECKS = ("thin and in proportion", "outline", "likeness")


def arm_name(row, steps):
    return f"{row}-st{steps}"


def chunky_rows(closeups, inventory):
    """The inventory's rows with a close-up in `closeups` whose size is CHUNKY, at most MOST_TAKES, by id."""
    found = [row for row in sorted(inventory["rows"], key=lambda row: row["id"])
             if (pathlib.Path(closeups) / f"{row['id']}.png").exists() and predict.shape_of(row.get("size")) == CHUNKY]
    return found[:MOST_TAKES]


def benchmark_lines(closeups, rows):
    """The batch list's lines: each row's close-up at LOCKED and at LOWER steps, same SEED."""
    return [f"{arm_name(row['id'], steps)} {pathlib.Path(closeups) / (row['id'] + '.png')} --seed {SEED} "
            f"--steps {steps}" for row in rows for steps in (LOCKED, LOWER)]


def told(passed):
    """A check's sort: "pass", "fail", or None when it could not tell."""
    return None if passed is None else "pass" if passed else "fail"


def arm_sorts(entry, scores, least):
    """{check: "pass" | "fail" | None} of one model's measured entry ({shape_pass, outline}) and its DINOv2 score."""
    import score.stages.props.likeness as likeness
    likeness_score = scores.get(entry["name"])
    return {"thin and in proportion": told(entry["shape_pass"]),
            "outline": told(entry["outline"] >= likeness.OUTLINE_LEAST),
            "likeness": told(None if likeness_score is None or least is None else likeness_score >= least)}


def take_verdict(locked, lower):
    """{same, untold}: whether every check sorts one take the same at both settings, and the checks that could not
    tell at either."""
    untold = [check for check in CHECKS if locked[check] is None or lower[check] is None]
    return {"same": not untold and all(locked[check] == lower[check] for check in CHECKS), "untold": untold}


def shape_verdict(takes):
    """{steps, takes, why} of one shape from its takes' verdicts: LOWER only when at least MIN_TAKES were told on
    every check and every one sorted the same, else LOCKED and why."""
    if len(takes) < MIN_TAKES:
        return {"steps": LOCKED, "takes": len(takes), "why": f"{len(takes)} takes measured, under {MIN_TAKES}"}
    untold = sorted({check for verdict in takes.values() for check in verdict["untold"]})
    if untold:
        return {"steps": LOCKED, "takes": len(takes), "why": f"could not tell: {', '.join(untold)}"}
    differ = sorted(row for row, verdict in takes.items() if not verdict["same"])
    if differ:
        return {"steps": LOCKED, "takes": len(takes), "why": f"sorted otherwise at {LOWER} steps: {', '.join(differ)}"}
    return {"steps": LOWER, "takes": len(takes), "why": f"every take sorted the same at {LOWER} and {LOCKED} steps"}


def sorted_same(sorts, shapes):
    """{shape: shape_verdict} of P2's sorts ({row: {LOCKED: arm_sorts, LOWER: arm_sorts}}), `shapes` {row: shape}."""
    by_shape = {}
    for row, arms in sorted(sorts.items()):
        by_shape.setdefault(shapes[row], {})[row] = take_verdict(arms[LOCKED], arms[LOWER])
    return {shape: shape_verdict(takes) for shape, takes in by_shape.items()}


def benchmark_euros(per_unit, likeness_euros):
    """{likely_euros, high_euros} of P2: MOST_TAKES takes twice at pixal's measured per unit with the bill share
    (estimate.layer_price's rule for a card layer), and DINOv2's pairs."""
    from score.stages.complete.holes import price
    runs = MOST_TAKES * 2 * price.BILL_SHARE
    return {"likely_euros": round(runs * per_unit["likely_euros"] + likeness_euros, 2),
            "high_euros": round(runs * per_unit["high_euros"] + likeness_euros, 2)}


def record():
    """The prepare record's Pixal3D steps: the lock, the lower setting P2 tests and the owner's yes. Nothing reads a
    lower setting into a take's batch line yet: that wiring lands with the owner's yes; every take runs at LOCKED."""
    return {"locked": LOCKED, "lower": LOWER, "owner_yes": OWNER_YES, "benchmark": "P2",
            "why": "a shape runs lower only where P2 sorts it the same on " + ", ".join(CHECKS)
                   + " and the owner said yes on #55"}


# --- the commands: free and local ----------------------------------------------------------------------------------

def write_list(closeups, inventory_path, out):
    """P2's batch list in `out` (list.txt): its path and the rows in it."""
    rows = chunky_rows(closeups, json.loads(pathlib.Path(inventory_path).read_text()))
    if len(rows) < MIN_TAKES:
        raise SystemExit(f"{len(rows)} chunky close-ups in {closeups}; P2 needs at least {MIN_TAKES}")
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "list.txt").write_text("\n".join(benchmark_lines(closeups, rows)) + "\n")
    return out / "list.txt", [row["id"] for row in rows]


def stood(raw, folder):
    """A copy of a raw model in `folder` in the frame the route checks: turned back to Pixal3D's -Z
    (pixal.facing_back), stood upright and levelled as pixal.stand_and_pad does with no --long, --feet or --tube (P2's
    lines and the route's own pass none); its path."""
    import shutil
    from score.stages.props import prop_data
    with prop_data.tools("props"):
        import glb_file
        import pixal
    folder.mkdir(parents=True, exist_ok=True)
    copy = folder / pathlib.Path(raw).name
    shutil.copyfile(raw, copy)
    pixal.facing_back(copy)
    document, views = glb_file.read(copy)
    glb_file.turned(document, views, glb_file.upright_turn(glb_file.positions(document, views)))
    glb_file.turned(document, views, glb_file.level_turn(*glb_file.faces(document, views)))
    glb_file.write(document, views, copy)
    return copy


def route_cut(closeup, model, folder):
    """The close-up as likeness_row's check cuts it: Pixal3D's own cut-out of this take when its camera folder came
    back (likeness_row.pixal_cut), else likeness_row.cut_out."""
    import score.stages.props.likeness_row as likeness_row
    name = pathlib.Path(model).stem
    kept = pathlib.Path(model).with_suffix(".svviews") / "input.png"
    return likeness_row.pixal_cut(kept, folder, name) if kept.exists() else likeness_row.cut_out(closeup, folder)


def measure_arm(model, closeup, size, kind, out):
    """{name, shape_pass, outline, pair} of one raw model against its close-up, both as the route's check sees them:
    the free checks, no renderer."""
    import score.stages.props.likeness as likeness
    import score.stages.props.likeness_row as likeness_row
    name = pathlib.Path(model).stem
    cut = route_cut(closeup, model, out / "cuts")
    upright = stood(model, out / "stood")
    best = likeness.best_way(upright, cut)
    checks = likeness_row.model_checks(upright, size, kind, False)
    return {"name": name, "shape_pass": checks["model_check"]["pass"], "outline": best["outline"],
            "pair": likeness.write_pair(upright, cut, best["way"], out / "pairs", name)}


def measure(models, closeups, inventory_path, out):
    """{row: {steps: measure_arm}} of every chunky row with both raw models in `models`; pairs.json in `out`."""
    inventory = json.loads(pathlib.Path(inventory_path).read_text())
    out = pathlib.Path(out)
    found = {}
    for row in chunky_rows(closeups, inventory):
        arms = {steps: pathlib.Path(models) / f"{arm_name(row['id'], steps)}.glb" for steps in (LOCKED, LOWER)}
        if not all(path.exists() for path in arms.values()):
            continue
        closeup = pathlib.Path(closeups) / f"{row['id']}.png"
        found[row["id"]] = {steps: measure_arm(path, closeup, row["size"], f"{inventory['place']}_{row['id']}", out)
                            for steps, path in arms.items()}
    (out / "pairs.json").write_text(json.dumps({arm["name"]: arm["pair"] for arms in found.values()
                                                for arm in arms.values()}, indent=1) + "\n")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    sorting = commands.add_parser("sort")
    sorting.add_argument("models", type=pathlib.Path)
    for each in (listing, sorting):
        each.add_argument("closeups", type=pathlib.Path)
        each.add_argument("inventory", type=pathlib.Path)
        each.add_argument("out", type=pathlib.Path)
    sorting.add_argument("--scores", type=pathlib.Path, help="similar.py's out.json for pairs.json")
    sorting.add_argument("--least", type=float, help="the place's DINOv2 least (likeness-calibration)")
    options = parser.parse_args(argv)
    if options.command == "list":
        path, rows = write_list(options.closeups, options.inventory, options.out)
        print(f"P2: {len(rows)} chunky takes at {LOCKED} and {LOWER} steps, seed {SEED}; {path}")
        return
    found = measure(options.models, options.closeups, options.inventory, options.out)
    scores = json.loads(options.scores.read_text()) if options.scores else {}
    sorts = {row: {steps: arm_sorts(arm, scores, options.least) for steps, arm in arms.items()}
             for row, arms in found.items()}
    inventory = json.loads(options.inventory.read_text())
    shapes = {row["id"]: predict.shape_of(row.get("size")) for row in inventory["rows"]}
    result = {"sorts": sorts, "shapes": sorted_same(sorts, shapes), "owner_yes": OWNER_YES}
    (options.out / "sorted.json").write_text(json.dumps(result, indent=1) + "\n")
    print("; ".join(f"{shape}: {verdict['steps']} steps ({verdict['why']})"
                    for shape, verdict in result["shapes"].items()) or "P2: no take with both models",
          f"{options.out / 'sorted.json'}")


if __name__ == "__main__":
    main()
