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
along the push `METRES_PER_NEWTON` long a newton, so a body's arrows on the Moon are a sixth of its arrows on Earth;
one of PUSHED or less is not drawn. The arrows are the film's `--film-push` colour (design/tokens/colours.css),
slim at a fixed width on screen, a little see-through, and fade in with the sim body (`arrow_fade`).
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
from pxr import Usd, UsdGeom, UsdPhysics

from score.stages import demo_film, sim_body
from score.stages.demo_film import lettering

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import colliders  # noqa: E402
BLENDER_SCRIPT = REPO / "score/stages/demo_film/blender/body_peel.py"
# The Blender tools/blender/session.py sets up on this machine (its newest version).
BLENDER = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / \
    "blender-mcp/blender-5.2.2/blender"
PASSES = ("dressed", "mesh", "sim")
PLACE_PASSES = ("finished", "bare", "physics")
NOT_SOLID = ("Sky",)  # the physics layer's own: the sky is drawn, never collided with (tools/usd/physics.py)
RATE = 24
METRES_PER_NEWTON = 1.0 / 1000.0  # an arrow 1 m long is the push of 1,000 N
PUSHED = 1.0  # newtons: a body the ground pushes less than this carries nothing worth an arrow
WIPE_SECONDS = 0.6
FADE_SECONDS = 1.0  # the push arrows' fade in, from the start of the sim body's wipe
WIDE_LENS, CLOSE_LENS = 40.0, 35.0  # mm
CLOSE_METRES = 4.0  # the close-up's camera off its person's path: the whole body in view at CLOSE_LENS
FOLLOW_SECONDS = 0.5  # the close-up's aim smoothed over this either side
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


def pushes(frames, bodies):
    """Each touching body's push from the ground each record frame as an arrow (frames x bodies x 6: start, vector;
    NaN where the ground pushes it PUSHED or less): from its centre of pressure on the ground along the push,
    METRES_PER_NEWTON a newton (the record's `touches`, the person's frame)."""
    arrows = np.full((len(frames), len(bodies), 6), np.nan)
    for index, frame in enumerate(frames):
        for number, body in enumerate(bodies):
            if body not in frame["touches"]:
                continue
            force, centre = np.asarray(frame["touches"][body][:3]), np.asarray(frame["touches"][body][3:])
            if np.linalg.norm(force) > PUSHED:
                arrows[index, number] = [*centre, *(force * METRES_PER_NEWTON)]
    return arrows


def arrow_fade(count):
    """How far the push arrows have faded in at each film frame of `count` (0 to 1): from the start of the wipe that
    brings the sim body in, over FADE_SECONDS, so they come in with its layer."""
    third, wipe = count / len(PASSES), WIPE_SECONDS * RATE
    begins = (len(PASSES) - 1) * third - wipe / 2
    return np.clip((np.arange(count) - begins) / (FADE_SECONDS * RATE), 0.0, 1.0).tolist()


def push_colour():
    """The push arrows' colour, the film's own `--film-push` token (lettering.token), as Blender's linear RGB."""
    srgb = np.array(lettering.token("film-push")[:3]) / 255.0
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4).tolist()


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
    arrows = pushes(frames, touching(frames))
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


def following(person):
    """The close-up: a camera a film frame (Z up) CLOSE_METRES off one person's path to its side and a little ahead,
    aimed at its hips (its whole body, its feet and the push under them in view), the aim smoothed over
    FOLLOW_SECONDS either side so it glides rather than bobs."""
    middles = person["points"].mean(axis=1)
    middles[:, 2] = person["points"][:, :, 2].min(axis=1) + 0.9
    width = max(1, round(FOLLOW_SECONDS * RATE))
    padded = np.concatenate([np.repeat(middles[:1], width, axis=0), middles, np.repeat(middles[-1:], width, axis=0)])
    kernel = np.ones(2 * width + 1) / (2 * width + 1)
    smooth = np.column_stack([np.convolve(padded[:, axis], kernel, mode="same")[width:-width] for axis in range(3)])
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
           "arrows": {"colour": push_colour(), "fade": arrow_fade(len(shown))}, "people": people, "ground": None}
    if ground is not None:
        np.save(folder / "ground.npy", underfoot(points_to_z(np.asarray(ground, dtype=float)), list(shapes.values())))
        job["ground"] = str(folder / "ground.npy")
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    return folder / "job.json"


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


def stage_of(frame, count):
    """(the pass shown, the next pass, how far the wipe to it has risen 0 to 1) at film frame `frame` of `count`: a
    wipe of WIPE_SECONDS centred on each third."""
    third, wipe = count / len(PASSES), WIPE_SECONDS * RATE
    for coming in range(1, len(PASSES)):
        into = frame - (coming * third - wipe / 2)
        if 0 <= into < wipe:
            return coming - 1, coming, into / wipe
    shown = min(int(frame // third), len(PASSES) - 1)
    return shown, shown, 0.0


def wiped(pictures, frame, count):
    """Film frame `frame`: the pass it shows, the next one risen from the bottom over it during a wipe."""
    shown, coming, share = stage_of(frame, count)
    picture = pictures[shown].copy()
    if coming != shown and share > 0:
        wide, tall = picture.size
        edge = round(tall * (1 - share))
        picture.paste(pictures[coming].crop((0, edge, wide, tall)), (0, edge))
        ImageDraw.Draw(picture).rectangle((0, edge - 1, wide, edge + 1), fill=EDGE)
    return picture


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


def joined(folder, count, passes=PASSES, drawn_in=None):
    """The shot's frames, the passes joined by their wipes, into folder/peel/<frame>.png; each pass's frame from
    whichever of `drawn_in` (the slices' folders, else `folder`) drew it."""
    out = folder / "peel"
    out.mkdir(exist_ok=True)
    places = list(drawn_in or [folder])
    for frame in range(count):
        pictures = [Image.open(next(found for found in (place / name / f"{frame:04d}.png" for place in places)
                                    if found.exists())).convert("RGB") for name in passes]
        wiped(pictures, frame, count).save(out / f"{frame:04d}.png")
    return out


def drawn(job):
    """The job's passes drawn in this machine's Blender, without a window (`-b`: no display needed)."""
    subprocess.run([str(BLENDER), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                    str(BLENDER_SCRIPT), "--", str(job)], check=True, stdin=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--cast", type=pathlib.Path)
    parser.add_argument("--sim", type=pathlib.Path)
    parser.add_argument("--rig", type=pathlib.Path)
    parser.add_argument("--dressed", type=pathlib.Path)
    parser.add_argument("--stage", type=pathlib.Path, help="a place peel: the place's finished stage output folder")
    parser.add_argument("--physics", type=pathlib.Path, help="a place peel: the place's physics-layer output folder")
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--size", type=int, nargs=2, default=(1280, 720))
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--close", action="store_true", help="follow one walker (close_walker) instead of all")
    parser.add_argument("--clips", type=pathlib.Path, help="scene-clips' scene_clips.json, for close_walker")
    parser.add_argument("--ground", type=pathlib.Path, help="the scene's ground triangles (.npy, n x 3 x 3, Y up)")
    parser.add_argument("--build", type=pathlib.Path, help="the person's built body rig (people-body's rig.npz)")
    arguments = parser.parse_args()
    arguments.folder.mkdir(parents=True, exist_ok=True)
    count = round(arguments.seconds * RATE)
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
