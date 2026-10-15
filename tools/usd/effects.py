"""Put a place's particle effects into its OpenUSD stage: the dust the wind blows, the devils that wander, the smoke a
breath lets out, from the place's effects record (`data/effects/<place>.json`), each written two ways at once.

    .venv/bin/python tools/usd/effects.py <place> --stage <the place's stage folder>

It writes `<stage>/layers/effects.usda`, a layer of its own that the stage's root holds between the creator's edit
layer and the framework's base (tools/usd/export.py, STAGE_LAYERS), and each emitter's baked particles once into
`<stage>/assets/effects/<emitter>.usdc`.

The effect schema. Every emitter is an Xform `/<place>/Effects/<emitter>` standing where the effect leaves from, its
own frame the emitter's (x, y, z as the game's emitter turns them; y is the emitter's up), carrying what an engine
adapter needs to make the effect again with its own particle system, in the game's numbers:

    score:effect:kind               string   what it is (dust_drift, dust_devil_grains, smoke_breath, landing_dust...)
    score:effect:look               token    speck (a flat unlit round grain, solid to 0.4 of its radius) or puff
                                             (a soft lit card, thickest in the middle as (1 - r^2)^1.5, faded out
                                             near the eye over score:effect:near_fade metres)
    score:effect:card               token    a puff's card: dust (the game's dust card, its tint multiplied in) or
                                             plain (steam, fog, mist: white water, drawn in its own colour)
    score:effect:emitter            token    box, ring, sphere or point
    score:effect:emitter_size       float3   a box's half sides; a ring's radius, inner radius and height (about y);
                                             a sphere's radius (then 0, 0)
    score:effect:count              int      particles alive at once at the state written (a burst's grains)
    score:effect:rate               float    particles let out a second (count / lifetime; a burst's are let out over
                                             (1 - explosiveness) of a lifetime each trigger)
    score:effect:lifetime           float    seconds a particle lives
    score:effect:explosiveness      float    0 lets them out evenly, 1 all at once
    score:effect:trigger_every      float    a burst's period in the bake (0: always emitting)
    score:effect:direction          float3   the way they leave, in the emitter's frame
    score:effect:spread             float    degrees either side of it; score:effect:flatness squashes it toward the
                                             emitter's level (Godot's ParticleProcessMaterial spread and flatness)
    score:effect:speed              float2   metres a second, least and most
    score:effect:gravity            float3   the pull on each, metres a second squared, in the emitter's frame
    score:effect:damping            float2   metres a second squared taken off its speed, least and most
    score:effect:radial_accel       float2   push away from the emitter's middle, least and most
    score:effect:turbulence         float4   strength, scale and least and most influence a step (0s: none)
    score:effect:size               float    metres across at scale 1
    score:effect:scale              float2   least and most of its random scale
    score:effect:size_over_life     float2[] (share of its life, scale) points, straight between them
    score:effect:colour             color3f  linear colour (the game's sRGB colour, linearised)
    score:effect:opacity            float    how thick at its thickest
    score:effect:opacity_over_life  float2[] (share of its life, share of the opacity) points
    score:effect:near_fade          float2   a puff is gone this near the eye and whole past the second (metres)
    score:effect:wind               float3   the wind the particles go with, metres a second in the place's frame
    score:effect:spin               float    the emitter's own turn about its up, radians a second
    score:effect:space              token    world (a particle stays where it was let out) or local (carried with
                                             the emitter as it moves and turns)
    score:effect:seed               int      the seed the bake draws from
    score:effect:loop               float    seconds the bake runs before it repeats exactly
    score:effect:brightness         float    how many times its colour a speck gives off (a flame's 1 and more)
    score:effect:starts             float    the stage's second a looped emitter lights (nothing before; -1: always)
    score:effect:once               float2   an event's emitter: the stage's seconds it lets its `count` particles
                                             out between, evenly, each once (0, 0: looped)
    score:effect:follows            string   the motion (data/motion) whose climb the particles are let out from: each
                                             leaves from where the moving thing stood at its birth ("" for none)
    score:effect:from               string   the game file and lines every number came from, or for an effect the
                                             game never drew, the real footage it was measured on
                                             (data/effects/footage.json)

Under it a UsdGeomPoints `<emitter>_points` holds the particles baked over the loop, so any USD reader (Blender,
usdview, Omniverse) shows them without knowing the schema: `points` in the emitter's frame, `widths` (metres across)
and `primvars:displayOpacity` sampled SAMPLES times a second, `primvars:displayColor` constant, bound to a
UsdPreviewSurface reading both primvars. The samples are a value clip (`assets/effects/<emitter>.usdc`) the layer
loops over the stage's time (UsdClipsAPI clipTimes, out to HORIZON seconds), so the stage moves for as long as a
walk-through runs; between samples USD reads them straight. The layer runs at RATE time codes a second, as the
stage's root does.

An emitter placed `on` a prim of the base (`{"on": "Fixtures/rocket", "offset": [...]}`) is written as that prim's
child, `/<place>/<prim>/<emitter>`, in the prim's own frame, so it moves with it (the rocket's flame). One that
`follows` a motion (`{"follows": "rocket_launch", "offset": [...]}`) stands where the motion's prim rests, level, and
lets each particle out where the prim has climbed to at its birth (the trail a rocket leaves). One that fills a
`room` (`{"room": 0.15}`, metres in from its walls, floor and ceiling) is a box over the scene record's floor up to
its ceiling (a pump-down's fog). An event's emitter
(`once`: [first, last] seconds of the stage; any second of the record may be given as a moment of the place's climb
and seconds from it, `["ignition", s]` or `["lift-off", s]`, read off its motion record by `timed`) is baked once over its own span at its own `samples` a second and held
dead before and after; a looped one that `starts` at a second of the stage is dead before it. A record's `lights` are
UsdLux sphere lights on a prim (`on`, `offset`), their intensity (Blender's units, as scene.py writes lights) keyed
over the stage's seconds (`intensity`: [[seconds, intensity], ...]), `score:game:shadows` as given: the flame's light.

An emitter that travels (a dust devil wandering downwind) has its translate and its turn sampled at the start and the
end of its life, which USD reads straight between. A record's `replaces` makes a prim of the base inactive where the
effects layer draws the same thing moving (the camp's still drift). Entries with a `variant` go into that variant of
the `/<place>/Effects` variant set (the camp's weather: calm, the state the scene record holds, and storm). A record's
`interiors` (upright cylinders in the place's frame: the camp's domes) hold no particle of an emitter standing under
the open sky: one there at a sample is baked dead.

How the bake moves a particle repeats Godot 4's ParticleProcessMaterial (its emission shapes, spread and flatness,
gravity, damping, radial push, turbulence's steer toward a noise direction, size and colour over life, stepped at
the GPUParticles3D's 30 steps a second), with this module's own seeded generator and its own smooth noise: the same
record always gives the same particles, but not the game's own draws (Godot's particle hash is not repeated here).
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, Vt

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import ground as grounds  # noqa: E402
import motion as motion_record  # noqa: E402
import scene as scene_record  # noqa: E402

RECORDS = REPO / "data/effects"
KITS = REPO / "data/kit"
LAYER = "layers/effects.usda"
ASSETS = "assets/effects"
NOTE = "Generated by tools/usd/effects.py from the place's effects record (data/effects); rewritten on every run."
# The stage's time codes a second (its root names none, so USD reads 24) and how often the bake samples a particle.
RATE = 24.0
SAMPLES = 12.0
# The game's particles step 30 times a second (GPUParticles3D.fixed_fps).
STEP = 1.0 / 30.0
# How often a travelling emitter is stood on the ground again along its way, in seconds.
TRAVEL_STEP = 1.0
# How far into the stage's time the loop is laid, in seconds.
HORIZON = 600.0
# How many numbers a particle draws when it is let out: three for its spot, two for its way, speed, damping, radial
# push, turbulence's influence and scale.
DRAWS = 10
# The noise turbulence steers by: this many waves a direction.
NOISE_WAVES = 4
# A puff's own colour and thickness at its middle (2099's dust.tres dust_color), which the game multiplies into the
# particle's colour and opacity.
PUFF_TINT = (0.65882355, 0.6392157, 0.60784316)
PUFF_THICKNESS = 0.6


# --- the record ---------------------------------------------------------------------------------------------------

def record(place, path=None):
    """The place's effects record, or None when it has none."""
    path = pathlib.Path(path) if path else RECORDS / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def place_ground(place):
    """The place's planned ground (tools/usd/ground.py), or None for a flat place."""
    kit_path = KITS / f"{place}.json"
    on_seat = json.loads(kit_path.read_text()).get("on_seat", [0.0, 0.0]) if kit_path.exists() else [0.0, 0.0]
    return grounds.place_ground(place, on_seat)


def godot_basis(columns):
    """A 3 x 3 whose columns are the given axes, made orthonormal the way Godot's Basis.orthonormalized does
    (Gram-Schmidt, x kept, then y, then z)."""
    x_axis, y_axis, z_axis = (np.asarray(column, dtype=float) for column in columns)
    x_axis = x_axis / np.linalg.norm(x_axis)
    y_axis = y_axis - x_axis * x_axis.dot(y_axis)
    y_axis = y_axis / np.linalg.norm(y_axis)
    z_axis = z_axis - x_axis * x_axis.dot(z_axis) - y_axis * y_axis.dot(z_axis)
    return np.column_stack([x_axis, y_axis, z_axis / np.linalg.norm(z_axis)])


def looking_basis(eye, aim):
    """The camera's turn as Godot's Basis.looking_at gives it (its -z toward the aim, up kept near y)."""
    back = np.asarray(eye, dtype=float) - np.asarray(aim, dtype=float)
    back /= np.linalg.norm(back)
    right = np.cross([0.0, 1.0, 0.0], back)
    right /= np.linalg.norm(right)
    return np.column_stack([right, np.cross(back, right), back])


def quaternion_basis(turn):
    """A unit quaternion [x, y, z, w] as a 3 x 3 (the scene record's `placed_turn`)."""
    x, y, z, w = (float(value) for value in turn)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def wind_along(up, minute, turn_a_day):
    """Which way the wind blows along the ground under `up` (a way out from the world's middle, in its own space) at
    a base minute: 2099's MarsWind.wind_along, a heading fixed to the ground that turns slowly over the day."""
    up = np.asarray(up, dtype=float) / np.linalg.norm(up)
    level = np.cross(up, [1.0, 0.0, 0.0])
    if np.linalg.norm(level) < 0.001:
        level = np.cross(up, [0.0, 0.0, -1.0])
    level /= np.linalg.norm(level)
    turned = grounds.turned(level, up, minute / (24.0 * 60.0) * turn_a_day)
    return turned / np.linalg.norm(turned)


def on_ground(ground, across, along, lift):
    """A spot of the place lifted off its planned ground, with the ground's up there, both in the place's frame; on a
    flat place the ground is y = 0."""
    if ground is None:
        return np.array([across, lift, along], dtype=float), np.array([0.0, 1.0, 0.0])
    position, seat_turn = ground.standing(across, along, lift)
    return np.asarray(position, dtype=float), np.asarray(seat_turn[1], dtype=float)


def place_wind(ground, across, along, wind):
    """The record's wind at a spot of the place, as a way along the ground in the place's frame: worked out in the
    world's own space as the game does it, then turned into the place's."""
    if ground is None:
        return np.array([1.0, 0.0, 0.0])
    out = ground.direction(ground.frame, ground.origin, across, along)
    return ground.frame @ wind_along(out, float(wind["minute"]), float(wind["turn_a_day"]))


def cell_emitters(entry, ground, wind):
    """A drift laid on square cells round the place's middle (`cells`: `side` metres a cell, `out` cells either side):
    one emitter a cell, a box on the ground under its middle, half as high as the drift, turned along the wind there
    (2099's MarsWind._blow), its particles let out downwind at the wind's speed."""
    cells = entry["placement"]["cells"]
    side, out, high = float(cells["side"]), int(cells["out"]), float(cells["high"])
    emitters = []
    for row in range(-out, out + 1):
        for column in range(-out, out + 1):
            number = (row + out) * (2 * out + 1) + column + out
            across, along = column * side, row * side
            ground_point, up = on_ground(ground, across, along, 0.0)
            way = place_wind(ground, across, along, wind)
            basis = godot_basis([way, up, np.cross(way, up)])
            name = f"{entry['name']}_{row + out}_{column + out}"
            emitters.append(dict(entry, name=name, origin=ground_point + up * high / 2.0, basis=basis,
                                 wind_velocity=way * float(cells["wind_speed"]), seed=int(entry["seed"]) + number))
    return emitters


def upright(up):
    """A turn standing an emitter's y along `up` (2099's DustDevil.stand: x is up crossed with up x x)."""
    level = np.cross(up, [1.0, 0.0, 0.0])
    return godot_basis([np.cross(up, level), up, level])


def ground_emitter(entry, ground, wind):
    """An emitter standing on the ground at (`across`, `along`), upright along the ground's up there; one that
    `travel`s wanders downwind at its speed for the rest of its life, stood on the ground again every TRAVEL_STEP
    seconds as the game stands its devils (its `path`: seconds, spot, turn)."""
    across, along, lift = (float(value) for value in entry["placement"]["ground"])
    point, up = on_ground(ground, across, along, lift)
    emitter = dict(entry, origin=point, basis=upright(up))
    travel = entry.get("travel")
    if travel:
        way = place_wind(ground, across, along, wind)
        emitter["wind_velocity"] = way * float(travel["downwind"])
        flat = np.array([way[0], way[2]]) / np.linalg.norm([way[0], way[2]]) * float(travel["downwind"])
        left = float(travel["seconds"]) - float(travel.get("age", 0.0))
        path = []
        for seconds in np.arange(0.0, left + TRAVEL_STEP / 2, TRAVEL_STEP):
            spot, spot_up = on_ground(ground, across + flat[0] * seconds, along + flat[1] * seconds, lift)
            path.append((float(seconds), spot, upright(spot_up)))
        emitter["path"] = path
    return emitter


def eye_emitter(entry, scene):
    """An emitter hung off one of the scene record's cameras, as the game hangs the cigarette's smoke off the player's
    camera: at `offset` in the camera's own numbers (x right, y up, -z ahead), turned with the camera."""
    view = next(view for view in scene["views"] if view["name"] == entry["placement"]["eye"])
    basis = looking_basis(view["eye"], view["aim"])
    origin = np.asarray(view["eye"], dtype=float) + basis @ np.asarray(entry["placement"]["offset"], dtype=float)
    return dict(entry, origin=origin, basis=basis)


def structure_emitter(entry, scene):
    """An emitter on a structure of the scene record (the landing pad), at `offset` in that structure's own frame,
    turned as it is placed (`placed_at`, `placed_turn`)."""
    found = next(item for item in scene["structure"] if item["name"] == entry["placement"]["structure"])
    basis = quaternion_basis(found.get("placed_turn", (0.0, 0.0, 0.0, 1.0)))
    origin = np.asarray(found.get("placed_at", (0.0, 0.0, 0.0)), dtype=float) + basis @ np.asarray(
        entry["placement"].get("offset", (0.0, 0.0, 0.0)), dtype=float)
    return dict(entry, origin=origin, basis=basis)


def room_emitter(entry, scene):
    """An emitter filling a room (`room`: how far in from its walls, floor and ceiling, metres): a box over the scene
    record's floor up to its ceiling, upright in the room's frame (the pump-down's fog)."""
    margin = float(entry["placement"]["room"])
    low, high = np.asarray(scene["floor"][0], dtype=float), np.asarray(scene["floor"][1], dtype=float)
    ceiling = float(scene["ceiling"])
    origin = np.array([(low[0] + high[0]) / 2.0, ceiling / 2.0, (low[1] + high[1]) / 2.0])
    extents = [(high[0] - low[0]) / 2.0 - margin, ceiling / 2.0 - margin, (high[1] - low[1]) / 2.0 - margin]
    return dict(entry, origin=origin, basis=np.eye(3), emitter={"shape": "box", "extents": extents})


def prim_emitter(entry):
    """An emitter riding a prim of the base (`on`): its `origin` the offset in the prim's own frame, written as the
    prim's child so it moves and turns with it."""
    return dict(entry, origin=np.asarray(entry["placement"].get("offset", (0.0, 0.0, 0.0)), dtype=float),
                basis=np.eye(3), parent=entry["placement"]["on"])


def motion_named(motions, name):
    """The motion record's entry of that name."""
    found = [motion for motion in (motions or {}).get("motions", []) if motion["name"] == name]
    if len(found) != 1:
        raise ValueError(f"the motion record has {len(found)} motions named {name}")
    return found[0]


def following_emitter(entry, scene, motions):
    """An emitter that lets its particles out where a climbing motion's prim stands at each birth: level, at the
    prim's rest (the scene record's object of the prim's name) plus `offset`, the climb kept for the bake."""
    motion = motion_named(motions, entry["placement"]["follows"])
    name = motion["prim"].rsplit("/", 1)[-1]
    rest = next(item for item in scene["objects"] if item["name"] == name)
    origin = np.asarray(rest["at"], dtype=float) + np.asarray(entry["placement"].get("offset", (0.0, 0.0, 0.0)))
    return dict(entry, origin=origin, basis=np.eye(3), climb=dict(motion["climb"], start=float(motion["start"])))


# The moments of a place's climb an effect's second may be given from: the engines' start and the release.
MOMENTS = {"ignition": lambda climb: float(climb["start"]),
           "lift-off": lambda climb: float(climb["start"]) + float(climb["climb"]["lift"])}


def second_of(value, motions):
    """A record's second of the stage: a number as it is, `[moment, seconds]` that many seconds from the moment of the
    place's climb (MOMENTS), so the effects keep to the motion record's timing."""
    if not isinstance(value, list):
        return float(value)
    moment, offset = value
    climbs = [motion for motion in (motions or {}).get("motions", []) if "climb" in motion]
    if len(climbs) != 1 or moment not in MOMENTS:
        raise ValueError(f"{value}: a second from {moment} needs one climb in the motion record, "
                         f"and a moment of {', '.join(MOMENTS)}")
    return MOMENTS[moment](climbs[0]) + float(offset)


def timed(effects, motions):
    """The record with every second given from a moment of the climb (an emitter's `once` and `starts`, a light's
    `intensity` keys) as its second of the stage."""
    found = json.loads(json.dumps(effects))
    for entry in found["effects"]:
        if "once" in entry:
            entry["once"] = [second_of(value, motions) for value in entry["once"]]
        if entry.get("starts") is not None:
            entry["starts"] = second_of(entry["starts"], motions)
    for light in found.get("lights", []):
        light["intensity"] = [[second_of(seconds, motions), intensity] for seconds, intensity in light["intensity"]]
    return found


def emitters_of(effects, ground, scene, motions=None):
    """Every emitter the record lays, each with its `origin` and `basis` (columns: its x, y, z) in the place's frame
    (one `on` a prim: in that prim's frame)."""
    wind = effects.get("wind")
    emitters = []
    for entry in effects["effects"]:
        placement = entry["placement"]
        if "on" in placement:
            emitters.append(prim_emitter(entry))
        elif "follows" in placement:
            emitters.append(following_emitter(entry, scene, motions))
        elif "cells" in placement:
            emitters += cell_emitters(entry, ground, wind)
        elif "ground" in placement:
            emitters.append(ground_emitter(entry, ground, wind))
        elif "eye" in placement:
            emitters.append(eye_emitter(entry, scene))
        elif "structure" in placement:
            emitters.append(structure_emitter(entry, scene))
        elif "room" in placement:
            emitters.append(room_emitter(entry, scene))
        else:
            raise ValueError(f"{entry['name']}: no placement this module knows ({sorted(placement)})")
    return emitters


def gravity_of(emitter):
    """The pull on the emitter's particles in its own frame: its `gravity` as given there, plus its `rise` (metres a
    second squared along the place's up, turned into the emitter's frame, as the game sets a world pull on an emitter
    that turns with the head)."""
    gravity = np.asarray(emitter.get("gravity", (0.0, 0.0, 0.0)), dtype=float)
    if emitter.get("rise"):
        gravity = gravity + emitter["basis"].T @ np.array([0.0, float(emitter["rise"]), 0.0])
    return gravity


def speeds_of(emitter):
    """Least and most speed: the record's, or with `wind_share` that share of the wind's speed (the drift goes with
    the wind)."""
    if "wind_share" in emitter:
        speed = float(np.linalg.norm(emitter["wind_velocity"]))
        return [speed * float(share) for share in emitter["wind_share"]]
    return [float(value) for value in emitter.get("speed", (0.0, 0.0))]


# --- the bake: Godot 4's ParticleProcessMaterial, stepped ---------------------------------------------------------

def mix(pair, share):
    pair = pair if pair is not None else (0.0, 0.0)
    return float(pair[0]) + (float(pair[1]) - float(pair[0])) * share


def emission_points(emitter, draws):
    """Where each particle is let out, in the emitter's frame (Godot's emission shapes)."""
    shape = emitter["emitter"]
    kind = shape["shape"]
    if kind == "box":
        return (draws[:, 0:3] * 2.0 - 1.0) * np.asarray(shape["extents"], dtype=float)
    if kind == "ring":
        radius, inner = float(shape["radius"]), float(shape["inner"])
        angle = draws[:, 0] * 2.0 * math.pi
        out = np.sqrt(draws[:, 1] * (radius * radius - inner * inner) + inner * inner)
        height = (draws[:, 2] - 0.5) * float(shape["height"])
        # About y, starting along z (Godot: the axis crossed with x, turned by the angle).
        return np.column_stack([out * np.sin(angle), height, out * np.cos(angle)])
    if kind == "sphere":
        radius = float(shape["radius"])
        height = draws[:, 0] * 2.0 - 1.0
        angle = draws[:, 1] * 2.0 * math.pi
        across = radius * np.sqrt(1.0 - height * height)
        return np.column_stack([across * np.cos(angle), across * np.sin(angle), radius * height]) * draws[:, 2:3]
    if kind == "point":
        return np.zeros((len(draws), 3))
    raise ValueError(f"{emitter['name']}: no emission shape {kind}")


def spread_directions(direction, spread, flatness, first, second):
    """Godot 4's get_random_direction_from_spread: each particle's way, `spread` degrees either side of `direction`,
    squashed toward its level by `flatness`; `first` and `second` are draws from 0 to 1."""
    spread_radians = math.radians(spread)
    angle_one = (first * 2.0 - 1.0) * spread_radians
    angle_two = (second * 2.0 - 1.0) * spread_radians * (1.0 - flatness)
    lean = np.cos(angle_two)
    lean = lean / np.maximum(np.sqrt(np.abs(lean)), 0.0001)
    local = np.column_stack([np.sin(angle_one) * lean, np.sin(angle_two), np.cos(angle_one) * lean])
    ahead = np.asarray(direction, dtype=float)
    ahead = ahead / np.linalg.norm(ahead) if np.linalg.norm(ahead) > 0 else np.array([0.0, 0.0, 1.0])
    binormal = np.cross([0.0, 1.0, 0.0], ahead)
    binormal = binormal / np.linalg.norm(binormal) if np.linalg.norm(binormal) >= 0.0001 else np.array([0.0, 0.0, 1.0])
    normal = np.cross(binormal, ahead)
    ways = local[:, 0:1] * binormal + local[:, 1:2] * normal + local[:, 2:3] * ahead
    return ways / np.linalg.norm(ways, axis=1, keepdims=True)


class Noise:
    """A smooth direction field from a seed: a few waves a direction, the stage's own stand-in for Godot's turbulence
    noise (its scale kept: features about one over `scale` metres)."""

    def __init__(self, seed, scale):
        draw = np.random.default_rng([int(seed), 7])
        self.waves = draw.normal(size=(3, NOISE_WAVES, 3)) * float(scale)
        self.phases = draw.uniform(0.0, 2.0 * math.pi, size=(3, NOISE_WAVES))

    def direction(self, points):
        field = np.stack([np.sin(points @ self.waves[axis].T + self.phases[axis]).sum(axis=1) for axis in range(3)],
                         axis=1)
        return field / np.maximum(np.linalg.norm(field, axis=1, keepdims=True), 1e-6)


def steps_of(emitter):
    return int(math.ceil(float(emitter["lifetime"]) / STEP)) + 1


def flight(emitter, draws, seed):
    """Every particle's way through one life, from its draws: its spot at each of the game's steps (steps x count x
    3, in the emitter's frame) and its own scale."""
    points = emission_points(emitter, draws)
    ways = spread_directions(emitter.get("direction", (1.0, 0.0, 0.0)), float(emitter.get("spread", 0.0)),
                             float(emitter.get("flatness", 0.0)), draws[:, 3], draws[:, 4])
    low, high = speeds_of(emitter)
    velocity = ways * (low + (high - low) * draws[:, 5])[:, None]
    damping = mix(emitter.get("damping"), draws[:, 6])
    radial = mix(emitter.get("radial_accel"), draws[:, 7])
    turbulence = emitter.get("turbulence")
    noise = Noise(seed, turbulence["scale"]) if turbulence else None
    influence = mix(turbulence["influence"], draws[:, 8]) if turbulence else None
    gravity = gravity_of(emitter)
    track = np.empty((steps_of(emitter), len(points), 3), dtype=np.float32)
    track[0] = points
    for step in range(1, len(track)):
        force = np.broadcast_to(gravity, points.shape).copy()
        if np.any(radial):
            away = np.linalg.norm(points, axis=1, keepdims=True)
            force += np.where(away > 0, points / np.maximum(away, 1e-9), 0.0) * np.asarray(radial)[..., None]
        velocity = velocity + force * STEP
        if noise is not None:
            speed = np.linalg.norm(velocity, axis=1, keepdims=True)
            steer = np.clip(influence, 0.0, 1.0)[:, None]
            velocity = velocity * (1.0 - steer) + noise.direction(points) * speed * (1.0 + (1.0 - steer) * 0.2) * steer
        if np.any(damping):
            speed = np.linalg.norm(velocity, axis=1, keepdims=True)
            slowed = np.maximum(speed - np.asarray(damping)[..., None] * STEP, 0.0)
            velocity = np.where(speed > 0, velocity / np.maximum(speed, 1e-9) * slowed, 0.0)
        points = points + velocity * STEP
        track[step] = points
    scale = mix(emitter.get("scale", (1.0, 1.0)), draws[:, 9])
    return track, np.broadcast_to(scale, (len(points),)).astype(np.float32)


def over_life(curve, shares, default=1.0):
    """A curve of (share of life, value) points read at each share, straight between them."""
    if not curve:
        return np.full(np.shape(shares), default)
    curve = np.asarray(curve, dtype=float)
    return np.interp(shares, curve[:, 0], curve[:, 1])


def loop_of(emitter):
    """How long the bake runs before it repeats exactly: a burst's period, else its lifetime times `lives`; an event's
    span (it never repeats) from its first birth to its last death."""
    if emitter.get("once"):
        first, last = (float(value) for value in emitter["once"])
        return last - first + float(emitter["lifetime"])
    if emitter.get("one_shot"):
        return float(emitter["one_shot"]["every"])
    return float(emitter["lifetime"]) * int(emitter.get("lives", 1))


def births(emitter):
    """When each particle is let out within a lifetime (a burst: within its period, from its trigger), seconds:
    evenly over (1 - explosiveness) of a lifetime, as Godot spaces them."""
    count, lifetime = int(emitter["count"]), float(emitter["lifetime"])
    spaced = np.arange(count) / count * lifetime * (1.0 - float(emitter.get("explosiveness", 0.0)))
    if emitter.get("one_shot"):
        return spaced + float(emitter["one_shot"].get("at", 0.0))
    return spaced


def look_colour(emitter):
    """The colour a reader without the schema draws the particles in (linear): a puff's colour carries its card's
    tint, as the game's dust material multiplies it in, unless its `card` is plain (steam, fog, mist); a speck's is
    its colour times its brightness."""
    linear = np.asarray(scene_record.colour(emitter["colour"]), dtype=float)
    if emitter["look"] == "puff":
        tint = PUFF_TINT if emitter.get("card", "dust") == "dust" else (1.0, 1.0, 1.0)
        return linear * np.asarray(scene_record.colour(list(tint)))
    return linear * float(emitter.get("brightness", 1.0))


def look_opacity(emitter):
    return float(emitter["opacity"]) * (PUFF_THICKNESS if emitter["look"] == "puff" else 1.0)


def samples_of(emitter):
    """How often a second the bake samples the emitter's particles: its own `samples`, else SAMPLES."""
    return float(emitter.get("samples", SAMPLES))


def climbed(emitter, born):
    """How far the followed motion's prim has risen at each birth (seconds of the stage); none for an emitter that
    follows nothing."""
    climb = emitter.get("climb")
    if not climb:
        return np.zeros(len(born))
    return np.array([motion_record.climb_height(climb, seconds - climb["start"]) for seconds in born])


def bake_once(emitter):
    """An event's particles, each let out once, evenly between its `once` seconds, from its first second to its last
    particle's death at its samples a second: spots (samples x count x 3, its frame; a following emitter's lifted by
    its prim's climb at each birth), widths and opacities (samples x count), nothing alive before birth or after."""
    count, lifetime = int(emitter["count"]), float(emitter["lifetime"])
    first, last = (float(value) for value in emitter["once"])
    draws = np.random.default_rng([int(emitter["seed"]), 0]).random((count, DRAWS))
    track, scale = flight(emitter, draws, int(emitter["seed"]))
    born = first + (np.arange(count) + 0.5) / count * (last - first)
    times = first + np.arange(int(math.ceil(loop_of(emitter) * samples_of(emitter))) + 1) / samples_of(emitter)
    since = times[:, None] - born[None, :]
    alive = (since >= 0.0) & (since < lifetime)
    age = np.clip(since, 0.0, lifetime)
    step_at = age / STEP
    lower = np.clip(np.floor(step_at).astype(int), 0, track.shape[0] - 2)
    part = (step_at - lower)[..., None].astype(np.float32)
    which = np.broadcast_to(np.arange(count), age.shape)
    points = track[lower, which] * (1.0 - part) + track[lower + 1, which] * part
    points[..., 1] += climbed(emitter, born).astype(np.float32)[None, :]
    share = age / lifetime
    widths = float(emitter["size"]) * scale[which] * over_life(emitter.get("size_over_life"), share)
    opacity = look_opacity(emitter) * over_life(emitter.get("opacity_over_life"), share)
    return (points.astype(np.float32), np.where(alive, widths, 0.0).astype(np.float32),
            np.where(alive, opacity, 0.0).astype(np.float32))


def bake(emitter):
    """The emitter's particles over its loop, `samples_of` a second from 0 to the loop's end (the last sample is the
    first again): spots (samples x count x 3, its frame), widths and opacities (samples x count). An event's
    (`once`) are bake_once's."""
    if emitter.get("once"):
        return bake_once(emitter)
    count, lifetime = int(emitter["count"]), float(emitter["lifetime"])
    loop = loop_of(emitter)
    lives = 1 if emitter.get("one_shot") else int(emitter.get("lives", 1))
    seed = int(emitter["seed"])
    tracks, scales = [], []
    for life in range(lives):
        draws = np.random.default_rng([seed, life]).random((count, DRAWS))
        track, scale = flight(emitter, draws, seed)
        tracks.append(track)
        scales.append(scale)
    tracks, scales = np.stack(tracks), np.stack(scales)
    # The clip lays sample n at n / samples_of seconds (write_clip), so the bake samples at the same rate.
    times = np.arange(int(round(loop * samples_of(emitter))) + 1) / samples_of(emitter)
    born = births(emitter)
    since = (times[:, None] - born[None, :]) % loop if emitter.get("one_shot") else times[:, None] - born[None, :]
    life = (np.floor(since / lifetime).astype(int) % lives) if not emitter.get("one_shot") else np.zeros_like(since,
                                                                                                             dtype=int)
    age = since % lifetime if not emitter.get("one_shot") else np.minimum(since, lifetime)
    alive = np.ones_like(since, dtype=bool) if not emitter.get("one_shot") else since < lifetime
    step_at = age / STEP
    first = np.clip(np.floor(step_at).astype(int), 0, tracks.shape[1] - 2)
    part = (step_at - first)[..., None]
    which = np.broadcast_to(np.arange(count), since.shape)
    points = tracks[life, first, which] * (1.0 - part) + tracks[life, first + 1, which] * part
    share = np.clip(age / lifetime, 0.0, 1.0)
    widths = float(emitter["size"]) * scales[life, which] * over_life(emitter.get("size_over_life"), share)
    opacity = look_opacity(emitter) * over_life(emitter.get("opacity_over_life"), share)
    widths = np.where(alive, widths, 0.0).astype(np.float32)
    opacity = np.where(alive, opacity, 0.0).astype(np.float32)
    return points.astype(np.float32), widths, opacity


# --- the stage ----------------------------------------------------------------------------------------------------

def inside(spots, interiors):
    """Which spots (place's frame) lie inside any of the record's interiors (each an upright cylinder: `middle` x
    and z, `radius`, from `floor` to `top`)."""
    within = np.zeros(spots.shape[:-1], dtype=bool)
    for room in interiors or []:
        across = np.hypot(spots[..., 0] - float(room["middle"][0]), spots[..., 2] - float(room["middle"][1]))
        within |= ((across <= float(room["radius"])) & (spots[..., 1] >= float(room["floor"]))
                   & (spots[..., 1] <= float(room["top"])))
    return within


def kept_out(emitter, points, widths, interiors):
    """The widths with every particle let out under the open sky that stands inside an interior at a sample made
    dead (the camp's drift blew through its domes): only an emitter standing still in the place's frame, not one
    that rides a prim, travels or fills a room (those the `outside` gate measures as they stand)."""
    if not interiors or emitter.get("parent") or emitter.get("path") or "room" in emitter["placement"] \
            or emitter.get("climb"):
        return widths
    spots = points.astype(float) @ np.asarray(emitter["basis"], dtype=float).T + np.asarray(emitter["origin"])
    return np.where(inside(spots, interiors), 0.0, widths).astype(np.float32)


def write_clip(emitter, out, interiors=None):
    """The emitter's baked particles as a clip file of their own (`assets/effects/<emitter>.usdc`, the prim
    /Effect), sampled every RATE / its samples a second, none inside the record's `interiors`; one that `starts`
    gets one more sample after its loop, every particle dead, held before it lights; its path in the stage folder
    and how many samples it holds."""
    points, widths, opacity = bake(emitter)
    widths = kept_out(emitter, points, widths, interiors)
    if emitter.get("starts") is not None:
        points = np.concatenate([points, points[:1]])
        widths = np.concatenate([widths, np.zeros_like(widths[:1])])
        opacity = np.concatenate([opacity, np.zeros_like(opacity[:1])])
    path = pathlib.Path(out) / ASSETS / f"{emitter['name']}.usdc"
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path)) if not path.exists() else Sdf.Layer.FindOrOpen(str(path))
    layer.Clear()
    layer.timeCodesPerSecond = RATE
    clip = Usd.Stage.Open(layer)
    grains = UsdGeom.Points.Define(clip, "/Effect")
    opacity_primvar = UsdGeom.PrimvarsAPI(grains).CreatePrimvar("displayOpacity", Sdf.ValueTypeNames.FloatArray,
                                                               UsdGeom.Tokens.vertex)
    for sample in range(len(points)):
        time = sample * RATE / samples_of(emitter)
        grains.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(points[sample]), time)
        grains.GetWidthsAttr().Set(Vt.FloatArray.FromNumpy(widths[sample]), time)
        opacity_primvar.Set(Vt.FloatArray.FromNumpy(opacity[sample]), time)
    layer.defaultPrim = "Effect"
    layer.Save()
    return path, len(points)


def looped_times(loop):
    """Stage time codes onto clip time codes: the clip's 0 to its loop, again and again out to HORIZON seconds, each
    loop's end jumping back to its start."""
    span = loop * RATE
    pairs = []
    for turn in range(int(math.ceil(HORIZON / loop))):
        pairs += [Gf.Vec2d(turn * span, 0.0), Gf.Vec2d((turn + 1) * span, span)]
    return pairs


def clip_times(emitter, samples):
    """Stage time codes onto the emitter's clip: an event's span laid once from its first second (held dead before
    and after), a looped one again and again, from the second it `starts` when it has one (its dead last sample
    held before)."""
    if emitter.get("once"):
        first, span = float(emitter["once"][0]) * RATE, (samples - 1) * RATE / samples_of(emitter)
        return [Gf.Vec2d(first, 0.0), Gf.Vec2d(first + span, span)]
    looped = looped_times(loop_of(emitter))
    if emitter.get("starts") is None:
        return looped
    start, dead = float(emitter["starts"]) * RATE, (samples - 1) * RATE / samples_of(emitter)
    return [Gf.Vec2d(0.0, dead), Gf.Vec2d(start, dead)] + [Gf.Vec2d(pair[0] + start, pair[1]) for pair in looped]


def effect_look(stage, root, emitter):
    """A UsdPreviewSurface drawing a Points prim in its displayColor and displayOpacity primvars: lit for a puff, its
    own light for a speck."""
    path = f"{root}/Looks/{emitter['look']}"
    if stage.GetPrimAtPath(path):
        return UsdShade.Material(stage.GetPrimAtPath(path))
    material = UsdShade.Material.Define(stage, path)
    surface = UsdShade.Shader.Define(stage, f"{path}/surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    colour = UsdShade.Shader.Define(stage, f"{path}/colour")
    colour.CreateIdAttr("UsdPrimvarReader_float3")
    colour.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
    thickness = UsdShade.Shader.Define(stage, f"{path}/thickness")
    thickness.CreateIdAttr("UsdPrimvarReader_float")
    thickness.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayOpacity")
    lit_by = "diffuseColor" if emitter["look"] == "puff" else "emissiveColor"
    surface.CreateInput(lit_by, Sdf.ValueTypeNames.Color3f).ConnectToSource(
        colour.CreateOutput("result", Sdf.ValueTypeNames.Float3))
    if lit_by == "emissiveColor":
        surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))
    surface.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(
        thickness.CreateOutput("result", Sdf.ValueTypeNames.Float))
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    material.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    return material


SCHEMA = {  # attribute: (type, how it is read off the emitter)
    "kind": (Sdf.ValueTypeNames.String, lambda emitter: emitter["kind"]),
    "look": (Sdf.ValueTypeNames.Token, lambda emitter: emitter["look"]),
    "card": (Sdf.ValueTypeNames.Token, lambda emitter: emitter.get("card", "dust")),
    "emitter": (Sdf.ValueTypeNames.Token, lambda emitter: emitter["emitter"]["shape"]),
    "emitter_size": (Sdf.ValueTypeNames.Float3, lambda emitter: emitter_size(emitter["emitter"])),
    "count": (Sdf.ValueTypeNames.Int, lambda emitter: int(emitter["count"])),
    "rate": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter["count"]) / letting_out(emitter)),
    "lifetime": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter["lifetime"])),
    "explosiveness": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter.get("explosiveness", 0.0))),
    "trigger_every": (Sdf.ValueTypeNames.Float,
                      lambda emitter: float(emitter["one_shot"]["every"]) if emitter.get("one_shot") else 0.0),
    "direction": (Sdf.ValueTypeNames.Float3, lambda emitter: Gf.Vec3f(*emitter.get("direction", (1.0, 0.0, 0.0)))),
    "spread": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter.get("spread", 0.0))),
    "flatness": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter.get("flatness", 0.0))),
    "speed": (Sdf.ValueTypeNames.Float2, lambda emitter: Gf.Vec2f(*speeds_of(emitter))),
    "gravity": (Sdf.ValueTypeNames.Float3, lambda emitter: Gf.Vec3f(*gravity_of(emitter))),
    "damping": (Sdf.ValueTypeNames.Float2, lambda emitter: Gf.Vec2f(*emitter.get("damping", (0.0, 0.0)))),
    "radial_accel": (Sdf.ValueTypeNames.Float2, lambda emitter: Gf.Vec2f(*emitter.get("radial_accel", (0.0, 0.0)))),
    "turbulence": (Sdf.ValueTypeNames.Float4, lambda emitter: turbulence_values(emitter.get("turbulence"))),
    "size": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter["size"])),
    "scale": (Sdf.ValueTypeNames.Float2, lambda emitter: Gf.Vec2f(*emitter.get("scale", (1.0, 1.0)))),
    "size_over_life": (Sdf.ValueTypeNames.Float2Array,
                       lambda emitter: Vt.Vec2fArray([Gf.Vec2f(*point) for point in emitter.get("size_over_life",
                                                                                                [[0, 1], [1, 1]])])),
    "colour": (Sdf.ValueTypeNames.Color3f, lambda emitter: Gf.Vec3f(*scene_record.colour(emitter["colour"]))),
    "opacity": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter["opacity"])),
    "opacity_over_life": (Sdf.ValueTypeNames.Float2Array,
                          lambda emitter: Vt.Vec2fArray([Gf.Vec2f(*point) for point in emitter.get(
                              "opacity_over_life", [[0, 1], [1, 1]])])),
    "near_fade": (Sdf.ValueTypeNames.Float2, lambda emitter: Gf.Vec2f(*emitter.get("near_fade", (0.0, 0.0)))),
    "wind": (Sdf.ValueTypeNames.Float3, lambda emitter: Gf.Vec3f(*emitter.get("wind_velocity", (0.0, 0.0, 0.0)))),
    "spin": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter.get("spin", 0.0))),
    "space": (Sdf.ValueTypeNames.Token, lambda emitter: emitter.get("space", "world")),
    "seed": (Sdf.ValueTypeNames.Int, lambda emitter: int(emitter["seed"])),
    "loop": (Sdf.ValueTypeNames.Float, loop_of),
    "brightness": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter.get("brightness", 1.0))),
    "starts": (Sdf.ValueTypeNames.Float, lambda emitter: float(emitter.get("starts", -1.0))),
    "once": (Sdf.ValueTypeNames.Float2, lambda emitter: Gf.Vec2f(*emitter.get("once", (0.0, 0.0)))),
    "follows": (Sdf.ValueTypeNames.String, lambda emitter: emitter["placement"].get("follows", "")),
    "from": (Sdf.ValueTypeNames.String, lambda emitter: emitter["from"]),
}


def letting_out(emitter):
    """The seconds over which the emitter lets out its count: an event's span of births, else a lifetime."""
    if emitter.get("once"):
        return float(emitter["once"][1]) - float(emitter["once"][0])
    return float(emitter["lifetime"])


def emitter_size(shape):
    if shape["shape"] == "box":
        return Gf.Vec3f(*shape["extents"])
    if shape["shape"] == "ring":
        return Gf.Vec3f(float(shape["radius"]), float(shape["inner"]), float(shape["height"]))
    if shape["shape"] == "sphere":
        return Gf.Vec3f(float(shape["radius"]), 0.0, 0.0)
    return Gf.Vec3f(0.0, 0.0, 0.0)


def turbulence_values(turbulence):
    if not turbulence:
        return Gf.Vec4f(0.0, 0.0, 0.0, 0.0)
    return Gf.Vec4f(float(turbulence["strength"]), float(turbulence["scale"]), *map(float, turbulence["influence"]))


def usd_turn(basis):
    """A turn (columns: the axes) as a USD matrix, whose rows are the axes."""
    return Gf.Matrix4d(Gf.Matrix3d(*np.asarray(basis, dtype=float).T.flatten()), Gf.Vec3d(0.0, 0.0, 0.0))


def stood(xform, emitter):
    """The emitter's transform: where it stands and its turn; one that travels is sampled along its `path` and one
    that spins turns about its up, sampled at the ends of what is left of its life (USD reads straight between)."""
    translate = xform.AddTranslateOp()
    turn = xform.AddTransformOp(opSuffix="turn")
    path = emitter.get("path")
    if path:
        for seconds, spot, basis in path:
            translate.Set(Gf.Vec3d(*map(float, spot)), seconds * RATE)
            turn.Set(usd_turn(basis), seconds * RATE)
    else:
        translate.Set(Gf.Vec3d(*map(float, emitter["origin"])))
        turn.Set(usd_turn(emitter["basis"]))
    if emitter.get("spin"):
        span = path[-1][0] if path else HORIZON
        spin = xform.AddRotateYOp(opSuffix="spin")
        spin.Set(0.0, 0.0)
        spin.Set(math.degrees(float(emitter["spin"]) * span), span * RATE)


def write_emitter(stage, root, emitter, out, interiors=None):
    """One emitter: its schema prim and its baked points, played from their clip; the particles it holds. One `on` a
    prim of the base is that prim's child, the prims over it left as the base's."""
    path = emitter_path(stage, root, emitter)
    xform = UsdGeom.Xform.Define(stage, path)
    stood(xform, emitter)
    for name, (kind, read) in SCHEMA.items():
        xform.GetPrim().CreateAttribute(f"score:effect:{name}", kind).Set(read(emitter))
    clip, samples = write_clip(emitter, out, interiors)
    grains = UsdGeom.Points.Define(stage, f"{path}/{emitter['name']}_points")
    prim = grains.GetPrim()
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("effect")
    prim.CreateAttribute("score:effect:look", Sdf.ValueTypeNames.Token).Set(emitter["look"])
    UsdGeom.PrimvarsAPI(grains).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray,
                                              UsdGeom.Tokens.constant).Set(Vt.Vec3fArray([Gf.Vec3f(*look_colour(
                                                  emitter))]))
    UsdGeom.PrimvarsAPI(grains).CreatePrimvar("displayOpacity", Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex)
    grains.CreatePointsAttr()
    grains.CreateWidthsAttr()
    grains.SetWidthsInterpolation(UsdGeom.Tokens.vertex)
    clips = Usd.ClipsAPI(prim)
    relative = f"../{ASSETS}/{clip.name}"
    clips.SetClipAssetPaths([Sdf.AssetPath(relative)])
    clips.SetClipPrimPath("/Effect")
    clips.SetClipActive([Gf.Vec2d(0.0, 0.0)])
    clips.SetClipTimes(clip_times(emitter, samples))
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(effect_look(stage, root, emitter))
    return int(emitter["count"])


def emitter_path(stage, root, emitter):
    """Where the emitter is written: under the effects' root, or as the child of the prim it rides on, every prim
    between the place and it an over (the base's)."""
    if not emitter.get("parent"):
        return f"{root}/{emitter['name']}"
    parent = Sdf.Path(root).GetParentPath().AppendPath(emitter["parent"])
    for prefix in parent.GetPrefixes():
        stage.OverridePrim(prefix)
    return str(parent.AppendChild(emitter["name"]))


def write_light(stage, place, light):
    """One of the record's lights: a sphere light on a prim of the base (`on`, at `offset` in its frame), its
    intensity keyed at the record's seconds (Blender's units, as scene.py writes lights)."""
    parent = Sdf.Path(f"/{place}").AppendPath(light["on"])
    for prefix in parent.GetPrefixes():
        stage.OverridePrim(prefix)
    lamp = UsdLux.SphereLight.Define(stage, parent.AppendChild(light["name"]))
    lamp.AddTranslateOp().Set(Gf.Vec3d(*map(float, light.get("offset", (0.0, 0.0, 0.0)))))
    lamp.CreateColorAttr(Gf.Vec3f(*scene_record.colour(light["colour"])))
    lamp.CreateRadiusAttr(float(light.get("radius", 0.5)))
    for seconds, intensity in light["intensity"]:
        lamp.CreateIntensityAttr().Set(float(intensity), float(seconds) * RATE)
    prim = lamp.GetPrim()
    prim.CreateAttribute("score:game:shadows", Sdf.ValueTypeNames.Bool).Set(bool(light.get("shadows", True)))
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("effect_light")
    prim.CreateAttribute("score:effect:from", Sdf.ValueTypeNames.String).Set(light["from"])


def variant_target(stage, root, variant):
    """Where an entry of a variant is written: inside that variant of /<place>/Effects's variant set."""
    variant_set = stage.GetPrimAtPath(root).GetVariantSets().AddVariantSet(variant[0])
    variant_set.AddVariant(variant[1])
    variant_set.SetVariantSelection(variant[1])
    return variant_set.GetVariantEditTarget()


def write_layer(place, effects, out, ground=None, scene=None, motions=None):
    """The effects layer of the place's stage under `out`, rewritten whole; how many particles each emitter holds.
    `motions` is the place's motion record (data/motion), which a following emitter reads."""
    effects = timed(effects, motions)
    if scene:
        scene_record.refuse_rejected(scene, [entry["name"] for entry in effects["effects"]], "the effects record")
    out = pathlib.Path(out)
    path = out / LAYER
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.FindOrOpen(str(path)) or Sdf.Layer.CreateNew(str(path))
    layer.Clear()
    layer.documentation = NOTE
    layer.timeCodesPerSecond = RATE
    layer.framesPerSecond = RATE
    stage = Usd.Stage.Open(layer)
    root = f"/{place}/Effects"
    UsdGeom.Scope.Define(stage, root)
    layer.GetPrimAtPath(f"/{place}").specifier = Sdf.SpecifierOver  # the place itself is the base's
    for replaced in effects.get("replaces", []):
        stage.OverridePrim(f"/{place}/{replaced['prim']}").SetActive(False)
    held = {}
    for emitter in emitters_of(effects, ground, scene, motions):
        if emitter.get("variant"):
            with Usd.EditContext(stage, variant_target(stage, root, emitter["variant"])):
                held[emitter["name"]] = write_emitter(stage, root, emitter, out, effects.get("interiors"))
        else:
            held[emitter["name"]] = write_emitter(stage, root, emitter, out, effects.get("interiors"))
    for light in effects.get("lights", []):
        write_light(stage, place, light)
    for name, choice in effects.get("variants", {}).items():
        stage.GetPrimAtPath(root).GetVariantSets().GetVariantSet(name).SetVariantSelection(choice)
    layer.Save()
    export.held_by_root(place, out)
    return held


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place")
    parser.add_argument("--stage", required=True, type=pathlib.Path, help="the place's stage folder (export.py --out)")
    parser.add_argument("--record", type=pathlib.Path, help="the effects record, by default data/effects/<place>.json")
    arguments = parser.parse_args()
    effects = record(arguments.place, arguments.record)
    if effects is None:
        raise SystemExit(f"{arguments.place} has no effects record (data/effects/{arguments.place}.json)")
    held = write_layer(arguments.place, effects, arguments.stage, place_ground(arguments.place),
                       scene_record.record(arguments.place), motion_record.record(arguments.place))
    print(json.dumps({"emitters": len(held), "particles": sum(held.values()), "layer": str(arguments.stage / LAYER)}))


if __name__ == "__main__":
    main()
