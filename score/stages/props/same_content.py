"""What props-inputs@<place> hands on as content, never as path text: the carry's content rule for it
(score/stages/surfaces/carry.py, #75). 655e0465 wrote rows.json's pictures relative to PROPS_HOME where they had been
absolute paths into the frozen home of the run that made them; the pictures are the same files, so a close-up made
from the old output is the one the new would make. Framework (score/graph/_code.py FRAMEWORK): no row reads it, so
no key moves by it.
"""
import pathlib

from score.store import PROPS_HOME

# Each picture rows.json names, and the props-inputs file (prop_data.inputs_files) it was read from.
PICTURES = {"concept": lambda row: f"view {row['view']}", "drawn": lambda row: f"close-up {row['id']}"}


def at_home(text):
    """The file a rows.json path names: one into a run's frozen home (<a home>/frozen/<copy>.home/<path>) as the same
    path under this PROPS_HOME, a relative one under PROPS_HOME, any other as it is."""
    path = pathlib.Path(text)
    if not path.is_absolute():
        return PROPS_HOME / path
    parts = path.parts
    for index in range(1, len(parts) - 1):
        if parts[index - 1] == "frozen" and parts[index].endswith(".home"):
            return PROPS_HOME.joinpath(*parts[index + 1:])
    return path


def picture_sha(row, field, files):
    """The sha256 of the picture a row's field names: the props-inputs record's hash of the file it read it from
    (its bytes as the output was made). Raises ValueError when the path resolves to no file, or when the record holds
    no hash for it: today's bytes on disk would judge an old output by a picture it may never have read (review of
    2026-11-05: a picture swapped between two outputs with no hashes read as the same)."""
    path = at_home(row[field])
    if not path.is_file():
        raise ValueError(f"row {row['id']}'s {field} {row[field]} resolves to no file ({path})")
    name = PICTURES[field](row)
    if not files.get(name):
        raise ValueError(f"row {row['id']}'s {field}: its record holds no hash for {name}")
    return files[name]


def props_inputs(store, record):
    """The content of the props-inputs output `record` made: {file: sha256} of every file but rows.json, and
    rows.json itself with each picture's path replaced by that picture's sha256 (picture_sha)."""
    listing = {name: sha for name, sha in store.listing(record["output"]).items() if name != "rows.json"}
    rows = store.read_file(record["output"], "rows.json")
    if rows is None:
        raise ValueError(f"output {record['output'][:12]} has no rows.json")
    for row in rows["rows"]:
        for field in PICTURES:
            if row.get(field):
                row[field] = picture_sha(row, field, record.get("files", {}))
    return {"files": listing, "rows.json": rows}


# {input stage: its content rule} for the rows that read props-inputs whole (closeup).
RULES = {"props-inputs": props_inputs}
