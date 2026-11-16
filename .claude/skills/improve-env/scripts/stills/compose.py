"""Compose a place's stage folder in scratch from the PC store, read-only.

    python compose.py <place> <out folder> [--newest]

The final stage where one stands accepted (assembly@place, which is also its scene-tree); else the lit stage as
light-passes lays it (the assembly's own source code: earth seed, scene record, bakes, made ground) with the accepted
light@place layer taken in, from the inputs the accepted light-passes record was made from. Prints one JSON line:
{"place", "stage", "folder", "root", "note"}.

--newest (a preview of work not yet accepted): the lit stage of every place, each part (the parts its newest
light-passes record read, the shown places as its newest scene record gives them) from that part's newest made output,
accepted or not, and the light layer from the newest light@<place>, else the newest light-layer@<place>, else none
(Blender's default light). Its note names each part's output and whether it stands accepted, rejected, made on the
live run's commit (current) or before it (older: a part the run has not remade yet, such as a bake, keeps it).
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


def run_commit():
    """The commit the live PC run is on (the newest in runs/active.json), else the stills' checkout's."""
    active = fast_store.OBJECTS.parents[1] / "runs/active.json"
    runs = json.loads(active.read_text()) if active.is_file() else {}
    if runs:
        return runs[max(runs, key=int)]["commit"]
    import subprocess
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()


def newest_record(node):
    """The newest record (by finished) of `node` whose output's listing is in the store, else None."""
    made = [record for record in fast_store.records("records", node)
            if record.get("output") and (fast_store.OBJECTS / "outputs" / f"{record['output']}.json").is_file()]
    return max(made, key=lambda record: record.get("finished") or "") if made else None


def standing(node, record, commit):
    """How a part's output stands: accepted or rejected, and made on the live run's commit or before it."""
    output = record["output"]
    judged = ("accepted" if fast_store.accepted(node) == output
              else "rejected" if any(reject["output"] == output for reject in fast_store.records("rejects", node))
              else "not judged")
    made = "current" if record.get("commit") == commit else f"older (commit {record.get('commit', '?')[:9]})"
    return f"{judged}, {made}, finished {(record.get('finished') or '?')[:16]}"


def node_of(name, place):
    """The store node a light-passes read names: an after's is the place's own (terrain's the world's), a beside's
    its own name."""
    return name if "@" in name or name == "terrain" else f"{name}@{place}"


def shown_by(place):
    """The places the newest scene record of `place` shows (light-passes' neighbours rule on that record)."""
    from score.stages.light import passes
    record = newest_record(f"{passes.RECORD}@{place}")
    if record is None:
        return set()
    path = fast_store.checkout(record["output"]) / "record" / f"{place}.json"
    shown = {entry["stage"] for entry in json.loads(path.read_text()).get("places", [])} - {place}
    return {name for name in shown if passes.recorded(name)}


def newest_reads(place, made):
    """The read names of the newest light-passes record, the shown places brought to the newest scene record's."""
    reads = {*made["after"], *made.get("beside", {})}
    was = {name.split("@", 1)[1] for name in reads if name.startswith("scene-record@")
           and f"earth-seed@{name.split('@', 1)[1]}" in reads}
    now = shown_by(place)
    for gone in was - now:
        reads -= {f"scene-record@{gone}", f"earth-seed@{gone}"}
    for new in now - was:
        reads |= {f"scene-record@{new}", f"earth-seed@{new}"}
        if newest_record(f"surface-library@{new}"):
            reads.add(f"surface-library@{new}")
    return reads, sorted(was - now), sorted(now - was)


def newest(place, out):
    from score import stages
    from score.stages.light import passes
    commit = run_commit()
    table = {stage.name: stage for stage in stages.STAGES}
    world = stages.world1()
    row = table["light-passes"]
    made = newest_record(f"light-passes@{place}")
    if made is None:
        raise SystemExit(f"no light-passes record of {place}: its reads are unknown")
    reads, dropped, added = newest_reads(place, made)
    patterns = row.files(place) if callable(row.files) else row.files
    inputs, parts = {}, {}
    for name, pattern in patterns.items():
        pattern = pattern[0] if isinstance(pattern, tuple) else pattern
        inputs[name] = pathlib.Path(pattern.format(place=place, **world.roots))
    for name in sorted(reads):
        node = node_of(name, place)
        record = newest_record(node)
        if record is None:
            parts[name] = f"{node}: no made output, left out"
            continue
        inputs[name] = fast_store.checkout(record["output"])
        parts[name] = f"{node} {record['output'][:12]} ({standing(node, record, commit)})"
    inputs = stages.seed_inputs(inputs, passes.passes_files(place), place)
    tree = out
    shutil.rmtree(tree / place, ignore_errors=True)
    tree.mkdir(parents=True, exist_ok=True)
    light = next(((node, record) for node in (f"light@{place}", f"light-layer@{place}")
                  if (record := newest_record(node))), None)
    if light:
        root = passes.lit_tree(place, fast_store.checkout(light[1]["output"]), tree, inputs)
        parts["light layer"] = f"{light[0]} {light[1]['output'][:12]} ({standing(*light, commit)})"
    else:
        root = passes.source(place, inputs, tree / place) / f"{place}.usda"
        parts["light layer"] = "none made: Blender's default light, no shown places"
    older = sorted(name for name, said in parts.items() if "older (" in said)
    note = {"mode": "newest made outputs, a preview: not the accepted stage", "live run commit": commit[:9],
            "reads from": f"light-passes@{place} {made['output'][:12]} ({standing(f'light-passes@{place}', made, commit)})",
            "parts": parts,
            "not remade on the live run's commit yet (each keeps its newest earlier output, a bake its earlier bake)":
                older,
            "shown places dropped / added by the newest scene record": [dropped, added],
            "left out": "settle, motion, effects and people layers (only an assembly takes them)"}
    return {"stage": f"newest lit stage of {place} ({parts['light layer']})", "folder": str(tree / place),
            "root": str(root), "note": note}


if __name__ == "__main__":
    name, where = sys.argv[1], pathlib.Path(sys.argv[2])
    if "--newest" in sys.argv[3:]:
        found = newest(name, where)
    else:
        found = final(name, where) if fast_store.accepted(f"assembly@{name}") else lit(name, where)
    print(json.dumps({"place": name, **found}))
