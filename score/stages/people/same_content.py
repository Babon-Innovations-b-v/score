"""What people-made@people hands the rows that read it beside (each look's parts, body and dress rows) as content,
never as path text: the carry's content rule for it (score/stages/surfaces/carry.py, #26). people-made wrote each
look's `model` as an absolute path into the frozen run home that made it (…/frozen/<stamp>.home/store/cache/checkouts/
<bake output>/made/<look>.gltf), so a remake in another frozen home moved every look's paid rows by that text alone
(2026-11-10: the 9 accepted look-parts, about EUR 15). loop.py now writes the path in its surfaces-bake output; this
rule reads an older output's model the same way, so the accepted rows are kept. Framework (score/graph/_code.py
FRAMEWORK): no row reads it, so no key moves by it.
"""
import pathlib

MADE = "made.json"
CHECKOUTS = "checkouts"  # the store's checkout folder: <home>/store/cache/checkouts/<output>/<file>


def in_output(text):
    """A model path as its place in the output that holds it: an absolute one into a store checkout from the file
    after its output's folder, a relative one as it is. Raises ValueError for an absolute path outside a checkout,
    which names no output's file."""
    path = pathlib.PurePosixPath(text)
    if not path.is_absolute():
        return path.as_posix()
    parts = path.parts
    for index in range(len(parts) - 2, 0, -1):
        if parts[index - 1] == CHECKOUTS:
            return pathlib.PurePosixPath(*parts[index + 1:]).as_posix()
    raise ValueError(f"model {text} is in no store checkout")


def people_made(store, record):
    """The content of the people-made output `record` made: {file: sha256} of every file but made.json, and made.json
    with each look's model as its place in the surfaces-bake output (in_output)."""
    listing = getattr(store, "listing", None)
    if listing is None:
        raise ValueError("this store lists no output's files")
    files = {name: sha for name, sha in listing(record["output"]).items() if name != MADE}
    made = store.read_file(record["output"], MADE)
    if made is None:
        raise ValueError(f"output {record['output'][:12]} has no {MADE}")
    for entry in made.values():
        if "model" in entry:
            entry["model"] = in_output(entry["model"])
    return {"files": files, MADE: made}


# {input stage: its content rule} for the rows that read people-made beside (each look's parts, body and dress).
RULES = {"people-made": people_made}
