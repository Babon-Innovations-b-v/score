"""Write what keys a row in this Python: {"python": its code version's first part, "versions": {stage: code version
hash} for every row of every stage table, "freeze": the installed packages}, as JSON into the path given.

    python tools/cloud/images/runner/versions.py <out.json>     # from the repository's root

The runner image's proof runs it in the image and the conductor runs it in its own Python on the same tree: the image
gives the conductor's keys only when the two answers' versions are equal (score/stages/images, "keys as the
conductor")."""
import importlib.metadata
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd()))

from score import graph, stages  # noqa: E402
from score.graph import _code  # noqa: E402


def every_stage():
    """Each row of the default table and of every world's own table, once by name."""
    rows = [*stages.STAGES, *(row for table in stages.TABLES.values() for row in table)]
    return {row.name: row for row in rows}


def answer():
    """The python part, each stage's code version hash, and the installed packages."""
    return {"python": _code.python_part(),
            "versions": {name: graph.stage_code(row) for name, row in sorted(every_stage().items())},
            "freeze": sorted(f"{found.metadata['Name']}=={found.version}"
                             for found in importlib.metadata.distributions())}


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(answer(), indent=1) + "\n")
