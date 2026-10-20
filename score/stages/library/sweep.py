"""Compare an environment with its library and write every mismatch where the cockpit shows a place's problems:

    .venv/bin/python -m score.stages.library.sweep [--out FOLDER]

Reads, never writes: the framework's store (each library node's accepted output and its handover.json, the accepted
output of every node an entry names), the library folder SCORE_LIB_ROOT (else the score_lib checkout beside score) and its
pictures (SCORE_LIB_BLOBS_DIR). Writes, for each place and for the environment's own nodes, <out>/<place>/findings.json
({"place", "answer", "reason", "outputs": {library node: the output judged}, "findings": [{"rule", "prim", "name",
"sentence", "picture"}]}) with each entry's picture beside it, and <out>/summary.json. The default out is
WORK/checks/library-handover, which the cockpit reads (`check_findings`) as the place's problems. The comparison is
`invariant.py`'s. Free, local, seconds; prints one summary line.
"""
import argparse
import json
import pathlib
import shutil

from score import library
from score.stages.complete.library import stored
from score.stages.library import PLACE_ROW, WORLD_ROW, backend, handover, invariant
from score.store import PROPS_HOME

OUT = PROPS_HOME / "work/checks/library-handover"
FREE = pathlib.Path(__file__).resolve().parents[3] / "data/checks/library-free.json"


def node_of(where):
    return WORLD_ROW if where == invariant.WORLD else f"{PLACE_ROW}@{where}"


def stored_report(store, output):
    """The handover.json of a stored library output, read from its blob."""
    sha = store.listing(output).get(handover.REPORT)
    return json.loads(pathlib.Path(store.objects.path(f"blobs/{sha}")).read_text()) if sha else None


def handed_of(store, places):
    """{place or "world": {"node", "output", "why", "report"}} of every library node of the environment."""
    found = {}
    for where in [invariant.WORLD, *places]:
        node = node_of(where)
        output = store.accepted(node)
        found[where] = {"node": node, "output": output, "why": "" if output else "nothing stands accepted",
                        "report": stored_report(store, output) if output else None}
    return found


def entry_row(record):
    """One entry.json record as the invariant reads it: provenance flattened, its version, its picture."""
    provenance = record.get("provenance") or {}
    picture = (record.get("files") or {}).get((record.get("picture") or {}).get("file") or "") or {}
    return {"address": record["address"], "kind": record["kind"], "id": record["id"], "version": int(record["version"]),
            "state": record.get("state") or "", "world": provenance.get("world"), "place": provenance.get("place"),
            "node": provenance.get("node") or next(iter(provenance.get("nodes") or []), None),
            "output": provenance.get("output"), "picture": picture.get("sha256")}


def library_rows(root):
    """Every entry of the library folder, every version."""
    return [entry_row(record) for record in library.entries(root)] if root else []


def library_free(world, path=FREE):
    """True when the owner decided the environment is made without a library (a full dated row in library-free.json)."""
    rows = json.loads(path.read_text()).get("worlds", []) if path.is_file() else []
    return any(row.get("world") == world and all(str(row.get(field) or "").strip() for field in ("why", "who", "when"))
               for row in rows)


def picture_of(address, rows, blobs, folder):
    """The entry's picture copied beside the findings (pictures/<n>.png), its name; None when it has none here."""
    sha = next((row["picture"] for row in rows if row["address"] == address and row.get("picture")), None)
    source = pathlib.Path(blobs).expanduser() / "blobs" / sha[:2] / sha if sha and blobs else None
    if not source or not source.is_file():
        return None
    name = f"pictures/{address.replace('/', '-').replace('@', '-')}.png"
    (folder / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, folder / name)
    return name


def written(where, held, found, rows, blobs, folder):
    """The findings.json of one place or the environment, its pictures copied beside it; as written."""
    folder.mkdir(parents=True, exist_ok=True)
    listed = [{"rule": item["rule"], "prim": None, "name": item["address"] or item["node"],
               "sentence": item["sentence"],
               "picture": picture_of(item["address"], rows, blobs, folder) if item["address"] else None}
              for item in found]
    report = {"place": where, "answer": "fail" if listed else "pass",
              "reason": f"{len(listed)} things the world and its library disagree on" if listed else
              "the world and its library agree", "outputs": {held["node"]: held["output"]} if held["output"] else {},
              "findings": listed}
    (folder / "findings.json").write_text(json.dumps(report, indent=1))
    return report


def run(out=OUT):
    """Compare environment 1 with its library and write every place's findings under `out`; the summary line."""
    from score import stages
    world = stages.world1()
    values = backend.settings()
    configured = backend.kind(values) != backend.NONE or library_free(world.name)
    store = stored.reading()
    handed = handed_of(store, stages.places(world))
    rows = library_rows(values.get("SCORE_LIB_ROOT"))
    accepted = {row["node"]: store.accepted(row["node"]) for row in rows if row.get("node")}
    found = invariant.problems(world.name, handed, rows, accepted, configured)
    summary = {where: written(where, held, found.get(where, []), rows, values.get("SCORE_LIB_BLOBS_DIR"),
                              out / where)["answer"] for where, held in handed.items()}
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    count = sum(len(items) for items in found.values())
    return (f"{len(summary)} library nodes, {count} library problems, "
            f"{sum(answer == 'fail' for answer in summary.values())} with one")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    options = parser.parse_args(argv)
    print(f"{run(options.out)}; {options.out / 'summary.json'}")


if __name__ == "__main__":
    main()
