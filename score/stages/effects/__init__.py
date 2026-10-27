"""The effects stage (experimental, PRD #6, until the owner reviews it): a scene's effects made from its design
(the owner, 2026-10-21: "the modules are not agnostic"), never from a record written for it: every object of a scene
inventory row whose kind emits (score/stages/row_kinds.py, data/checks/row-kinds.json) carries the measured effects
its kind emits (data/checks/effects.json), made into the scene's OpenUSD effects layer, which the assembly stage puts
into its stage.

    make     the record made from the design over the scene's stage (from_design.py: record.json), then tools/usd/
             effects.py's write_layer on it: layers/effects.usda and each emitter's clip under assets/effects/.
             How an effect is made is one rule, by what it is made of (effects.json `methods`, each kind's
             `matter`): grains Newton has a solver for (the drill's cuttings, a granular pile by implicit MPM) are
             simulated in the physics trial's own Python (inside/newton_pile.py) under the gravity of the scene's
             body and drawn as one surface built from every grain; a cloud or a flame, which Newton has no solver
             for, is baked particles. A parameter a row needs that neither the design nor a rule gives (a kind's
             `asked`: the drill's bore and how much it brings up) is read off the locked concept by one recorded
             model call for the scene (asked.py)
    gates    attached  every emitter and light on a prim of the base (`on`) is that prim's child and keeps its place on
                       it through the prim's motion, and every emitter that follows a motion lets each particle out
                       where the moving prim stands at its birth (read off the composed stage, the seed's own layers
                       under the effects layer)
             footage   every check of the record's `footage` block: a measure of the baked particles at a moment (how
                       far the cloud reaches out, how high it stands, how far it reaches any way and how far off its
                       way it spreads, how long the flame is, how high it stands over the ground beneath (a
                       drift), the slope of a pile's flank, how fine and how thick the particles are, how few lie
                       loose at its edge as lone blobs, what share of them shows) lies within the range measured on
                       real footage: the launch's after lift-off in the rocket's heights from its rest, any other
                       place's at its own `at` second in metres from its `anchor` emitter
             light     the flame's light reaches the pad: from half a second after the engines light to two seconds
                       after lift-off it lights the pad round the rocket at least LIGHT_OVER times as much as the
                       place's own lamps do; a record with no lights passes only when it says why (`no_light`)
             outside   no particle of an emitter under the open sky shows inside the place's interiors (the record's
                       `interiors`, each centred on the prim it names: the camp's domes), and the record says which
                       interiors there are when anything stands outside
             designed  every emitter rides an object of a row of the scene's inventory, and every row whose kind emits
                       has an object on the stage to carry it

A record where nothing rides or follows a moving prim passes `attached` only when it says why (`rides_nothing`).
The stage is the place's seed with its accepted scene record (and motion models) taken as the assembly takes them
(score/stages/layer_base.py): the design's objects stand there by their names.

Only scenes whose design has a row that emits have the row (applies). A scene's effects are modelled on real footage
first (the owner's rule): many fine particles tied to the world, never thinned to draw cheaper.
"""
import functools
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

from score import checks, contracts, store
from score.stages import layer_base, row_kinds
from score.stages.physics import design as physics_design
from score.stages.effects import asked, from_design

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import effects as effect_layer  # noqa: E402

# How far an emitter on a moving prim may drift from its place on it, metres.
DRIFT_MOST = 0.01
# How often the composed stage is read along a motion and an event, seconds.
READ_EVERY = 0.5
# The flame's light on the pad against the place's own lamps: in the night launch footage (the old launch record's
# footage sources) the apron round the flame is lit far brighter than the floodlit tower beside it.
LIGHT_OVER = 2.0
# The pad round the rocket the light is judged on: rings this far out from its middle, eight spots each, metres.
PAD_RINGS = (10.0, 20.0, 30.0)
LIGHT_FROM_IGNITION = 0.5
LIGHT_AFTER_LIFT = 2.0
# Particles of a cloud at least this thick (one behind another) make it read as a cloud, not dots.
LAYERS = 3
# A particle thinner than this (its opacity) does not show: one just born or dying between two baked samples.
SEEN = 0.02
# A fog's particles are each far thinner than SEEN and show only many deep: one under this share of its own thickest
# is the nearly-nothing of birth or death (SEEN is about this share of the launch's clouds' thickest, 0.15).
SEEN_SHARE = 0.14
# How far an interior's middle may lie off the prim it names there, metres (a dome's roof cap), and how long the
# outside gate reads particles for and how often, seconds (a devil wanders a minute).
HELD_SLACK = 0.3
OUTSIDE_SPAN = 60.0
OUTSIDE_EVERY = 2.0


# A pile's flank is read on this many rings across its outer half, each by this share of its grains' heights.
FLANK_RINGS = 8
FLANK_TOP = 98

RECORD = "record.json"
# A pile Newton makes (an effect kind's `newton` block): its script, run in the physics trial's own Python, which
# newton_env.sh builds once in this folder under PROPS_HOME.
NEWTON_PILE = pathlib.Path(__file__).resolve().parent / "inside/newton_pile.py"
NEWTON_ENV = REPO / "score/stages/physics/inside/newton_env.sh"
NEWTON_FOLDER = "envs/newton_env"


def files(place):
    """What the stage reads: the scene's design inventory and locked concept (what a row's effect asks is read off
    it), the row-kind rules and the library of measured effects,
    its seed stage with its kit (the record is made and the gates judge the layer over it), its design's surface
    data (which bakes of other places it lays, as the settle) and the setting whose body's gravity a Newton pile falls
    under."""
    return {**row_kinds.DESIGNED, "effect kinds": "{data}/checks/effects.json", "seed": "{seeds}/usd-r3/{place}",
            "concept": "{home}/design/concepts/{place}.png",
            "surfaces": "{home}/design/surfaces/{place}.json", "physics": "{data}/physics/setting.json",
            "bodies": "{data}/physics/bodies.json", "within": "{data}/places/within.json", **layer_base.files(place)}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def motions_of(inputs):
    return read_json(inputs["motion"]) if "motion" in inputs else None


def scene_of(inputs):
    """The place's scene record where the stage reads one (data/scene: its views, structure and objects as the effects
    name them), else None: a record made from the design places every emitter on an object."""
    return read_json(inputs["scene"]) if "scene" in inputs else None


def record_of(inputs):
    """The scene's effects record, made from its design (record.json beside the layer), its seconds from the climb's
    moments as seconds of the stage (effects.timed)."""
    return effect_layer.timed(read_json(inputs["record"]), motions_of(inputs))


def make(inputs, out, seed, params):
    """The scene's effects record made from its design over its stage, its effects layer and baked particles."""
    place = pathlib.Path(inputs["seed"]).name
    effects = read_json(inputs["effect kinds"])
    with layer_base.built(inputs) as source:
        stage = layer_base.opened(source)
        design = read_json(inputs["design"])
        record = from_design.record(place, design, row_kinds.table(inputs["row kinds"]), effects, stage)
        record = dict(record, effects=with_asked(record["effects"], place, inputs, design, effects))
        with tempfile.TemporaryDirectory() as baking:
            record = dict(record, effects=[made(entry, inputs, place, pathlib.Path(baking))
                                           for entry in record["effects"]])
            kept = [{key: value for key, value in entry.items() if key != "baked"} for entry in record["effects"]]
            (out / RECORD).write_text(json.dumps(dict(record, effects=kept), indent=1))
            held = effect_layer.write_layer(place, record, out, base=stage)
    (out / "held.json").write_text(json.dumps({"place": place, "particles": held}, indent=1))


def with_asked(entries, place, inputs, design, effects):
    """The entries with what their kind asks (its `asked`), read off the scene's locked concept for each row by the
    scene's one model call (asked.py), its numbers and reasons as each entry's `asked`."""
    rows = {row["id"]: row for row in design["rows"]}
    pairs = list({(entry["row"], entry["kind"]): (rows[entry["row"]], entry["kind"]) for entry in entries}.values())
    found = asked.values(place, inputs.get("concept"), pairs, effects)
    return [dict(entry, asked=found[(entry["row"], entry["kind"])]) if (entry["row"], entry["kind"]) in found
            else entry for entry in entries]


def made(entry, inputs, place, baking):
    """The entry made by its method (from_design: its matter's, effects.json `methods`): baked particles as the
    layer bakes them, or Newton's pile; a method with no maker here stops the row."""
    if entry["made_by"] == "particles":
        return entry
    if entry["made_by"] == "newton-mpm":
        return poured(entry, inputs, place, baking)
    raise ValueError(f"{entry['name']}: no maker for {entry['made_by']} yet (effects.json `methods`)")


def body_gravity(inputs, place):
    """The gravity of the body the scene stands on (its site's, else its holder's: the physics trial's own rule),
    metres a second squared."""
    within = {name: entry["within"] for name, entry in read_json(inputs["within"]).get("within", {}).items()}
    return physics_design.ground(place, within, read_json(inputs["physics"]))[1]


def newton_python():
    """The physics trial's own Python (Newton 1.7.0), built once under PROPS_HOME by newton_env.sh."""
    folder = store.PROPS_HOME / NEWTON_FOLDER
    subprocess.run(["bash", str(NEWTON_ENV), str(folder)], check=True)
    return folder / "bin/python"


def poured(entry, inputs, place, baking):
    """A granular pile Newton makes (its `newton` block and what its row was asked: the bore and how much it brings
    up), poured over its `once` span in the physics trial's Python under the scene's body's gravity at the emitter's
    samples a second: the entry with its gravity, how many grains it holds (its `count`) and its `baked` surface
    file (in `baking`, gone once the layer is written)."""
    gravity = body_gravity(inputs, place)
    first, last = (float(value) for value in entry["once"])
    pile = dict(entry["newton"], **entry["asked"]["values"], pour=last - first, seconds=effect_layer.loop_of(entry),
                samples=effect_layer.samples_of(entry), seed=int(entry["seed"]), gravity=gravity)
    wanted, baked = baking / f"{entry['name']}.json", baking / f"{entry['name']}.npz"
    wanted.write_text(json.dumps(pile))
    newton_pile(wanted, baked)
    return dict(entry, gravity=[0.0, -gravity, 0.0], count=int(np.load(baked)["grains"]), baked=baked)


def newton_pile(asked, baked):
    """inside/newton_pile.py run in the physics trial's Python on the pile `asked` (a json file), into `baked`."""
    subprocess.run([str(newton_python()), str(NEWTON_PILE), str(asked), str(baked)], check=True)


def judged_on_design(judge):
    """A gate judged on the record made from the design (the output's record.json) over the scene's stage built for
    it (layer_base.built), the build removed when it is judged."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        with layer_base.built(inputs) as source:
            return judge(output, dict(inputs, built=source, record=pathlib.Path(output) / RECORD), evidence)
    return judged


# --- the composed stage -------------------------------------------------------------------------------------------

def composed(output, inputs):
    """The effects layer over the place's stage (the one built for the gate, else its seed: its edit, stage layers and
    base), with the place's motion record, where it reads one, written between them, opened as one stage. The seed's
    own motion layer is round three's (the launch's rocket at the game's 3 s and 24 m/s/s): the riders and followers are judged against the motion the record gives, as the
    assembly stacks it, not that one (effects-layer@launch, 2026-10-15: a plume 1735 m off a rocket the seed moved)."""
    from pxr import Sdf, Usd
    seed = pathlib.Path(inputs.get("built", inputs["seed"]))
    moving = Sdf.Layer.CreateAnonymous(".usda")
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(pathlib.Path(output) / effect_layer.LAYER), moving.identifier,
                          str(seed / f"{seed.name}.usda")]
    stage = Usd.Stage.Open(root)
    motions = motions_of(inputs)
    if motions:
        stood(stage, moving, scene_of(inputs), motions, seed.name)
        written(stage, moving, motions, effect_layer.motion_record.stage_rate(seed.name, seed))
    return stage


def stood(stage, layer, scene, motions, place):
    """Each prim a motion moves that is an object of the scene record stood at the record's spot in `layer`, as the
    assembly lays it (the seed's launch rocket stood 3.4 m off the record's, 2026-10-15)."""
    from pxr import Gf, Usd
    spots = {item["name"]: item["at"] for item in scene.get("objects", []) if "at" in item}
    stage.SetEditTarget(Usd.EditTarget(layer))
    for motion in motions["motions"]:
        name = motion["prim"].rsplit("/", 1)[-1]
        if name in spots and stage.GetPrimAtPath(motion["prim"]):
            effect_layer.motion_record.translate_attribute(
                stage, motion["prim"], effect_layer.motion_record.rest_translate(stage, motion["prim"])[1]
            ).Set(Gf.Vec3d(*map(float, spots[name])))


def written(stage, layer, motions, rate):
    """Every motion of the record written into `layer` of the stage, as the motion stage writes its layer."""
    from pxr import Usd
    motion_record = effect_layer.motion_record
    stage.SetEditTarget(Usd.EditTarget(layer))
    for motion in motions["motions"]:
        if "adds" in motion and not stage.GetPrimAtPath(motion["prim"]):  # the seed's motion layer may hold it
            motion_record.added(stage, motion)
        motion_record.WRITERS[motion_record.kind_of(motion)](stage, motion, rate, motion_record.WRITTEN_SECONDS)


def place_of(inputs):
    return pathlib.Path(inputs["seed"]).name


def where(stage, path, seconds):
    """A prim's place in the world at a second of the stage."""
    from pxr import UsdGeom
    matrix = UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(seconds * effect_layer.RATE)
    return np.asarray(matrix.ExtractTranslation(), dtype=float)


def live(stage, path, seconds):
    """The live particles of an emitter's points at a second of the stage: their world spots and widths."""
    from pxr import UsdGeom
    prim = stage.GetPrimAtPath(path)
    grains = UsdGeom.Points(prim)
    code = seconds * effect_layer.RATE
    spots = np.asarray(grains.GetPointsAttr().Get(code), dtype=float)
    widths = np.asarray(grains.GetWidthsAttr().Get(code), dtype=float)
    matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(code))
    world = spots @ matrix[:3, :3] + matrix[3, :3]
    scale = float(np.linalg.norm(matrix[0, :3]))
    alive = widths > 0
    return world[alive], widths[alive] * scale


def seen(stage, path, seconds, thickest):
    """The particles of an emitter's points that show at a second of the stage (thicker than SEEN, or than
    SEEN_SHARE of `thickest`, its particles' own thickest, for one as thin as a fog; one just born or dying between
    two samples is nearly nothing): their world spots and widths."""
    from pxr import UsdGeom
    if stage.GetPrimAtPath(path).IsA(UsdGeom.Mesh):
        return surface_spots(stage, path, seconds)
    grains = UsdGeom.Points(stage.GetPrimAtPath(path))
    code = seconds * effect_layer.RATE
    widths = np.asarray(grains.GetWidthsAttr().Get(code), dtype=float)
    thickness = np.asarray(UsdGeom.PrimvarsAPI(grains).GetPrimvar("displayOpacity").Get(code), dtype=float)
    spots, sizes = live(stage, path, seconds)
    shows = thickness[widths > 0] > min(SEEN, SEEN_SHARE * thickest)
    return spots[shows], sizes[shows]


def surface_spots(stage, path, seconds):
    """A surface's vertices at a second of the stage (a Newton pile, drawn from every grain): their world spots, and
    widths of 0 (the surface is their edge)."""
    from pxr import UsdGeom
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
    code = seconds * effect_layer.RATE
    spots = np.asarray(mesh.GetPointsAttr().Get(code) or [], dtype=float).reshape(-1, 3)
    matrix = np.asarray(UsdGeom.Xformable(mesh.GetPrim()).ComputeLocalToWorldTransform(code))
    return spots @ matrix[:3, :3] + matrix[3, :3], np.zeros(len(spots))


def points_path(place, entry):
    """Where an emitter's points (or its surface, one drawn as a surface) stand in the stage (tools/usd/effects.py's
    layout)."""
    placement = entry["placement"]
    holder = f"/{place}/{placement['on']}" if "on" in placement else f"/{place}/Effects"
    drawn = "surface" if entry.get("drawn") == "surface" else "points"
    return f"{holder}/{entry['name']}/{entry['name']}_{drawn}"


def motion_span(motions, name):
    """(motion, its first and last second of the stage)."""
    motion = effect_layer.motion_named(motions, name)
    return motion, float(motion["start"]), float(motion["start"]) + float(motion["length"])


def moments(first, last):
    return np.arange(first, last + 1e-9, READ_EVERY)


# --- attached -----------------------------------------------------------------------------------------------------

def riding_drift(stage, place, holder, path, motions):
    """How far a prim riding `holder` strays from its place on it over every motion of the holder (metres), and how
    far the holder moves meanwhile; (0, 0) when nothing moves it."""
    own = [motion for motion in (motions or {}).get("motions", []) if motion["prim"] == f"/{place}/{holder}"]
    drift, moved = 0.0, 0.0
    for motion in own:
        first, last = float(motion["start"]), float(motion["start"]) + float(motion["length"])
        start_offset = where(stage, path, first) - where(stage, f"/{place}/{holder}", first)
        for seconds in moments(first, last):
            offset = where(stage, path, seconds) - where(stage, f"/{place}/{holder}", seconds)
            drift = max(drift, float(np.linalg.norm(offset - start_offset)))
        moved = max(moved, float(np.linalg.norm(where(stage, f"/{place}/{holder}", last)
                                                - where(stage, f"/{place}/{holder}", first))))
    return drift, moved


def newborn_miss(stage, place, entry, motions):
    """How far the particles a following emitter lets out stand from where its motion's prim is at their birth, past
    what the emitter's size and their first moment's flight allow (metres; 0 when every one is within)."""
    motion, _, _ = motion_span(motions, entry["placement"]["follows"])
    path = points_path(place, entry)
    rate = effect_layer.samples_of(entry)
    first, last = (float(value) for value in entry["once"])
    reach = (effect_layer.emitter_size(entry["emitter"])[0] + max(entry.get("speed", (0.0, 0.0))) / rate
             + float(entry["size"]) * max(entry.get("scale", (1.0, 1.0))))
    offset = np.asarray(entry["placement"].get("offset", (0.0, 0.0, 0.0)), dtype=float)
    worst = 0.0
    for seconds in moments(first + 1.0 / rate, last):
        from pxr import UsdGeom
        grains = UsdGeom.Points(stage.GetPrimAtPath(path))
        now = np.asarray(grains.GetWidthsAttr().Get(seconds * effect_layer.RATE))
        before = np.asarray(grains.GetWidthsAttr().Get((seconds - 1.0 / rate) * effect_layer.RATE))
        born = (now > 0) & (before == 0)
        if not born.any():
            continue
        spots, _ = live(stage, path, seconds)
        spots = spots[born[now > 0]]
        prim = where(stage, motion["prim"], seconds) + offset
        # Born within the last sample: the prim stood up to one sample's travel back.
        travel = float(np.linalg.norm(prim - where(stage, motion["prim"], seconds - 1.0 / rate) - offset))
        worst = max(worst, float(np.linalg.norm(spots - prim, axis=1).max()) - reach - travel)
    return max(worst, 0.0)


def judge_attached(output, inputs, evidence):
    """Pass when everything on a moving prim moves with it and every following emitter lets out at its prim."""
    stage, place, record = composed(output, inputs), place_of(inputs), record_of(inputs)
    motions = motions_of(inputs)
    faults, measures = [], {"drift": 0.0, "miss": 0.0, "carried": 0.0}
    riders = [(entry["name"], entry["placement"]["on"]) for entry in record["effects"] if "on" in entry["placement"]]
    riders += [(light["name"], light["on"]) for light in record.get("lights", [])]
    for name, holder in riders:
        path = f"/{place}/{holder}/{name}"
        if not stage.GetPrimAtPath(path):
            faults.append(f"{name}: not on {holder} ({path} missing)")
            continue
        drift, moved = riding_drift(stage, place, holder, path, motions)
        measures["drift"] = max(measures["drift"], round(drift, 4))
        measures["carried"] = max(measures["carried"], round(moved, 1))
        if drift > DRIFT_MOST:
            faults.append(f"{name}: strays {drift:.3f} m from its place on {holder} as it moves {moved:.0f} m")
    for entry in [entry for entry in record["effects"] if "follows" in entry["placement"]]:
        miss = newborn_miss(stage, place, entry, motions)
        measures["miss"] = max(measures["miss"], round(miss, 3))
        if miss > 0:
            faults.append(f"{entry['name']}: lets particles out {miss:.2f} m past where its prim stands")
    followers = sum("follows" in entry["placement"] for entry in record["effects"])
    if not riders and not followers and record.get("rides_nothing"):
        return checks.Verdict("attached", checks.PASS, f"nothing in the record rides a prim: {record['rides_nothing']}")
    if not riders and not followers:
        return checks.Verdict("attached", checks.UNKNOWN, "nothing in the record rides or follows a moving prim and "
                                                          "it does not say why (`rides_nothing`)")
    reason = (f"{len(faults)} faults over {len(riders)} riders and {followers} following emitters" if faults else
              f"{len(riders)} riders keep their place over {measures['carried']:.0f} m of their prim's travel and "
              f"{followers} following emitters let out where their prim stands")
    return checks.Verdict("attached", checks.FAIL if faults else checks.PASS, reason, measures,
                          {"drift": "lower", "miss": "lower"}, tuple(faults))


# --- footage ------------------------------------------------------------------------------------------------------

def rocket_of(record, scene, motions):
    """The footage block's rocket: its height (metres), its rest spot and its motion."""
    named = record["footage"]["rocket"]
    found = next(item for item in scene["objects"] if item["name"] == named["object"])
    motion = effect_layer.motion_named(motions, named["motion"])
    return float(found["height"]), np.asarray(found["at"], dtype=float), motion


def lift_second(motion):
    return float(motion["start"]) + float(motion["climb"]["lift"])


def gathered(stage, place, record, names, seconds):
    """Every particle of the named emitters that shows at a second: world spots and widths."""
    entries = {entry["name"]: entry for entry in record["effects"]}
    spots, widths = [np.zeros((0, 3))], [np.zeros(0)]
    for name in names:
        for laid in laid_names(entries[name]):  # a drift laid on cells: every cell's
            found = seen(stage, points_path(place, dict(entries[name], name=laid)), seconds,
                         effect_layer.look_opacity(entries[name]))
            spots.append(found[0])
            widths.append(found[1])
    return np.concatenate(spots), np.concatenate(widths)


def reach(spots, widths, rest):
    """How far the particles reach out from the rocket's middle along the ground (95th share, their edges), m."""
    out = np.hypot(spots[:, 0] - rest[0], spots[:, 2] - rest[2]) + widths / 2
    return float(np.percentile(out, 95))


def height(spots, widths, rest):
    """How high the particles stand over the rocket's foot (95th share, their tops), metres."""
    return float(np.percentile(spots[:, 1] + widths / 2 - rest[1], 95))


def flank(spots, widths):
    """The slope of a pile's outer flank round its anchor (its frame's y up), degrees: a straight line through its
    top (each of FLANK_RINGS rings' FLANK_TOP share of heights, the grains' tops) between half and nine tenths of its
    reach (95th share across), as a slip face's slope is read off a terrain model."""
    across, up = np.hypot(spots[:, 0], spots[:, 2]), spots[:, 1] + widths / 2
    far = float(np.percentile(across, 95))
    ring = 0.4 * far / FLANK_RINGS
    inner = 0.5 * far + np.arange(FLANK_RINGS) * ring
    tops = [np.percentile(up[(across >= edge) & (across < edge + ring)], FLANK_TOP) for edge in inner]
    return float(np.degrees(np.arctan(-np.polyfit(inner + ring / 2, tops, 1)[0])))


def flame_length(spots, nozzle):
    """How far the flame reaches under the rocket's foot (95th share), metres."""
    return float(np.percentile(nozzle[1] - spots[:, 1], 95))


def layering(spots, widths, rest):
    """The share of the cloud's side outline (seen across x, cells half a median particle wide) that at least LAYERS
    particles cover one behind another."""
    cell = max(float(np.median(widths)) / 2, 0.05)
    across, up = (spots[:, 0] - rest[0]) / cell, (spots[:, 1] - rest[1]) / cell
    low = np.floor([across.min() - widths.max() / cell, up.min() - widths.max() / cell]).astype(int)
    shape = (np.ceil([across.max() + widths.max() / cell, up.max() + widths.max() / cell]).astype(int) - low) + 1
    cover = np.zeros(shape, dtype=np.int32)
    for column, row, width in zip(across - low[0], up - low[1], widths / 2 / cell):
        first = (max(int(column - width), 0), max(int(row - width), 0))
        lasts = (min(int(column + width) + 1, shape[0]), min(int(row + width) + 1, shape[1]))
        grid_x, grid_y = np.mgrid[first[0]:lasts[0], first[1]:lasts[1]]
        cover[first[0]:lasts[0], first[1]:lasts[1]] += ((grid_x + 0.5 - column) ** 2 + (grid_y + 0.5 - row) ** 2
                                                        <= width * width)
    outline = cover > 0
    return float((cover[outline] >= LAYERS).mean()) if outline.any() else 0.0


def loose(spots, widths):
    """The share of the particles that touch no other (the nearest one's middle farther than their own width): the
    lone blobs a cloud in the footage never shows at its edge."""
    from scipy.spatial import cKDTree
    if len(spots) < 2:
        return 1.0
    nearest, _ = cKDTree(spots).query(spots, k=2)
    return float((nearest[:, 1] > widths).mean())


def length(spots, widths, anchor):
    """How far the particles reach from the anchor any way (95th share, their edges), metres."""
    return float(np.percentile(np.linalg.norm(spots - anchor, axis=1) + widths / 2, 95))


def spread(spots, anchor):
    """How far off their own mean way the particles lie seen from the anchor (95th share), degrees: a jet's half
    angle."""
    ways = spots - anchor
    ways = ways / np.maximum(np.linalg.norm(ways, axis=1, keepdims=True), 1e-9)
    mean = ways.mean(axis=0) / max(float(np.linalg.norm(ways.mean(axis=0))), 1e-9)
    return float(np.percentile(np.degrees(np.arccos(np.clip(ways @ mean, -1.0, 1.0))), 95))


def over_ground(spots, ground):
    """Each spot's height over the planned ground beneath it (tools/usd/ground.py's ball and heights; a flat place's
    ground is y = 0), metres."""
    if ground is None:
        return spots[:, 1]
    world = (spots + np.array([0.0, ground.drop, 0.0])) @ ground.frame + ground.origin
    out = world / np.linalg.norm(world, axis=1, keepdims=True)
    height, _ = ground.height(out)
    return np.linalg.norm(world, axis=1) - (ground.radius + height)


def gap(spots, widths, anchor):
    """How far from the anchor the particles first show (the nearest one's near edge), metres: the clear gap at a
    kettle's spout."""
    return float(max((np.linalg.norm(spots - anchor, axis=1) - widths / 2).min(), 0.0))


def alive_share(stage, place, record, names, seconds):
    """The share of the named emitters' particles that show at a second."""
    counts = {entry["name"]: int(entry["count"]) for entry in record["effects"]}
    shown = len(gathered(stage, place, record, names, seconds)[0])
    return shown / sum(counts[name] for name in names)


def framed(check, stage, place, record, rocket):
    """A check's second of the stage, its anchor (world spot) and its unit (metres): the launch's after lift-off,
    from the rocket's rest (or its `anchor` emitter), in its heights; any other place's at its own `at` second, from
    its `anchor` emitter's spot then, in metres."""
    if rocket is not None:
        tall, rest, motion = rocket
        seconds = lift_second(motion) + float(check["after_lift"])
        return seconds, anchor_spot(check, stage, place, record, seconds) if "anchor" in check else rest, tall
    seconds = float(check["at"])
    return seconds, anchor_spot(check, stage, place, record, seconds), 1.0


def anchor_holder(check, place, record):
    """The path of a check's `anchor` emitter (a drift laid on cells: its middle cell)."""
    entry = next(entry for entry in record["effects"] if entry["name"] == check["anchor"])
    laid = laid_names(entry)
    return points_path(place, dict(entry, name=laid[len(laid) // 2])).rsplit("/", 1)[0]


def anchor_spot(check, stage, place, record, seconds):
    """Where a check's `anchor` emitter stands at a second."""
    return where(stage, anchor_holder(check, place, record), seconds)


def upright(stage, path, seconds, spots):
    """Spots of the world in an emitter's own turn about its spot: its up their y (a devil standing on the curved
    ground of a 220 m world leans with it)."""
    from pxr import UsdGeom
    matrix = np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(
        seconds * effect_layer.RATE))
    turn = matrix[:3, :3] / np.linalg.norm(matrix[:3, :3], axis=1, keepdims=True)
    return (spots - matrix[3, :3]) @ turn.T


def measured(check, stage, place, record, rocket):
    """One footage check's measure at its moment, in the rocket's heights or metres (fineness, layering, loose and
    alive as shares, spread in degrees)."""
    seconds, rest, tall = framed(check, stage, place, record, rocket)
    if check["measure"] == "alive":
        return alive_share(stage, place, record, check["emitters"], seconds)
    spots, widths = gathered(stage, place, record, check["emitters"], seconds)
    if "within" in check:  # only what the footage's frame held: the particles this near the anchor, metres
        near = np.linalg.norm(spots - rest, axis=1) <= float(check["within"])
        spots, widths = spots[near], widths[near]
    if not len(spots):
        return None
    if check["measure"] in ("reach", "height", "flank") and rocket is None:  # across and up the anchor's own frame
        spots, rest = upright(stage, anchor_holder(check, place, record), seconds, spots), np.zeros(3)
    if check["measure"] == "reach":
        return reach(spots, widths, rest) / tall
    if check["measure"] == "flank":
        return flank(spots, widths)
    if check["measure"] == "height":
        return height(spots, widths, rest) / tall
    if check["measure"] == "length":
        return length(spots, widths, rest) / tall
    if check["measure"] == "spread" and "slot" in check:  # a slit's cone is measured across it, its length left out
        along = np.asarray(check["slot"], dtype=float) / np.linalg.norm(check["slot"])
        return spread(spots - np.outer((spots - rest) @ along, along), rest)
    if check["measure"] == "spread":
        return spread(spots, rest)
    if check["measure"] == "over_ground":  # how high the particles' tops stand over the ground beneath (95th share)
        return float(np.percentile(over_ground(spots, effect_layer.place_ground(place)) + widths / 2, 95))
    if check["measure"] == "gap":
        return gap(spots, widths, rest) / tall
    if check["measure"] == "flame_length":
        return flame_length(spots, where(stage, rocket[2]["prim"], seconds)) / tall
    if check["measure"] == "fineness":
        return float(np.median(widths)) / (2 * reach(spots, widths, rest))
    if check["measure"] == "layering":
        return layering(spots, widths, rest)
    if check["measure"] == "loose":
        return loose(spots, widths)
    raise ValueError(f"no footage measure {check['measure']}")


def judge_footage(output, inputs, evidence):
    """Pass when every footage check of the record measures within its range."""
    record = record_of(inputs)
    if "footage" not in record:
        return checks.Verdict("footage", checks.UNKNOWN, "the record names no footage to measure its effects on")
    stage, place = composed(output, inputs), place_of(inputs)
    rocket = rocket_of(record, scene_of(inputs), motions_of(inputs)) if "rocket" in record["footage"] else None
    faults, measures, found = [], {}, []
    for check in record["footage"]["checks"]:
        value = measured(check, stage, place, record, rocket)
        low, high = check["range"]  # None: the footage bounds it on one side only (a plume running off the frame)
        measures[check["name"]] = None if value is None else round(value, 4)
        line = f"{check['name']}: {'nothing alive' if value is None else f'{value:.3f}'} (footage {low} to {high})"
        found.append(line)
        if value is None or (low is not None and value < low) or (high is not None and value > high):
            faults.append(line)
    reason = (f"{len(faults)} of {len(found)} measures lie outside the footage's ranges" if faults
              else f"all {len(found)} measures lie within the footage's ranges")
    return checks.Verdict("footage", checks.FAIL if faults else checks.PASS, reason, measures, {},
                          tuple(faults or found))


# --- outside ------------------------------------------------------------------------------------------------------

def under_sky(record):
    """The record's emitters that stand under the open sky: neither riding a prim nor filling a room."""
    return [entry for entry in record["effects"] if "on" not in entry["placement"]
            and "room" not in entry["placement"]]


def laid_names(entry):
    """The names an entry's emitters get in the stage: a drift laid on cells one a cell (tools/usd/effects.py's
    cell_emitters), any other its own."""
    cells = entry["placement"].get("cells")
    if not cells:
        return [entry["name"]]
    side = 2 * int(cells["out"]) + 1
    return [f"{entry['name']}_{row}_{column}" for row in range(side) for column in range(side)]


def unheld(stage, place, room):
    """What is wrong with where an interior stands: the prim it names at its middle (`middle_of`, under the place:
    a dome's roof cap) missing, its middle more than HELD_SLACK off the interior's, or its top over the interior's.
    An interior of a neighbour's stage (the camp's domes seen from its grounds) names none: its `from` says where."""
    from pxr import Usd, UsdGeom
    if "middle_of" not in room:
        return []
    prim = stage.GetPrimAtPath(f"/{place}/{room['middle_of']}")
    if not prim:
        return [f"{room['name']}: no prim {room['middle_of']}"]
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(prim).ComputeAlignedRange()
    middle = (np.asarray(box.GetMin(), dtype=float) + np.asarray(box.GetMax(), dtype=float)) / 2
    off = float(np.hypot(middle[0] - float(room["middle"][0]), middle[2] - float(room["middle"][1])))
    missed = [f"{room['name']}: {room['middle_of']} stands {off:.2f} m off its middle"] if off > HELD_SLACK else []
    if float(box.GetMax()[1]) > float(room["top"]) + HELD_SLACK:
        missed.append(f"{room['name']}: {room['middle_of']} stands over its top")
    return missed


def judge_outside(output, inputs, evidence):
    """Pass when no particle of an emitter under the open sky shows inside the place's interiors (`interiors`:
    upright cylinders, each centred on the prim it names) over the first OUTSIDE_SPAN seconds."""
    record = record_of(inputs)
    outdoor = under_sky(record)
    if not outdoor:
        return checks.Verdict("outside", checks.PASS, "no emitter stands under the open sky")
    if "interiors" not in record:
        return checks.Verdict("outside", checks.UNKNOWN, "the record does not say which interiors the place has "
                                                         "(`interiors`, empty for none)")
    stage, place = composed(output, inputs), place_of(inputs)
    faults = [fault for room in record["interiors"] for fault in unheld(stage, place, room)]
    drawn = [(dict(entry, name=name), entry) for entry in outdoor for name in laid_names(entry)
             if stage.GetPrimAtPath(points_path(place, dict(entry, name=name)))]  # none of a variant not chosen
    worst = 0
    for seconds in np.arange(0.0, OUTSIDE_SPAN + 1e-9, OUTSIDE_EVERY):
        for entry, laid in drawn:
            spots, _ = seen(stage, points_path(place, entry), seconds, effect_layer.look_opacity(laid))
            count = int(effect_layer.inside(spots, record["interiors"]).sum())
            worst = max(worst, count)
            if count:
                faults.append(f"{entry['name']}: {count} particles inside at {seconds:.1f} s")
    reason = (f"{len(faults)} faults" if faults else
              f"no particle of {len(drawn)} emitters under the sky shows inside the place's "
              f"{len(record['interiors'])} interiors")
    return checks.Verdict("outside", checks.FAIL if faults else checks.PASS, reason, {"most inside": worst},
                          {"most inside": "lower"}, tuple(faults[:20]))


# --- light --------------------------------------------------------------------------------------------------------

def lamp_light(stage, path, spot, seconds):
    """What a sphere light of the stage gives a spot of level ground facing up at a second (its intensity over the
    distance squared times the slant; nothing outside a cone it is shaped to)."""
    from pxr import UsdLux
    prim = stage.GetPrimAtPath(path)
    lamp = UsdLux.SphereLight(prim)
    matrix = np.asarray(UsdLux.SphereLight(prim).ComputeLocalToWorldTransform(seconds * effect_layer.RATE))
    way = spot - matrix[3, :3]
    distance = float(np.linalg.norm(way))
    slant = max(0.0, -way[1] / distance)
    if prim.HasAPI(UsdLux.ShapingAPI):
        aim = -matrix[2, :3] / np.linalg.norm(matrix[2, :3])
        cone = float(UsdLux.ShapingAPI(prim).GetShapingConeAngleAttr().Get())
        if np.degrees(np.arccos(np.clip(np.dot(aim, way / distance), -1.0, 1.0))) > cone:
            return 0.0
    return float(lamp.GetIntensityAttr().Get(seconds * effect_layer.RATE)) * slant / distance ** 2


def pad_spots(rest):
    """Spots of the pad round the rocket's foot: PAD_RINGS out, eight round each."""
    turns = np.radians(np.arange(8) * 45.0)
    return [rest + np.array([ring * np.cos(turn), 0.0, ring * np.sin(turn)]) for ring in PAD_RINGS for turn in turns]


def judge_light(output, inputs, evidence):
    """Pass when the flame's light lights the pad at least LIGHT_OVER times the place's own lamps, from just after
    the engines light to just after lift-off; or when the record has no lights and says why its effects give none
    (`no_light`: steam, fog and ice light nothing)."""
    from pxr import UsdLux
    record = record_of(inputs)
    if not record.get("lights") and record.get("no_light"):
        return checks.Verdict("light", checks.PASS, f"the record's effects give off no light: {record['no_light']}")
    if not record.get("lights"):
        return checks.Verdict("light", checks.UNKNOWN, "the record gives the effects no light of their own and does "
                                                       "not say why (`no_light`)")
    stage, place = composed(output, inputs), place_of(inputs)
    tall, rest, motion = rocket_of(record, scene_of(inputs), motions_of(inputs))
    flames = [f"/{place}/{light['on']}/{light['name']}" for light in record["lights"]]
    lamps = [str(prim.GetPath()) for prim in stage.Traverse()
             if prim.IsA(UsdLux.SphereLight) and str(prim.GetPath()) not in flames]
    worst, faults = None, []
    for seconds in moments(float(motion["start"]) + LIGHT_FROM_IGNITION, lift_second(motion) + LIGHT_AFTER_LIFT):
        for spot in pad_spots(rest):
            flame = sum(lamp_light(stage, path, spot, seconds) for path in flames)
            own = sum(lamp_light(stage, path, spot, seconds) for path in lamps)
            ratio = flame / own if own > 0 else float("inf")
            worst = ratio if worst is None else min(worst, ratio)
            if ratio < LIGHT_OVER:
                faults.append(f"{seconds:.1f} s, ({spot[0]:.0f}, {spot[2]:.0f}): the flame lights it {ratio:.2f} "
                              "times the lamps")
    reason = (f"{len(faults)} pad spots and moments lit under {LIGHT_OVER} times the lamps" if faults else
              f"the flame lights the pad at least {worst:.1f} times the place's {len(lamps)} lamps from ignition to "
              "lift-off")
    return checks.Verdict("light", checks.FAIL if faults else checks.PASS, reason,
                          {"least over the lamps": round(float(worst), 3)}, {"least over the lamps": "higher"},
                          tuple(faults[:20]))


def layer_faults(folder):
    """The effects layer and every clip it plays are there."""
    folder = pathlib.Path(folder)
    if not (folder / effect_layer.LAYER).exists():
        return [f"no {effect_layer.LAYER}"]
    held = read_json(folder / "held.json")["particles"] if (folder / "held.json").exists() else {}
    return [f"{name} has no baked clip" for name in held
            if not (folder / effect_layer.ASSETS / f"{name}.usdc").exists()] or ([] if held else ["no emitter"])


def judge_designed(output, inputs, evidence):
    """Pass when every emitter rides an object of a row of the scene's inventory and every row whose kind emits has an
    object on the stage to carry its effects (the record's `missing`)."""
    record = record_of(inputs)
    stage, place = composed(output, inputs), place_of(inputs)
    faults = [f"{name}: no object of a row of the scene's inventory" for name in row_kinds.strangers(
        [entry["placement"]["on"] for entry in record["effects"]], read_json(inputs["design"]))]
    faults += [f"{entry['name']}: no object {entry['placement']['on']} on the stage" for entry in record["effects"]
               if not stage.GetPrimAtPath(f"/{place}/{entry['placement']['on']}")]
    faults += list(record.get("missing", []))
    measures = {"emitters": len(record["effects"]), "missing": len(faults)}
    reason = (f"{len(faults)} effects stand on nothing of the inventory" if faults else
              f"{len(record['effects'])} emitters each ride an object of an inventory row")
    return checks.Verdict("designed", checks.FAIL if faults else checks.PASS, reason, measures, {"missing": "lower"},
                          tuple(faults))


LAYER = contracts.Contract("effects-layer", 1, layer_faults, {"length": "metre", "up axis": "Y", "time": "second"})
CHECKS = tuple(checks.Check(name, judged_on_design(judge)) for name, judge in (
    ("attached", judge_attached), ("footage", judge_footage), ("light", judge_light), ("outside", judge_outside),
    ("designed", judge_designed)))
