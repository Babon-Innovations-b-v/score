"""The pick lock: the model the owner picked for a row stays the model the place shows, unless the owner writes otherwise.

    .venv/bin/python tools/usd/picks.py record <place> <row> <model.gltf> [<more .gltf>] --decided "<who, when: what was picked and why>"
    .venv/bin/python tools/usd/picks.py check <stage.usda>

A pick is written on the inventory row (`pick`: the model's name, its file hash, complete.model_hash, and the
decision in words; a row the owner saw drawn by several models, a piece's variants or its glowing part, holds them all
as `models`, {name: hash}) and, at every export, onto each object of that row in the stage (`score:pick_sha256`, beside the
hash of the model the object actually shows, `score:model_sha256`). Export refuses to write a stage where a picked row's
object shows another model (another take, a code build, a different file) or where a picked row has no object at all
(a slab or a code build drawn in its place), unless the row carries `pick_replaced`: the owner's written decision to
replace it. The lock is protected entities in LEGO-Anything's sense (arXiv 2609.36380, App. G.4): an agent may not
change what the owner picked; the check is exact, by hash, never by looking.

The case it stops (2026-10-09): a rocket built in code shown in place of the made model the owner had picked.
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import complete  # noqa: E402


class PickBroken(ValueError):
    """An export that would replace a picked model without a written owner decision."""


def picked(row):
    """A row's pick, or None: only a row whose pick has a hash and no written replacement is locked."""
    pick = row.get("pick")
    if not pick or not pick_hashes(pick) or str(row.get("pick_replaced", "")).strip():
        return None
    return pick


def pick_hashes(pick):
    """The model hashes a pick allows: its one model's, or each of its several models'."""
    return set((pick.get("models") or {}).values()) or ({pick["sha256"]} if pick.get("sha256") else set())


def pick_sha256(pick, model):
    """The hash the pick holds for one model of its row: its several models' entry for it, else its one model's."""
    return (pick.get("models") or {}).get(model) if pick.get("models") else pick.get("sha256")


def pick_name(pick):
    """The picked model or models, named for a fault."""
    models = pick.get("models")
    return ", ".join(f"{name} ({sha256[:12]})" for name, sha256 in sorted(models.items())) if models else \
        f"{pick['model']} ({pick['sha256'][:12]})"


def faults(rows, shown):
    """Every way the shown objects break the picks: rows is the inventory's rows, shown {row: [(object, model,
    model sha256)]}. A fault is {row, object, why}."""
    found = []
    for row in rows:
        pick = picked(row)
        if pick is None:
            continue
        objects = shown.get(row["id"], [])
        if not objects:
            found.append({"row": row["id"], "object": None,
                          "why": f"the owner picked {pick_name(pick)}, and no object of this row "
                                 "is on the stage (something else stands in its place, or it was dropped)"})
        allowed = pick_hashes(pick)
        for name, model, sha256 in objects:
            if sha256 not in allowed:
                found.append({"row": row["id"], "object": name,
                              "why": f"shows {model} ({(sha256 or 'no hash')[:12]}), not the owner's pick "
                                     f"{pick_name(pick)}"})
    return found


def locked_count(rows):
    """How many rows are locked to an owner's pick."""
    return sum(1 for row in rows if picked(row) is not None)


def stage_shown(stage_path):
    """{row: [(object path, model, model sha256)]} of a stage's laid objects."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_path))
    found = {}
    for prim in stage.Traverse():
        if not prim.HasAttribute("score:row"):
            continue
        sha256 = prim.GetAttribute("score:model_sha256").Get() if prim.HasAttribute("score:model_sha256") else None
        found.setdefault(prim.GetAttribute("score:row").Get(), []).append(
            (str(prim.GetPath()), prim.GetAttribute("score:model").Get(), sha256))
    return found


def check(stage_path, inventory):
    """The pick lock on a stage: (faults, how many rows are locked)."""
    return faults(inventory["rows"], stage_shown(stage_path)), locked_count(inventory["rows"])


def record(inventory_path, row_id, gltfs, decided):
    """Write the owner's pick of a row into its inventory: the model (or the row's several models), each hash and the
    decision in words."""
    if not decided.strip():
        raise SystemExit("a pick needs the owner's decision in words (--decided)")
    inventory = json.loads(pathlib.Path(inventory_path).read_text())
    row = next((row for row in inventory["rows"] if row["id"] == row_id), None)
    if row is None:
        raise SystemExit(f"no row {row_id} in {inventory_path}")
    gltfs = [gltfs] if isinstance(gltfs, (str, pathlib.Path)) else list(gltfs)
    if len(gltfs) == 1:
        row["pick"] = {"model": pathlib.Path(gltfs[0]).stem, "sha256": complete.model_hash(gltfs[0]), "decided": decided}
    else:
        row["pick"] = {"models": {pathlib.Path(gltf).stem: complete.model_hash(gltf) for gltf in gltfs},
                       "decided": decided}
    write_inventory(inventory_path, inventory)
    return row["pick"]


def write_inventory(inventory_path, inventory):
    """Write an inventory back in its file's own indent (tabs or one space), so a pick changes only its own lines."""
    path = pathlib.Path(inventory_path)
    indent = "\t" if path.read_text().startswith("{\n\t") else 1
    path.write_text(json.dumps(inventory, indent=indent, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    recording = commands.add_parser("record")
    recording.add_argument("place")
    recording.add_argument("row")
    recording.add_argument("gltf", type=pathlib.Path, nargs="+")
    recording.add_argument("--decided", required=True)
    checking = commands.add_parser("check")
    checking.add_argument("stage", type=pathlib.Path)
    options = parser.parse_args()
    if options.command == "record":
        print(record(complete.inventory_path(options.place), options.row, options.gltf, options.decided))
        return
    place = options.stage.stem
    found, locked = check(options.stage, json.loads(complete.recorded_inventory(place, options.stage).read_text()))
    for fault in found:
        print(f"{fault['row']}: {fault['object'] or '(none)'}: {fault['why']}")
    print(f"{locked} rows locked to an owner's pick, {len(found)} broken")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
