"""Write each place's holes: what its route still needs, over its accepted stage, for the creator cockpit:

    .venv/bin/python -m score.stages.complete.holes [--place P ...] [--out FOLDER] [--data FOLDER]

For each place, <out>/<place>/: stage/ (the accepted stage, its neighbours output where it has one, else its
assembly, laid out as links to the stored bytes), holes.usda (the holes layer over it: layers/holes.usda, then
./stage/<place>.usda; the holes layer alone when no assembly stands accepted) and findings.json:

    {"place", "answer", "outputs": {neighbours@P, assembly@P, plan@P, complete@P: each its accepted output or null},
     "counts": {"missing", "gate", "place"},
     "findings": [{"id", "rule", "prim", "kind", "sentence", "picture": null, "row", "gates", "source", "node",
                   "work", "placed", "low", "high"}]}

    id      missing:<row>_<n>, gate:<stage>/<gate>:<object>, place:concept|plan|rough-model or
            place:lost:<kind>:<item>, stable run to run
    rule    missing (a scene inventory row with nothing made for it), gate (a made object a written fault names)
            or place (a step of the route the place has not been through, or an input its line reads that is lost
            and no row makes: inputs.py, read from the stage table over the repository's data only)
    source  inventory, check:<name>, gap:<name>, judgement:<node> or route
    node    the node that fills it (`<stage>@<place>`, or a world stage's name), else null and `work` its code work
    placed  a missing object's: spot, wall, on or unplaced; null for the rest
    low, high  its world box ([x, y, z]), or null

The default out is WORK/checks/holes, where the cockpit reads it; the other checks' findings are read beside it.
Reads the store, the scene inventories, kits, plans and named gaps, and the checks already written; judges nothing,
writes nothing to the store. Free and local, seconds a place. Prints one line a place and one summary line, and
fails loudly on a findings.json that breaks the contract above (holes_faults) and on a box with no store.
"""
import argparse
import json
import pathlib
import shutil

from pxr import UsdGeom

from score.stages.assembly import stage_file
from score.stages.complete.holes import fill, inputs, layer, marks, route, rows
from score.stages.complete.library import stored
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[4]
OUT = PROPS_HOME / "work/checks/holes"
DATA = REPO / "data"
FINDINGS = "findings.json"
STAGE = "stage"
MISSING, GATE, PLACE = "missing", "gate", "place"
RULES = (MISSING, GATE, PLACE)
SOURCES = ("neighbours", "assembly")  # the stage the holes stand over: the first accepted
STEP_SENTENCES = {fill.CONCEPT: "no concept is picked for this place",
                  fill.PLAN: "this place's plan is not accepted",
                  fill.ROUGH_MODEL: "this place has no rough model"}


def accepted_stage(store, place):
    """(node, output) of the place's accepted stage, its neighbours output before its assembly; (None, None)."""
    for stage in SOURCES:
        output = store.accepted(f"{stage}@{place}")
        if output:
            return f"{stage}@{place}", output
    return None, None


def laid(store, output, folder):
    """The accepted stage's root file, laid out afresh under folder/stage as links to its stored bytes."""
    shutil.rmtree(folder / STAGE, ignore_errors=True)
    return stage_file(stored.laid_out(store, output, folder / STAGE))


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def missing_holes(stage, place, written, kit):
    """Each missing object's box written, and its finding (its box's bounds read once the layer is whole)."""
    found = []
    for box in rows.boxes(stage, place, written, kit, rows.missing(stage, place, written)):
        row = box["row"]
        node, work = fill.missing_row(row, place, bool(rows.kit_pieces(row, kit)))
        values = {"score:hole": MISSING, "score:hole:row": row["id"], "score:hole:placed": box["placed"],
                  "score:kind": row.get("kind", ""), "score:anchor": str(row.get("anchor", "")),
                  **({"score:hole:node": node} if node else {"score:hole:work": work})}
        layer.write_box(stage, box, values)
        sentence = f"{row.get('name') or row['id']}: nothing made for it yet ({row.get('made') or row.get('kind')})"
        if box["placed"] == rows.UNPLACED:
            sentence += "; the inventory gives it no spot"
        found.append({"id": f"{MISSING}:{box['name']}", "rule": MISSING, "prim": box["path"],
                      "kind": row.get("kind"), "sentence": sentence, "picture": None, "row": row["id"], "gates": [],
                      "source": "inventory", "node": node, "work": work, "placed": box["placed"],
                      "bounds": (f"{box['path']}/{layer.BOX}", [UsdGeom.Tokens.guide])
                      if box["placed"] != rows.UNPLACED else None})
    return found


def gate_holes(stage, place, store, data, own, row_ids):
    """Each object a written fault names, marked on its prims, and its finding."""
    found = marks.judged(store, place) + marks.checked(own, place, store) + marks.gapped(data, place)
    holes = []
    for hole in marks.holes(stage, place, found):
        for path in hole["prims"]:
            layer.write_mark(stage, path, hole["gates"])
        more = len(hole["sentences"]) - 1
        prim = hole["prims"][0] if hole["prims"] else None
        holes.append({"id": f"{GATE}:{hole['gates'][0]}:{hole['object']}", "rule": GATE, "prim": prim,
                      "kind": hole["kind"],
                      "sentence": hole["sentences"][0] + (f" (and {more} more)" if more else ""), "picture": None,
                      "row": hole["object"] if hole["object"] in row_ids else None, "gates": hole["gates"],
                      "source": hole["source"], "node": hole["node"],
                      "work": "; ".join(hole["works"]) if hole["node"] is None else None, "placed": None,
                      "bounds": (prim, layer.SEEN) if prim else None})
    return holes


def place_holes(stage, place, store, written, plan):
    """Each step of the route the place lacks, on its root, and its finding."""
    kinds = route.missing(store, place, written, plan)
    layer.write_place(stage, place, kinds)
    found = []
    for kind in kinds:
        node, work = fill.place_step(kind, place, route.wanted(kind, place))
        found.append({"id": f"{PLACE}:{kind}", "rule": PLACE, "prim": f"/{place}", "kind": None,
                      "sentence": STEP_SENTENCES[kind], "picture": None, "row": None, "gates": [], "source": "route",
                      "node": node, "work": work, "placed": None, "bounds": None})
    return found


def lost_holes(runner, place):
    """Each input the place's line reads that is lost and no row makes (inputs.lost), on its root, as a place hole
    with its code work."""
    return [{"id": f"{PLACE}:{hole['id']}", "rule": PLACE, "prim": f"/{place}", "kind": None,
             "sentence": hole["sentence"], "picture": None, "row": None, "gates": [], "source": "inputs",
             "node": None, "work": hole["work"], "placed": None, "bounds": None} for hole in inputs.lost(runner, place)]


def bounded(stage, finding):
    """A finding with its world box (`low`, `high`) in place of where to read it."""
    where = finding.pop("bounds")
    low, high = layer.bounds(stage, *where) if where else (None, None)
    return dict(finding, low=low, high=high)


def holes_faults(written):
    """Each way a findings.json breaks its contract: an unknown rule, node and work both or neither, one of low and
    high alone, a duplicate id."""
    found, seen = [], set()
    for item in written["findings"]:
        if item["rule"] not in RULES:
            found.append(f"{item['id']}: unknown rule {item['rule']!r}")
        if (item.get("node") is None) == (item.get("work") is None):
            found.append(f"{item['id']}: needs exactly one of node and work")
        if (item.get("low") is None) != (item.get("high") is None):
            found.append(f"{item['id']}: has only one of low and high")
        if item["id"] in seen:
            found.append(f"{item['id']}: duplicate id")
        seen.add(item["id"])
    return found


def outputs_read(store, place):
    """{node: accepted output or None} of every node the holes were read against: the stages they may stand over,
    the place's plan and its complete row; one accepted later then fails the cockpit's current-findings test."""
    return {node: store.accepted(node) for node in (*(f"{stage}@{place}" for stage in SOURCES), f"plan@{place}",
                                                    f"complete@{place}")}


def written_place(store, place, data, folder, runner=None):
    """Work out one place's holes and write holes.usda and findings.json; findings.json as written. `runner`: the
    stage table's, for the lost inputs (the table reads the repository's data, so none for another data folder)."""
    folder.mkdir(parents=True, exist_ok=True)
    _, output = accepted_stage(store, place)
    stage = layer.opened(folder, place, laid(store, output, folder) if output else None)
    inventory = rows.inventory(data, place)
    kit = read(data / "kit" / f"{place}.json") or {}
    row_ids = {row["id"] for row in (inventory or {}).get("rows", [])}
    found = (missing_holes(stage, place, inventory, kit)
             + gate_holes(stage, place, store, data, folder.parent, row_ids)
             + place_holes(stage, place, store, inventory, read(data / "plans" / f"{place}.json"))
             + (lost_holes(runner, place) if runner is not None else []))
    layer.saved(stage)
    findings = [bounded(stage, finding) for finding in found]
    written = {"place": place, "answer": "fail" if findings else "pass",
               "outputs": outputs_read(store, place),
               "counts": {rule: sum(item["rule"] == rule for item in findings) for rule in RULES},
               "findings": findings}
    faults = holes_faults(written)
    if faults:
        raise SystemExit(f"{place}: the holes break their contract: " + "; ".join(faults[:5]))
    (folder / FINDINGS).write_text(json.dumps(written, indent=1))
    return written


def places_of(chosen):
    """The places asked for, else every place of environment 1."""
    if chosen:
        return chosen
    from score import stages
    return stages.places(stages.world1())


def summary_line(written):
    counts = written["counts"]
    over = next((node for node, output in written["outputs"].items()
                 if output and node.split("@", 1)[0] in SOURCES), "no accepted stage")
    return f"{written['place']}: {counts[MISSING]} missing, {counts[GATE]} gate, {counts[PLACE]} place; over {over}"


def existing_store():
    """The framework's store, read only; fails loudly when it has no objects folder, since an absent store would
    read as nothing made and every inventory row as missing."""
    objects = PROPS_HOME / "store/objects"
    if not objects.is_dir():
        raise SystemExit(f"no store at {objects.parent}: the holes need the accepted outputs")
    return stored.reading()


def table_runner(store):
    """The stage table's runner over environment 1, on the store read."""
    from score import stages
    return stages.runner(store=store)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--place", action="append", default=[])
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--data", type=pathlib.Path, default=DATA, help="the environment's data folder")
    options = parser.parse_args(argv)
    store = existing_store()
    totals = dict.fromkeys(RULES, 0)
    places = places_of(options.place)
    table = table_runner(store) if options.data.resolve() == DATA.resolve() else None
    for place in places:
        written = written_place(store, place, options.data, options.out / place, table)
        for rule in RULES:
            totals[rule] += written["counts"][rule]
        print(summary_line(written), flush=True)
    print(f"{len(places)} places: {totals[MISSING]} missing, {totals[GATE]} gate, {totals[PLACE]} place holes; "
          f"{options.out}")


if __name__ == "__main__":
    main()
