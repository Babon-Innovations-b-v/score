"""The video clips (experimental, #52; CONTEXT.md "video clip"): a body's motion captured from a video the creator
uploads, played by the people's bodies beside Kimodo's generated clips. Each video kept at
`{home}/design/clips/<clip>.mp4` is one environment row of its own:

    video-clip-<clip>   paid: the video copied into the output (the store keeps the upload), SAM 3D Body run over it
                        frame by frame on one rented characters machine (tools/characters/clips/video_motion.py through
                        tools/props/cloud/characters.py: sam3dbody-cpp's offline extractor, one BVH per person seen, the
                        longest kept), then here, free: retargeted onto SOMA-X's 27 kept joints of the people's rig
                        (people-clips-made's rig.npz), resampled to 30 frames a second, smoothed and put on the spot
                        (tools/characters/clips/retarget.py). Out: clip.bvh, clip.npz ({clip [F, 27, 4, 4] each joint
                        against its parent in metres, the rig's own `clip_<name>` form; names; parents}), record.json,
                        make.json (the machine's minutes) and video.mp4.

Gates (unknown blocks): `clip read`: at least LEAST_FRAMES frames, on the rig's joints, every number finite and every
turn a rotation; `steady`: no joint turns more than MOST_TURN_DEG from one frame to the next (a flip or a lost track).

Price: no video was ever read by a stage, so the row has no measured price; EUROS is a guess the runner keeps apart.
Untested until a paid run: the extractor on the characters machine, its BVH's joint names and turns as the retarget
reads them, and the clip played on a body. Only the retarget is tested, on a synthetic sequence (retarget_test.py).
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np

from score import contracts, graph
from score.checks import FAIL, PASS, UNKNOWN, Check, Verdict
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
CLIP_TOOLS = REPO / "tools/characters/clips"
CLOUD = REPO / "tools/props/cloud"
VIDEOS = PROPS_HOME / "design" / "clips"
ROW = "video-clip"
RIG = "people-clips-made"
SIGMA = 2.0  # frames at 30 a second: the smoothing of the turns read frame by frame
LEAST_FRAMES = 30  # people/body.py's LEAST_FRAMES: under a second reads as a twitch
MOST_TURN_DEG = 20.0  # in one frame at 30 a second, 600 degrees a second: past it a joint flipped
# Not measured: one characters machine's set-up (14 min measured, characters.SETUP_MINUTES) and the read of one
# short video (never timed) on an L4 at EUR 0.79 an hour, rounded up.
EUROS = 0.5


def make_folder(place, video, name):
    """The make folder characters.py runs video_motion.py on: in/spec.json and in/files/video.mp4."""
    (place / "in" / "files").mkdir(parents=True)
    shutil.copy2(video, place / "in" / "files" / "video.mp4")
    spec = {"name": f"video-{name}", "program": "video_motion.py", "steps": ["video"], "references": [],
            "files": {"video": "in/files/video.mp4"}, "approved": f"the creator's upload, design/clips/{name}.mp4"}
    (place / "in" / "spec.json").write_text(json.dumps(spec, indent=1))
    return place


def read_on_machine(place, who):
    """The video read by SAM 3D Body on a rented characters machine: place/out/clip.bvh and make.json."""
    sys.path.insert(0, str(REPO / "tools/props"))
    from paths import HOME
    subprocess.run([str(HOME / "env/bin/python"), str(CLOUD / "characters.py"), str(place), "--who", who], check=True)


def clip_of(bvh_text, rig):
    """(the clip on the rig, its record's numbers): retargeted, at 30 a second, smoothed and on the spot."""
    sys.path.insert(0, str(CLIP_TOOLS))
    import retarget
    bvh = retarget.read_bvh(bvh_text)
    local = retarget.retarget(bvh, rig["names"], rig["parents"], rig["bind"])
    local = retarget.smoothed(retarget.resampled(local, bvh["fps"]), SIGMA)
    local, drift, moved_back = retarget.on_the_spot(local, rig["names"])
    sources = retarget.source_of(list(map(str, rig["names"])), list(rig["parents"]), set(bvh["names"]))
    unmoved = [str(name) for name, source in zip(rig["names"], sources) if source is None]
    return local, {"frames": len(local), "seconds": round(len(local) / retarget.RATE, 3), "read_fps": bvh["fps"],
                   "rate": retarget.RATE, "sigma_frames": SIGMA, "drift_metres": round(drift, 3),
                   "moved_back_metres": round(moved_back, 3), "unmoved_joints": unmoved}


def make(inputs, out, seed, params):
    name = params["clip"]
    shutil.copy2(inputs["video"], out / "video.mp4")
    place = make_folder(out / "make", inputs["video"], name)
    read_on_machine(place, f"{ROW}-{name}")
    for found in ("clip.bvh", "make.json"):
        shutil.copy2(place / "out" / found, out / found)
    shutil.rmtree(place)
    with np.load(pathlib.Path(inputs[RIG]) / "rig.npz") as held:
        rig = {key: held[key] for key in ("names", "parents", "bind")}
    local, numbers = clip_of((out / "clip.bvh").read_text(), rig)
    np.savez_compressed(out / "clip.npz", clip=local, names=rig["names"], parents=rig["parents"])
    (out / "record.json").write_text(json.dumps({
        "clip": name, "video_sha256": hashlib.sha256((out / "video.mp4").read_bytes()).hexdigest(),
        "source": "SAM 3D Body, sam3dbody-cpp's offline extractor (its BVH on bvh/body_mhr.bvh)", **numbers},
        indent=1))


def faults(folder):
    return [f"no {name}" for name in ("clip.npz", "record.json") if not (pathlib.Path(folder) / name).exists()]


def held_clip(output):
    with np.load(output / "clip.npz") as held:
        return held["clip"], [str(name) for name in held["names"]]


def judge_read(output, inputs, evidence):
    """At least LEAST_FRAMES frames on the rig's joints, finite, every turn a rotation."""
    clip, names = held_clip(output)
    with np.load(pathlib.Path(inputs[RIG]) / "rig.npz") as rig:
        wanted = [str(name) for name in rig["names"]]
    turns = clip[..., :3, :3]
    skew = float(np.abs(np.swapaxes(turns, -1, -2) @ turns - np.eye(3)).max()) if clip.size else 0.0
    failing = ([f"{len(clip)} frames, under {LEAST_FRAMES}"] if len(clip) < LEAST_FRAMES else []) + \
              (["not on the rig's joints"] if names != wanted else []) + \
              (["a number not finite"] if not np.isfinite(clip).all() else []) + \
              ([f"a turn off a rotation by {skew:.2g}"] if skew > 1e-4 else [])
    return Verdict("clip read", FAIL if failing else PASS, "; ".join(failing) or f"{len(clip)} frames on the rig",
                   {"frames": len(clip)}, {}, tuple(failing))


def judge_steady(output, inputs, evidence):
    """No joint turns more than MOST_TURN_DEG from one frame to the next."""
    clip, names = held_clip(output)
    turns = clip[..., :3, :3]
    step = np.swapaxes(turns[:-1], -1, -2) @ turns[1:]
    degrees = np.degrees(np.arccos(np.clip((np.trace(step, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))
    worst = float(degrees.max()) if degrees.size else 0.0
    jumps = sorted({names[joint] for _, joint in zip(*np.nonzero(degrees > MOST_TURN_DEG))})
    return Verdict("steady", FAIL if jumps else PASS,
                   f"{', '.join(jumps)} turn over {MOST_TURN_DEG:g} degrees in a frame" if jumps else
                   f"the largest turn in a frame {worst:.1f} degrees", {"worst degrees": round(worst, 2)},
                   {"worst degrees": "lower"}, tuple(jumps))


def guarded(name, judge):
    """A check whose missing or unreadable output answers unknown, never pass."""
    def judged(output, inputs, evidence):
        try:
            return judge(output, inputs, evidence)
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as missing:
            return Verdict(name, UNKNOWN, f"cannot tell: {type(missing).__name__}: {missing}")
    return Check(name, judged)


def row(name):
    """The row of one uploaded video."""
    return graph.Stage(f"{ROW}-{name}", "world", make, contracts.Contract(ROW, 1, faults),
                       (guarded("clip read", judge_read), guarded("steady", judge_steady)),
                       files={"video": "{home}/design/clips/" + f"{name}.mp4",
                              "clip tools": "{repo}/tools/characters/clips"},
                       after={RIG: (RIG, 1)}, params={"clip": name}, paid=True, euros=EUROS)


def rows():
    """A row a video the creator uploaded; none while there is none."""
    return tuple(row(path.stem) for path in sorted(VIDEOS.glob("*.mp4")))
