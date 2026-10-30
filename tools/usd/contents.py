"""The completion gate's contents checks: what a complete place holds, judged on its stage and the stage outputs, not
only that the stages before it passed. One source for both ways in: tools/usd/complete.py runs them on a work stage
(the accepted outputs read from the framework's store), the runner's complete stage (score/stages/complete) on the
place's assembled stage (the accepted outputs it reads). Each answers pass, fail or unknown with its faults; unknown
blocks like fail.

    people      the stage's characters are the cast its design gives (its people rows mapped in
                data/people/rows.json, score/stages/people_rows.cast_record): every person by name, the crowd with
                its count (any count above none while the design gives none); every look a made model: the
                place's accepted characters layer (characters-layer@<place>, the cast stage) wrote every person of it with no look missing and none
                the licence rule refused; without one, the stage's bodies are the seed's, each judged by its built
                body's report, and a body of SOMA's mesh in drapes is no made model (the owner, #5, 2026-10-10:
                "soma is for the rig, not the mesh"); and no far-only look (one the design does not make in
                full: score/stages/people_bodies/full.py on data/people/rows.json; the crowd's far body always) stands near enough to fill over FAR_SHARE of the frame
                height in any of the record's views, as the cast stage measures it (score/stages/cast/spread.py).
                A design that shows nobody (no row that acts, score/stages/design_layers.py): nobody may stand
                there. One that shows people while none are mapped for it: unknown
    effects     every row of the place's design that emits (its row kind, score/stages/row_kinds.py) has an effect
                standing: an emitter the effects layer laid on one of the row's objects, with the row's id in its
                name or its holder's
    motion      every moving thing of its accepted motion output (motion@<place>'s moves.json, made from its design)
                moves on the stage (time samples), and every row of its design that moves is one of them or written
                down as still with why; a design that moves with no motion output read is unknown
    crops       where its design shows crops (score/stages/design_layers.py): the share of soil tiles (meshes said
                `soil`) with a plant of the crops layer (/<place>/Crops, a point instancer a kind) over them, at
                least PLANTED_SHARE
    The design is the place's locked concept's scene inventory, kept under DESIGN; a place with none answers unknown
    on effects, motion and crops.
    likeness    every generated row's object (inventory kind `generate`) held to its close-up: the place's accepted
                likeness output (the props rows) names it, or a ship place's made piece the likeness of the place
                whose bake laid it (read beside); none for a place with generated models is unknown
    painted     every generated row's object on the stage repainted by the surface stage's bake (score:repaint_of,
                stamped by the assembly, or laid by it straight from the bake: the grounds' cairn, a ship place's made
                pieces by its origin.json) and the place's surfaces-check accepted (a code row's model is painted by
                its builder with the library's surfaces). The palette gate joins once it lands (#8)
    light       the light layer (layers/light.usda, the per-lamp baked layers of the owner's light plan) is held by
                the stage's root, and every lamp of the scene record stands under /<place>/Lights
    sound       the sound layer (layers/sound.usda) is held by the root and every sound of the place's bed (its room
                tone, or what the suit lets through outside: score/stages/sound/beds.py, from its design) stands
                under /<place>/Sound/Room; a bed its design does not decide is unknown
    neighbours  every place the scene record shows stands under /<place>/Places, its references resolve to files,
                and it has children
    game        no record the place is made from (its scene records: the one beside the stage, data/scene's and the
                accepted scene-record output's; its cast) cites the game 2099
                as where its numbers come from (a `from` or `source`: the game, 2099, a .gd or .tscn file); each
                fault counts the citing fields and the positions (at, centre, position, placed_at) so taken
    waiting     no entry of the scene record waits on its model (the assembly lays nothing for one and names it on
                the root prim, score:waiting): each such entry fails as a gap

Light and neighbours read the scene record the stage was assembled from (scene.json beside its root, which the
assembly stage writes: the accepted scene-record output, else the seed's), and data/scene/<place>.json for a stage
with none beside it. Game reads every one of them, so a record the stage was not built from still fails it.

The world files are read from DATA (the repository's data; the runner's complete stage declares the same folders
as its files) and built bodies from BODIES. Nothing here imports OpenUSD at the top, so complete.py's hook can import
it.
"""
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = REPO / "data"
BODIES = pathlib.Path(os.environ.get("MOTION_WORK", pathlib.Path.home() / ".farm-factory-motion/work")) / "bodies"
DESIGN = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "design/inventory"
ROW_KINDS = "checks/row-kinds.json"
# The share of a place's soil tiles its crops must plant where its design shows crops: a tenth left for the paths
# and bare ends a concept shows between beds.
PLANTED_SHARE = 0.9
PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
LIGHT_LAYER = "./layers/light.usda"
ASSEMBLED_SCENE = "scene.json"  # the record the assembly stage built the stage from, beside its root
WAITING = "score:waiting"  # the root prim's entries of that record laid nothing, waiting on their model
SOUND_LAYER = "./layers/sound.usda"
MADE_ROUTE = "prop"
EFFECT_KIND = "score:effect:kind"  # what an effect is, on every emitter the effects layer lays (tools/usd/effects.py)
GAME = re.compile(r"\b2099\b|\bthe game\b|\.gd\b|\.tscn\b", re.IGNORECASE)
# A far-only look may fill at most this share of a view's frame height (a person HEIGHT tall, the frame ASPECT wide, the
# view's fov vertical): the cast stage's own rule (score/stages/cast/spread.py, the captain's cut of 2026-10-13).
FAR_SHARE = 0.10
HEIGHT = 1.7
ASPECT = 16 / 9
DESIGNED_PEOPLE = "people/rows.json"
# The stage outputs a check reads: {name: the accepted output's folder, or None when there is none}.
OUTPUTS = ("likeness", "surfaces-check", "characters-layer", "scene-record", "motion")


# --- the place's records --------------------------------------------------------------------------------------------

def record(kind, place):
    """A place's record of one kind (data/<kind>/<place>.json), or None when it has none."""
    path = DATA / kind / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def design(place):
    """The place's design: its locked concept's scene inventory (DESIGN/<place>.json), None while it has none."""
    path = DESIGN / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def row_rules():
    """The row-kind rules (data/checks/row-kinds.json's kinds)."""
    return json.loads((DATA / ROW_KINDS).read_text())["kinds"]


def stages_module(name):
    """score.stages.<name>, the repository put on the path first (tools/usd/complete.py runs alone too)."""
    import importlib
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    return importlib.import_module(f"score.stages.{name}")


def rows_doing(found, what):
    """The ids of a design's rows whose kind does `what` (score/stages/row_kinds.py)."""
    return [row["id"] for row in stages_module("row_kinds").rows_that(found, what, row_rules())]


def cast_of(place):
    """The cast the place's design gives (its people rows mapped in data/people/rows.json, people_rows.cast_record),
    None while its people are not mapped."""
    path = DATA / DESIGNED_PEOPLE
    found = json.loads(path.read_text()) if path.exists() else {"places": {}}
    if place not in found["places"]:
        return None
    return stages_module("people_rows").cast_record(place, found)


def root_layers(stage):
    """The sublayer paths the stage's root holds."""
    return list(stage.GetRootLayer().subLayerPaths)


def generated_rows(inventory, place):
    """The rows whose model the shared loop makes (every row but a mechanic's, made on its own line, whatever the
    row's own kind), the ones the surface line paints and the likeness gate holds to their close-ups."""
    return {row["id"] for row in inventory["rows"] if row.get("kind") != "mechanic"}


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


def designed_cast(place):
    """The cast the place's design gives: nobody where its design shows no row that acts (design_layers), else its
    people mapped (cast_of); why it is not known, a sentence, while it has no design or its people are not mapped."""
    found = design(place)
    if found is None:
        return NO_DESIGN.format(place=place, folder=DESIGN)
    if "people" not in stages_module("design_layers").kinds_of(found, row_rules()):
        return {"place": place, "people": [], "note": "nobody, as its design shows"}
    cast = cast_of(place)
    if cast is None or not (cast.get("people") or cast.get("crowd") or cast.get("groups")):
        return (f"its design shows people and data/{DESIGNED_PEOPLE} maps none of them for it: who is here is not "
                "known")
    return cast


def judge_people(stage, place, inventory, outputs):
    """The stage's characters against the cast: each by name, the crowd's count, every look a made model."""
    from pxr import UsdGeom
    cast = designed_cast(place)
    if isinstance(cast, str):
        return UNKNOWN, [], cast
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
        wrong = not shown if crowd["count"] is None else shown != crowd["count"]
        if wrong:
            faults.append(f"{crowd['name']}: the cast's crowd is {crowd['count'] or 'some'}, the stage shows {shown}")
        bodies |= set() if layer else {crowd["character"]}
    extra = sorted(set(standing) - set(wanted) - ({crowd["name"]} if crowd else set()))
    faults += [f"{name}: on the stage, not in the cast" for name in extra]
    faults += far_faults(stage, place, cast, standing)
    for body in sorted(body for body in bodies if body):
        faults += body_faults(body)
    if None in bodies:
        faults.append("a character on the stage names no body (score:character)")
    return outcome(faults, f"{len(wanted)} people{' and a crowd of ' + str(crowd['count']) if crowd else ''}, every "
                           "body a made model" if wanted or crowd else cast.get("note", "nobody, as the cast says"))


def frame_shares(view, spots):
    """How much of a view's frame height a person standing at each spot fills (score/stages/cast/spread.frame_share,
    over many spots at once): 0 behind the eye or out of the frame."""
    import numpy as np
    eye, aim = np.asarray(view["eye"], float), np.asarray(view["aim"], float)
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    towards = np.asarray(spots, float).reshape(-1, 3) + [0.0, HEIGHT / 2, 0.0] - eye
    depth = towards @ forward
    half = np.tan(np.radians(view.get("fov", 70)) / 2)
    seen = (depth > 0.0) & (np.abs(towards @ up) <= half * depth) & (np.abs(towards @ right) <= half * ASPECT * depth)
    return np.where(seen, HEIGHT / (2 * np.maximum(depth, 1e-9) * half), 0.0)


def far_only(character, look, worn, full):
    """Whether a character wears a far-only look: its look (`<character>-<outfit>`, from the cast's `look` or the
    outfit it wears) not made in full; with none known, its character with no look made in full."""
    outfit = look.removeprefix(f"{character}_") if look else next(
        (part.removeprefix("plain_").replace("_", "-") for part in worn if part.startswith(("plain_", "work_"))), None)
    if outfit:
        return f"{character}-{outfit}" not in full
    return not any(made.startswith(f"{character}-") for made in full)


def far_spots(stage, standing, cast, full):
    """{name: [spots]} of every far-only character on the stage: a person where it stands, the crowd's copies (its
    far body) where its instancer puts them."""
    import numpy as np
    from pxr import Usd, UsdGeom
    looks = {person["name"]: person.get("look") for person in cast.get("people", [])}
    crowd = (cast.get("crowd") or {}).get("name")
    found = {}
    for name, prim in standing.items():
        world = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        if name == crowd and prim.IsA(UsdGeom.PointInstancer):
            points = np.asarray(UsdGeom.PointInstancer(prim).GetPositionsAttr().Get() or [], float).reshape(-1, 3)
            matrix = np.asarray(world)
            found[name] = (points @ matrix[:3, :3] + matrix[3, :3]).tolist()
            continue
        about = prim.GetCustomDataByKey("score") or {}
        if far_only(about.get("character", name), looks.get(name), list(about.get("worn") or []), full):
            found[name] = [list(world.ExtractTranslation())]
    return found


def full_looks():
    """The looks made in full, by the design's rule (score/stages/people_bodies/full.py) on its people rows."""
    if str(REPO) not in sys.path:
        sys.path.append(str(REPO))
    from score.stages.people_bodies import full
    return full.full_looks(json.loads((DATA / DESIGNED_PEOPLE).read_text()))


def far_faults(stage, place, cast, standing):
    """Each far-only character filling over FAR_SHARE of a view's frame height: who, the view and the share."""
    full = full_looks()
    views = (assembled_scene(stage, place) or {}).get("views", [])
    faults = []
    for name, spots in far_spots(stage, standing, cast, full).items():
        for view in views:
            shares = frame_shares(view, spots)
            if len(shares) and shares.max() > FAR_SHARE:
                faults.append(f"{name}: a far-only look fills {shares.max():.1%} of the frame height in view "
                              f"{view.get('name', '?')} ({int((shares > FAR_SHARE).sum())} of {len(spots)} over "
                              f"{FAR_SHARE:.0%})")
    return faults


# --- effects and motion ---------------------------------------------------------------------------------------------

def effects_standing(stage, place):
    """The names under /<place>/Effects in every variant of every variant set it has, and of every prim the effects
    layer laid on an object of the place (its child with `score:effect:kind`: the launch's flame on its rocket)."""
    from pxr import Usd
    root = stage.GetPrimAtPath(f"/{place}")
    laid = {prim.GetName() for prim in Usd.PrimRange(root) if prim.HasAttribute(EFFECT_KIND)} if root else set()
    scope = stage.GetPrimAtPath(f"/{place}/Effects")
    if not scope:
        return laid
    names = laid | {child.GetName() for child in scope.GetChildren()}
    with Usd.EditContext(stage, stage.GetSessionLayer()):  # the stage is shared by every check: its files stay as read
        for set_name in scope.GetVariantSets().GetNames():
            variant_set = scope.GetVariantSet(set_name)
            for name in variant_set.GetVariantNames():
                variant_set.SetVariantSelection(name)
                names |= {child.GetName() for child in scope.GetChildren()}
            variant_set.ClearVariantSelection()
    return names


def unmet(needs, names):
    """The needs no name has in it."""
    return [need for need in needs if not any(need in name for name in names)]


def effect_holders(stage, place):
    """The names of every prim of the place holding an emitter the effects layer laid (score:effect:kind)."""
    from pxr import Usd
    root = stage.GetPrimAtPath(f"/{place}")
    return {prim.GetParent().GetName() for prim in (Usd.PrimRange(root) if root else [])
            if prim.HasAttribute(EFFECT_KIND)}


NO_DESIGN = "{place} has no design ({folder}/{place}.json): what it must show is not known"


def judge_effects(stage, place, inventory, outputs):
    """Every row of the place's design that emits has an effect standing on the stage: an emitter the effects layer
    laid on one of the row's objects (its name or its holder's holding the row's id)."""
    found = design(place)
    if found is None:
        return UNKNOWN, [], NO_DESIGN.format(place=place, folder=DESIGN)
    needs = rows_doing(found, "emits")
    standing = effects_standing(stage, place)
    faults = [f"{need}: the design's row emits, and no effect stands on the stage on its object"
              for need in unmet(needs, standing | effect_holders(stage, place))]
    return outcome(faults, f"{len(standing)} effects stand; rows that emit met: {', '.join(needs) or 'none'}")


def moving(prim):
    """Whether any attribute of the prim has more than one time sample."""
    return any(attribute.GetNumTimeSamples() > 1 for attribute in prim.GetAttributes())


def judge_motion(stage, place, inventory, outputs):
    """Every moving thing of the place's motion output (the accepted motion row's moves.json, made from its design)
    moving on the stage, and every row of its design that moves one of them (its name or its prim's holding the row's
    id) or covered: a thing the output writes down as rightly still, with why (`still`). A design that moves with no
    motion output read is unknown."""
    found = design(place)
    if found is None:
        return UNKNOWN, [], NO_DESIGN.format(place=place, folder=DESIGN)
    needs = rows_doing(found, "moves")
    folder = outputs.get("motion")
    if needs and not folder:
        return UNKNOWN, [], f"{place}'s design moves {', '.join(needs)} and no accepted motion output is read"
    moves = json.loads((pathlib.Path(folder) / "moves.json").read_text()) if folder else {}
    motions = moves.get("moves", [])
    made = {motion["name"] for motion in motions
            if stage.GetPrimAtPath(motion["prim"]) and moving(stage.GetPrimAtPath(motion["prim"]))}
    covered = {name.rsplit("/", 1)[-1] for name, why in moves.get("still", {}).items() if str(why).strip()}
    still = [f"{motion['name']}: {motion['prim']} does not move on the stage" for motion in motions
             if motion["name"] not in made]
    moved = {motion["prim"].rsplit("/", 1)[-1] for motion in motions if motion["name"] in made}
    faults = still + [f"{need}: the design's row moves, and no motion of the output moves it or keeps it still"
                      for need in unmet(needs, made | moved | covered)]
    return outcome(faults, f"{len(made)} motions move, {len(covered)} written down as still; rows that move met: "
                           f"{', '.join(needs) or 'none'}")


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
    """Where the place's design shows crops, the share of soil tiles with a plant of the crops layer over them at least
    PLANTED_SHARE."""
    from pxr import Usd, UsdGeom
    found = design(place)
    if found is None:
        return UNKNOWN, [], NO_DESIGN.format(place=place, folder=DESIGN)
    if "crops" not in stages_module("design_layers").kinds_of(found, row_rules()):
        return PASS, [], "no crops here"
    least = PLANTED_SHARE
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


def shown_laid(stage, place, shown):
    """The backdrop rows (`shown`: {row: {place, row}}, prepare's groups.shown_from) whose object stands on the stage
    in the place it is shown from: an object of that place's row under /<place>/Places/<that place>."""
    stood = {(str(prim.GetPath()).split("/")[3], prim.GetAttribute("score:row").Get()) for prim in stage.Traverse()
             if prim.HasAttribute("score:row") and str(prim.GetPath()).startswith(f"/{place}/Places/")}
    return {row for row, source in shown.items() if (source["place"], source["row"]) in stood}


# The assembly's record beside a stage (origin.json): a ship place's "made pieces" ({row: model}) are laid straight from
# their painting place's bake (score/stages/assembly/ship_made.py) on a kit base with no seed paint to repaint.
ASSEMBLY_ORIGIN = "origin.json"


def made_pieces(stage):
    """{row: model} the assembly laid straight from a bake (its origin's made pieces); none without the record."""
    beside = pathlib.Path(stage.GetRootLayer().realPath).parent / ASSEMBLY_ORIGIN
    return json.loads(beside.read_text()).get("made pieces", {}) if beside.exists() else {}


# A ship place's made pieces' painting places' likeness outputs, read beside it (likeness@<place>).
LIKENESS_BESIDE = "likeness@"


def held_beside(stage, outputs):
    """The rows of a ship place's made pieces (its origin's, laid from another place's bake) that place's likeness
    output, read beside, holds to their close-up."""
    made = made_pieces(stage)
    held = set()
    for node, path in outputs.items():
        if node.startswith(LIKENESS_BESIDE) and path is not None:
            held |= set(json.loads((pathlib.Path(path) / "likeness.json").read_text())["objects"])
    return held & set(made)


def judge_likeness(stage, place, inventory, outputs):
    """Every generated row's object held to its close-up by the place's accepted likeness output."""
    generated = sorted(generated_rows(inventory, place) & laid_rows(stage, place))
    if not generated:
        return PASS, [], "no generated model on the stage"
    if outputs.get("likeness") is None:
        return UNKNOWN, [], (f"{len(generated)} generated rows and no accepted likeness@{place} (the props rows run "
                             f"only with data/props/{place}.json): none is held to its close-up")
    held = set(json.loads((pathlib.Path(outputs["likeness"]) / "likeness.json").read_text())["objects"])
    held |= held_beside(stage, outputs)
    faults = [f"{row}: generated, not held to its close-up by likeness@{place}" for row in generated if row not in held]
    return outcome(faults, f"{len(generated)} generated rows held to their close-ups")


# The mark the assembly writes on a waiting record entry it lays straight from the surface line's bake
# (score/stages/assembly/made_waiting.py, score:from): no seed paint was ever laid, so nothing is left to repaint.
LAID_FROM_BAKE = "; laid by the assembly with the surface line's baked "






def repainted(prim, from_bake=frozenset()):
    """Whether an object carries the bake's paint: repainted over its seed's (score:repaint_of), laid from the bake
    (a waiting entry's score:from), a ship place's made piece (`from_bake`, made_pieces), or a model the motion
    models layer lays from its take's bake (score:motion_model: the garage's rover, the hangar's ship and its thrusters)."""
    said = prim.GetAttribute("score:from").Get() if prim.HasAttribute("score:from") else ""
    return (prim.HasAttribute("score:repaint_of") or LAID_FROM_BAKE in (said or "")
            or prim.HasAttribute("score:motion_model") or prim.GetAttribute("score:model").Get() in from_bake)


def judge_painted(stage, place, inventory, outputs):
    """Every generated model on the stage repainted by the surface stage's bake, and the place's paint checked."""
    models = model_prims(stage, place, generated_rows(inventory, place))  # the old kits' code models went with them
    if not models:
        return PASS, [], "no generated model on the stage"
    from_bake = set(made_pieces(stage).values())
    unpainted = sorted({prim.GetAttribute("score:model").Get() for prim in models
                        if not repainted(prim, from_bake)})
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
    """The sound layer held by the root, and every sound of the place's bed (score/stages/sound/beds.py, from its
    design) standing."""
    if str(REPO) not in sys.path:
        sys.path.append(str(REPO))
    from score.stages.sound import beds
    bed = beds.of_place(place, beds.paths(place, DATA, DESIGN.parent))  # his design: plans, inventories
    if not bed["sounds"]:
        lacks = "; ".join(bed["facts"]["missing"]) or "no library bed's brief fits its design"
        return UNKNOWN, [], f"the bed of {place} is undecided (score/stages/sound/beds.py): {lacks}"
    faults = [] if SOUND_LAYER in root_layers(stage) else [f"no sound layer ({SOUND_LAYER}) on this stage"]
    names = bed["sounds"]
    faults += [f"{name}: a sound of the place's bed, not on the stage" for name in names
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

SOURCES = ("from", "source")  # the fields a record names where an entry's numbers come from
POSITIONS = ("at", "centre", "position", "placed_at")  # the fields that place an entry


def entries(found, where=""):
    """Every dict in a record, at any depth: [(where, entry)]."""
    if isinstance(found, dict):
        return [(where or "the record", found)] + [hit for key, value in found.items()
                                                   for hit in entries(value, f"{where}.{key}" if where else key)]
    if isinstance(found, list):
        return [hit for number, value in enumerate(found) for hit in entries(value, f"{where}[{number}]")]
    return []


def cited_fields(entry):
    """The entry's source fields (SOURCES) that cite the game."""
    return [field for field in SOURCES if isinstance(entry.get(field), str) and GAME.search(entry[field])]


def game_sources(found):
    """Each source field in a record (at any depth) that cites the game: [(where, field, text)]."""
    return [(where, field, entry[field]) for where, entry in entries(found) for field in cited_fields(entry)]


def game_positions(found):
    """Each position of an entry whose source cites the game: [(where, field)]."""
    return [(where, field) for where, entry in entries(found) if cited_fields(entry)
            for field in POSITIONS if field in entry]


def game_records(stage, place, outputs):
    """{name: record} of every record the place is made from that the game check reads (None where there is none)."""
    beside = pathlib.Path(stage.GetRootLayer().realPath).parent / ASSEMBLED_SCENE
    made = pathlib.Path(outputs["scene-record"]) / "record" / f"{place}.json" if outputs.get("scene-record") else None
    records = {str(beside): json.loads(beside.read_text()) if beside.exists() else None,
               f"data/scene/{place}.json": record("scene", place),
               f"scene-record output {made}": json.loads(made.read_text()) if made and made.exists() else None}
    records[f"its cast ({DESIGNED_PEOPLE})"] = cast_of(place)
    return records


def judge_game(stage, place, inventory, outputs):
    """No record the place is made from cites the game as its source: every scene record of it (game_records), the
    rest from data. A fault counts the citing fields and the positions they place."""
    faults = []
    for name, found in game_records(stage, place, outputs).items():
        sources = game_sources(found) if found else []
        if sources:
            fields = ", ".join(sorted({field for _, field, _ in sources}))
            faults.append(f"{name}: {len(sources)} entries take their numbers from the game ({fields}), "
                          f"{len(game_positions(found))} positions placed from it")
    return outcome(faults, "no record cites the game")


def judge_waiting(stage, place, inventory, outputs):
    """Fail on every entry of the scene record the assembly laid nothing for because it waits on its model (the
    root prim's score:waiting): a gap, named."""
    root = stage.GetPrimAtPath(f"/{place}")
    waiting = list(root.GetAttribute(WAITING).Get() or []) if root and root.HasAttribute(WAITING) else []
    return outcome([f"a gap: {entry}" for entry in waiting], "no entry of the scene record waits on its model")


JUDGES = {"people": judge_people, "effects": judge_effects, "motion": judge_motion, "crops": judge_crops,
          "likeness": judge_likeness, "painted": judge_painted, "light": judge_light,
          "sound": judge_sound, "neighbours": judge_neighbours, "game": judge_game,
          "waiting": judge_waiting}
