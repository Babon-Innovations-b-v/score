"""A scene's physics trial made from its design (the owner, 2026-10-21: "the modules are not agnostic"), never from a
record written for the scene: its loose objects (the scene inventory's rows whose row kind is loose,
score/stages/row_kinds.py) as the assembly lays them, each lifted DROP_OVER straight up over where it stands and let
fall back onto it, under the gravity of the body the scene stands on in the environment's physics (its top scene's
site, data/physics/setting.json, the body's values from the reference table). A loose object something else stands in
the fall of is left out of the trial, named in `left out`. Doors move in the motion layer, so the trial hangs no hinge
and says why (`no_hinges`). A laid made model with moving parts (#177: maker/parts.py's nodes under its object, the
joints, limits and kg in its library record's `moving_parts`) gets its `parted` entry, each part its own body on its
joint (tools/usd/physics.write_parted); a made model the trial drops falls as one piece.

    ground(place, within, setting)                  (the body the scene stands on, its gravity in m/s²)
    trial(place, stage, inventory, kinds, ground)   the trial record tools/usd/physics.py writes
    parted(stage, dropped, record_of)               each laid made model's moving parts, the record's `parted`
"""
import json
import pathlib
import sys

import numpy as np

from score.review import setting as physics_setting
from score.stages import row_kinds

REPO = pathlib.Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO / "tools/usd"))
import physics  # noqa: E402

DROP_OVER = 0.5
SECONDS = 8.0
MOMENTS = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.5, 8.0)
SIZE = (960, 540)
EYE_HEIGHT = 1.6
FOV = 75.0
# The one material of data/physics/materials.json: the models carry no labelled parts yet, so each takes it.
MATERIAL = "steel"
NO_HINGES = ("the scene's doors move in its motion layer (score/stages/motion/from_design.py); the trial hangs none, "
             "since no door of a design has its frame and pins as objects of their own")


def ground(place, within, setting):
    """(the body the scene stands on, its gravity): its own site's, else the site of the scene holding it, up the
    holders of `within` ({place: what holds it}). Refused when no holder has a site, or its site is on a plot."""
    checked = physics_setting.checked(setting, physics_setting.reference())
    sites = {site["place"]: site["on"] for site in checked["sites"]}
    bodies = {body["body"]: body for body in checked["bodies"]}
    plots = {plot["plot"]: plot for plot in checked["plots"]}
    holder, seen = place, set()
    while holder not in sites:
        if holder in seen or holder not in within:
            raise ValueError(f"{place}: no scene holding it has a site in the environment's physics")
        seen.add(holder)
        holder = within[holder]
    on = sites[holder]
    found = bodies.get(on) or plots.get(on)
    return on, float(found["gravity"])


def falls(stage, name):
    """The drop of an object back onto where it stands, and whether its fall is clear (physics.faults)."""
    drop = {"object": name, "over": DROP_OVER}
    return drop, not physics.faults(stage, {"drops": [drop], "hinges": [], "moved": []})


def view_of(stage, names):
    """One view of the trial: from over the middle of the place's laid objects at eye height, at the bodies' middle."""
    boxes = [physics.world_box(prim) for prim in physics.laid_objects(stage)]
    low, high = np.min([box[0] for box in boxes], axis=0), np.max([box[1] for box in boxes], axis=0)
    middles = [np.mean(physics.world_box(physics.object_prim(stage, name)), axis=0) for name in names]
    aim = np.mean(middles, axis=0)
    eye = [float(low[0] + high[0]) / 2, float(low[1]) + EYE_HEIGHT, float(low[2] + high[2]) / 2]
    return {"name": "trial", "eye": eye, "aim": [float(value) for value in aim], "up": [0.0, 1.0, 0.0], "fov": FOV}


def made_record(address):
    """A library model's record (its `<id>.json`, place_build/maker's), or None when the address names no such file."""
    if str(REPO / "tools/library") not in sys.path:
        sys.path.insert(0, str(REPO / "tools/library"))
    import library_files
    found = library_files.parsed(address)
    if not found:
        return None
    path = library_files.resolve(library_files.reference(address, f"{found['id']}.json"))
    return json.loads(pathlib.Path(path).read_text()) if path and pathlib.Path(path).is_file() else None


def parted(stage, dropped, record_of=made_record):
    """The record's `parted` entries: each laid object not `dropped` holding part nodes (motion's PART names) whose
    library record (`record_of(address)`) lists its `moving_parts`, each part laid there its node, joint, axis, sign,
    limits and kg."""
    from score.stages.motion import from_design
    found = []
    for prim in physics.laid_objects(stage):
        nodes = {child.GetName() for child in prim.GetChildren() if from_design.PART.match(child.GetName())}
        address = prim.GetAttribute("score:library").Get() if prim.HasAttribute("score:library") else None
        if not nodes or prim.GetName() in dropped or not address:
            continue
        moving = (record_of(address) or {}).get("moving_parts") or {}
        parts = [{key: part[key] for key in ("node", "joint", "axis", "sign", "limits", "kg")}
                 for part in moving.get("parts", []) if part["node"] in nodes]
        if parts:
            found.append({"object": prim.GetName(), "parts": parts})
    return found


def trial(place, stage, inventory, kinds, under):
    """The trial record: every loose row's laid object whose fall is clear dropped back onto its own spot."""
    loose = [row["id"] for row in row_kinds.rows_that(inventory, "loose", kinds)]
    laid = [prim.GetName() for prim in physics.laid_objects(stage)]
    names = [name for name in laid if any(row_kinds.of_row(name, row) for row in loose)]
    drops, left = [], []
    for name in names:
        drop, clear = falls(stage, name)
        (drops if clear else left).append(drop if clear else name)
    body, gravity = under
    return {"place": place, "body": body, "gravity": gravity, "material": MATERIAL, "seconds": SECONDS,
            "drops": drops, "hinges": [], "no_hinges": NO_HINGES, "pushes": [], "moved": [],
            "parted": parted(stage, {drop["object"] for drop in drops}),
            "left out": [f"{name}: something stands in its fall" for name in left],
            "views": [view_of(stage, [drop["object"] for drop in drops])] if drops else [],
            "moments": list(MOMENTS), "size": list(SIZE),
            "from": f"the design: {len(loose)} loose rows of the scene inventory (data/checks/row-kinds.json), "
                    f"their {len(names)} laid objects; {body}'s gravity from the environment's physics"}
