"""The handover report, the one file score reads from the library side: contract library-handover, version 1.

    handover.LIBRARY_HANDOVER         the library rows' output contract: handover.json and reads.json
    handover.report(output)           the report of a stored library output
    handover.handed(output)           [{node, output}] score handed it (reads.json, written by score itself)
    handover.none_report(run)         the report of a world with no library configured

The library's command writes `handover.json`; score writes `reads.json` beside it, every accepted output the node
read, so the gate compares the two without trusting the library to say what it was handed. The keys are the
contract's (handover_example.json holds one full report; the library repository keeps its own copy of the shape and
compares field names in its own test):

    {"schema": "library-handover", "version": 1, "backend", "library", "world", "place", "commit", "command",
     "covered":  [{"node", "output", "entries", "exception", "why"}],
     "entries":  [{"address", "kind", "state", "status", "node", "output", "source", "copy", "copy_why", "quality",
                   "quality_why"}],
     "refused":  [{"kind", "id", "node", "output", "reason"}],
     "saved":    {"committed", "pushed", "why"}}

Sorted keys and no clock fields, so the output's hash moves only when its content moves.
"""
import json

from score import contracts

SCHEMA, VERSION = "library-handover", 1
REPORT, READS = "handover.json", "reads.json"
KEYS = ("backend", "command", "commit", "covered", "entries", "library", "place", "refused", "saved", "schema",
        "version", "world")
COVERED_KEYS = ("entries", "exception", "node", "output", "why")
ENTRY_KEYS = ("address", "copy", "copy_why", "kind", "node", "output", "quality", "quality_why", "source", "state",
              "status")
REFUSED_KEYS = ("id", "kind", "node", "output", "reason")
SAVED_KEYS = ("committed", "pushed", "why")
ROWS = {"covered": COVERED_KEYS, "entries": ENTRY_KEYS, "refused": REFUSED_KEYS}
NO_LIBRARY = "no library configured"


def row_faults(report):
    """Why the report's lists or its saved block lack a key of the contract, or [] when none does."""
    faults = []
    for area, keys in ROWS.items():
        rows = report.get(area)
        if not isinstance(rows, list):
            faults.append(f"{area} is not a list")
            continue
        faults += [f"{area} row {number} lacks {', '.join(sorted(set(keys) - set(row)))}"
                   for number, row in enumerate(rows, 1) if set(keys) - set(row)]
    saved = report.get("saved")
    if not isinstance(saved, dict) or set(SAVED_KEYS) - set(saved):
        faults.append(f"saved is not a block of {', '.join(SAVED_KEYS)}")
    return faults


def report_faults(report):
    """Why a handover report is off its contract, or [] when it is on it."""
    if (report.get("schema"), report.get("version")) != (SCHEMA, VERSION):
        return [f"handover.json is {report.get('schema')} v{report.get('version')}, not {SCHEMA} v{VERSION}"]
    missing = sorted(set(KEYS) - set(report))
    if missing:
        return [f"handover.json lacks {', '.join(missing)}"]
    return row_faults(report)


def output_faults(folder):
    """Why a folder is not a library node's output (the library's report and score's reads), or [] when it is."""
    faults = [f"no {name}" for name in (REPORT, READS) if not (folder / name).is_file()]
    if faults:
        return faults
    return report_faults(json.loads((folder / REPORT).read_text()))


LIBRARY_HANDOVER = contracts.Contract(SCHEMA, VERSION, output_faults)


def report(output):
    return json.loads((output / REPORT).read_text())


def handed(output):
    return json.loads((output / READS).read_text())


def none_report(run):
    """The report of a node with no library configured: nothing covered, nothing saved, and why."""
    return {"schema": SCHEMA, "version": VERSION, "backend": "none", "library": "", "world": run["world"],
            "place": run["place"], "commit": run["commit"], "command": [], "covered": [], "entries": [],
            "refused": [], "saved": {"committed": None, "pushed": False, "why": NO_LIBRARY}}


def write(path, content):
    """A report or reads file, keys sorted, so equal content is equal bytes."""
    path.write_text(json.dumps(content, indent=1, sort_keys=True) + "\n")
