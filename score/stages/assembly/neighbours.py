"""The neighbours stage (experimental, PRD #6): a place's accepted assembly with every other place its scene record
shows (`places`: the square and the launch past the flat's balcony) standing in it, each read from the store, so a
view looks out onto the other place and not onto empty space. The record is the one the assembly built from (its
scene.json: the accepted scene-record output where the place has one, else data/scene/<place>.json).

    make     copies the place's accepted assembly, then each neighbour's accepted assembly (read beside, as the runner
             reads `after`: versioned and waited on) into places/<neighbour>/, and points each layer's reference (the
             seed's base and the terrain's ground write ../../<neighbour>/<neighbour>.usda) there. A neighbour is its assembly alone, without its
             own neighbours: the showing place makes the shown one's Places inactive anyway (tools/usd/scene.py's
             write_places), and so two places that show each other read no cycle. A shown place no stage makes yet
             (the far city, far_city_stage.py's seed) is read from its seed folder, a declared world file.
    gate     neighbours  every entry of the record stands under /<place>/Places, each reference there resolves to a
                         file, each shown place has children, and none draws its own ground (its Outside) over the
                         place's own
"""
import json
import pathlib
import shutil

from score import checks
from score.stages import scene_record
from score.stages.assembly import RECORD, stage_file
from score.store import Store

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = "places"
SEEN = "seen {}"
# A shown place's own made ground (score/stages/terrain/outside.py writes it under /<place>/Outside).
OUTSIDE = "Outside"


def record_of(place):
    """The scene record the place's assembly builds from: its accepted scene-record output (the framework's store)
    where its plan has the row, else its seed record in data/scene; {} for a place with neither."""
    if scene_record.written(place):
        store = Store.default()
        output = store.accepted(f"scene-record@{place}")
        if output:
            return store.read_file(output, f"record/{place}.json")
    path = REPO / f"data/scene/{place}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def shown(place):
    """The other places the place's scene record shows, by stage name (a place shown in itself, the tube's twin, is
    its own base layer and no neighbour)."""
    return sorted({entry["stage"] for entry in record_of(place).get("places", [])} - {place})


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
    # The seed's base layer references its shown places, and the terrain's ground layer the ones the seed lacks.
    layers = [Sdf.Layer.FindOrOpen(str(path)) for path in sorted((out / "layers").glob("*.usd*"))]
    entries = json.loads((out / RECORD).read_text()).get("places", [])
    for other in sorted({entry["stage"] for entry in entries} - {stage_file(out).stem}):
        source = inputs.get(f"assembly@{other}") or inputs[SEEN.format(other)]
        shutil.copytree(source, out / PLACES / other, copy_function=shutil.copyfile)
        for layer in layers:
            layer.UpdateCompositionAssetDependency(f"../../{other}/{other}.usda", f"../{PLACES}/{other}/{other}.usda")
    place = stage_file(out).stem
    owns = has_own_ground(layers, place)
    for layer in layers:
        if owns:
            ground_left_out(layer, place)
        layer.Save()


def has_own_ground(layers, place):
    """Whether one of the place's layers draws its own made ground (/<place>/Outside): a room the terrain gave none
    (the airlock, the habitat) sees the ground through its doors only as its shown places draw it."""
    return any(layer.GetPrimAtPath(f"/{place}/{OUTSIDE}") for layer in layers)


def ground_left_out(layer, place):
    """Each place the layer stands under /<place>/Places with its own made ground (its Outside) made inactive, as the
    terrain stage does for the places it adds (outside.NEIGHBOUR_SHARED): a seed's base layer stood its places before
    any ground was made, so their grounds stayed on over the place's own and cut through the view (the old station's
    grey slab, 2026-10-18)."""
    from pxr import Sdf
    places = layer.GetPrimAtPath(f"/{place}/Places")
    for shown in (places.nameChildren if places else []):
        Sdf.CreatePrimInLayer(layer, shown.path.AppendChild(OUTSIDE)).active = False


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
    """Fail when a shown place is missing, its reference resolves to nothing, stands empty or draws its own ground over
    the place's own."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_file(output)))
    place = stage.GetDefaultPrim().GetName()
    scope = stage.GetPrimAtPath(f"/{place}/Places")
    standing = {prim.GetName(): prim for prim in (scope.GetAllChildren() if scope else [])}
    entries = json.loads((output / RECORD).read_text()).get("places", [])
    own_ground = stage.GetPrimAtPath(f"/{place}/{OUTSIDE}")
    faults = [f"/{place}/Places/{entry['name']}: in the scene record, not in the stage" for entry in entries
              if entry["name"] not in standing]
    for name, prim in sorted(standing.items()):
        faults += reference_faults(prim)
        if not prim.GetChildren():
            faults.append(f"{prim.GetPath()}: no children, the shown place is empty")
        ground = prim.GetChild(OUTSIDE)
        if own_ground and ground and ground.IsActive():
            faults.append(f"{prim.GetPath()}: its own ground ({OUTSIDE}) is drawn inside this place")
    reason = (f"{len(faults)} faults in {len(standing)} shown places" if faults
              else f"{len(standing)} shown places stand, each with children: {', '.join(sorted(standing))}")
    return checks.Verdict("neighbours", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "shown": len(standing)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("neighbours", judge_neighbours),)
