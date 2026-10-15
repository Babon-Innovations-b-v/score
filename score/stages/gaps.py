"""Named gaps: a fault the owner decided to ship with today, moved from the gate that stops a line to the completion
gate, which fails it by name. Never a loosened gate: only the objects a dated decision names move, the fault stays in
complete's report with its measured numbers, and any other fault still stops the line.

data/checks/gaps/<place>.json: {"gaps": [{"name": what complete fails ("ship: no made model"), "row": the row whose
gate it moves from ("assembly"), "check": that gate ("placeholders"), "objects": the faults' objects as the gate names
them (each finding starts "<object>: "), "contains": a phrase each of its findings holds, when only one kind of the
gate's faults moves (optional), "unknown": a phrase the gate's unknown answer holds, when the gap is a check that
cannot answer (no likeness output: it has no findings) (optional), "reason", "decided": who and when, "faults": the findings as measured when it
was decided}]}. A place without a file has no gaps; the rows that read it declare it only where it exists.
"""
import json
import pathlib

from score import checks

REPO = pathlib.Path(__file__).resolve().parents[2]
FOLDER = REPO / "data/checks/gaps"
NAME = "gaps"


# The places whose gaps file every gap row has keyed since 2026-10-14, the accepted paint among them: they keep it, so
# no accepted output moves. shortcut: a judged-only input (in the judgement's state, not the key; a change to
# score/graph) would let these read only their own gaps too.
KEYED_WHOLE = ("campgrounds", "galley", "garage", "greenhouse", "hangar", "navigation", "wreck")
# The rows that keyed those files whole: a gate given gaps later (complete-boxes) reads only the gaps naming it.
KEYED_ROWS = ("assembly", "surfaces-check", "surfaces-paint")


def files(place, row=None):
    """{"gaps": its pattern} for a place with a gaps file, else nothing (no key of another place moves): for the
    completion gate (`row` None) always, as it fails every gap by name; for a row whose gate a gap may move from, only
    where a gap of the file names that row, so a gap is never an input of a row it does not reach (the street's gaps
    of complete re-keyed the paid paint at three places, overseer 2026-10-15); the KEYED_WHOLE places as before."""
    path = FOLDER / f"{place}.json"
    if not path.exists():
        return {}
    if row is not None and not (place in KEYED_WHOLE and row in KEYED_ROWS) and not any(
            entry["row"] == row for entry in json.loads(path.read_text())["gaps"]):
        return {}
    return {NAME: "{data}/checks/gaps/" + f"{place}.json"}


def entries(inputs, row=None, check=None):
    """The gaps the inputs' declared file names, of one row's gate when given."""
    path = inputs.get(NAME)
    found = json.loads(pathlib.Path(path).read_text())["gaps"] if path else []
    return [entry for entry in found
            if (row is None or entry["row"] == row) and (check is None or entry["check"] == check)]


def object_of(finding):
    """The object a finding names: before its first ": ", or the `row` of a JSON finding (complete's rows check)."""
    if finding.startswith("{"):
        return json.loads(finding).get("row", "")
    return finding.split(": ", 1)[0]


def covers(entry, finding):
    """True when a finding is the entry's: one of its objects, and of its kind when the entry says one (`contains`,
    a phrase the finding holds: the bake check's order rule among its other faults)."""
    return object_of(finding) in entry["objects"] and entry.get("contains", "") in finding


def moved(verdict, gaps):
    """The gate's verdict with the faults of the named objects moved to the completion gate: a fail whose every
    finding is a named object's passes, its findings and measures kept and each named gap said; any other fault
    keeps the fail. An unknown whose reason holds an entry's `unknown` phrase passes the same way. Another answer is
    as given."""
    named = [entry for entry in gaps if entry.get("unknown") and entry["unknown"] in verdict.reason]
    if verdict.answer == checks.UNKNOWN and named:
        said = "; ".join(f"{entry['name']} ({entry['decided']})" for entry in named)
        return checks.Verdict(verdict.check, checks.PASS, f"{verdict.reason}; moved to complete as named gaps: {said}",
                              {**verdict.measures, "moved": 1}, verdict.better, verdict.findings)
    if verdict.answer != checks.FAIL or not verdict.findings or not gaps:
        return verdict
    if not all(any(covers(entry, finding) for entry in gaps) for finding in verdict.findings):
        return verdict
    said = "; ".join(f"{entry['name']} ({entry['decided']})" for entry in gaps
                     if any(covers(entry, finding) for finding in verdict.findings))
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
