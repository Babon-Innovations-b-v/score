"""The `held` gate's face rule (#72, #36): two design objects held on the same face of the same holder whose laid boxes
overlap each other along that face, and in height, more than fitting.HELD_MOST, fail by name, both objects and the
overlap in metres (street's three restaurant doors 0.58 m apart, each 1 m wide). No relation lets objects on one face
overlap. Kept apart from fitting.py and the assembly's package, which makers' code versions hash: only the table's
`held` check reads this file, so it moves the assembly's key alone.

    overlapping(record, laid)   [(object, what is wrong, metres)]: each overlapping pair, named by its first object
    judge_held(output, ...)     the assembly's `held` verdict with those faults added
"""
import itertools
import json
import pathlib

import numpy as np

from score import checks
from score.stages import assembly
from score.stages.assembly import fitting, made_waiting


def face_of(on, box, holders):
    """(the holder box's ends, the face's axis, its sign): the face of the holder box nearest `box` that `out` points
    from, as fitting.off_holder reads it."""
    out = on.get("out", (0.0, 1.0))
    axis = 0 if abs(out[0]) >= abs(out[1]) else 2
    held = fitting.nearest(holders, *box)
    return tuple(tuple(np.round(end, 4)) for end in held), axis, float(np.sign(out[axis // 2]))


def overlapping(record, laid):
    """[(object, what is wrong, metres)] of each pair of the record's objects laid `face` on one face of one holder
    whose boxes overlap along the face and in height more than fitting.HELD_MOST."""
    boxes = {entry["name"]: tuple(np.asarray(end, float) for end in (entry["low"], entry["high"]))
             for entry in [*laid.get("objects", []), *laid.get("holders", [])]}
    faces = {}
    for entry in record.get("objects") or []:
        on = entry.get("on")
        if not on or on["how"] != "face" or entry["name"] not in boxes:
            continue
        holders = [boxes[name] for name in on.get("holder") or [] if name in boxes]
        if holders:
            faces.setdefault(face_of(on, boxes[entry["name"]], holders), []).append(entry["name"])
    faults = []
    for (_, axis, _), names in faces.items():
        side = 2 - axis
        for first, second in itertools.combinations(names, 2):
            (low, high), (other_low, other_high) = boxes[first], boxes[second]
            along = min(high[side], other_high[side]) - max(low[side], other_low[side])
            tall = min(high[1], other_high[1]) - max(low[1], other_low[1])
            if along > fitting.HELD_MOST and tall > fitting.HELD_MOST:
                faults.append((first, f"overlaps {second} by {along:.2f} m along their holder's face",
                               round(float(along), 3)))
    return faults


def judge_held(output, inputs, evidence):
    """assembly.judge_held's verdict, failing too on each overlapping pair (`overlapping`), its count a measure."""
    verdict = assembly.judge_held(output, inputs, evidence)
    laid_path, record_path = pathlib.Path(output) / made_waiting.LAID, pathlib.Path(output) / assembly.RECORD
    if not laid_path.exists() or not record_path.exists():
        return verdict
    faults = overlapping(json.loads(record_path.read_text()), json.loads(laid_path.read_text()))
    measures = {**verdict.measures, "overlapping": len(faults)}
    better = {**verdict.better, "overlapping": "lower"}
    reason = f"{verdict.reason}; {len(faults)} pairs overlap on their holder's face" if faults else verdict.reason
    return checks.Verdict("held", checks.FAIL if faults else verdict.answer, reason, measures, better,
                          (*verdict.findings, *(f"{name}: {words}" for name, words, _ in faults)))
