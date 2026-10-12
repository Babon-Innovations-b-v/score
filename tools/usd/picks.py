"""The pick lock: the model the owner picked for a row stays the model the place shows, unless the owner writes otherwise.

    .venv/bin/python tools/usd/picks.py record <place> <row> <model.gltf> [<more .gltf>] --decided "<who, when: what was picked and why>"
    .venv/bin/python tools/usd/picks.py check <stage.usda>

A pick is written on the inventory row (`pick`: the model's name, its file hash, stage_inputs.model_hash, and the
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
import stage_inputs  # noqa: E402
from pick_lock import PickBroken, faults, locked_count, pick_hashes, pick_name, pick_sha256, picked  # noqa: E402,F401


def stage_shown(stage_path):
    """{row: [(object path, model, model sha256)]} of a stage's own laid objects (a neighbour shown through a doorway,
    under /<place>/Places, is held by its own place's picks). An object the surface stage repainted shows the model its
    bake repainted (`score:repaint_of`, written by the assembly beside the baked file's hash): a pick chooses the
    model, never its old paint (owner, 2026-10-12)."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_path))
    found = {}
    for prim in stage.Traverse():
        if not prim.HasAttribute("score:row") or str(prim.GetPath()).split("/")[2:3] == ["Places"]:
            continue
        named = next((name for name in ("score:repaint_of", "score:model_sha256") if prim.HasAttribute(name)), None)
        sha256 = prim.GetAttribute(named).Get() if named else None
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
        row["pick"] = {"model": pathlib.Path(gltfs[0]).stem, "sha256": stage_inputs.model_hash(gltfs[0]),
                       "decided": decided}
    else:
        row["pick"] = {"models": {pathlib.Path(gltf).stem: stage_inputs.model_hash(gltf) for gltf in gltfs},
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
        print(record(stage_inputs.inventory_path(options.place), options.row, options.gltf, options.decided))
        return
    place = options.stage.stem
    found, locked = check(options.stage, json.loads(stage_inputs.recorded_inventory(place, options.stage).read_text()))
    for fault in found:
        print(f"{fault['row']}: {fault['object'] or '(none)'}: {fault['why']}")
    print(f"{locked} rows locked to an owner's pick, {len(found)} broken")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
