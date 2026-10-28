"""A layer peel (the film script's `body-peel` cut, owner 2026-10-27: "show the layers in the demo, from full player
model with clothes, to mesh, to sim body"): every person of a scene's cast drawn three times on one camera, clothed
(its dressed body posed by the sim body's clip, its rest fitted to the clip rig's bind turned about up), as its bare
SOMA mesh (the clip rig's surface skinned by the same clip) and as its sim body (whatever geometry the sim body layer
holds under the person's SimBody, bones, boxes or muscles, at its own time samples; each foot's push an arrow), the
three joined by a wipe rising up the picture at each third of the shot; or, closer, the camera following one walker
(`close_walker`).

    python -m score.stages.demo_film.peel <job folder> --cast <cast.json> --sim <sim-body output> --rig <rig.npz>
        --dressed <body.glb> [--seconds 5] [--size 1280 720] [--samples 64] [--close [--clips <scene_clips.json>]]
        [--ground <triangles.npy>] [--build <people-body rig.npz>]

Free and local: the frames are drawn by `blender/body_peel.py` in this machine's Blender (tools/blender/session.py's
set-up, `-b` on its card), never a paid row; no row makes a peel's frames yet (the environment film names the cut as
one no row makes). Everything but the sim body's own geometry is worked out here in numpy; the Blender side imports
that from its layer, lays it all out and draws it.

Nothing is invented: the clothed pass is the dressed body's own surface and skin on the sim body's clip, the mesh
pass the clip rig's own points and skin weights, the sim pass the sim body's own layer at its time codes (the
record's frames) and its measures' push on each foot. A shot longer than the record is refused, never stretched
or looped. Each foot's push is the record's own (its `feet`: the ground's upward push on the segment and its height
over the ground), an arrow from the ground under it `METRES_PER_NEWTON` long, so a body's arrows on the Moon are a
sixth of its arrows on Earth.
"""
import argparse
import json
import os
import pathlib
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from score.stages import sim_body

REPO = pathlib.Path(__file__).resolve().parents[3]
BLENDER_SCRIPT = REPO / "score/stages/demo_film/blender/body_peel.py"
# The Blender tools/blender/session.py sets up on this machine (its newest version).
BLENDER = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / \
    "blender-mcp/blender-5.2.2/blender"
PASSES = ("dressed", "mesh", "sim")
RATE = 24
METRES_PER_NEWTON = 1.0 / 1000.0  # an arrow 1 m long is the push of 1,000 N
PUSHED = 1.0  # newtons: a foot the ground pushes less than this carries nothing worth an arrow
WIPE_SECONDS = 0.6
WIDE_LENS, CLOSE_LENS = 40.0, 35.0  # mm
CLOSE_METRES = 4.0  # the close-up's camera off its person's path: the whole body in view at CLOSE_LENS
FOLLOW_SECONDS = 0.5  # the close-up's aim smoothed over this either side
EDGE = (255, 196, 64)  # the wipe's edge line
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


def foot_bottoms(layer, root, feet, times):
    """Each foot's bottom (the middle of its drawn geometry's lowest face) at each of the layer's time codes
    (times x feet x 3, the person's frame, Y up): whatever geometry sits under the foot's prim below `root`, read at
    its own time samples, guides included."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(layer))
    body = stage.GetPrimAtPath(root)
    if not body:
        raise ValueError(f"{layer}: no sim body at {root}")
    named = {prim.GetName(): prim for prim in Usd.PrimRange(body)}
    missing = [foot for foot in feet if foot not in named]
    if missing:
        raise ValueError(f"{layer}: no prim of {', '.join(missing)} under {root}")
    purposes = [UsdGeom.Tokens.default_, UsdGeom.Tokens.guide, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy]
    found = np.empty((len(times), len(feet), 3))
    for row, time in enumerate(times):
        cache = UsdGeom.BBoxCache(Usd.TimeCode(time), purposes)
        for column, foot in enumerate(feet):
            box = cache.ComputeWorldBound(named[foot]).ComputeAlignedRange()
            low, high = np.asarray(box.GetMin()), np.asarray(box.GetMax())
            found[row, column] = [(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2]
    return found


def pushes(bottoms, frames):
    """Each foot's push from the ground each record frame as an arrow (frames x feet x 6: start, vector; NaN where the
    ground does not push it): from under the foot's bottom (`bottoms`, foot_bottoms), dropped by its recorded height
    over the ground, up METRES_PER_NEWTON a newton of the recorded push (the record's `feet`)."""
    feet = list(frames[0]["feet"])
    arrows = np.full((len(frames), len(feet), 6), np.nan)
    for index, frame in enumerate(frames):
        for number, foot in enumerate(feet):
            height, push = frame["feet"][foot]
            if height is None or push <= PUSHED:
                continue
            bottom = bottoms[index, number]
            arrows[index, number] = [bottom[0], bottom[1] - height, bottom[2], 0.0, push * METRES_PER_NEWTON, 0.0]
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


def person_arrays(record, rig, frames, bottoms, shown):
    """One person's arrays for Blender, every one in the place and Z up, at the film's frames `shown`: its bare
    mesh's points and its feet's push arrows; and, in its own frame, each rig joint's move from its bind frame (which
    poses its dressed body) and the bind frames' places (which the dressed body's rest is fitted to). The sim body
    itself is the layer's, drawn by Blender at the same frames (its time codes)."""
    where = sim_body.own_frame(record["at"], record.get("turn", 0.0))
    mesh = skinned(rig, record["clip"]) @ where[:3, :3].T + where[:3, 3]
    arrows = pushes(bottoms, frames)
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


def job_of(folder, cast, sim, rig_path, dressed, seconds, size, samples, close=None, ground=None, build=None):
    """Write the Blender job (job.json and one npz a person) into `folder` and return its path: the wide shot of
    everyone, or, `close` naming one of them, the close-up following that person alone (no one else between it and
    the camera). `ground`: the scene's ground under them (n x 3 x 3 triangles, the place's frame, Y up; else a flat
    floor at 0). `build`: the person's built body rig (people-body's rig.npz), which the sim body was built at
    (sim_body.person_rig); else the clips rig on its own bind (sim_body.person_rig's no-build case)."""
    record = json.loads((sim / "sim_bodies.json").read_text())
    rig = sim_body.person_rig(dict(np.load(rig_path)), build)[0]
    people, shown = [], None
    for single in cast["characters"]:
        name = single["name"]
        if name not in record["bodies"] or close not in (None, name):
            continue  # the sim body stage left it out and said why in its record, or the close-up follows another
        frames = json.loads((sim / "measures" / f"{name}.json").read_text())
        shown = source_frames(seconds, record["rate"], len(frames))
        layer, root = sim / sim_body.LAYER, sim_root(record["place"], name)
        bottoms = foot_bottoms(layer, root, list(frames[0]["feet"]), range(len(frames)))
        arrays = person_arrays(record["bodies"][name], rig, frames, bottoms, shown)
        np.savez(folder / f"{name}.npz", faces=np.asarray(rig["faces"]), **arrays)
        people.append({"name": name, "glb": str(dressed), "clip": record["bodies"][name]["clip"],
                       "joints": [str(joint) for joint in rig["names"]], "sim_layer": str(layer), "sim_root": root,
                       "arrays": str(folder / f"{name}.npz"), "placed": arrays["placed"].tolist(),
                       "_points": arrays["points"]})
    if not people:
        raise ValueError(f"{sim}: no sim body of the cast to peel")
    shapes = {person["name"]: {"points": person.pop("_points"), "placed": np.asarray(person["placed"])}
              for person in people}
    if close is not None and close not in shapes:
        raise ValueError(f"{sim}: no sim body of {close} to follow")
    path = following(shapes[close]) if close else framing(list(shapes.values()), len(shown))
    job = {"out": str(folder), "size": list(size), "samples": samples, "record_rate": record["rate"],
           "source": shown, "passes": list(PASSES), "camera": {"lens": CLOSE_LENS if close else WIDE_LENS,
                                                                "path": path},
           "people": people, "ground": None}
    if ground is not None:
        np.save(folder / "ground.npy", points_to_z(np.asarray(ground, dtype=float)))
        job["ground"] = str(folder / "ground.npy")
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    return folder / "job.json"


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


def joined(folder, count):
    """The shot's frames, the passes joined by their wipes, into folder/peel/<frame>.png."""
    out = folder / "peel"
    out.mkdir(exist_ok=True)
    for frame in range(count):
        pictures = [Image.open(folder / name / f"{frame:04d}.png").convert("RGB") for name in PASSES]
        wiped(pictures, frame, count).save(out / f"{frame:04d}.png")
    return out


def drawn(job):
    """The job's passes drawn in this machine's Blender, without a window (`-b`: no display needed)."""
    subprocess.run([str(BLENDER), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                    str(BLENDER_SCRIPT), "--", str(job)], check=True, stdin=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--cast", type=pathlib.Path, required=True)
    parser.add_argument("--sim", type=pathlib.Path, required=True)
    parser.add_argument("--rig", type=pathlib.Path, required=True)
    parser.add_argument("--dressed", type=pathlib.Path, required=True)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--size", type=int, nargs=2, default=(1280, 720))
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--close", action="store_true", help="follow one walker (close_walker) instead of all")
    parser.add_argument("--clips", type=pathlib.Path, help="scene-clips' scene_clips.json, for close_walker")
    parser.add_argument("--ground", type=pathlib.Path, help="the scene's ground triangles (.npy, n x 3 x 3, Y up)")
    parser.add_argument("--build", type=pathlib.Path, help="the person's built body rig (people-body's rig.npz)")
    arguments = parser.parse_args()
    arguments.folder.mkdir(parents=True, exist_ok=True)
    cast = json.loads(arguments.cast.read_text())
    close = close_walker(cast, json.loads(arguments.clips.read_text()) if arguments.clips else None) \
        if arguments.close else None
    job = job_of(arguments.folder, cast, arguments.sim, arguments.rig, arguments.dressed, arguments.seconds,
                 arguments.size, arguments.samples, close,
                 np.load(arguments.ground) if arguments.ground else None,
                 dict(np.load(arguments.build)) if arguments.build else None)
    drawn(job)
    out = joined(arguments.folder, round(arguments.seconds * RATE))
    print(f"peel: {round(arguments.seconds * RATE)} frames in {out}")


if __name__ == "__main__":
    main()
