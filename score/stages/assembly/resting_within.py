"""The `resting` gate with the plan's "within" read (round 32's docking airlock, 2026-11-11: its door's window in its
door and its suit in its locker, laid within their holders by the scene record, failed twice as overlaps "still inside
after the nudge"). An overlap of two things the record lays one within the other is the plan's own placement, not a
fault, as the settle's resting gate already reads it (settling.planned_within); any other overlap, two things on each
other or unrelated, still fails. Kept apart from the assembly's package, which makers' code versions hash: only the
table's `resting` check reads this file, so it moves the assembly's key alone (assembly.judge_resting, which it
replaces in the table, goes once an edit there moves its rows anyway).

    laid_within(record)              {object: the objects the record lays it within}
    planned_overlap(fault, within)   whether a triage fault is such a planned pair
    judge_resting(output, ...)       the assembly's `resting` verdict without those
"""
import json
import pathlib
import tempfile

from score import checks
from score.stages import assembly


def laid_within(record):
    """{object: the objects the scene `record` lays it within} (`on` how "within": a door's window in its door, a suit
    in its locker), as settling.within_of reads it (not imported: settling's code would key the assembly's row)."""
    return {entry["name"]: set((entry.get("on") or {}).get("holder") or []) for entry in record.get("objects") or []
            if (entry.get("on") or {}).get("how") == "within"}


def planned_overlap(fault, within):
    """Whether a triage fault is two things inside each other that the plan lays one within the other."""
    if fault["kind"] != "overlaps" or not fault.get("partner"):
        return False
    one, other = fault["object"].rsplit("/", 1)[-1], str(fault["partner"]).rsplit("/", 1)[-1]
    return other in within.get(one, ()) or one in within.get(other, ())


def judge_resting(output, inputs, evidence):
    """assembly.judge_resting (the triage on the world files the stage declares, each row's support as the record
    lays it), with every overlap the record lays one within the other left out of the real faults."""
    inventory = assembly.declared_inventory(output, inputs["inventories"])
    if inventory is None or not inventory.exists():
        return checks.Verdict("resting", checks.UNKNOWN, "the seed names no inventory in the world's inventory "
                              f"folder ({inventory or 'none named'}), so what holds each object up is not known")
    record_file = pathlib.Path(output) / assembly.RECORD
    record = json.loads(record_file.read_text()) if record_file.exists() else None
    with tempfile.TemporaryDirectory() as folder:  # triage's own support rule reads a row's `support` first
        given = pathlib.Path(folder) / inventory.name
        given.write_text(json.dumps(assembly.resting_rows(json.loads(inventory.read_text()), record)))
        found = assembly.triage.triage(assembly.stage_file(output), json.loads(pathlib.Path(evidence).read_text()),
                                       rules_file=inputs["resting rules"], kit_file=inputs["kit"],
                                       inventory_file=given)
    within = laid_within(record or {})
    real = [fault for fault in found["faults"] if fault["real"] and not planned_overlap(fault, within)]
    objects = len({fault["object"] for fault in real})
    findings = tuple(f"{fault['object']}: {fault['kind']} {fault['measure']}: {fault['why']}" for fault in real)
    reason = f"{objects} objects with real resting faults, {found['false_objects']} false alarms after the drop run"
    return checks.Verdict("resting", checks.FAIL if real else checks.PASS, reason,
                          {"real faults": len(real), "objects": objects},
                          {"real faults": "lower", "objects": "lower"}, findings)
