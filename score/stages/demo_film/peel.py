"""A layer peel (the film script's `body-peel` cut, owner 2026-10-27: "show the layers in the demo, from full player
model with clothes, to mesh, to sim body"): every person of a scene's cast drawn three times on one camera, clothed
(its dressed body posed by the sim body's clip, its rest fitted to the clip rig's bind turned about up), as its bare
SOMA mesh (the clip rig's surface skinned by the same clip) and as its sim body (whatever geometry the sim body layer
holds under the person's SimBody, bones, boxes or muscles, at its own time samples; each touching body's push an
arrow), the
three joined by a wipe rising up the picture at each third of the shot; or, closer, the camera following one walker
(`close_walker`).

A place peel (the script's `place-peel` cut; owner, 2026-11-05: "every scene needs the peel", and asked whether that
meant adding people or peeling the place itself: "2", the place itself) is the same renderer's other job (`place_job`):
a place without people on its scene record's first camera, standing, three ways: `finished` (its finished stage as
its rows made it: the neighbours output, else the assembly, every finish its own library surface), `bare` (the same
models with no finish, one plain clay) and `physics` (the bodies its physics uses, `physics_bodies`: every prim the
stage collides with, `colliders.collides`, as its approximation makes it, from the physics-layer output where the place
has one, its moving bodies apart), joined by the same wipes.

    python -m score.stages.demo_film.peel <job folder> --cast <cast.json> --sim <sim-body output> --rig <rig.npz>
        --dressed <body.glb> [--seconds 5] [--size 1280 720] [--samples 64] [--close [--clips <scene_clips.json>]]
        [--ground <triangles.npy>] [--build <people-body rig.npz>]
    python -m score.stages.demo_film.peel <job folder> --stage <finished stage folder>
        [--physics <physics-layer output>] [--seconds 5] [--size 1280 720] [--samples 64]
    python -m score.stages.demo_film.peel <job folder> --scene <place_build scene folder> --rows <rows.json>
        [--walker <name>] [--size 1280 720] [--review]

A walker peel (walker_job; owner, 2026-11-17: "where is the peel? player model- soma body - sim body with grf arrow")
is a place's whole film in its place_build scene, one continuous shot (owner, 2026-11-18: no hard cuts): the place
drawn and its walkers played as its film draws and plays them, every one already walking, the camera opening on the
concept's view, moving on to one walker (`--walker`, else close_walker's rule) and following it close while it peels
from the player model to its SOMA body to its sim body with its GRF arrows and muscle activation (closing), each
shown for its WALKER_HOLDS (owner, 2026-11-17: "zoom in, 4 sec normal, 4 sec soma, 8 sec skeli"), changing by a short
dissolve; the shot lasts walker_seconds. `--rows` names the rows' output
folders the sim body ran from ({"cast", "sim-body", "people-clips-made", "scene-clips", "people-body-<look>"}); it is
drawn on this machine's card through the card queue (place_build.render.queued) by `blender/walker_peel.py`.

The film's peels are the body-peel and place-peel rows' (`peel_rows.py`): the same jobs (job_of, place_job),
their frames dealt over rented cards (`sliced`) and drawn there by `blender/body_peel.py`, joined here. This command
line draws one in this machine's Blender (tools/blender/session.py's set-up, `-b` on its card), free, for a look
before a batch. Everything but the sim body's own geometry is worked out here in numpy; the Blender side imports that
from its layer, lays it all out and draws it.

Nothing is invented: the clothed pass is the dressed body's own surface and skin on the sim body's clip, the mesh
pass the clip rig's own points and skin weights, the sim pass the sim body's own layer at its time codes (the
record's frames) and its measures' push on each body the ground touches. A shot longer than the record is refused,
never stretched or looped. Each push is the record's own (its `touches`: the ground's push on a body, summed over its
skin points touching a floor, a seat, a bed or a ledge, and its centre of pressure there), an arrow from that centre
along the push, `METRES_PER_BODY_WEIGHT` long for a push of the body's own weight (%BW, the record's `weight N`), so a
walker's arrows read alike on the Moon, Mars and Earth; one of PUSHED or less is not drawn. The arrows are the film's
`--film-push` colour (design/tokens/colours.css), at a fixed width on screen that reads at film distance, their centre
of pressure marked by a dot, and fade in with the sim body (`arrow_fade`).
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from score.stages import demo_film, sim_body
from score.stages.demo_film import lettering

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import camera_paths  # noqa: E402
import colliders  # noqa: E402
BLENDER_SCRIPT = REPO / "score/stages/demo_film/blender/body_peel.py"
WALKER_SCRIPT = REPO / "score/stages/demo_film/blender/walker_peel.py"
# The Blender tools/blender/session.py sets up on this machine (its newest version).
BLENDER = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / \
    "blender-mcp/blender-5.2.2/blender"
PASSES = ("dressed", "mesh", "sim")
PLACE_PASSES = ("finished", "bare", "physics")
NOT_SOLID = ("Sky",)  # the physics layer's own: the sky is drawn, never collided with (tools/usd/physics.py)
RATE = 24
METRES_PER_BODY_WEIGHT = 0.5  # an arrow 0.5 m long is a push of the body's own weight (100 %BW), every walker alike
PUSHED = 1.0  # newtons: a body the ground pushes less than this carries nothing worth an arrow
WIPE_SECONDS = 0.6
FADE_SECONDS = 1.0  # the push arrows' fade in, from the start of the sim body's wipe
WIDE_LENS, CLOSE_LENS = 40.0, 35.0  # mm
CLOSE_METRES = 4.0  # the close-up's camera off its person's path: the whole body in view at CLOSE_LENS
FOLLOW_SECONDS = 0.5  # the close-up's aim smoothed over this either side
HIPS = 0.9  # metres over a person's lowest point a camera aims at: its whole body and the push under its feet in view
# A walker peel in its place (walker_job) is the place's whole film, one continuous shot (owner, 2026-11-18: "the
# cutting and transfers in the films are very weird"): OPENING_SECONDS on the concept's view, then over its approach
# (approach_seconds) the camera moves on from it to CLOSE_METRES off the walker at most (CLOSE_LEAST at least, else no
# room for one; WIDE_METRES the most room it measures) and follows it to the end while each pass shows for its
# WALKER_HOLDS seconds (the player model's after the approach), the passes changing by a DISSOLVE_SECONDS dissolve on
# the same moving shot; TALL_METRES of the walker fill the picture's height at the close-up. The shot starts
# LEAD_SECONDS at least into the records (owner, 2026-11-18: "everyone is standing still while ur starting each
# shot"), so every walker is walking from its first frame; a record too short for the holds shortens them alike
# (walker_holds), to HOLDS_LEAST of them at most.
WIDE_METRES = 9.0
CLOSE_LEAST = 1.6
TALL_METRES = 2.4
OPENING_SECONDS = 1.0
APPROACH_SECONDS = 2.5  # the least: a longer way in takes up to APPROACH_MOST, at APPROACH_SPEED on the whole
APPROACH_MOST = 5.0
APPROACH_SPEED = 9.0  # metres a second from the concept's eye to the walker, straight
THROUGH_EVERY = 12  # the place film's path frames tried as a way in for the camera (approach_route)
THROUGH_WALKED = 3  # of them, the nearest walked from (camera_paths.leg) when the walker is straight from none
AIM_LEADS = 0.7  # the share of the approach the look takes to come round to the walker, ahead of the eye
LEAD_SECONDS = 2.0
DISSOLVE_SECONDS = 0.5
WALKER_HOLDS = {"dressed": 4.0, "mesh": 4.0, "sim": 8.0}  # owner, 2026-11-17: "4 sec normal, 4 sec soma, 8 sec skeli"
HOLDS_LEAST = 0.4
# The GRF arrows a walker peel draws (owner, 2026-11-18: "the grf arrows are way to aggresive and inconsistent", "he
# only has grf arrows going for his right leg"): one a foot, its every body the record's `feet` names on that side
# (heel and toes), whenever it touches; the drawn force (never the solve's) rid of single-frame spikes by a median
# over MEDIAN_SECONDS and low-passed by a gaussian whose half-power cut is LOW_PASS_HZ, its centre of pressure the
# force-weighted mean, so an arrow grows from and shrinks to nothing as the foot lands and lifts.
MEDIAN_SECONDS = 0.1
LOW_PASS_HZ = 4.0
SIDES = ("Left", "Right")
SHOWN_FROM = 0.1  # of the body's weight: an arrow under it shrinks its head and dot with it (body_peel.arrow_at)
# The muscles' activation in the sim body pass (owner, 2026-11-18: "its really hard to see the muscle activation"):
# each muscle a MUSCLE_RADIUS thick line in the film's activation colours (--film-activation-0 to -3, 0 to 1), lit
# from within MUSCLE_GLOW, a colour bar beside it (`activation_bar`).
MUSCLE_RADIUS = 0.005
MUSCLE_GLOW = 2.0
ACTIVATION_TOKENS = ("film-activation-0", "film-activation-1", "film-activation-2", "film-activation-3")
HEADINGS = 12  # the ways round the walker tried for the camera, straight ahead of it first
# Where no one way round a walker keeps CLOSE_LEAST clear over the whole close-up (a walker through a doorway and up a
# turning stair), the close-up's eye comes round with it (`turning`): of TURN_HEADINGS ways round at RISES and
# TURN_METRES off, at most TURN_STEPS headings and rises between measured frames, each step costing TURN_COST metres.
TURN_HEADINGS = 24
TURN_METRES = (4.0, 3.2, 2.4, 1.6)
TURN_STEPS = 1
TURN_COST = 0.5
TURN_SMOOTH = 0.5  # seconds either side its eye's corners are rounded over
# A close-up looks at the place behind its walker (owner's fault, 2026-11-17: the street peel faced the plaza's flat
# backdrop): a way whose look past the walker, level at BACKED_HEIGHT over its hips, straight on and BACKED_SPREAD
# degrees to either side (the picture's middle and its sides), meets the place within BACKED_METRES on every measured
# frame is taken before one that looks out past the place's edge into the empty sky.
BACKED_HEIGHT = 0.8
BACKED_SPREAD = 30.0
BACKED_METRES = 40.0
FACING = 60.0  # degrees off the way a walker walks the camera looks from first, room alike: its gait and its face
RISES = (0.12, 0.3)  # radians: the camera's rise over the hips, the lower first
# degrees across: the widest lens a close-up in a narrow place takes; at TURN_METRES' nearest it frames over 2.1 m, the
# walker's feet and the push under them in view (rf3-stairwell, 2026-11-18: at 85 the woman's sim body on the top
# landing showed from the knees up, her GRF arrows out of the picture)
FOV_MOST = 100.0
EVERY = 4  # the frames between those the camera's room is measured on (rays and sweeps)
OWN_ROOM = 0.5  # metres out of the hips a sight line is swept from: the walker's own body and what it walks by
SIGHT = 0.05  # metres: a sight line's own radius, kept clear of the place
EDGE = (255, 196, 64)  # the wipe's edge line
LEVEL = 0.7  # a ground triangle's normal against up (cosine): floors, treads, seats and beds, never a wall
# The person's own frame is Y up (OpenUSD); Blender's is Z up: x stays, y becomes z, z becomes -y.
Y_TO_Z = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]])


def clip_worlds(rig, clip):
    """Every rig joint's frame in the person's frame, frame by frame (frames x joints x 4 x 4)."""
    local = np.asarray(rig[f"clip_{clip}"], dtype=float)
    world = np.empty_like(local)
    for joint, parent in enumerate(rig["parents"]):
        world[:, joint] = local[:, joint] if parent < 0 else world[:, parent] @ local[:, joint]
    return world


def skinned(rig, clip):
    """The rig's surface skinned by its clip (frames x points x 3, the person's frame): each point carried by its
    joints' moves from their bind frames, weighed by its skin weights."""
    moves = clip_worlds(rig, clip) @ np.linalg.inv(np.asarray(rig["bind"], dtype=float))
    points = np.concatenate([rig["points"], np.ones((len(rig["points"]), 1))], axis=1)
    blended = np.einsum("pj,fjab->fpab", np.asarray(rig["weights"], dtype=float), moves)
    return np.einsum("fpab,pb->fpa", blended, points)[..., :3]


def sim_root(place, name):
    """Where a person's sim body sits in the sim body layer (score/stages/sim_body: whatever geometry it holds)."""
    return f"/{place}/Characters/{name}/SimBody"


def touching(frames):
    """The bodies the ground pushes more than PUSHED on any of the record's frames (its `touches`: feet, a seat under
    the thighs, a bed under the back), in their first frame's order; refused for a record written before it held
    them."""
    if any("touches" not in frame for frame in frames):
        raise ValueError("the sim body record holds no `touches`: its sim body was run before they were written; run "
                         "it again")
    found = {}
    for frame in frames:
        for body, push in frame["touches"].items():
            if np.linalg.norm(push[:3]) > PUSHED:
                found.setdefault(body, None)
    return list(found)


def body_weight(body):
    """A sim body's weight in newtons (its record's measures, `weight N`: its mass at its place's gravity); refused for
    a record written without it."""
    weight = body.get("measures", {}).get("weight N")
    if not weight:
        raise ValueError("the sim body record holds no `weight N`: its arrows have no body weight to be scaled by")
    return float(weight)


def pushes(frames, bodies, weight):
    """Each touching body's push from the ground each record frame as an arrow (frames x bodies x 6: start, vector;
    NaN where the ground pushes it PUSHED or less): from its centre of pressure on the ground along the push,
    METRES_PER_BODY_WEIGHT for a push of `weight` newtons, the body's own (%BW; the record's `touches`, the person's
    frame)."""
    arrows = np.full((len(frames), len(bodies), 6), np.nan)
    for index, frame in enumerate(frames):
        for number, body in enumerate(bodies):
            if body not in frame["touches"]:
                continue
            force, centre = np.asarray(frame["touches"][body][:3]), np.asarray(frame["touches"][body][3:])
            if np.linalg.norm(force) > PUSHED:
                arrows[index, number] = [*centre, *(force / weight * METRES_PER_BODY_WEIGHT)]
    return arrows


def arrow_fade(count, ends=None, seconds=WIPE_SECONDS):
    """How far the push arrows have faded in at each film frame of `count` (0 to 1): from the start of the wipe (or
    dissolve, `seconds` long) that brings the sim body in (at the last of `ends`, pass_ends'), over FADE_SECONDS, so
    they come in with its layer."""
    begins = pass_ends(count, ends)[-1] - seconds * RATE / 2
    return np.clip((np.arange(count) - begins) / (FADE_SECONDS * RATE), 0.0, 1.0).tolist()


def linear(name):
    """A colour token of the film's (lettering.token) as Blender's linear RGB."""
    srgb = np.array(lettering.token(name)[:3]) / 255.0
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4).tolist()


def push_colour():
    """The push arrows' colour, the film's own `--film-push` token, as Blender's linear RGB."""
    return linear("film-push")


def muscle_look():
    """How the sim body pass draws its muscles: the sim body layer's own colour ends (a muscle's colour runs from
    RESTING at activation 0 to ACTIVE at 1, sim_body/_layer.py, so Blender reads its activation back from the red),
    the film's activation colours (linear RGB, 0 to 1 evenly), the line's radius and its glow."""
    from score.stages.sim_body import _layer
    return {"resting": list(_layer.RESTING), "active": list(_layer.ACTIVE),
            "colours": [linear(name) for name in ACTIVATION_TOKENS], "radius": MUSCLE_RADIUS, "glow": MUSCLE_GLOW}


def despiked(values, width):
    """`values` (frames x ...) each the median of the `width` frames round it (an odd count; the ends held)."""
    reach = width // 2
    padded = np.concatenate([np.repeat(values[:1], reach, axis=0), values, np.repeat(values[-1:], reach, axis=0)])
    return np.median(np.lib.stride_tricks.sliding_window_view(padded, width, axis=0), axis=-1)


def foot_pushes(frames, weight, rate, segments=()):
    """Each foot's push from the ground each record frame as an arrow (frames x SIDES x 6: start, vector; the person's
    frame, Y up), for drawing: the force on every body the record's `feet` names on that side summed (its `touches`),
    despiked (a median over MEDIAN_SECONDS) and low-passed (a gaussian of LOW_PASS_HZ half power) at the record's
    `rate`, METRES_PER_BODY_WEIGHT for a push of `weight` newtons; from its centre of pressure, the push-weighted mean
    of its bodies' own, smoothed alike (a foot in the air keeps its last one, its push nought). A touch whose centre
    the record holds as NaN (a skin point the solve pushed with no ground found under it: street's walkers on the
    pavement, 2026-11-18 records) stands under its own segment's pose (`segments`, the record body's segment names
    in its frames' `poses` order) at the ground's height of the last centre known, and with no pose places nothing:
    a NaN never blanks a foot's arrows for the whole film."""
    from score.stages.place_build.film import smoothed
    feet = {body for frame in frames for body in frame.get("feet", {})}
    force, moment, load = (np.zeros((len(frames), len(SIDES), 3)), np.zeros((len(frames), len(SIDES), 3)),
                           np.zeros((len(frames), len(SIDES))))
    named, level = list(segments), next((float(push[4]) for frame in frames for push in frame["touches"].values()
                                         if np.isfinite(push[3:]).all()), 0.0)
    for index, frame in enumerate(frames):
        for body, push in frame["touches"].items():
            side = next((number for number, name in enumerate(SIDES) if body.startswith(name)), None)
            if body not in feet or side is None:
                continue  # a hand on a rail, a hip on a wall: not the ground's push on a foot
            force[index, side] += push[:3]
            centre = np.asarray(push[3:], dtype=float)
            if np.isfinite(centre).all():
                level = float(centre[1])
            elif body in named and "poses" in frame:
                centre = np.asarray(frame["poses"][named.index(body)][:3], dtype=float)
                centre[1] = level  # under its segment, on the ground the last centre stood on
            else:
                continue  # no centre and no pose: its force counts, it places nothing
            pressed = max(float(push[1]), 0.0)
            moment[index, side] += centre * pressed
            load[index, side] += pressed
    width = max(3, 2 * round(MEDIAN_SECONDS * rate / 2) + 1)
    spread = np.sqrt(np.log(2.0)) / (2.0 * np.pi * LOW_PASS_HZ) * rate
    force = smoothed(despiked(force, width).reshape(len(frames), -1), spread).reshape(force.shape)
    load = smoothed(despiked(load, width), spread)
    moment = smoothed(despiked(moment, width).reshape(len(frames), -1), spread).reshape(moment.shape)
    arrows = np.zeros((len(frames), len(SIDES), 6))
    for side in range(len(SIDES)):
        pressed = load[:, side] > 1e-6
        if not pressed.any():
            continue
        kept = np.flatnonzero(pressed)
        nearest = kept[np.clip(np.searchsorted(kept, np.arange(len(frames))), 0, len(kept) - 1)]
        held = np.maximum.accumulate(np.where(pressed, np.arange(len(frames)), -1))
        nearest = np.where(held >= 0, held, nearest)
        arrows[:, side, :3] = (moment[nearest, side] / load[nearest, side, None])
        arrows[:, side, 3:] = force[:, side] / weight * METRES_PER_BODY_WEIGHT
    return arrows


def to_z(matrices):
    """Matrices of the place (Y up) in Blender's frame (Z up)."""
    return Y_TO_Z @ matrices @ Y_TO_Z.T


def points_to_z(points):
    return points @ Y_TO_Z[:3, :3].T


def source_frames(seconds, record_rate, record_frames):
    """The record frame each film frame shows (nearest); refused when the shot outlasts the record."""
    count = round(seconds * RATE)
    found = [round(frame * record_rate / RATE) for frame in range(count)]
    if found[-1] >= record_frames:
        raise ValueError(f"a {seconds:g} s shot outlasts the sim body record's {record_frames / record_rate:g} s")
    return found


def person_arrays(record, rig, frames, shown):
    """One person's arrays for Blender, every one in the place and Z up, at the film's frames `shown`: its bare
    mesh's points and its touching bodies' push arrows; and, in its own frame, each rig joint's move from its bind frame (which
    poses its dressed body) and the bind frames' places (which the dressed body's rest is fitted to). The sim body
    itself is the layer's, drawn by Blender at the same frames (its time codes)."""
    where = sim_body.own_frame(record["at"], record.get("turn", 0.0))
    mesh = skinned(rig, record["clip"]) @ where[:3, :3].T + where[:3, 3]
    arrows = pushes(frames, touching(frames), body_weight(record))
    starts = arrows[..., :3] @ where[:3, :3].T + where[:3, 3]
    vectors = arrows[..., 3:] @ where[:3, :3].T
    moves = clip_worlds(rig, record["clip"]) @ np.linalg.inv(np.asarray(rig["bind"], dtype=float))
    return {"points": points_to_z(mesh[shown]), "moves": to_z(moves[shown]),
            "bind_heads": points_to_z(np.asarray(rig["bind"], dtype=float)[:, :3, 3]),
            "arrow_start": points_to_z(starts[shown]), "arrow_vector": points_to_z(vectors[shown]),
            "placed": to_z(where)}


def framing(people, count):
    """The wide shot: one still camera a film frame (Z up), aimed at the middle of every person's mesh over the
    shot, back far enough for all of them, a little above, from the front of the first person's spot (the clip rig's
    people face +z, Y up)."""
    every = np.concatenate([person["points"].reshape(-1, 3) for person in people])
    low, high = every.min(axis=0), every.max(axis=0)
    aim = (low + high) / 2
    spread = max(np.linalg.norm(high[:2] - low[:2]), high[2] - low[2], 1.0)
    facing = people[0]["placed"][:3, :3] @ np.array([0.0, -1.0, 0.0])  # +z of Y up is -y of Z up
    away = facing + np.array([0.6 * facing[1], -0.6 * facing[0], 0.0])
    away = away / np.linalg.norm(away)
    eye = aim + away * spread * 1.6 + np.array([0.0, 0.0, 0.35 * spread])
    return [{"eye": eye.tolist(), "aim": aim.tolist()}] * count


def hips_path(points, up=2):
    """A person's hips over a shot (frames x 3) from its mesh's points (frames x points x 3, `up` the up axis): its
    middle at HIPS over its lowest point, smoothed over FOLLOW_SECONDS either side so a camera on it glides rather than
    bobs."""
    middles = points.mean(axis=1)
    middles[:, up] = points[:, :, up].min(axis=1) + HIPS
    width = max(1, round(FOLLOW_SECONDS * RATE))
    padded = np.concatenate([np.repeat(middles[:1], width, axis=0), middles, np.repeat(middles[-1:], width, axis=0)])
    kernel = np.ones(2 * width + 1) / (2 * width + 1)
    return np.column_stack([np.convolve(padded[:, axis], kernel, mode="same")[width:-width] for axis in range(3)])


def following(person):
    """The close-up: a camera a film frame (Z up) CLOSE_METRES off one person's path to its side and a little ahead,
    aimed at its hips (its whole body, its feet and the push under them in view), the aim smoothed (hips_path)."""
    smooth = hips_path(person["points"])
    travel = smooth[-1] - smooth[0]
    travel[2] = 0.0
    if np.linalg.norm(travel) < 0.5:  # not walking anywhere: its front is the way to look from
        travel = np.cross(person["placed"][:3, :3] @ np.array([0.0, -1.0, 0.0]), [0.0, 0.0, 1.0])
    travel = travel / np.linalg.norm(travel)
    side = np.cross([0.0, 0.0, 1.0], travel) + 0.35 * travel
    side = side / np.linalg.norm(side)
    return [{"eye": (aim + side * CLOSE_METRES + np.array([0.0, 0.0, 0.25])).tolist(), "aim": aim.tolist()}
            for aim in smooth]


def close_walker(cast, clips=None):
    """The walker a close-up follows, by rule: of the cast's walkers, the one whose scene-made clip crosses the most
    uneven ground (`clips`: scene-clips' scene_clips.json, each walker's `relief`), the cast's first on a tie;
    refused with no walker, or with more than one and no record to tell them apart."""
    walkers = [single["name"] for single in cast["characters"] if single.get("doing") == "walking"]
    if not walkers:
        raise ValueError(f"{cast['place']}: no walker in the cast to follow")
    if clips is None:
        if len(walkers) > 1:
            raise ValueError(f"{cast['place']}: {len(walkers)} walkers and no scene-made clips to tell their ground")
        return walkers[0]
    relief = {plan["name"]: plan["relief"] for plan in clips["clips"]}
    return max(walkers, key=lambda name: (relief.get(name, -1.0), -walkers.index(name)))


def job_of(folder, cast, sim, person_of, seconds, size, samples, close=None, ground=None):
    """Write the Blender job (job.json and one npz a person) into `folder` and return its path: the wide shot of
    everyone, or, `close` naming one of them, the close-up following that person alone (no one else between it and
    the camera). `person_of(single, body)`: a cast person and its sim body record's entry give (its rig at its own
    build, sim_body.person_rig, holding the clip it played; its dressed body's .glb; that clip's name), or None for
    one left out as an accepted gap. `ground`: the
    scene's ground under them (n x 3 x 3 triangles, the place's frame, Y up; else a flat floor at 0), drawn where it
    is underfoot (`underfoot`)."""
    record = json.loads((sim / "sim_bodies.json").read_text())
    people, shown, shapes = [], None, {}
    for single in cast["characters"]:
        name = single["name"]
        if name not in record["bodies"] or close not in (None, name):
            continue  # the sim body stage left it out and said why in its record, or the close-up follows another
        found = person_of(single, record["bodies"][name])
        if found is None:
            continue  # an accepted gap: no body of its look (peel_rows.people_of)
        rig, dressed, clip = found
        frames = json.loads((sim / "measures" / f"{name}.json").read_text())
        shown = source_frames(seconds, record["rate"], len(frames))
        layer, root = sim / sim_body.LAYER, sim_root(record["place"], name)
        arrays = person_arrays(dict(record["bodies"][name], clip=clip), rig, frames, shown)
        np.savez(folder / f"{name}.npz", faces=np.asarray(rig["faces"]), **arrays)
        people.append({"name": name, "glb": str(dressed), "clip": clip,
                       "joints": [str(joint) for joint in rig["names"]], "sim_layer": str(layer), "sim_root": root,
                       "arrays": str(folder / f"{name}.npz"), "placed": arrays["placed"].tolist()})
        shapes[name] = {"points": arrays["points"], "placed": arrays["placed"]}
    if not people:
        raise ValueError(f"{sim}: no sim body of the cast to peel")
    if close is not None and close not in shapes:
        raise ValueError(f"{sim}: no sim body of {close} to follow")
    path = following(shapes[close]) if close else framing(list(shapes.values()), len(shown))
    job = {"out": str(folder), "size": list(size), "samples": samples, "record_rate": record["rate"],
           "source": shown, "passes": list(PASSES), "camera": {"lens": CLOSE_LENS if close else WIDE_LENS,
                                                                "path": path},
           "arrows": {"colour": push_colour(), "fade": arrow_fade(len(shown))}, "muscles": muscle_look(),
           "people": people, "ground": None}
    if ground is not None:
        np.save(folder / "ground.npy", underfoot(points_to_z(np.asarray(ground, dtype=float)), list(shapes.values())))
        job["ground"] = str(folder / "ground.npy")
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    return folder / "job.json"


def approach_seconds(metres):
    """How long the camera takes from the concept's eye to a walker `metres` from it: APPROACH_SPEED on the whole,
    between APPROACH_SECONDS and APPROACH_MOST."""
    return float(np.clip(metres / APPROACH_SPEED, APPROACH_SECONDS, APPROACH_MOST))


def approach(count, seconds=APPROACH_SECONDS):
    """How far the camera has come from the concept's view to its close-up at each frame of `count` (0 to 1): still
    for OPENING_SECONDS, then over its approach `seconds` eased in and out (smootherstep, its speed and its change
    nought at both ends), then on the close-up to the end; (its eye's share, its look's share, the look coming round
    to the walker over AIM_LEADS of the approach, ahead of the eye)."""
    into = np.clip((np.arange(count) / RATE - OPENING_SECONDS) / seconds, 0.0, 1.0)
    looked = np.clip(into / AIM_LEADS, 0.0, 1.0)
    return tuple(share ** 3 * (share * (share * 6.0 - 15.0) + 10.0) for share in (into, looked))


def turned_looks(start, ends, shares):
    """Unit looks (Y up) from the look `start` round to each of `ends` by its share: its heading turned the shorter way
    round the vertical and its pitch eased alone, so a look coming round to a walker behind it pans across the place,
    never tips through the ground under the camera (rf5 street, 2026-11-18: the straight blend of two near-opposite
    looks pointed the camera at its own feet halfway round)."""
    start, ends = np.asarray(start, dtype=float), np.asarray(ends, dtype=float)
    heading = np.arctan2(start[0], start[2])
    headings = np.arctan2(ends[:, 0], ends[:, 2])
    pitch = np.arcsin(np.clip(start[1], -1.0, 1.0))
    pitches = np.arcsin(np.clip(ends[:, 1], -1.0, 1.0))
    turns = (headings - heading + np.pi) % (2.0 * np.pi) - np.pi
    shares = np.asarray(shares, dtype=float)
    now, lean = heading + turns * shares, pitch + (pitches - pitch) * shares
    return np.stack([np.cos(lean) * np.sin(now), np.sin(lean), np.cos(lean) * np.cos(now)], axis=1)


def ways_round(aims, headings=HEADINGS):
    """The ways a camera may look at a walker from (unit vectors, Y up), each with how many `headings` steps it turns
    from the three-quarter front (FACING degrees off the way it walks): every heading from straight ahead round, at
    every rise of RISES, so along a corridor and square to the walker are among them."""
    travel = aims[-1] - aims[0]
    travel[1] = 0.0
    travel = travel / np.linalg.norm(travel) if np.linalg.norm(travel) > 0.5 else np.array([0.0, 0.0, 1.0])
    side = np.cross(travel, [0.0, 1.0, 0.0])
    found = []
    for step in range(headings):
        turn = 2.0 * np.pi * step / headings
        flat = np.cos(turn) * travel + np.sin(turn) * side
        off = abs((np.degrees(turn) - FACING + 180.0) % 360.0 - 180.0) / (360.0 / headings)
        found += [(np.cos(rise) * flat + np.array([0.0, np.sin(rise), 0.0]), round(off)) for rise in RISES]
    return found


def sighted(scenes, aims, eyes, seen_from=0):
    """Whether the camera moves clear and sees the walker: its eye's way between measured frames (each EVERYth and
    the last) CLEARANCE off the place's solids, and from frame `seen_from` on its sight line from OWN_ROOM out of the
    hips towards it SIGHT clear (camera_paths.swept_clear; never clearances, whose inside_solid counts a closed dome's
    inside as solid)."""
    measured = sorted({*range(0, len(aims), EVERY), len(aims) - 1})
    if not all(camera_paths.swept_clear(scenes["solid"], eyes[frame], eyes[after], camera_paths.CLEARANCE)
               for frame, after in zip(measured, measured[1:] or measured)):
        return False
    for frame in measured:
        if frame < seen_from:
            continue
        towards = (eyes[frame] - aims[frame]) / max(np.linalg.norm(eyes[frame] - aims[frame]), 1e-9)
        if not camera_paths.swept_clear(scenes["solid"], aims[frame] + towards * OWN_ROOM, eyes[frame], SIGHT):
            return False
    return True


def approach_route(scenes, opened, goal, through=None):
    """A clear way for the camera from the concept's eye `opened` to `goal` (Y up), its corners rounded where they
    stay clear (place_build.film.rounded): straight, or over the goal and down (place_build.film.straight); else
    along `through` (the place film's own clear path from the concept's eye, its eyes in order) to the nearest of its
    eyes (each THROUGH_EVERY) the goal is straight from, or from the nearest THROUGH_WALKED of them down to the goal's
    height over the floor and walked from there (camera_paths.leg); None where none is."""
    from score.stages.place_build import film as place_film
    found = place_film.straight(scenes, opened, goal)
    if found is None and through is not None and len(through):
        through = np.asarray(through, dtype=float)
        tried = [index for index in np.argsort(np.linalg.norm(through - goal, axis=1)) if index % THROUGH_EVERY == 0]
        for index in tried:
            if camera_paths.swept_clear(scenes["solid"], through[index], goal, camera_paths.CLEARANCE):
                found = [opened, *through[:index + 1], goal]
                break
        over = goal[1] - camera_paths.eyes_over(scenes, [[goal[0], goal[2]]], 0.0, [goal[1]])[0][1]
        bounds = np.asarray(scenes["extent"]) + [-place_film.MARGIN, -place_film.MARGIN, place_film.MARGIN,
                                                 place_film.MARGIN]
        for index in tried[:THROUGH_WALKED] if found is None and np.isfinite(over) else ():
            low = camera_paths.eyes_over(scenes, [[through[index][0], through[index][2]]], over,
                                         [through[index][1]])[0]
            if not (np.isfinite(low[1]) and camera_paths.swept_clear(scenes["solid"], through[index], low,
                                                                      camera_paths.CLEARANCE)):
                continue
            walked = camera_paths.leg(scenes, low, goal, bounds, 0, over, camera_paths.CLEARANCE)
            if walked is not None:
                found = [opened, *through[:index + 1], low, *walked[1:]]
                break
    if found is None:
        return None
    found = [found[0], *(point for previous, point in zip(found, found[1:])
                         if np.linalg.norm(np.subtract(point, previous)) > 1e-6)]
    return place_film.rounded(scenes, found)[0]


def kept_off(eyes, hips, least):
    """The eyes (Y up) on their way in, each pushed out along its line from the walker's hips to at least `least`
    metres (its close-up's distance, one or a frame each) from them, so a way in past the walker arcs round it at the
    close-up's distance and never brushes its head (rf5 street, 2026-11-18: the straight way in from the concept's eye
    to the close-up in front of the walker crossed 1.4 m over his head)."""
    off = eyes - hips
    apart = np.maximum(np.linalg.norm(off, axis=1), 1e-9)
    return hips + off * (np.maximum(apart, least) / apart)[:, None]


def along(route, shares):
    """The points `shares` (0 to 1) of the way along a polyline."""
    lengths = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(route, axis=0), axis=1))])
    return np.column_stack([np.interp(shares * lengths[-1], lengths, route[:, axis]) for axis in range(3)])


def turning(scenes, aims, measured):
    """A close-up whose eye comes round its walker with it, where no one way keeps CLOSE_LEAST clear over the whole
    shot: at each measured frame (`measured`, indexes into `aims`, the hips a frame) an eye on one of ways_round
    (TURN_HEADINGS of them) at one of TURN_METRES, within the room on its ray from the hips (as closing's), CLEARANCE
    clear of the place with its sight line to the walker SIGHT clear (as `sighted` asks), each the next one's way at most TURN_STEPS headings and rises round and the move
    between them clear; of those runs, the one nearest CLOSE_METRES on the whole, less TURN_COST metres a step turned and
    the metres it closes in or backs off, then nearest the three-quarter front. Each frame's offset of its eye from its
    hips (frames x 3), between measured frames along the move; None where no run is."""
    found = ways_round(aims, TURN_HEADINGS)
    ways = np.array([way for way, _ in found])
    turned = np.array([off for _, off in found], dtype=float)
    states = [(way, metres) for way in range(len(ways)) for metres in TURN_METRES]
    index = np.arange(len(found))
    heading, rise = index // len(RISES), index % len(RISES)
    offsets = np.array([ways[way] * metres for way, metres in states])
    spots = [aims[frame] + offsets for frame in measured]
    room = (camera_paths.first_hits(scenes["blocking"], np.repeat(aims[measured], len(ways), axis=0),
                                    np.tile(ways, (len(measured), 1))).reshape(len(measured), len(ways))
            - camera_paths.CLEARANCE)  # on the ray from the hips, as closing's room: nothing of the place between

    def seen(frame, state):
        way, metres = states[state]
        eye = spots[frame][state]
        return (room[frame, way] >= metres and camera_paths.swept_clear(scenes["solid"], eye, eye, camera_paths.CLEARANCE) and
                camera_paths.swept_clear(scenes["solid"], aims[measured[frame]] + ways[way] * OWN_ROOM, eye, SIGHT))

    apart = np.abs(heading[:, None] - heading[None, :])
    apart = np.minimum(apart, TURN_HEADINGS - apart) + np.abs(rise[:, None] - rise[None, :])
    near = np.array([[apart[one, other] <= TURN_STEPS and abs(TURN_METRES.index(here) - TURN_METRES.index(there)) <= 1
                      for other, there in states] for one, here in states])
    cost = np.array([[TURN_COST * apart[one, other] + abs(here - there) for other, there in states]
                     for one, here in states])
    gain = np.array([CLOSE_METRES - abs(CLOSE_METRES - metres) - 1e-3 * turned[way] for way, metres in states])
    best = np.where([seen(0, state) for state in range(len(states))], gain, -np.inf)
    came = []
    for frame in range(1, len(measured)):
        open_now = np.array([seen(frame, state) for state in range(len(states))])
        scores = np.full((len(states), len(states)), -np.inf)
        for one in np.flatnonzero(np.isfinite(best)):
            for other in np.flatnonzero(near[one] & open_now):
                if camera_paths.swept_clear(scenes["solid"], spots[frame - 1][one], spots[frame][other],
                                            camera_paths.CLEARANCE):
                    scores[one, other] = best[one] - cost[one, other]
        came.append(np.argmax(scores, axis=0))
        best = scores.max(axis=0) + gain
        if not np.isfinite(best).any():
            return None
    chosen = [int(np.argmax(best))]
    for back in reversed(came):
        chosen.append(int(back[chosen[-1]]))
    picked = offsets[chosen[::-1]]
    frames = np.arange(len(aims))
    moved = np.column_stack([np.interp(frames, measured, picked[:, axis]) for axis in range(3)])
    width = max(1, round(TURN_SMOOTH * RATE))
    padded = np.concatenate([np.repeat(moved[:1], width, axis=0), moved, np.repeat(moved[-1:], width, axis=0)])
    kernel = np.ones(2 * width + 1) / (2 * width + 1)
    eased = np.column_stack([np.convolve(padded[:, axis], kernel, mode="same")[width:-width] for axis in range(3)])
    eyes = aims[measured] + eased[measured]
    kept = all(camera_paths.swept_clear(scenes["solid"], eye, after, camera_paths.CLEARANCE) and
               camera_paths.swept_clear(scenes["solid"], hips + (eye - hips) / np.linalg.norm(eye - hips) * OWN_ROOM,
                                        eye, SIGHT)
               for hips, eye, after in zip(aims[measured], eyes, [*eyes[1:], eyes[-1]]))
    return eased if kept else moved  # its corners rounded over TURN_SMOOTH where that stays clear


def closing(points, scenes, count, size, view, lead=0, through=None, seconds=APPROACH_SECONDS):
    """A walker peel's start and camera, a view a film frame in the place's frame (Y up), from the walker's mesh over
    its whole record at the film's rate (`points`): of the starts each second into the record from `lead` frames on
    that leave the shot's `count` frames, and the ways round it (ways_round), the one with most room for the close-up
    (measured from the camera's arrival on; before it the camera is on its way in, its moves checked by sighted),
    then for the zoom, then nearest its three-quarter front, then earliest, that has a clear way in (approach_route,
    `through` the place film's own path) and whose camera moves clear and sees the walker from halfway through its
    approach on (sighted), a way with the place behind the walker (`backed`) before any that looks past it into the
    empty sky. The camera opens on `view` (the concept's: eye, aim, fov) and comes on from it along that way
    (approach, over `seconds`) to its follow, on its ray from the walker's hips (hips_path), never past the place's meshes on that ray
    less CLEARANCE (camera_paths' `blocking`), so nothing of the place stands between it and the walker, looking round
    from the view's look to the walker; its angle from the view's to the one framing TALL_METRES at the close-up.
    Where no camera has a clear way in (a walker under glass the concept sees from outside), the best one with room
    comes in from the most room it has to its close-up over the approach instead, the film dissolving to it from the
    concept's view (walker_job's `cut_in`). Where no one way leaves CLOSE_LEAST (a walker in through a doorway and up a
    turning stair), the close-up's eye comes round with the walker (`turning`), in from the concept's view as above,
    the walker seen from the camera's arrival on (one may walk in through a doorway as it arrives); where that turning
    close-up has no clear way in either (camp's tunnel astronaut at Earth's pace, 2026-11-19: through a glass tunnel
    and round into a dome the concept sees from outside), the film dissolves to it from the concept's view, the walker
    seen and its eye coming round with it from the dissolve's start on. (the start, the views, whether the camera came
    in from the concept's view); refused where no start and way leave CLOSE_LEAST."""
    path = hips_path(points, up=1)
    eye_share, look_share = approach(count, seconds)
    seen_from = int(np.searchsorted(eye_share, 0.5))
    arrived = min(int(np.searchsorted(eye_share, 1.0)), count - 1)
    opened = np.asarray(view["eye"], dtype=float)
    opening_look = np.asarray(view["aim"], dtype=float) - opened
    reach = float(np.linalg.norm(opening_look))
    opening_look = opening_look / max(reach, 1e-9)

    def came_in(eyes, aims, fovs):  # the views coming in from the concept's: its angle and look on to the close-up's
        apart = np.linalg.norm(aims - eyes, axis=1)
        towards = (aims - eyes) / np.maximum(apart, 1e-9)[:, None]
        looks = turned_looks(opening_look, towards, look_share)
        looked = (reach + (apart - reach) * eye_share)[:, None] * looks + eyes
        return viewed(eyes, looked, float(view["fov"]) + (fovs - float(view["fov"])) * eye_share)

    tried = []
    for start in range(lead, len(points) - count + 1, RATE):
        aims = path[start:start + count]
        measured = aims[sorted({*range(arrived, count, EVERY), count - 1})]  # the close-up's frames
        for way, turned in ways_round(aims):
            free = camera_paths.first_hits(scenes["blocking"], measured, np.tile(way, (len(measured), 1)))
            room = min(float(free.min()) - camera_paths.CLEARANCE, WIDE_METRES)
            tried.append((min(room, CLOSE_METRES), room, turned, start, way, backed(scenes, measured, way)))
    tried = sorted((kept for kept in tried if kept[0] >= CLOSE_LEAST),
                   key=lambda kept: (not kept[5], -kept[0], -kept[1], kept[2], kept[3]))
    for close, room, _, start, way, _ in tried:
        aims = path[start:start + count]
        followed = aims + close * way
        route = approach_route(scenes, opened, followed[arrived], through)
        if route is None:
            continue
        eyes = kept_off(along(route, eye_share) + eye_share[:, None] * (followed - followed[arrived]), aims, close)
        if sighted(scenes, aims, eyes, seen_from):
            return start, came_in(eyes, aims, np.full(count, close_fov(close, size))), True
    for close, room, _, start, way, _ in tried:
        aims = path[start:start + count]
        eyes = aims + (room + (close - room) * eye_share)[:, None] * way
        if sighted(scenes, aims, eyes):
            return start, viewed(eyes, aims, np.full(count, close_fov(close, size))), False
    shut = []  # turning close-ups with no clear way in: dissolved to from the concept's view, after every other
    for start in range(lead, len(points) - count + 1, RATE):
        aims = path[start:start + count]
        offsets = turning(scenes, aims, sorted({*range(arrived, count, EVERY), count - 1}))
        if offsets is None:
            continue
        closes, followed = np.linalg.norm(offsets, axis=1), aims + offsets
        route = approach_route(scenes, opened, followed[arrived], through)
        if route is None:
            shut.append(start)
            continue
        eyes = kept_off(along(route, eye_share) + eye_share[:, None] * (followed - followed[arrived]), aims,
                        closes)
        if sighted(scenes, aims, eyes, arrived):  # seen once arrived: a walker may come in through a doorway
            fovs = np.array([close_fov(close, size) for close in closes])
            return start, came_in(eyes, lowered(aims, closes, fovs, size), fovs), True
    shown = max(0, seen_from - round(DISSOLVE_SECONDS * RATE) - 1)  # the dissolve's start (walker_job's cut_in)
    for start in shut:  # its eye round the walker from the dissolve's start on, the frames before never drawn
        aims = path[start:start + count]
        offsets = turning(scenes, aims, sorted({*range(shown, count, EVERY), count - 1}))
        if offsets is None or not sighted(scenes, aims[shown:], (aims + offsets)[shown:]):
            continue
        closes = np.linalg.norm(offsets, axis=1)
        fovs = np.array([close_fov(close, size) for close in closes])
        return start, viewed(aims + offsets, lowered(aims, closes, fovs, size), fovs), False
    raise ValueError(f"no start and way round the walker leave {CLOSE_LEAST} m clear of the place for a close-up "
                     "with a clear way in from the concept's view")


def close_fov(close, size):
    """The angle across (degrees) framing TALL_METRES at `close` metres in a picture of `size`, at most FOV_MOST."""
    tall = 2.0 * np.arctan(TALL_METRES / 2.0 / close)
    return min(float(np.degrees(2.0 * np.arctan(np.tan(tall / 2.0) * size[0] / size[1]))), FOV_MOST)


def lowered(aims, closes, fovs, size):
    """The aims (Y up) lowered by half what a close-up held at FOV_MOST frames short of TALL_METRES at its `closes`,
    so the picture gives up headroom before the walker's feet and the push under them (rf3-stairwell, 2026-11-18:
    the woman's sim body on the top landing, 1.6 m off, showed from the knees up)."""
    tall = 2.0 * np.arctan(np.tan(np.radians(fovs) / 2.0) * size[1] / size[0])
    short = np.maximum(TALL_METRES - 2.0 * closes * np.tan(tall / 2.0), 0.0) / 2.0
    return aims - short[:, None] * np.array([0.0, 1.0, 0.0])


def viewed(eyes, aims, fovs):
    """usd_views' views (Y up) a film frame from eyes, aims and angles."""
    return [{"eye": eye.round(4).tolist(), "aim": aim.round(4).tolist(), "up": [0.0, 1.0, 0.0],
             "fov": round(float(angle), 3)} for eye, aim, angle in zip(eyes, aims, fovs)]


def backed(scenes, aims, way):
    """Whether the place stands behind a walker seen from `way` (Y up): the look past its hips (`aims`), level at
    BACKED_HEIGHT over them, straight on and BACKED_SPREAD degrees to either side, meets the place's meshes within
    BACKED_METRES on every one."""
    level = -np.array([way[0], 0.0, way[2]])
    level = level / max(np.linalg.norm(level), 1e-9)
    origins = np.asarray(aims) + [0.0, BACKED_HEIGHT, 0.0]
    for turn in np.radians([0.0, -BACKED_SPREAD, BACKED_SPREAD]):
        look = np.array([np.cos(turn) * level[0] + np.sin(turn) * level[2], 0.0,
                         -np.sin(turn) * level[0] + np.cos(turn) * level[2]])
        behind = camera_paths.first_hits(scenes["still"], origins, np.tile(look, (len(origins), 1)))
        if not np.all(behind <= BACKED_METRES):
            return False
    return True


def needed(frame, count, passes=PASSES, ends=None, seconds=WIPE_SECONDS):
    """The passes film frame `frame` of `count` shows: the one shown, and the one coming over it during a wipe (or
    dissolve) `seconds` long."""
    shown, coming, share = stage_of(frame, count, ends, seconds)
    return [passes[shown]] if coming == shown or share <= 0 else [passes[shown], passes[coming]]


def lerped(values, times):
    """`values` (frames x ...) at fractional frames `times`, each between its two frames by its share."""
    first = np.floor(times).astype(int)
    after = np.minimum(first + 1, len(values) - 1)
    share = (times - first).reshape(-1, *([1] * (values.ndim - 1)))
    return values[first] * (1.0 - share) + values[after] * share


def timed_layer(folder, sim, place, name, scene_rate, record_rate):
    """A layer holding the sim body layer's person (its SimBody) on the place's time codes: referenced with a scale,
    so the place's time code t shows the record's frame t * record_rate / scene_rate (the layer keeps the record's
    frames as its time codes; this one declares the layer's own time codes a second, so OpenUSD scales nothing else);
    its path and the prim to import."""
    layer = sim / sim_body.LAYER
    rate = Sdf.Layer.FindOrOpen(str(layer)).timeCodesPerSecond
    path, scale = folder / "sim_timed.usda", scene_rate / record_rate
    path.write_text(f"""#usda 1.0
(
    defaultPrim = "peel"
    metersPerUnit = 1
    timeCodesPerSecond = {rate}
    upAxis = "Y"
)

def Xform "peel"
{{
    def Xform "SimBody" (
        prepend references = @{layer.resolve()}@<{sim_root(place, name)}> (offset = 0; scale = {scale!r})
    )
    {{
    }}
}}
""")
    return path, "/peel/SimBody"


def walker_job(folder, scene, cast, sim, person_of, walker, size, review=False):
    """Write a walker peel's Blender job into `folder` and return its views.json (usd_views' listing, its `peel` the
    job): the place's whole film, one shot. The place_build scene (`scene`, its folder) drawn as its film draws it,
    its walkers played in it as the film plays them, from LEAD_SECONDS at least into their records, so every one is
    walking from the first frame; the camera opening on the concept's view (the scene record's `camera`) and coming
    on to follow the walker close (closing, which picks the shot's start in the record), for its passes, each its
    holds (walker_holds, walker_ends), `dressed` (the place as it is), `mesh` (the walker's bare SOMA surface, the clip
    rig skinned by the clip its sim body played, between the record's frames) and `sim` (its sim body layer, its
    muscles in the film's activation colours, each foot's push an arrow, fading in: foot_pushes), the walker's own
    dressed body hidden in the last two; only the passes a frame shows are drawn (needed, at DISSOLVE_SECONDS). Where
    the camera has no clear way in from the concept's view (closing), the place is also drawn on that view (`opening`,
    views o<frame>) until the film has dissolved from it to the close-up, over twice DISSOLVE_SECONDS halfway through
    the approach (`cut_in`, its first and end frames). Film
    frame k shows the record's time start + k / RATE, the place's time code at its own rate (its walkers start their
    records at its 0); a record too short for the shot is refused."""
    from score.stages import place_build
    from score.stages.place_build import film as place_film
    record = json.loads((sim / "sim_bodies.json").read_text())
    if walker not in record["bodies"]:
        raise ValueError(f"{sim}: no sim body of {walker}")
    single = next(single for single in cast["characters"] if single["name"] == walker)
    body = record["bodies"][walker]
    rig, _, clip = person_of(single, body)
    frames = json.loads((sim / "measures" / f"{walker}.json").read_text())
    times = np.arange(int((len(frames) - 1) / record["rate"] * RATE) + 1) * record["rate"] / RATE
    where = sim_body.own_frame(body["at"], body.get("turn", 0.0))
    mesh = lerped(skinned(rig, clip) @ where[:3, :3].T + where[:3, 3], times)
    concept, lead = place_build.record_of(scene)["camera"], round(LEAD_SECONDS * RATE)
    seconds = approach_seconds(float(np.linalg.norm(hips_path(mesh, up=1)[min(lead, len(mesh) - 1)] -
                                                    np.asarray(concept["eye"], dtype=float))))
    holds = walker_holds((len(frames) - 1) / record["rate"], seconds)
    count, ends = round(walker_seconds(holds, seconds) * RATE), walker_ends(holds, seconds)
    filmed = pathlib.Path(scene) / "film" / "path.json"  # the place film's own clear path, a way in for the camera
    through = [view["eye"] for view in json.loads(filmed.read_text())["views"]] if filmed.exists() else None
    start, path, entered = closing(mesh, place_film.place_scenes(scene), count, size, concept, lead, through, seconds)
    middle = (OPENING_SECONDS + seconds / 2) * RATE
    cut_in = None if entered else [round(middle - DISSOLVE_SECONDS * RATE), round(middle + DISSOLVE_SECONDS * RATE)]
    mesh, times = mesh[start:start + count], times[start:start + count]
    arrows = lerped(foot_pushes(frames, body_weight(body), record["rate"], body.get("segments", ())), times)
    scene_rate = place_build.opened(scene)[0].GetTimeCodesPerSecond()
    layer, root = timed_layer(folder, sim, record["place"], walker, scene_rate, record["rate"])
    np.savez(folder / f"{walker}.npz", faces=np.asarray(rig["faces"]), points=points_to_z(mesh),
             arrow_start=points_to_z(arrows[..., :3] @ where[:3, :3].T + where[:3, 3]),
             arrow_vector=points_to_z(arrows[..., 3:] @ where[:3, :3].T))
    job = {"kind": "walker", "out": str(folder), "walker": walker, "passes": list(PASSES),
           "start_seconds": start / RATE, "approach_seconds": seconds, "holds": holds, "ends": ends,
           "draws": [needed(frame, count, ends=ends, seconds=DISSOLVE_SECONDS) if cut_in is None or frame >= cut_in[0]
                     else [] for frame in range(count)], "cut_in": cut_in,
           "arrows": {"colour": push_colour(), "fade": arrow_fade(count, ends, DISSOLVE_SECONDS),
                      "full": SHOWN_FROM * METRES_PER_BODY_WEIGHT},
           "muscles": muscle_look(),
           "people": [{"name": walker, "sim_layer": str(layer), "sim_root": root,
                       "arrays": str(folder / f"{walker}.npz"), "placed": to_z(where).tolist()}]}
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    views = [dict(spot, name=f"f{frame:04d}", frame=round((start + frame) * scene_rate / RATE), look_only=True)
             for frame, spot in enumerate(path) if job["draws"][frame]]
    views += [dict(eye=concept["eye"], aim=concept["aim"], up=[0.0, 1.0, 0.0], fov=concept["fov"], name=f"o{frame:04d}",
                   frame=round((start + frame) * scene_rate / RATE), look_only=True)
              for frame in range(cut_in[1] if cut_in else 0)]  # the concept's view the film dissolves in from
    listed = folder / "views.json"
    listed.write_text(json.dumps({"size": list(size), "review": review, "views": views,
                                  "peel": str(folder / "job.json")}, indent=1))
    return listed


def underfoot(triangles, people):
    """The ground's triangles (Z up) a body stands, sits or lies on and the camera sees past: the level ones
    (their normal within LEVEL of up, either winding) wholly below the people's highest point; never a wall, nor a
    roof over their heads."""
    if not len(triangles):
        return triangles
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    level = np.abs(normals[:, 2]) >= LEVEL * np.maximum(lengths, 1e-12)
    top = max(float(person["points"][..., 2].max()) for person in people)
    return triangles[level & (lengths > 0) & (triangles[:, :, 2].max(axis=1) < top)]


def ground_of(stage_folder, record):
    """The ground the sim bodies stood on (n x 3 x 3 triangles, the place's frame, Y up), from the place's finished
    stage: every solid the sim body record names under its bodies (`ground.solids`, cast/measure.solids' names) as
    that stage holds it; refused naming a solid the stage does not hold."""
    from score.stages.cast import measure
    found = measure.solids(stage_root(stage_folder), record["place"])
    named = sorted({solid for body in record["bodies"].values() for solid in body["ground"]["solids"]})
    missing = [solid for solid in named if solid not in found]
    if missing:
        raise ValueError(f"{stage_folder}: the sim bodies stood on {', '.join(missing)}, which the stage does not hold")
    return np.concatenate([found[solid] for solid in named]) if named else None


def sliced(job_path, parts, drawn):
    """The job dealt into `parts` jobs of consecutive film frames (each its `frames` [first, end) of the whole), each
    drawing into a folder of its own under `drawn` (jobs never share an output folder): the slices' job files, written
    beside the job."""
    job = json.loads(pathlib.Path(job_path).read_text())
    count = len(job["source"])
    edges = np.linspace(0, count, min(parts, count) + 1).round().astype(int)
    written = []
    for number, (first, end) in enumerate(zip(edges[:-1], edges[1:])):
        path = pathlib.Path(job_path).with_name(f"job-{number}.json")
        path.write_text(json.dumps(dict(job, frames=[int(first), int(end)], out=str(drawn / str(number))), indent=1))
        written.append(path)
    return written


def pass_ends(count, ends=None):
    """The film frames each pass but the last ends at in a shot of `count`: `ends` as given, else each third."""
    return list(ends) if ends is not None else [coming * count / len(PASSES) for coming in range(1, len(PASSES))]


def walker_holds(record_seconds, approach=APPROACH_SECONDS):
    """The seconds each pass of a walker peel shows for in a shot from LEAD_SECONDS into a record `record_seconds`
    long, after its opening and its `approach`: WALKER_HOLDS, else all shortened alike to fit it (whole film frames),
    refused below HOLDS_LEAST of them."""
    room = record_seconds - LEAD_SECONDS - OPENING_SECONDS - approach
    share = min(1.0, room / sum(WALKER_HOLDS.values()))
    if share < HOLDS_LEAST:
        raise ValueError(f"a {record_seconds:g} s sim body record leaves {max(room, 0.0):.1f} s for the peel's "
                         f"{sum(WALKER_HOLDS.values()):g} s of holds after its lead, opening and approach")
    return {name: round(seconds * share * RATE) / RATE for name, seconds in WALKER_HOLDS.items()}


def walker_seconds(holds=None, approach=APPROACH_SECONDS):
    """A walker peel's length: its opening, its `approach` and its holds (WALKER_HOLDS unless given)."""
    return OPENING_SECONDS + approach + sum((holds or WALKER_HOLDS).values())


def walker_ends(holds=None, approach=APPROACH_SECONDS):
    """A walker peel's pass ends (film frames): the player model through the opening, the `approach` and its hold,
    then each hold (WALKER_HOLDS unless given)."""
    holds = holds or WALKER_HOLDS
    held = np.cumsum([holds[name] for name in PASSES[:-1]]) + OPENING_SECONDS + approach
    return (held * RATE).round().tolist()


def stage_of(frame, count, ends=None, seconds=WIPE_SECONDS):
    """(the pass shown, the next pass, how far the wipe to it has come 0 to 1) at film frame `frame` of `count`: a
    wipe (or dissolve) `seconds` long centred on each pass's end (pass_ends: each third unless `ends` names them)."""
    ends, wipe = pass_ends(count, ends), seconds * RATE
    for coming, end in enumerate(ends, start=1):
        into = frame - (end - wipe / 2)
        if 0 <= into < wipe:
            return coming - 1, coming, into / wipe
    shown = sum(frame >= end for end in ends)
    return shown, shown, 0.0


def wiped(pictures, frame, count, ends=None):
    """Film frame `frame`: the pass it shows, the next one risen from the bottom over it during a wipe."""
    shown, coming, share = stage_of(frame, count, ends)
    picture = pictures[shown].copy()
    if coming != shown and share > 0:
        wide, tall = picture.size
        edge = round(tall * (1 - share))
        picture.paste(pictures[coming].crop((0, edge, wide, tall)), (0, edge))
        ImageDraw.Draw(picture).rectangle((0, edge - 1, wide, edge + 1), fill=EDGE)
    return picture


def dissolved(pictures, frame, count, ends):
    """Film frame `frame` of a walker peel: the pass it shows, the next one dissolving in over it (DISSOLVE_SECONDS,
    eased), and the activation colour bar over the sim body pass, as much as it shows."""
    shown, coming, share = stage_of(frame, count, ends, DISSOLVE_SECONDS)
    eased = lettering.eased(share)
    picture = pictures[shown] if coming == shown or share <= 0 else Image.blend(pictures[shown], pictures[coming],
                                                                                 eased)
    sim = PASSES.index("sim")
    showing = (1.0 if shown == sim else 0.0) * (1.0 - eased if coming != shown else 1.0) + \
        (eased if coming == sim and coming != shown else 0.0)
    return activation_bar(picture, showing) if showing > 0 else picture


def activation_bar(picture, showing):
    """The muscles' colour bar laid over a frame's lower right, `showing` of it (0 to 1): the film's activation
    colours from 0 to 1 as Blender's ramp blends them (evenly in linear light), its ends and its name in the film's
    caption type."""
    wide, tall = picture.size
    unit = tall / 1080.0
    bar_wide, bar_tall, margin = round(300 * unit), max(2, round(14 * unit)), round(48 * unit)
    colours = np.array([linear(name) for name in ACTIVATION_TOKENS])
    shares = np.linspace(0.0, 1.0, bar_wide) * (len(colours) - 1)
    low = np.minimum(shares.astype(int), len(colours) - 2)
    mixed = colours[low] * (1 - (shares - low))[:, None] + colours[low + 1] * (shares - low)[:, None]
    srgb = np.where(mixed <= 0.0031308, mixed * 12.92, 1.055 * mixed ** (1 / 2.4) - 0.055)
    strip = np.repeat((srgb * 255).round().astype(np.uint8)[None], bar_tall, axis=0)
    small, ink = lettering.face(400, 20 * unit), lettering.token("film-caption")[:3]
    layer = Image.new("RGBA", picture.size, (0, 0, 0, 0))
    left, top = wide - margin - bar_wide, tall - margin - bar_tall
    shade = round(140 * showing)
    draw = ImageDraw.Draw(layer)
    draw.rectangle((left - round(14 * unit), top - round(42 * unit), left + bar_wide + round(14 * unit),
                    top + bar_tall + round(34 * unit)), fill=(0, 0, 0, shade))
    layer.paste(Image.fromarray(strip, "RGB"), (left, top))
    alpha = layer.getchannel("A")
    alpha.paste(round(255 * showing), (left, top, left + bar_wide, top + bar_tall))
    layer.putalpha(alpha)
    draw = ImageDraw.Draw(layer)
    written = (*ink, round(255 * showing))
    draw.text((left, top - round(8 * unit)), "muscle activation", font=small, fill=written, anchor="ls")
    draw.text((left, top + bar_tall + round(6 * unit)), "0", font=small, fill=written, anchor="lt")
    draw.text((left + bar_wide, top + bar_tall + round(6 * unit)), "1", font=small, fill=written, anchor="rt")
    return Image.alpha_composite(picture.convert("RGBA"), layer).convert("RGB")


def triangles_of(mesh, time):
    """A mesh prim's triangles in the stage's frame (n x 3 x 3, Y up), its faces fanned."""
    points = np.asarray(mesh.GetPointsAttr().Get(time), dtype=float)
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(time), dtype=int)
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(time), dtype=int)
    matrix = np.asarray(mesh.ComputeLocalToWorldTransform(time), dtype=float)
    placed = points @ matrix[:3, :3] + matrix[3, :3]  # USD's row vectors
    found, start = [], 0
    for count in counts:
        found += [[indices[start], indices[start + corner], indices[start + corner + 1]]
                  for corner in range(1, count - 1)]
        start += count
    return placed[np.asarray(found, dtype=int).reshape(-1, 3)]


def collider_shape(prim, triangles):
    """The shape a collider collides by (UsdPhysics' approximation): a convex hull round it, its box, or its own
    triangles (none or a mesh simplification: the triangles the simplification starts from)."""
    approximation = UsdPhysics.MeshCollisionAPI(prim).GetApproximationAttr().Get() \
        if prim.HasAPI(UsdPhysics.MeshCollisionAPI) else None
    if approximation == UsdPhysics.Tokens.convexHull:
        hull = trimesh.convex.convex_hull(triangles.reshape(-1, 3))
        return np.asarray(hull.vertices)[np.asarray(hull.faces)]
    if approximation == UsdPhysics.Tokens.boundingCube:
        box = trimesh.creation.box(bounds=[triangles.reshape(-1, 3).min(axis=0), triangles.reshape(-1, 3).max(axis=0)])
        return np.asarray(box.vertices)[np.asarray(box.faces)]
    return triangles


def moving(prim):
    """Whether the collider moves in the physics: it or an object above it is a rigid body."""
    while prim and prim.IsValid():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            return True
        prim = prim.GetParent()
    return False


def physics_bodies(stage_path):
    """The bodies a place's physics uses, from its stage (Z up): every mesh prim the stage collides with
    (colliders.collides), but the sky's, as its approximation makes it; ({"static", "moving"}: n x 3 x 3 triangles
    each, the names of the colliders no mesh draws)."""
    stage = Usd.Stage.Open(str(stage_path))
    time = Usd.TimeCode(stage.GetStartTimeCode()) if stage.HasAuthoredTimeCodeRange() else Usd.TimeCode.Default()
    found, unshaped = {"static": [], "moving": []}, []
    for prim in stage.Traverse():
        if not colliders.collides(prim) or any(part in NOT_SOLID for part in prim.GetPath().pathString.split("/")):
            continue
        if not prim.IsA(UsdGeom.Mesh):
            unshaped.append(prim.GetPath().pathString)  # a primitive's own shape (the ground's far ball)
            continue
        triangles = triangles_of(UsdGeom.Mesh(prim), time)
        if len(triangles):
            found["moving" if moving(prim) else "static"].append(collider_shape(prim, triangles))
    return ({kind: points_to_z(np.concatenate(shapes)) if shapes else np.zeros((0, 3, 3))
             for kind, shapes in found.items()}, unshaped)


def stage_root(folder):
    """A stage output's root stage file (its one top .usda, named for its place)."""
    return pathlib.Path(folder) / f"{demo_film.place_of(folder)}.usda"


def place_job(folder, stage, physics, seconds, size, samples):
    """Write a place peel's Blender job into `folder` and return its path: the finished stage (`stage`, a stage
    output folder) on its scene record's first camera, standing, its bodies from `physics` (the place's physics-layer
    output, else the finished stage itself), `seconds` long at RATE, each film frame the stage's time code at its
    own rate."""
    record = json.loads((pathlib.Path(stage) / "scene.json").read_text())
    view = demo_film.film_view(record, demo_film.first_camera(record), {})
    bodies, unshaped = physics_bodies(stage_root(physics or stage))
    np.savez(folder / "physics.npz", **bodies)
    opened = Usd.Stage.Open(str(stage_root(stage)))
    start, rate = opened.GetStartTimeCode(), opened.GetTimeCodesPerSecond()
    count = round(seconds * RATE)
    spot = {"eye": points_to_z(np.asarray(view["eye"], dtype=float)).tolist(),
            "aim": points_to_z(np.asarray(view["aim"], dtype=float)).tolist()}
    job = {"kind": "place", "out": str(folder), "size": list(size), "samples": samples, "record_rate": RATE,
           "stage": str(stage_root(stage)), "physics": str(folder / "physics.npz"), "unshaped": unshaped,
           "source": [round(start + frame * rate / RATE) for frame in range(count)], "passes": list(PLACE_PASSES),
           "camera": {"fov": float(view.get("fov", 75.0)), "path": [spot] * count}}
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    return folder / "job.json"


def joined(folder, count, passes=PASSES, drawn_in=None, ends=None, dissolve=False, cut_in=None):
    """The shot's frames, the passes joined by their wipes (at `ends`, pass_ends'), or a walker peel's by its
    dissolves (`dissolve`, walker_joined; from its `opening` pass over `cut_in`'s frames where it has one), into
    folder/peel/<frame>.png; each pass's frame a film frame shows (needed) from whichever of `drawn_in` (the slices'
    folders, else `folder`) drew it."""
    out = folder / "peel"
    out.mkdir(exist_ok=True)
    places = list(drawn_in or [folder])
    seconds = DISSOLVE_SECONDS if dissolve else WIPE_SECONDS

    def picture(name, frame):
        return Image.open(next(found for found in (place / name / f"{frame:04d}.png" for place in places)
                               if found.exists())).convert("RGB")

    for frame in range(count):
        if cut_in and frame < cut_in[0]:
            picture("opening", frame).save(out / f"{frame:04d}.png")
            continue
        pictures = {passes.index(name): picture(name, frame) for name in needed(frame, count, passes, ends, seconds)}
        made = dissolved(pictures, frame, count, ends) if dissolve else wiped(pictures, frame, count, ends)
        if cut_in and frame < cut_in[1]:
            made = Image.blend(picture("opening", frame), made,
                               lettering.eased((frame - cut_in[0]) / (cut_in[1] - cut_in[0])))
        made.save(out / f"{frame:04d}.png")
    return out


def walker_joined(folder, drawn_in=None):
    """A walker peel's film frames from its job (folder/job.json: its frames and pass ends), joined by its
    dissolves (joined)."""
    job = json.loads((pathlib.Path(folder) / "job.json").read_text())
    return joined(pathlib.Path(folder), len(job["draws"]), drawn_in=drawn_in, ends=job["ends"], dissolve=True,
                  cut_in=job.get("cut_in"))


def drawn(job):
    """The job's passes drawn in this machine's Blender, without a window (`-b`: no display needed)."""
    subprocess.run([str(BLENDER), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                    str(BLENDER_SCRIPT), "--", str(job)], check=True, stdin=subprocess.DEVNULL)


def walker_peel(arguments):
    """A walker peel drawn on this machine's card (the command line's --scene): its job, its passes through the card
    queue, joined and encoded silent to <folder>/peel.mp4."""
    from score.stages import place_build
    from score.stages.demo_film import peel_rows
    from score.stages.place_build import render as place_render
    inputs = json.loads(arguments.rows.read_text())
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    walker = arguments.walker or peel_rows.walker(inputs, cast)
    listed = walker_job(arguments.folder, arguments.scene, cast, pathlib.Path(inputs["sim-body"]),
                        peel_rows.people_of(inputs, clothed=False), walker, arguments.size, arguments.review)
    free = place_render.available_gb()
    if free <= place_render.FREE_GB:
        raise place_render.RenderFailed(f"{free:.1f} GB memory available, a Blender needs over {place_render.FREE_GB}")
    with (arguments.folder / "blender.log").open("w") as log:
        subprocess.run(place_render.queued(f"walker-peel-{walker}", WALKER_SCRIPT,
                                           [str(place_build.scene_path(arguments.scene).resolve()), str(listed),
                                            str(arguments.folder / "views")]),
                       check=True, stdout=log, stderr=subprocess.STDOUT, cwd=REPO)
    frames = walker_joined(arguments.folder)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(RATE), "-i", str(frames / "%04d.png"),
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(arguments.folder / "peel.mp4")], check=True)
    return arguments.folder / "peel.mp4"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--cast", type=pathlib.Path)
    parser.add_argument("--sim", type=pathlib.Path)
    parser.add_argument("--rig", type=pathlib.Path)
    parser.add_argument("--dressed", type=pathlib.Path)
    parser.add_argument("--stage", type=pathlib.Path, help="a place peel: the place's finished stage output folder")
    parser.add_argument("--physics", type=pathlib.Path, help="a place peel: the place's physics-layer output folder")
    parser.add_argument("--seconds", type=float, default=5.0, help="a body or place peel's (a walker peel's is "
                        "walker_seconds)")
    parser.add_argument("--size", type=int, nargs=2, default=(1280, 720))
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--close", action="store_true", help="follow one walker (close_walker) instead of all")
    parser.add_argument("--clips", type=pathlib.Path, help="scene-clips' scene_clips.json, for close_walker")
    parser.add_argument("--ground", type=pathlib.Path, help="the scene's ground triangles (.npy, n x 3 x 3, Y up)")
    parser.add_argument("--build", type=pathlib.Path, help="the person's built body rig (people-body's rig.npz)")
    parser.add_argument("--scene", type=pathlib.Path, help="a walker peel: the place_build scene folder")
    parser.add_argument("--rows", type=pathlib.Path, help="a walker peel: {row: output folder} the sim body ran from")
    parser.add_argument("--walker", help="a walker peel: the walker peeled (else close_walker's)")
    parser.add_argument("--review", action="store_true", help="a walker peel at the review's samples (a look only)")
    arguments = parser.parse_args()
    arguments.folder.mkdir(parents=True, exist_ok=True)
    count = round(arguments.seconds * RATE)
    if arguments.scene:
        print(f"walker peel: {walker_peel(arguments)}")
        return
    if arguments.stage:
        drawn(place_job(arguments.folder, arguments.stage, arguments.physics, arguments.seconds, arguments.size,
                        arguments.samples))
        print(f"place peel: {count} frames in {joined(arguments.folder, count, PLACE_PASSES)}")
        return
    if not all((arguments.cast, arguments.sim, arguments.rig, arguments.dressed)):
        parser.error("a layer peel needs --cast, --sim, --rig and --dressed; a place peel --stage")
    cast = json.loads(arguments.cast.read_text())
    close = close_walker(cast, json.loads(arguments.clips.read_text()) if arguments.clips else None) \
        if arguments.close else None
    rig = sim_body.person_rig(dict(np.load(arguments.rig)), dict(np.load(arguments.build)) if arguments.build
                              else None)[0]
    job = job_of(arguments.folder, cast, arguments.sim, lambda single, body: (rig, arguments.dressed, body["clip"]),
                 arguments.seconds, arguments.size, arguments.samples, close,
                 np.load(arguments.ground) if arguments.ground else None)
    drawn(job)
    out = joined(arguments.folder, round(arguments.seconds * RATE))
    print(f"peel: {round(arguments.seconds * RATE)} frames in {out}")


if __name__ == "__main__":
    main()
