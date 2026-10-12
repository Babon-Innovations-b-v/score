"""The neighbours stage (experimental, PRD #6): a place's accepted assembly with every other place its scene record
shows (`places` in data/scene/<place>.json: the square and the launch past the flat's balcony) standing in it, each
read from the store, so a view looks out onto the other place and not onto empty space.

    make     copies the place's accepted assembly, then each neighbour's accepted assembly (read beside, as the runner
             reads `after`: versioned and waited on) into places/<neighbour>/, and points the base layer's reference
             (the seed's ../../<neighbour>/<neighbour>.usda) there. A neighbour is its assembly alone, without its
             own neighbours: the showing place makes the shown one's Places inactive anyway (tools/usd/scene.py's
             write_places), and so two places that show each other read no cycle. A shown place no stage makes yet
             (the far city, far_city_stage.py's seed) is read from its seed folder, a declared world file.
    gate     neighbours  every entry of the record stands under /<place>/Places, each reference there resolves to a
                         file, and each shown place has children
"""
import json
import pathlib
import shutil

from score import checks
from score.stages.assembly import stage_file

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = "places"
SEEN = "seen {}"


def shown(place):
    """The other places the place's scene record shows, by stage name (a place shown in itself, the tube's twin, is
    its own base layer and no neighbour)."""
    record = REPO / f"data/scene/{place}.json"
    entries = json.loads(record.read_text()).get("places", []) if record.exists() else []
    return sorted({entry["stage"] for entry in entries} - {place})


def neighbours(place):
    """The shown places that are places of the world (a kit each), whose assembly the stage reads beside."""
    return [other for other in shown(place) if (REPO / f"data/kit/{other}.json").exists()]


def files(place):
    """The scene record, and the seed folder of each shown place no stage makes."""
    unmade = sorted(set(shown(place)) - set(neighbours(place)))
    return {"scene record": "{data}/scene/{place}.json", **{SEEN.format(other): f"{{seeds}}/usd-r3/{other}"
                                                             for other in unmade}}


def applies(place):
    """Only a place that shows another has neighbours to take."""
    return bool(shown(place))


def make(inputs, out, seed, params):
    """The place's assembly with each shown place's output copied in and its reference pointed at the copy."""
    from pxr import Sdf
    shutil.copytree(inputs["assembly"], out, dirs_exist_ok=True, copy_function=shutil.copyfile)
    base = Sdf.Layer.FindOrOpen(str(out / "layers/base.usda"))
    for other in shown(stage_file(out).stem):
        source = inputs.get(f"assembly@{other}") or inputs[SEEN.format(other)]
        shutil.copytree(source, out / PLACES / other, copy_function=shutil.copyfile)
        base.UpdateCompositionAssetDependency(f"../../{other}/{other}.usda", f"../{PLACES}/{other}/{other}.usda")
    base.Save()


def reference_faults(prim):
    """Each reference on the prim whose file is not there."""
    faults = []
    for spec in prim.GetPrimStack():
        items = spec.referenceList
        for reference in (*items.explicitItems, *items.prependedItems, *items.appendedItems):
            if reference.assetPath and not pathlib.Path(spec.layer.ComputeAbsolutePath(reference.assetPath)).exists():
                faults.append(f"{prim.GetPath()}: its reference {reference.assetPath} resolves to no file")
    return faults


def judge_neighbours(output, inputs, evidence):
    """Fail when a shown place is missing, its reference resolves to nothing, or it stands empty."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_file(output)))
    place = stage.GetDefaultPrim().GetName()
    scope = stage.GetPrimAtPath(f"/{place}/Places")
    standing = {prim.GetName(): prim for prim in (scope.GetAllChildren() if scope else [])}
    entries = json.loads(pathlib.Path(inputs["scene record"]).read_text()).get("places", [])
    faults = [f"/{place}/Places/{entry['name']}: in the scene record, not in the stage" for entry in entries
              if entry["name"] not in standing]
    for name, prim in sorted(standing.items()):
        faults += reference_faults(prim)
        if not prim.GetChildren():
            faults.append(f"{prim.GetPath()}: no children, the shown place is empty")
    reason = (f"{len(faults)} faults in {len(standing)} shown places" if faults
              else f"{len(standing)} shown places stand, each with children: {', '.join(sorted(standing))}")
    return checks.Verdict("neighbours", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "shown": len(standing)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("neighbours", judge_neighbours),)
