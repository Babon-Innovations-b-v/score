"""The `designed` gate with the hand-in's shown rows read (motion@street, 2026-11-10: its distant red flags and
distant rocket failed as moving rows with no object on the stage). A backdrop row the hand-in marks `shown` ({place,
row}: prepare's groups.shown_from) is no object of this place: the scene record stands that place in its stage and
lays the row's objects there, as that place's row (the street's distant flags are the square's red flags), so its move
is that place's motion row's to make and judge, where its fault, if any, stands. Every other moving row with no object
still fails. Kept apart from the motion package, which makers' code versions hash: only the table's `designed` check
reads this file, so it moves the motion row's key alone and no motion output.

    shown_rows(inputs)              {row id: {place, row}} of the hand-in's rows shown from another place
    judge_designed(output, ...)     motion's `designed` verdict without the shown rows' missing lines
"""
import json
import pathlib

from score import checks
from score.stages import motion


def shown_rows(inputs):
    """{row id: {place, row}} of the place's hand-in (`props`) rows that another place of its scene makes and this
    one shows; none without a hand-in."""
    handin = inputs.get("props")
    if not handin or not pathlib.Path(handin).is_file():
        return {}
    return {row["id"]: row["shown"] for row in json.loads(pathlib.Path(handin).read_text()).get("rows", [])
            if isinstance(row.get("shown"), dict) and row["shown"].get("place")}


def row_of(line):
    """The row a record's `missing` line names (from_design.record: "<row>: moves (<move>), and no object ...")."""
    return line.split(": moves (", 1)[0]


def judge_designed(output, inputs, evidence):
    """motion.judge_designed, with each missing row the hand-in shows from another place named as moved there."""
    verdict = motion.judge_designed(output, inputs, evidence)
    shown = shown_rows(inputs)
    elsewhere = sorted({row_of(line) for line in verdict.findings} & set(shown))
    if not elsewhere:
        return verdict
    faults = tuple(line for line in verdict.findings if row_of(line) not in shown)
    there = "; ".join(f"{row} is {shown[row]['place']}'s {shown[row].get('row')}" for row in elsewhere)
    reason = (f"{len(faults)} moving things stand on nothing of the inventory" if faults else
              f"{verdict.measures['named']} moving and standing things are each an object of an inventory row") + \
        f" ({len(elsewhere)} shown from another place, moved by its own motion row: {there})"
    return checks.Verdict("designed", checks.FAIL if faults else checks.PASS, reason,
                          {**verdict.measures, "missing": len(faults)}, verdict.better, faults)
