"""The library rows' gate: the world's outputs are in the library, by construction.

    configured   a library is configured, or the world is library-free (data/checks/library-free.json: an owner's
                 dated decision, each row {world, why, who, when})
    handed       every accepted output the node read (reads.json) is covered, with entries or a written exception, or
                 held through what it was made into: an output no exporter takes on its own (a finish route's list,
                 a light layer) is held by an entry of a row read here that is made from it (its `into`), and a
                 world output the places' rows are made from (its `beyond`) by those places' own library nodes
    refused      the library refused nothing
    traced       the library-finish check (score/stages/complete/library, wrapped in traced.py) finds nothing in the
                 place's assembled stage that is not a library entry or a written exception; every finish a library
                 surface (unknown with no library folder to trace to)
    copies       every model, layer, place and character entry has its 3D copy (unknown, naming each, otherwise)
    quality      every entry has its quality score (unknown, naming each, otherwise)
    saved        the library committed the handover (a failed push alone passes: the cockpit shows it)

Unknown blocks like fail. An accepted gap does not apply here: the library rule has its own exceptions file.
"""
import json
import pathlib

from score import checks
from score.stages.library import backend, handover

COPIED_KINDS = ("model", "layer", "place", "character")
SHOWN = 12  # findings named in a reason


def declared(inputs, name):
    """A declared world file's content, or None when the node does not declare it."""
    return json.loads(pathlib.Path(inputs[name]).read_text()) if name in inputs else None


def world_of(inputs):
    return declared(inputs, "world record")["name"]


def library_free(inputs):
    """The owner's library-free decision for this world, or None."""
    decisions = (declared(inputs, "library free") or {}).get("worlds", [])
    return next((row for row in decisions if row.get("world") == world_of(inputs)
                 and all(str(row.get(field) or "").strip() for field in ("why", "who", "when"))), None)


def exception_names(inputs):
    """The names an exception of library-exceptions.json answers to: its `id`, else its prim."""
    written = (declared(inputs, "exceptions") or {}).get("exceptions", [])
    return {str(row.get("id") or row.get("prim")) for row in written}


def listed(found):
    """The first findings in one reason."""
    return "; ".join(found[:SHOWN]) + (f" (and {len(found) - SHOWN} more)" if len(found) > SHOWN else "")


def verdict(name, found, failing, passing):
    """A check's verdict from its findings: `failing` (an answer) with them listed, else pass with `passing`."""
    if not found:
        return checks.Verdict(name, checks.PASS, passing, {"faults": 0}, {"faults": "lower"})
    return checks.Verdict(name, failing, f"{len(found)}: {listed(found)}", {"faults": len(found)},
                          {"faults": "lower"}, tuple(found))


def free_pass(name, inputs):
    """A pass for a library-free world, its decision named; None for any other world."""
    decision = library_free(inputs)
    if decision is None:
        return None
    return checks.Verdict(name, checks.PASS, f"{decision['world']} is library-free ({decision['why']}, "
                                             f"{decision['who']}, {decision['when']})")


def judge_configured(output, inputs, evidence):
    report = handover.report(output)
    if report["backend"] != "none":
        return checks.Verdict("configured", checks.PASS, f"handed to the {report['backend']} library "
                                                         f"{report['library'] or '(no identity)'}")
    return free_pass("configured", inputs) or checks.Verdict("configured", checks.FAIL, handover.NO_LIBRARY)


def holding(output):
    """The rows read here whose output an entry holds (their covered row names entries)."""
    reads = {(read["node"], read["output"]) for read in handover.handed(output)}
    return {row["node"].split("@", 1)[0] for row in handover.report(output)["covered"]
            if row["entries"] and (row["node"], row["output"]) in reads}


def held_through(read, held):
    """Whether an output with no entry of its own is held through what it was made into: a held row read here made
    from it, or a row of the other grain (whose own library node holds it)."""
    return bool(set(read.get("into", [])) & held or read.get("beyond"))


def uncovered(output, inputs):
    """Each accepted output the node read that the report does not cover with entries or a written exception, and
    that is not held through what it was made into (held_through)."""
    covered = {(row["node"], row["output"]): row for row in handover.report(output)["covered"]}
    allowed = exception_names(inputs)
    held = holding(output)
    found = []
    for read in handover.handed(output):
        row = covered.get((read["node"], read["output"]))
        if row is None:
            found.append(f"{read['node']} ({read['output'][:12]}) is not in the handover")
        elif not row["entries"] and not row["exception"] and held_through(read, held):
            continue
        elif not row["entries"] and not row["exception"]:
            found.append(f"{read['node']} ({read['output'][:12]}) holds no entry: {row['why'] or 'no reason given'}")
        elif not row["entries"] and str(row["exception"]) not in allowed:
            found.append(f"{read['node']} ({read['output'][:12]}) names exception {row['exception']}, which "
                         "data/checks/library-exceptions.json does not hold")
    return found


def judge_handed(output, inputs, evidence):
    return free_pass("handed", inputs) or verdict(
        "handed", uncovered(output, inputs), checks.FAIL,
        f"every one of the {len(handover.handed(output))} accepted outputs read is in the library "
        f"({through(output)} held through what they were made into)")


def through(output):
    """How many outputs read here no entry or exception holds on its own, held through what they were made into."""
    covered = {(row["node"], row["output"]): row for row in handover.report(output)["covered"]}
    held = holding(output)
    return sum(1 for read in handover.handed(output)
               if (row := covered.get((read["node"], read["output"]))) is not None and not row["entries"]
               and not row["exception"] and held_through(read, held))


def judge_refused(output, inputs, evidence):
    found = [f"{row['kind']} {row['id']} from {row['node']}: {row['reason']}"
             for row in handover.report(output)["refused"]]
    return verdict("refused", found, checks.FAIL, "the library refused nothing")


def judge_traced(output, inputs, evidence):
    free = free_pass("traced", inputs)
    if free:
        return free
    if "assembly" not in inputs and "neighbours" not in inputs:
        return checks.Verdict("traced", checks.PASS, "no assembled place here: each place's own library node traces "
                                                     "its stage")
    root = backend.settings().get("SCORE_LIB_ROOT")
    if not root:
        return checks.Verdict("traced", checks.UNKNOWN, "no library folder to trace to (SCORE_LIB_ROOT)")
    from score.stages.root_stage import stage_file
    from score.stages.library import traced
    assembled = pathlib.Path(inputs.get("neighbours") or inputs["assembly"])
    try:
        context = traced.context_of(pathlib.Path(inputs["place record"]).stem, root, inputs.get("exceptions"),
                                    traced.store_of(assembled), pathlib.Path(inputs["world record"]).parents[1])
    except ValueError as refused:  # exceptions.Refused: a half-written exception refuses the whole file
        return checks.Verdict("traced", checks.FAIL, f"data/checks/library-exceptions.json refuses: {refused}")
    return verdict("traced", traced.untraced(stage_file(assembled), context), checks.FAIL,
                   "everything in the place and every finish is a library entry or a written exception")


def judge_copies(output, inputs, evidence):
    found = [f"{row['address']}: {row['copy_why'] or 'no copy and no reason'}"
             for row in handover.report(output)["entries"] if row["kind"] in COPIED_KINDS and not row["copy"]]
    return verdict("copies", found, checks.UNKNOWN, "every model, layer, place and character entry has its 3D copy")


def judge_quality(output, inputs, evidence):
    found = [f"{row['address']}: {row['quality_why'] or 'no score and no reason'}"
             for row in handover.report(output)["entries"] if not row["quality"]]
    return verdict("quality", found, checks.UNKNOWN, "every entry has its quality score")


def judge_saved(output, inputs, evidence):
    saved = handover.report(output)["saved"]
    if saved["committed"]:
        pushed = "pushed" if saved["pushed"] else f"not pushed ({saved['why'] or 'no reason'}): the cockpit shows it"
        return checks.Verdict("saved", checks.PASS, f"committed {saved['committed'][:12]}, {pushed}")
    return free_pass("saved", inputs) or checks.Verdict(
        "saved", checks.FAIL, f"the library did not commit the handover: {saved['why'] or 'no reason given'}")


CHECKS = tuple(checks.Check(name, judge) for name, judge in (
    ("configured", judge_configured), ("handed", judge_handed), ("refused", judge_refused),
    ("traced", judge_traced), ("copies", judge_copies), ("quality", judge_quality), ("saved", judge_saved)))
