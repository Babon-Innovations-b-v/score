"""Read-only access to the PC store: accepted outputs and hard-linked checkouts into scratch (no rglob)."""
import json
import os
import pathlib
import shutil

OBJECTS = pathlib.Path(os.environ.get("PROPS_HOME", "~/.score-this-pc")).expanduser() / "store/objects"
SCRATCH = pathlib.Path(os.environ["STILLS"]) / "checkouts"


def records(kind, node):
    folder = OBJECTS / kind / node
    if not folder.is_dir():
        return []
    return [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))]


def current_accept(node):
    rejected = {}
    for reject in records("rejects", node):
        rejected[reject["output"]] = max(rejected.get(reject["output"], ""), reject["at"])
    standing = [accept for accept in records("accepts", node) if accept["at"] > rejected.get(accept["output"], "")]
    standing.sort(key=lambda accept: accept["at"])
    return standing[-1] if standing else None


def accepted(node):
    return (current_accept(node) or {}).get("output")


def listing(output):
    return json.loads((OBJECTS / "outputs" / f"{output}.json").read_text())


def checkout(output):
    folder = SCRATCH / output
    done = folder / ".done"
    if done.exists():
        return folder
    shutil.rmtree(folder, ignore_errors=True)
    for name, sha in listing(output).items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = OBJECTS / "blobs" / sha
        try:
            os.link(source, target)
        except OSError:
            shutil.copyfile(source, target)
    done.write_text("")
    return folder
