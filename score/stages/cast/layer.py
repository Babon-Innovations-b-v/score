"""The characters layer (experimental, 2026-10-13): row `characters-layer@<place>`, the place's people laid from its
accepted cast, each in its own look's accepted body, for the assembly to take in place of the seed's characters.

    make     every person of the cast (cast@<place>'s cast.json: spot or walk, turn, clip and its start, look) laid
             as tools/characters/cast.py lays one (a SkelRoot referencing its body, placed or walking, playing its
             clip, held still where the cast says), the body its look's dressed body (people-dress-<look>, or
             people-dress-<look>-in-<surface> where its design row wears a fabric of its own, `-v<n>` its own
             variant, converted by tools/characters/skel_usd.py into assets/characters/<that row's suffix>.usdc);
             the crowd as cast.py's point instancer over its look's body, its copies the cast's own. layers/characters.usda, and
             characters.json: each person's look and, for one not laid, what is missing (the completion gate's
             people check reads it)
    gate     laid    every person and the crowd laid in their own look's accepted body; a cast naming no look, or a
                     look with no usable dressed body (the dress rows are the row's optional reads), leaves its person
                     out, never a stand-in, and passes with each gap named in characters.json and its findings: the
                     place assembles with what passed and complete's people check fails each gap by name (the
                     overseer's 14:00 rule, 2026-10-13)

tools/characters is loaded by its file path inside the make, never put on the import path (the cast stage's overlay:
on the path it would join other stages' code versions); its two files are declared inputs instead.
"""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import tempfile

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
CHARACTERS = REPO / "tools/characters"
LAYER = "layers/characters.usda"
ASSETS = "assets/characters"
RECORD = "characters.json"
DRESS = "people-dress"
SCRATCH = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "tmp"


def files(place):
    """The place's design (its people and crowd, its palettes, what each row wears: data/people/rows.json, #26) and
    the two tools/characters files the make loads."""
    from score.stages import people_rows
    return {"design": ("{data}/people/rows.json", people_rows.place_part(place)),
            "cast writer": "{repo}/tools/characters/cast.py", "skeleton writer": "{repo}/tools/characters/skel_usd.py"}


def body_row(look, surface=None, variant=0):
    """The dress row of a cast look (`person/outfit`) worn in its row's fabric (`-in-<surface>`, people_rows'
    `dress`) and the person's variant (`-v<n>`, people_rows.persons), or None for a cast that names none."""
    if not look:
        return None
    return (f"{DRESS}-{look.replace('/', '-')}" + (f"-in-{surface}" if surface else "")
            + (f"-v{variant}" if variant else ""))


def dressed_of(row):
    """(look, surface or None, variant) of a dress row's name (body_row's, the look as the line names it)."""
    found = re.fullmatch(r"(.+?)(?:-in-(.+?))?(?:-v([1-9][0-9]*))?", row.removeprefix(f"{DRESS}-"))
    return found[1], found[2], int(found[3] or 0)


def loaded(name):
    """A tools/characters module, loaded by its file path (its folder put on the path only while it loads, for its
    own imports of its siblings)."""
    import sys
    if name in sys.modules:
        return sys.modules[name]
    sys.path.insert(0, str(CHARACTERS))
    try:
        spec = importlib.util.spec_from_file_location(name, CHARACTERS / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(CHARACTERS))
    return module


def asset_for(row, body, out):
    """A dress row's dressed body as the stage's asset, assets/characters/<look>[-in-<surface>][-v<n>].usdc (its row's
    name without the prefix: each fabric and variant of a look its own asset)."""
    skel_usd = loaded("skel_usd")
    with tempfile.TemporaryDirectory(dir=SCRATCH) as scratch:
        named = pathlib.Path(scratch) / f"{row.removeprefix(f'{DRESS}-')}.glb"
        shutil.copyfile(pathlib.Path(body) / "body.glb", named)
        return skel_usd.convert(named, out / ASSETS)


def lay_person(stage, root, single, asset):
    """One person as cast.py lays one, in its own look's body (the body is the outfit, so no part is hidden)."""
    writer = loaded("cast")
    parts, clips = writer.asset_facts(asset)
    path = f"{root}/{single['name']}"
    start = single.get("start", 0.0) * clips.get(single["doing"], 0.0)
    prim = writer.referenced(stage, path, asset, start)
    if single.get("path"):
        writer.walked(prim, single["path"], single.get("pace", writer.WALK_PACE))
    else:
        writer.placed(prim, single["at"], single["turn"])
    writer.playing(stage, path, single["doing"], clips)
    if single.get("held"):
        writer.held_still(stage, path, asset, single["doing"], start)
    prim.SetCustomDataByKey("score:character", single["character"])
    prim.SetCustomDataByKey("score:look", single["look"])


def lay_crowd(stage, root, crowd, record, asset):
    """The crowd as cast.py's point instancer, its copies the cast's own (spread.py's, kept off the views)."""
    from pxr import Gf, UsdGeom, Vt
    writer = loaded("cast")
    whole = {**record, **{key: value for key, value in crowd.items() if key != "copies"}}
    writer.write_crowd(stage, f"{root}/{crowd['name']}", whole, [], asset)
    instancer = UsdGeom.PointInstancer(stage.GetPrimAtPath(f"{root}/{crowd['name']}"))
    copies = crowd["copies"]
    prototypes = {path.name: number for number, path in enumerate(instancer.GetPrototypesRel().GetTargets())}
    instancer.GetPositionsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*copy["at"]) for copy in copies]))
    instancer.GetOrientationsAttr().Set(Vt.QuathArray([
        Gf.Quath(Gf.Rotation(Gf.Vec3d(0, 1, 0), copy["turn"]).GetQuat()) for copy in copies]))
    instancer.GetScalesAttr().Set(Vt.Vec3fArray([Gf.Vec3f(copy["tall"]) for copy in copies]))
    instancer.GetProtoIndicesAttr().Set(Vt.IntArray([
        prototypes[f"{whole['doing'][copy['clip']]}_{copy['phase']}_{copy['palette']}"] for copy in copies]))
    instancer.GetPrim().SetCustomDataByKey("score:character", crowd["character"])
    instancer.GetPrim().SetCustomDataByKey("score:look", crowd["look"])


def make(inputs, out, seed, params):
    """The characters layer from the accepted cast and its looks' accepted bodies, and characters.json."""
    from pxr import Sdf, Usd, UsdGeom
    SCRATCH.mkdir(parents=True, exist_ok=True)
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    from score.stages import people_rows
    place = cast["place"]
    record = people_rows.cast_record(place, json.loads(pathlib.Path(inputs["design"]).read_text()))
    path = out / LAYER
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    rate = loaded("skel_usd").RATE
    layer.timeCodesPerSecond, layer.framesPerSecond = rate, rate
    stage = Usd.Stage.Open(layer)
    root = f"/{place}/Characters"
    UsdGeom.Scope.Define(stage, root)
    layer.GetPrimAtPath(f"/{place}").specifier = Sdf.SpecifierOver  # the place itself is the base's
    looks, assets = {}, {}
    for single in cast["characters"] + ([cast["crowd"]] if cast.get("crowd") else []):
        row = body_row(single.get("look"), single.get("surface"), single.get("variant", 0))
        looks[single["name"]] = {"look": single.get("look") or "none named"}
        if row is None or row not in inputs:
            looks[single["name"]]["missing"] = (f"no accepted body of its look ({row})" if row
                                                else "the cast names no look")
            continue
        if single is cast.get("crowd") and not single["copies"]:
            looks[single["name"]]["missing"] = "no copy of the crowd stood on its ground (the cast's counted gate: why)"
            continue
        if single is cast.get("crowd") and not record.get("crowd", {}).get("palettes"):
            looks[single["name"]]["missing"] = f"the crowd's colours: {record['crowd'].get('palettes_from')}"
            continue
        if row not in assets:
            assets[row] = asset_for(row, inputs[row], out)
        if single is cast.get("crowd"):
            lay_crowd(stage, root, single, record.get("crowd", {}), assets[row])
        else:
            lay_person(stage, root, single, assets[row])
    layer.Save()
    (out / RECORD).write_text(json.dumps({"place": place, "looks": looks, "licence": []}, indent=1))


def layer_faults(folder):
    folder = pathlib.Path(folder)
    return [f"no {name}" for name in (LAYER, RECORD) if not (folder / name).exists()]


def judge_laid(output, inputs, evidence):
    """Unknown on every person not laid in their own look's accepted body, named; pass when all are."""
    looks = json.loads((output / RECORD).read_text())["looks"]
    missing = tuple(f"{name} ({look['look']}): {look['missing']}" for name, look in looks.items() if "missing" in look)
    if missing:  # the overseer's 14:00 rule: the layer stands with what passed; complete's people check fails the gap
        return checks.Verdict("laid", checks.PASS, f"{len(looks) - len(missing)} of {len(looks)} people laid; "
                              f"{len(missing)} named missing, for complete's people check to fail",
                              {"missing": len(missing)}, {"missing": "lower"}, missing)
    return checks.Verdict("laid", checks.PASS, f"{len(looks)} people laid, each in their own look's body",
                          {"missing": 0}, {"missing": "lower"})


CONTRACT = contracts.Contract("characters-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("laid", judge_laid),)


def dressed_looks(place):
    """{(look, surface or None, variant)} the place's picked design dresses (`person-outfit`, as the dress rows are
    named; data/people/rows.json)."""
    from score.stages import people_rows
    return people_rows.dressed_looks(place)
