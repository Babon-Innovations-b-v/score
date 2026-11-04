"""A scene's effects record made from its design, never written by hand (the owner, 2026-10-21: "the modules are not
agnostic"): every object of every scene inventory row whose kind emits (score/stages/row_kinds.py) carries each
effect its kind emits, from the library of measured effects (data/checks/effects.json), riding the object at the spot
its effect names on the object's own box, made and drawn by the one rule for what the effect is made of (its
`matter`'s method: Newton for grains, the baked particles for a cloud or a flame). Its footage checks are the effect's own, measured on that emitter; what
emits and stands nowhere on the stage is named in `missing`. A kind with `on` (a pot) emits only where its row stands
on a row of one of those kinds (a cooker): a pot on a shelf, or a bare hob, lets out no steam, named in `quiet`.

    held_on(row, rows, kinds)   whether a row stands where its kind emits (its `on`, or anywhere for a kind with none)

    record(place, inventory, kinds, effects, stage)   the effects record tools/usd/effects.py writes, from the design
"""
import numpy as np

from score.stages import row_kinds


def own_box(stage, path):
    """(middle, half size) of a prim's bounds in its own frame, metres."""
    from pxr import Usd, UsdGeom
    found = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeUntransformedBound(
        stage.GetPrimAtPath(path)).ComputeAlignedRange()
    if found.IsEmpty():
        return np.zeros(3), np.zeros(3)
    low, high = np.asarray(found.GetMin(), dtype=float), np.asarray(found.GetMax(), dtype=float)
    return (low + high) / 2, (high - low) / 2


def spot_on(stage, path, at):
    """Where on the object an effect stands: from its own box's middle, each axis `at` times its half size."""
    middle, half = own_box(stage, path)
    return [round(float(value), 4) for value in middle + np.asarray(at, dtype=float) * half]


def emitter(spec, method, name, row, on, offset, number):
    """One emitter of an effect on an object: the effect's measured template, how it is made and drawn (the method
    of its matter, effects.json `methods`), its seed moved on by the object's number so two objects of a row never
    let out the same particles."""
    entry = dict(spec["emitter"], name=name, row=row, placement={"on": on, "offset": offset},
                 made_by=method["made_by"], drawn=method["drawn"])
    entry["seed"] = int(spec["emitter"].get("seed", 0)) + number
    return entry


def checks_of(spec, name):
    """The effect's footage checks, each measured on this emitter."""
    return [dict(check, name=f"{name}: {check['name']}", emitters=[name], anchor=name) for check in spec["checks"]]


def held_on(row, rows, kinds):
    """Whether a row stands where its kind emits: on (its anchor `on:<row>`) a row of one of its kind's `on` kinds;
    anywhere for a kind with no `on`."""
    wanted = kinds[row["row_kind"]].get("on")
    if not wanted:
        return True
    anchor = str(row.get("anchor") or "")
    holder = rows.get(anchor.removeprefix("on:")) if anchor.startswith("on:") else None
    return holder is not None and row_kinds.kind_of(holder, kinds) in wanted


def record(place, inventory, kinds, effects, stage):
    """The scene's effects record from its design: {place, about, effects, no_light, footage, missing, quiet}."""
    entries, found_checks, sources, lights, missing, quiet = [], [], {}, set(), [], []
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    for row in row_kinds.rows_that(inventory, "emits", kinds):
        if not held_on(row, rows, kinds):
            quiet.append(f"{row['id']}: a {row['row_kind']} emits only standing on a "
                         f"{' or '.join(kinds[row['row_kind']]['on'])} (data/checks/row-kinds.json `on`), and it "
                         f"stands on {row.get('anchor') or 'nothing named'}")
            continue
        paths = row_kinds.objects_of(stage, place, row["id"])
        for effect in kinds[row["row_kind"]]["effects"]:
            spec = effects["kinds"][effect]
            if not paths:
                missing.append(f"{row['id']} emits {effect}, and no object of it stands on the stage")
            for number, path in enumerate(paths):
                name = f"{path.rsplit('/', 1)[-1]}_{effect}"
                on = path[len(f"/{place}/"):]
                entries.append(emitter(spec, effects["methods"][spec["matter"]], name, row["id"], on,
                                       spot_on(stage, path, spec["at"]), number))
                found_checks += checks_of(spec, name)
                sources.update(spec["sources"])
                lights.add(spec["no_light"])
    return {"place": place,
            "about": "Made from the scene's design (score/stages/effects/from_design.py): each object of a row whose "
                     "kind emits carries its kind's measured effects (data/checks/effects.json).",
            "effects": entries, "no_light": "; ".join(sorted(lights)) or None,
            "footage": {"how": effects["how"], "licence": effects["licence"], "sources": sources,
                        "checks": found_checks},
            "missing": missing, "quiet": quiet}
