"""Batch gaps: the takes a batch's paid step failed (CONTEXT.md "batch", "gap"; ADR-0005). Inside a batch a paid step
runs once and its checks only sort each output into a success or a named failure; a failure is a gap, decided by the
creator's yes to the batch, never by a per-gap accept. The row whose step failed names each such take in its output,
the rows after it leave the take out and carry its gap on, and complete lists every one by name with its faults (the
gates' faults on the take move there: score/stages/gaps.py `moved`, the table's `gap_moved`). New spend on one is a
new batch and a new ask.

<output>/batch-gaps.json: {"gaps": [{"name": what complete fails ("hatch: Pixal3D made no model"), "row": the stage
whose step failed, "check": the check that sorted it, "objects": the takes and rows it names (a gate's finding starts
"<object>: "), "faults": the failure as measured, "reason"}]}. A reader adds `output` (the output it was first read
from, kept as the gap is carried) and `decided` (the batch run, that row and output).

Its own module, imported by the paid rows' makes: an edit to gaps.py (the owner's accepted gaps) re-keys no paid row.
"""
import json
import pathlib

FILE = "batch-gaps.json"


def gap(name, row, check, objects, faults, reason):
    """One batch gap as a row writes it."""
    return {"name": name, "row": row, "check": check, "objects": sorted({str(item) for item in objects if item}),
            "faults": list(faults), "reason": reason}


def write(out, found):
    """batch-gaps.json in a row's output, its gaps once each by name."""
    (pathlib.Path(out) / FILE).write_text(json.dumps({"gaps": list({entry["name"]: entry for entry in found}.values())},
                                                     indent=1))


def read(folders):
    """Every batch gap the folders' batch-gaps.json name, once each by name, with the output it was first read from
    and who decided it."""
    found = {}
    for folder in map(pathlib.Path, folders):
        path = folder / FILE
        if not path.is_file():
            continue
        for entry in json.loads(path.read_text())["gaps"]:
            entry = {"output": folder.name, **entry}
            found.setdefault(entry["name"], {**entry, "decided": f"the batch run ({entry['row']}, output "
                                                                 f"{entry['output']})"})
    return list(found.values())


def of(inputs, output=None):
    """The batch gaps a node's inputs carry (every input folder's), and its own output's when given."""
    folders = [path for path in inputs.values() if isinstance(path, (str, pathlib.PurePath))
               and pathlib.Path(path).is_dir()]
    return read([*folders, *([output] if output is not None else [])])


def objects(found):
    """Every take and row the gaps name."""
    return {item for entry in found for item in entry["objects"]}
