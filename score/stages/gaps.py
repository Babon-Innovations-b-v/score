"""Named gaps: a fault the owner decided to ship with today, moved from the gate that stops a line to the completion
gate, which fails it by name. Never a loosened gate: only the objects a dated decision names move, the fault stays in
complete's report with its measured numbers, and any other fault still stops the line.

data/checks/gaps/<place>.json: {"gaps": [{"name": what complete fails ("ship: no made model"), "row": the row whose
gate it moves from ("assembly"), "check": that gate ("placeholders"), "objects": the faults' objects as the gate names
them (each finding starts "<object>: "), "reason", "decided": who and when, "faults": the findings as measured when it
was decided}]}. A place without a file has no gaps; the rows that read it declare it only where it exists.
"""
import json
import pathlib

from score import checks

REPO = pathlib.Path(__file__).resolve().parents[2]
FOLDER = REPO / "data/checks/gaps"
NAME = "gaps"


def files(place):
    """{"gaps": its pattern} for a place with a gaps file, else nothing (no key of another place moves)."""
    return {NAME: "{data}/checks/gaps/" + f"{place}.json"} if (FOLDER / f"{place}.json").exists() else {}


def entries(inputs, row=None, check=None):
    """The gaps the inputs' declared file names, of one row's gate when given."""
    path = inputs.get(NAME)
    found = json.loads(pathlib.Path(path).read_text())["gaps"] if path else []
    return [entry for entry in found
            if (row is None or entry["row"] == row) and (check is None or entry["check"] == check)]


def object_of(finding):
    return finding.split(": ", 1)[0]


def moved(verdict, gaps):
    """The gate's verdict with the faults of the named objects moved to the completion gate: a fail whose every
    finding is a named object's passes, its findings and measures kept and each named gap said; any other fault
    keeps the fail. Another answer is as given."""
    named = {name for entry in gaps for name in entry["objects"]}
    if verdict.answer != checks.FAIL or not verdict.findings or not named:
        return verdict
    if any(object_of(finding) not in named for finding in verdict.findings):
        return verdict
    said = "; ".join(f"{entry['name']} ({entry['decided']})" for entry in gaps
                     if set(entry["objects"]) & {object_of(finding) for finding in verdict.findings})
    return checks.Verdict(verdict.check, checks.PASS, f"{verdict.reason}; moved to complete as named gaps: {said}",
                          {**verdict.measures, "moved": len(verdict.findings)}, verdict.better, verdict.findings)


def judge_named(output, inputs, evidence):
    """The completion gate fails every named gap of the place by name, with the faults as measured when it was
    decided; passes when the place has none."""
    gaps = entries(inputs)
    if not gaps:
        return checks.Verdict("named gaps", checks.PASS, "no named gap", {"gaps": 0}, {"gaps": "lower"})
    findings = tuple(f"{entry['name']}: {fault}" for entry in gaps for fault in entry["faults"])
    return checks.Verdict("named gaps", checks.FAIL, "; ".join(f"{entry['name']} ({entry['reason']}; "
                                                               f"{entry['decided']})" for entry in gaps),
                          {"gaps": len(gaps)}, {"gaps": "lower"}, findings)
