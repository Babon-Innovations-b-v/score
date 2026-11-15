"""Compose a place's stage folder in scratch from the PC store, read-only.

    python compose.py <place> <out folder>

The final stage where one stands accepted (assembly@place, which is also its scene-tree); else the lit stage as
light-passes lays it (the assembly's own source code: earth seed, scene record, bakes, made ground) with the accepted
light@place layer taken in, from the inputs the accepted light-passes record was made from. Prints one JSON line:
{"place", "stage", "folder", "root", "note"}.
"""
import json
import os
import pathlib
import shutil
import sys

os.environ.setdefault("PROPS_HOME", str(pathlib.Path("~/.score-this-pc").expanduser()))
REPO = pathlib.Path(os.environ["SCORE_REPO"])  # the score checkout the stills are planned with
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fast_store  # noqa: E402

from score import store as score_store  # noqa: E402

runtime = score_store.runtime_store


def prefix_keys(self, prefix):
    """FolderStore.keys walking only the prefix's own folder (the whole store's rglob takes minutes)."""
    folder = self.root / prefix.rsplit("/", 1)[0] if "/" in prefix else self.root
    if not folder.is_dir():
        return []
    found = (str(path.relative_to(self.root)) for path in folder.rglob("*")
             if path.is_file() and not path.name.endswith(".partial"))
    return sorted(key for key in found if key.startswith(prefix))


runtime.FolderStore.keys = prefix_keys
CACHE = pathlib.Path(os.environ["STILLS"]) / "cache"
score_store.Store.default = classmethod(lambda cls: cls(runtime.FolderStore(fast_store.OBJECTS), CACHE))


def record_of(node, output):
    """The store's record that made `output` for `node`."""
    for path in sorted((fast_store.OBJECTS / "records" / node).glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("output") == output:
            return record
    raise SystemExit(f"no record of {node} made {output}")


def final(place, out):
    output = fast_store.accepted(f"assembly@{place}")
    folder = fast_store.checkout(output)
    target = out / place
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(folder, target, symlinks=True, copy_function=os.link, ignore=shutil.ignore_patterns(".done"))
    return {"stage": f"assembly@{place} {output[:12]} (accepted)", "folder": str(target),
            "root": str(target / f"{place}.usda"), "note": ""}


def lit(place, out):
    from score import stages
    from score.stages.light import passes
    table = {stage.name: stage for stage in stages.STAGES}
    world = stages.world1()
    row = table["light-passes"]
    passes_output = fast_store.accepted(f"light-passes@{place}")
    made = record_of(f"light-passes@{place}", passes_output)
    patterns = row.files(place) if callable(row.files) else row.files
    inputs = {}
    for name, pattern in patterns.items():
        pattern = pattern[0] if isinstance(pattern, tuple) else pattern
        inputs[name] = pathlib.Path(pattern.format(place=place, **world.roots))
    for before, output in {**made["after"], **made.get("beside", {})}.items():
        inputs[before] = fast_store.checkout(output)
    inputs = stages.seed_inputs(inputs, passes.passes_files(place), place)
    light_output = fast_store.accepted(f"light@{place}")
    layer_folder = fast_store.checkout(light_output)
    tree = out
    shutil.rmtree(tree / place, ignore_errors=True)
    tree.mkdir(parents=True, exist_ok=True)
    root = passes.lit_tree(place, layer_folder, tree, inputs)
    settle = fast_store.accepted(f"settle@{place}")
    note = ("the lit stage (light-passes' composition: earth seed, scene record, bakes, made ground) with "
            f"light@{place} {light_output[:12]}; no accepted assembly, so no settle, motion, effects or people layers"
            + (f" (settle@{place} {settle[:12]} stands accepted but only an assembly takes it)" if settle else ""))
    return {"stage": f"light@{place} {light_output[:12]} (accepted), on light-passes@{place} {passes_output[:12]}'s inputs",
            "folder": str(tree / place), "root": str(root), "note": note}


if __name__ == "__main__":
    name, where = sys.argv[1], pathlib.Path(sys.argv[2])
    found = final(name, where) if fast_store.accepted(f"assembly@{name}") else lit(name, where)
    print(json.dumps({"place": name, **found}))
