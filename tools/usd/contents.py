"""The completion gate's contents checks: what a complete place holds, judged on its stage and the stage outputs, not
only that the stages before it passed. One source for both ways in: tools/usd/complete.py runs them on a work stage
(the accepted outputs read from the framework's store), the runner's complete stage (score/stages/complete) on the
place's assembled stage (the accepted outputs it reads). Each answers pass, fail or unknown with its faults; unknown
blocks like fail.

    people      the stage's characters are the cast's (data/characters/<place>.json): every person and group member
                by name, the crowd with its count; every look a made model: the place's accepted characters layer
                (characters-layer@<place>, the cast stage) wrote every person of it with no look missing and none
                the licence rule refused; without one, the stage's bodies are the seed's, each judged by its built
                body's report, and a body of SOMA's mesh in drapes is no made model (the owner, #5, 2026-10-10:
                "soma is for the rig, not the mesh"). No cast: unknown
    effects     every need the place has (data/checks/contents.json) is an entry of its effects record that stands
                under /<place>/Effects (in any variant)
    motion      every motion of its records (data/motion, and data/movers: what SCORE moves that the game left
                standing) moves on the stage (time samples), and every need is one of them
    crops       where crops apply: the share of soil tiles (meshes said `soil`) with a plant of the crops layer
                (/<place>/Crops, a point instancer a kind) over them, at least the place's planted share
    likeness    every generated row's object (inventory kind `generate`) held to its close-up: the place's accepted
                likeness output (the props rows) names it; none for a place with generated models is unknown
    painted     every generated row's object on the stage repainted by the surface stage's bake (score:repaint_of,
                stamped by the assembly) and the place's surfaces-check accepted (a code row's model is painted by
                its builder with the library's surfaces). The palette gate joins once it lands (#8)
    light       the light layer (layers/light.usda, the per-lamp baked layers of the owner's light plan) is held by
                the stage's root, and every lamp of the scene record stands under /<place>/Lights
    sound       the sound layer (layers/sound.usda) is held by the root and every room tone the place's sound table
                (data/sound/places.json) names stands under /<place>/Sound/Room
    neighbours  every place the scene record shows stands under /<place>/Places, its references resolve to files,
                and it has children
    game        no record the place is made from (its scene record, cast, effects, motions, movers, room tones)
                cites the game 2099 as where its numbers come from (`from`: the game, 2099, a .gd or .tscn file)
    waiting     no entry of the scene record waits on its model (the assembly lays nothing for one and names it on
                the root prim, score:waiting): each such entry fails as a gap

Light and neighbours read the scene record the stage was assembled from (scene.json beside its root, which the
assembly stage writes: the accepted scene-record output, else the seed's), and data/scene/<place>.json for a stage
with none beside it.

A place that is a part of another (contents.json `part_of`: the garage's and the hangar's door leaves) is judged
on people, light, sound and neighbours on its host's stage, which shows it; its own stage on the rest.

The world files are read from DATA (the repository's data; the runner's complete stage declares the same folders
as its files) and built bodies from BODIES. Nothing here imports OpenUSD at the top, so complete.py's hook can import
it.
"""
import json
import os
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = REPO / "data"
BODIES = pathlib.Path(os.environ.get("MOTION_WORK", pathlib.Path.home() / ".farm-factory-motion/work")) / "bodies"
EXPECTED = "checks/contents.json"
PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
LIGHT_LAYER = "./layers/light.usda"
ASSEMBLED_SCENE = "scene.json"  # the record the assembly stage built the stage from, beside its root
WAITING = "score:waiting"  # the root prim's entries of that record laid nothing, waiting on their model
SOUND_LAYER = "./layers/sound.usda"
MADE_ROUTE = "prop"
GAME = re.compile(r"\b2099\b|\bthe game\b|\.gd\b|\.tscn\b", re.IGNORECASE)
# The stage outputs a check reads: {name: the accepted output's folder, or None when there is none}.
OUTPUTS = ("likeness", "surfaces-check", "characters-layer")


# --- the place's records --------------------------------------------------------------------------------------------

def record(kind, place):
    """A place's record of one kind (data/<kind>/<place>.json), or None when it has none."""
    path = DATA / kind / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def expected(place):
    """What the place must hold beyond its rows (data/checks/contents.json), or None when it is not listed."""
    return json.loads((DATA / EXPECTED).read_text())["places"].get(place)


def root_layers(stage):
    """The sublayer paths the stage's root holds."""
    return list(stage.GetRootLayer().subLayerPaths)


def generated_rows(inventory):
    """The rows whose model is generated (kind `generate`), the ones the surface line paints and the likeness gate
    holds to their close-ups; a code row's model is built and painted by its builder."""
    return {row["id"] for row in inventory["rows"] if row.get("kind") == "generate"}


def model_prims(stage, place, rows):
    """Every object prim of the place laying a model (score:model) of one of the rows, not in a shown place or a
    character."""
    left_out = (f"/{place}/Places/", f"/{place}/Characters/")
    return [prim for prim in stage.Traverse() if prim.HasAttribute("score:model") and prim.HasAttribute("score:row")
            and prim.GetAttribute("score:row").Get() in rows and not str(prim.GetPath()).startswith(left_out)]


def outcome(faults, passed, unknown=None):
    """(result, faults, note): fail on faults, unknown when it could not tell, else pass."""
    if faults:
        return FAIL, faults, f"{len(faults)} faults"
    if unknown:
        return UNKNOWN, [], unknown
    return PASS, [], passed


# --- people ---------------------------------------------------------------------------------------------------------

def cast_names(cast):
    """The characters a cast places by name: its people's and its groups' members' (`<group>_<n>`)."""
    return [person["name"] for person in cast.get("people", [])] + [
        f"{group['name']}_{number}" for group in cast.get("groups", []) for number in range(group["count"])]


def body_faults(body):
    """Why a body drawn on the stage is not a made model, from its built body's report."""
    report = BODIES / f"{body}.json"
    if not report.exists():
        return [f"{body}: no built body's report at {report}"]
    found = json.loads(report.read_text())
    if found.get("route") != MADE_ROUTE:
        drapes = sorted(found.get("drapes") or {})
        return [f"{body}: not a made model: its body is SOMA's mesh" + (f" in drapes ({', '.join(drapes)})" if drapes
                                                                         else "")
                + " (the owner, #5, 2026-10-10: soma is for the rig, not the mesh; make it on the prop route)"]
    rejected = [kind for kind, simulator in (found.get("drapes") or {}).items()
                if not str(simulator.get("name", "")).startswith(("Newton", "Blender"))]
    return [f"{body}: {kind} draped by a simulator that is not commercial-OK" for kind in rejected]


def layer_faults(layer):
    """What the place's accepted characters layer (its characters.json) left unmade or refused."""
    written = json.loads((pathlib.Path(layer) / "characters.json").read_text())
    return [f"{name} ({look['look']}): not a made model: {look['missing']}" for name, look in written["looks"].items()
            if "missing" in look] + [f"refused by the licence rule: {fault}" for fault in written["licence"]]


def judge_people(stage, place, inventory, outputs):
    """The stage's characters against the cast: each by name, the crowd's count, every look a made model."""
    from pxr import UsdGeom
    cast = record("characters", place)
    if cast is None:
        return UNKNOWN, [], f"no cast (data/characters/{place}.json): who is here is not recorded"
    scope = stage.GetPrimAtPath(f"/{place}/Characters")
    standing = {prim.GetName(): prim for prim in (scope.GetChildren() if scope else [])}
    wanted = cast_names(cast)
    faults = [f"{name}: in the cast, not on the stage" for name in wanted if name not in standing]
    layer = outputs.get("characters-layer")
    faults += layer_faults(layer) if layer else []
    bodies = set() if layer else {standing[name].GetCustomDataByKey("score:character") for name in wanted
                                  if name in standing}
    crowd = cast.get("crowd")
    if crowd:
        instancer = UsdGeom.PointInstancer(standing.get(crowd["name"])) if crowd["name"] in standing else None
        shown = len(instancer.GetPositionsAttr().Get() or []) if instancer else 0
        if shown != crowd["count"]:
            faults.append(f"{crowd['name']}: the cast's crowd is {crowd['count']}, the stage shows {shown}")
        bodies |= set() if layer else {crowd["character"]}
    extra = sorted(set(standing) - set(wanted) - ({crowd["name"]} if crowd else set()))
    faults += [f"{name}: on the stage, not in the cast" for name in extra]
    for body in sorted(body for body in bodies if body):
        faults += body_faults(body)
    if None in bodies:
        faults.append("a character on the stage names no body (score:character)")
    return outcome(faults, f"{len(wanted)} people{' and a crowd of ' + str(crowd['count']) if crowd else ''}, every "
                           "body a made model" if wanted or crowd else cast.get("note", "nobody, as the cast says"))


# --- effects and motion ---------------------------------------------------------------------------------------------

def effects_standing(stage, place):
    """The names under /<place>/Effects in every variant of every variant set it has."""
    scope = stage.GetPrimAtPath(f"/{place}/Effects")
    if not scope:
        return set()
    names = {child.GetName() for child in scope.GetChildren()}
    for set_name in scope.GetVariantSets().GetNames():
        variant_set = scope.GetVariantSet(set_name)
        chosen = variant_set.GetVariantSelection()
        for name in variant_set.GetVariantNames():
            variant_set.SetVariantSelection(name)
            names |= {child.GetName() for child in scope.GetChildren()}
        variant_set.SetVariantSelection(chosen)
    return names


def unmet(needs, names):
    """The needs no name has in it."""
    return [need for need in needs if not any(need in name for name in names)]


def judge_effects(stage, place, inventory, outputs):
    """Every need of the place an entry of its effects record that stands on the stage."""
    wants = expected(place)
    if wants is None:
        return UNKNOWN, [], f"{EXPECTED} lists no expectations for {place}"
    effects = record("effects", place) or {}
    standing = effects_standing(stage, place)
    made = {entry["name"] for entry in effects.get("effects", [])} & standing
    faults = [f"{need}: no effect of the record stands on the stage with it in its name" + (
        "" if effects else f" (no effects record, data/effects/{place}.json)")
        for need in unmet(wants.get("effects", []), made)]
    return outcome(faults, f"{len(made)} effects stand; needs met: {', '.join(wants.get('effects', [])) or 'none'}")


def moving(prim):
    """Whether any attribute of the prim has more than one time sample."""
    return any(attribute.GetNumTimeSamples() > 1 for attribute in prim.GetAttributes())


def judge_motion(stage, place, inventory, outputs):
    """Every motion and mover of the place's records moving on the stage, and every need of the place one of them."""
    wants = expected(place)
    if wants is None:
        return UNKNOWN, [], f"{EXPECTED} lists no expectations for {place}"
    motions = (record("motion", place) or {}).get("motions", []) + (record("movers", place) or {}).get("movers", [])
    made = {motion["name"] for motion in motions
            if stage.GetPrimAtPath(motion["prim"]) and moving(stage.GetPrimAtPath(motion["prim"]))}
    still = [f"{motion['name']}: {motion['prim']} does not move on the stage" for motion in motions
             if motion["name"] not in made]
    faults = still + [f"{need}: no motion of the records moves with it in its name"
                      for need in unmet(wants.get("motion", []), made)]
    return outcome(faults, f"{len(made)} motions move; needs met: {', '.join(wants.get('motion', [])) or 'none'}")


# --- crops ----------------------------------------------------------------------------------------------------------

def plants(stage, place):
    """(x, z) of every plant of the crops layer: each point of each point instancer under /<place>/Crops, in the
    place's frame."""
    from pxr import Gf, Usd, UsdGeom
    scope = stage.GetPrimAtPath(f"/{place}/Crops")
    found = []
    for prim in (Usd.PrimRange(scope) if scope else []):
        if prim.IsA(UsdGeom.PointInstancer):
            matrix = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            for point in UsdGeom.PointInstancer(prim).GetPositionsAttr().Get() or []:
                at = matrix.Transform(Gf.Vec3d(point))
                found.append((at[0], at[2]))
    return found


def judge_crops(stage, place, inventory, outputs):
    """Where crops apply, the share of soil tiles with a plant of the crops layer over them at least the place's."""
    from pxr import Usd, UsdGeom
    wants = expected(place)
    if wants is None:
        return UNKNOWN, [], f"{EXPECTED} lists no expectations for {place}"
    if not wants.get("crops"):
        return PASS, [], "no crops here"
    least = wants["crops"]["planted_share"]
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    soil = [cache.ComputeWorldBound(prim).ComputeAlignedRange() for prim in stage.Traverse()
            if prim.IsA(UsdGeom.Mesh) and prim.HasAttribute("score:plain")
            and prim.GetAttribute("score:plain").Get() == "soil"]
    crops = plants(stage, place)
    if not soil:
        return UNKNOWN, [], "no soil tiles (meshes said soil) on the stage to plant"
    planted = sum(any(tile.GetMin()[0] <= x <= tile.GetMax()[0] and tile.GetMin()[2] <= z <= tile.GetMax()[2]
                      for x, z in crops) for tile in soil)
    share = planted / len(soil)
    faults = [] if share >= least else [f"{planted} of {len(soil)} soil tiles planted ({share:.2f}), under {least}"
                                        + ("; no crops layer (/<place>/Crops) on the stage" if not crops else "")]
    return outcome(faults, f"{planted} of {len(soil)} soil tiles planted ({share:.2f})")


# --- likeness and paint ---------------------------------------------------------------------------------------------

def laid_rows(stage, place):
    """The rows whose objects stand on the stage (score:row), not in a shown place."""
    return {prim.GetAttribute("score:row").Get() for prim in stage.Traverse() if prim.HasAttribute("score:row")
            and not str(prim.GetPath()).startswith(f"/{place}/Places/")}


def judge_likeness(stage, place, inventory, outputs):
    """Every generated row's object held to its close-up by the place's accepted likeness output."""
    generated = sorted(generated_rows(inventory) & laid_rows(stage, place))
    if not generated:
        return PASS, [], "no generated model on the stage"
    if outputs.get("likeness") is None:
        return UNKNOWN, [], (f"{len(generated)} generated rows and no accepted likeness@{place} (the props rows run "
                             f"only with data/props/{place}.json): none is held to its close-up")
    held = json.loads((pathlib.Path(outputs["likeness"]) / "likeness.json").read_text())["objects"]
    faults = [f"{row}: generated, not held to its close-up by likeness@{place}" for row in generated if row not in held]
    return outcome(faults, f"{len(generated)} generated rows held to their close-ups")


def judge_painted(stage, place, inventory, outputs):
    """Every generated model on the stage repainted by the surface stage's bake, and the place's paint checked."""
    models = model_prims(stage, place, generated_rows(inventory))
    if not models:
        return PASS, [], "no generated model on the stage"
    unpainted = sorted({prim.GetAttribute("score:model").Get() for prim in models
                        if not prim.HasAttribute("score:repaint_of")})
    faults = [f"{model}: laid as the seed painted it, not repainted by the surface stage's bake" for model in unpainted]
    unknown = None if outputs.get("surfaces-check") else f"no accepted surfaces-check@{place}: its paint is unchecked"
    return outcome(faults, f"{len(models)} objects of generated models, each repainted and checked", unknown)


# --- light, sound and neighbours ------------------------------------------------------------------------------------

def assembled_scene(stage, place):
    """The scene record the stage was assembled from (scene.json beside it, written by the assembly stage), else the
    place's record in data/scene; None with neither."""
    beside = pathlib.Path(stage.GetRootLayer().realPath).parent / ASSEMBLED_SCENE
    return json.loads(beside.read_text()) if beside.exists() else record("scene", place)


def judge_light(stage, place, inventory, outputs):
    """The light layer held by the root, and every lamp of the scene record standing as a light."""
    from pxr import UsdLux
    scene = assembled_scene(stage, place)
    if scene is None:
        return UNKNOWN, [], f"no scene record (data/scene/{place}.json)"
    faults = [] if LIGHT_LAYER in root_layers(stage) else [
        f"no light layer ({LIGHT_LAYER}): the per-lamp baked layers of the light plan are not on this stage"]
    scope = stage.GetPrimAtPath(f"/{place}/Lights")
    lights = [prim for prim in (scope.GetChildren() if scope else []) if prim.HasAPI(UsdLux.LightAPI)]
    if len(lights) < len(scene.get("lights", [])):
        faults.append(f"{len(scene.get('lights', []))} lamps in the scene record, {len(lights)} on the stage")
    return outcome(faults, f"the light layer and {len(lights)} lamps")


def judge_sound(stage, place, inventory, outputs):
    """The sound layer held by the root, and every room tone of the place's sound table standing."""
    table = json.loads((DATA / "sound/places.json").read_text())["places"].get(place)
    if table is None:
        return UNKNOWN, [], f"the sound table (data/sound/places.json) has no entry for {place}"
    faults = [] if SOUND_LAYER in root_layers(stage) else [f"no sound layer ({SOUND_LAYER}) on this stage"]
    names = [*table.get("loops", []), *table.get("heard_through", [])]
    faults += [f"{name}: a room tone of the sound table, not on the stage" for name in names
               if not stage.GetPrimAtPath(f"/{place}/Sound/Room/{name}")]
    return outcome(faults, f"the sound layer and {len(names)} room tones")


def reference_faults(prim):
    """Each reference on the prim whose file is not there."""
    faults = []
    for spec in prim.GetPrimStack():
        items = spec.referenceList
        for reference in (*items.explicitItems, *items.prependedItems, *items.appendedItems):
            if reference.assetPath and not pathlib.Path(spec.layer.ComputeAbsolutePath(reference.assetPath)).exists():
                faults.append(f"{prim.GetPath()}: its reference {reference.assetPath} resolves to no file")
    return faults


def judge_neighbours(stage, place, inventory, outputs):
    """Every shown place standing, resolving and not empty."""
    scene = assembled_scene(stage, place)
    if scene is None:
        return UNKNOWN, [], f"no scene record (data/scene/{place}.json)"
    scope = stage.GetPrimAtPath(f"/{place}/Places")
    standing = {prim.GetName(): prim for prim in (scope.GetAllChildren() if scope else [])}
    entries = scene.get("places", [])
    faults = [f"/{place}/Places/{entry['name']}: in the scene record, not on the stage" for entry in entries
              if entry["name"] not in standing]
    for name in sorted({entry["name"] for entry in entries} & set(standing)):
        faults += reference_faults(standing[name])
        if not standing[name].GetChildren():
            faults.append(f"{standing[name].GetPath()}: no children, the shown place is empty")
    return outcome(faults, f"{len(entries)} shown places stand and resolve")


# --- nothing cites the game -----------------------------------------------------------------------------------------

def game_sources(found, where=""):
    """Each `from` in a record (at any depth) that cites the game: [(where, text)]."""
    if isinstance(found, dict):
        cited = [(where or "the record", found["from"])] if isinstance(found.get("from"), str) and \
            GAME.search(found["from"]) else []
        return cited + [hit for key, value in found.items() if key != "from"
                        for hit in game_sources(value, f"{where}.{key}" if where else key)]
    if isinstance(found, list):
        return [hit for number, value in enumerate(found) for hit in game_sources(value, f"{where}[{number}]")]
    return []


def judge_game(stage, place, inventory, outputs):
    """No record the place is made from cites the game as its source."""
    records = {f"data/{kind}/{place}.json": record(kind, place)
               for kind in ("scene", "characters", "effects", "motion", "movers")}
    records["data/sound/places.json"] = json.loads((DATA / "sound/places.json").read_text())["places"].get(place)
    counts = {name: len(game_sources(found)) for name, found in records.items() if found}
    faults = [f"{name}: {count} entries take their numbers from the game" for name, count in counts.items() if count]
    return outcome(faults, "no record cites the game")


def of_a_part(judge):
    """The judge, except on a place that is a part of another (contents.json `part_of`: a door's leaves, which the
    garage and the hangar show under their Places): it has no cast, lamps, room tones or shown places of its own, and
    those are judged on the host's stage, where it stands."""
    def judged(stage, place, inventory, outputs):
        host = (expected(place) or {}).get("part_of")
        if host:
            return PASS, [], f"a part of {host}: judged on {host}'s stage, where it stands"
        return judge(stage, place, inventory, outputs)
    judged.__doc__ = judge.__doc__
    return judged


def judge_waiting(stage, place, inventory, outputs):
    """Fail on every entry of the scene record the assembly laid nothing for because it waits on its model (the
    root prim's score:waiting): a gap, named."""
    root = stage.GetPrimAtPath(f"/{place}")
    waiting = list(root.GetAttribute(WAITING).Get() or []) if root and root.HasAttribute(WAITING) else []
    return outcome([f"a gap: {entry}" for entry in waiting], "no entry of the scene record waits on its model")


JUDGES = {"people": of_a_part(judge_people), "effects": judge_effects, "motion": judge_motion, "crops": judge_crops,
          "likeness": judge_likeness, "painted": judge_painted, "light": of_a_part(judge_light),
          "sound": of_a_part(judge_sound), "neighbours": of_a_part(judge_neighbours), "game": judge_game,
          "waiting": judge_waiting}
