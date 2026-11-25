"""props-inputs@<place>'s make (#89): closeup_row.make_inputs' rows.json with each picture's sha256 beside its path
(`concept_sha256`, `drawn_sha256`: the bytes it read). Since 655e0465 rows.json names its pictures by a path relative
to PROPS_HOME, so a concept or drawn close-up changed at the same path left the output, and with it closeup@<place>'s
key, where it stood. Apart from closeup_row.py so the paid closeup row's code version does not move for it; the carry
reads the content past the new fields (score/stages/props/same_content.py).
"""
import hashlib
import json
import pathlib

import score.stages.props.closeup_row as closeup_row  # the module, not the package: the table stays out of the code

# Each picture field rows.json names, and the field its sha256 is written in.
SHAS = {"concept": "concept_sha256", "drawn": "drawn_sha256"}


def picture_sha(path):
    """The sha256 of the file a picture field names, None when it names no file (a folder a row's tool took, or a
    missing picture: the close-up row names each as that object's fault)."""
    from score.store import PROPS_HOME

    found = PROPS_HOME / path
    return hashlib.sha256(found.read_bytes()).hexdigest() if found.is_file() else None


def make_inputs(inputs, out, seed, params):
    """rows.json as closeup_row.make_inputs writes it, each row's picture fields with their sha256 beside them."""
    closeup_row.make_inputs(inputs, out, seed, params)
    found = json.loads((out / "rows.json").read_text())
    for row in found["rows"]:
        for field, sha in SHAS.items():
            row[sha] = picture_sha(pathlib.Path(row[field])) if row.get(field) else None
    (out / "rows.json").write_text(json.dumps(found, indent=1))
