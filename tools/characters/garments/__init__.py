"""A person dressed in sewn clothes (PRD #223, its first clothes slice #225): GarmentCode's sewing patterns (pygarment,
MIT) sized to the person's SOMA body, draped and worn over one clip on Newton's SolverVBD (Apache-2.0), kept as a
time-sampled OpenUSD point cache beside the body, finished with score_lib surfaces and rendered in Blender.

    python -m tools.characters.garments <look> --outfit <outfit.json> --clip <clip> --out <folder> [--frames N]

The look is a built person of the people line: its fit (`PEOPLE/<look>/made/fit/rig.npz`: SOMA's surface on the
person's bones, `source_points`) and the clips rig every body plays (`CLIPS`). The outfit file names each garment's
GarmentCode design and settings, the mean body the unread measurements come from, and each garment's library surface;
the cloth's values are its recipe's row in data/physics/cloth.json, as the people cloth stage reads them.

Steps, each in its own Python: the body measured (`measure.py`, here); the patterns and box meshes
(`inside/pattern.py`, GarmentCode's environment, `inside/garment_env.sh`); the drape and the clip (`inside/drape.py`,
Newton's, score/stages/physics/inside/newton_env.sh) through this PC's card queue; the point cache (`cache.py`,
here); the pictures (`inside/render.py`, Blender). Written in --out: body.npz, pattern/, drape.npz, outfit.usda,
measures.json (body penetration every clip frame, drape seconds a frame), still.png and turn/.
"""
import json
import os
import pathlib
import subprocess

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
HOME = pathlib.Path.home()
PEOPLE = HOME / ".farm-factory-motion/candidates/prop-people"
CLIPS = PEOPLE / "people-clips/people-clips-make/out/rig.npz"
ENVS = pathlib.Path(os.environ.get("PROPS_HOME", HOME / ".farm-factory-props")) / "envs"
GARMENT_ENV, NEWTON_ENV = ENVS / "garment_env", ENVS / "newton_env"
GARMENT_SCRIPT = REPO / "tools/characters/garments/inside/garment_env.sh"
NEWTON_SCRIPT = REPO / "score/stages/physics/inside/newton_env.sh"
CLOTH_TABLE = REPO / "data/physics/cloth.json"
CARD_QUEUE = REPO / "tools/cloud/backends/card_queue.py"
RATE = 30.0  # the clips rig's frames a second (score/stages/sim_body/_body.py RATE)
# The body's turn from its bind (A-pose) to the clip's first frame: lowered over 1 s, the arms caught the sleeves'
# underarm cloth against the torso (up to 39 mm inside the body, 2026-11-24).
TURN_SECONDS = 2.0
THICKNESS_M = 0.003  # the cloth's thickness: the people gates' (tools/characters/maker/bodycloth.py MARGIN_MM)
RESOLUTION_CM = 1.5  # GarmentCode's mesh spacing (its datasets' 1.0 to 2.0 cm)
# 40 substeps a frame: at 20 woven cotton's membrane (3e4 N/m) on a walking body blew up at frame 33 (2026-11-24).
DRAPE = {"device": "cuda:0", "rate": RATE, "substeps": 40, "iterations": 10, "gravity": 9.81, "sew_seconds": 4.0,
         "still_seconds": 1.0,
         # Cloth on the body: the soft contact of Newton's VBD dressing benchmark (newton-physics/newton#3084: ke 1e5,
         # kd 0.1; Newton's own default ke 1e3 let a woven cotton's 3e4 N/m membrane through the body by up to 10 cm,
         # 2026-11-24), Newton's default friction (mu 0.5), the margin the cloth's thickness; cloth keeps the cloth's
         # thickness off cloth, looked for a thickness further.
         "contact": {"mu": 0.5, "ke": 1.0e5, "kd": 0.1, "margin": THICKNESS_M},
         "self": {"margin": THICKNESS_M, "gap": THICKNESS_M}}
CARD_GB = 4.0  # the drape's card share (one outfit, one body)


def built_body(look, clip):
    """The person's body for the drape: its SOMA surface at the bind, the clip played on its build (the sim body's
    `person_rig`), and the body's skin every frame of the turn from the bind into the clip and of the clip."""
    from score.stages.sim_body import _body
    from score.stages.people_cloth import skinned
    from tools.characters import played
    clips_rig = dict(np.load(CLIPS))
    built = dict(np.load(PEOPLE / look / "made/fit/rig.npz"))
    found, _ = _body.person_rig(clips_rig, built)
    parents, bind = np.asarray(clips_rig["parents"]), np.asarray(found["bind"], dtype=float)
    local = np.asarray(found[f"clip_{clip}"], dtype=float)
    worlds = np.concatenate([played.chained(turned(bind, local[0], parents), parents),
                             played.chained(local, parents)])
    weights = np.asarray(clips_rig["weights"], dtype=float)
    joints = np.tile(np.arange(weights.shape[1]), (len(weights), 1))
    points = np.asarray(found["points"], dtype=float)
    frames = skinned(points, joints, weights, np.concatenate([bind[None], worlds]), bind)
    return {"bind": points, "faces": np.asarray(built["source_faces"], dtype=np.int64), "weights": weights,
            "names": np.asarray(clips_rig["names"]), "joints": bind, "frames": frames,
            "clip_start": np.array(1 + int(round(TURN_SECONDS * RATE)))}


def turned(bind, first, parents):
    """The joints against their parents from the bind's to the clip's first frame's, over TURN_SECONDS (turns
    slerped, places moved straight): frames x joints x 4 x 4, the bind left out and the clip's first frame in."""
    from scipy.spatial.transform import Rotation, Slerp
    start = np.array([bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
                      for joint, parent in enumerate(parents)])
    count = int(round(TURN_SECONDS * RATE))
    shares = np.arange(1, count + 1) / count
    found = np.zeros((count, len(parents), 4, 4))
    found[:, :, 3, 3] = 1.0
    for joint in range(len(parents)):
        turns = Slerp([0.0, 1.0], Rotation.from_matrix([start[joint, :3, :3], first[joint, :3, :3]]))
        found[:, joint, :3, :3] = turns(shares).as_matrix()
        found[:, joint, :3, 3] = start[joint, :3, 3] * (1.0 - shares[:, None]) + first[joint, :3, 3] * shares[:, None]
    return found


def centre(body):
    """The point under the person's chest (Spine2) on its floor: GarmentCode lays a pattern round x = z = 0."""
    names = [str(name) for name in body["names"]]
    spine = np.asarray(body["joints"])[names.index("Spine2")][:3, 3]
    return np.array([spine[0], 0.0, spine[2]])


def measured_body(body):
    """The body's own measurements (measure.py), taken with its chest over x = z = 0."""
    from tools.characters.garments import measure
    shift = centre(body)
    joints = np.array(body["joints"])
    joints[:, :3, 3] -= shift
    return measure.measured(body["bind"] - shift, body["faces"], body["weights"], body["names"], joints)


def cloth_material(surface):
    """Newton's cloth values of a library surface: its recipe's row of data/physics/cloth.json, turned as the people
    cloth stage turns it (score/stages/people_cloth `material_of`) at RESOLUTION_CM's mean edge."""
    from score.stages.people_cloth import material_of
    table = json.loads(CLOTH_TABLE.read_text())["recipes"]
    if surface["recipe"] not in table:
        raise SystemExit(f"{surface['name']}: its recipe {surface['recipe']!r} has no row in {CLOTH_TABLE.name}")
    edge = RESOLUTION_CM / 100.0
    triangle = np.array([[0.0, 0.0, 0.0], [edge, 0.0, 0.0], [0.0, edge, 0.0]])
    return material_of(table[surface["recipe"]], triangle, np.array([[0, 1, 2]]), THICKNESS_M)


def environment(script, env):
    """An environment built by its script (once; the script's own mark)."""
    subprocess.run(["bash", str(script), str(env)], check=True, stdout=subprocess.DEVNULL)


def patterns(outfit, body, out):
    """GarmentCode's patterns and box meshes of the outfit on the body, in `out`/pattern/."""
    folder = out / "pattern"
    folder.mkdir(parents=True, exist_ok=True)
    job = {"garmentcode": str(GARMENT_ENV / "GarmentCode"), "out": str(folder), "measured": measured_body(body),
           "mean": outfit["mean"], "resolution": RESOLUTION_CM,
           "garments": [{"name": garment["name"], "design": garment["design"], "set": garment.get("set", {})}
                        for garment in outfit["garments"]]}
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    environment(GARMENT_SCRIPT, GARMENT_ENV)
    subprocess.run([str(GARMENT_ENV / "bin/python"), str(REPO / "tools/characters/garments/inside/pattern.py"),
                    str(folder / "job.json")], check=True)
    return folder


def holds(garment, record, measurements, shift):
    """The points a garment's sewing draws to a level, as GarmentCode's simulation attaches them while it sews
    (pygarment/meshgen/garment.py `_add_attachment_labels`): a neckline's sides (`right_collar`, `left_collar`) to
    either side of the neck, a centimetre inside it (its neck_w less 2 cm), along x."""
    half = (measurements["neck_w"] - 2.0) / 2.0 / 100.0
    return [{"label": label, "axis": 0, "value": float(shift[0] + side * half)}
            for label, side in (("right_collar", -1.0), ("left_collar", 1.0)) if f"label/{label}" in record]


def draped(outfit, body, pattern_folder, out, frames):
    """The outfit sewn, draped and worn over the clip on Newton, through this PC's card queue: drape.npz."""
    clip_end = int(body["clip_start"]) + frames if frames else len(body["frames"])
    np.savez(out / "body.npz", bind=body["bind"], faces=body["faces"], frames=body["frames"][:clip_end],
             clip_start=body["clip_start"])
    shift = centre(body)
    measurements = json.loads((pattern_folder / "measurements.json").read_text())
    records = {garment["name"]: np.load(pattern_folder / garment["name"] / f"{garment['name']}.npz")
               for garment in outfit["garments"]}
    job = dict(DRAPE, body=str(out / "body.npz"), garments=[
        {"name": garment["name"], "record": str(pattern_folder / garment["name"] / f"{garment['name']}.npz"),
         "offset": shift.tolist(), "worn": garment.get("worn", []),
         "holds": holds(garment, records[garment["name"]], measurements, shift),
         "material": cloth_material(garment["surface"])}
        for garment in outfit["garments"]])
    (out / "drape.json").write_text(json.dumps(job, indent=1))
    environment(NEWTON_SCRIPT, NEWTON_ENV)
    subprocess.run(["python3", str(CARD_QUEUE), "run", "--job", "garment-drape", "--card-gb", str(CARD_GB),
                    "--priority", "other", "--", str(NEWTON_ENV / "bin/python"),
                    str(REPO / "tools/characters/garments/inside/drape.py"), str(out / "drape.json"),
                    str(out / "drape.npz")], check=True)
    return out / "drape.npz"


def penetration(drape, thickness_m):
    """Body penetration of each garment over the clip, from the drape's signed distances: the points inside the body
    on the worst frame, the frames with any, the deepest (mm), and the same past the cloth's thickness."""
    found = {}
    for key in [key for key in drape if key.startswith("inside/")]:
        distance = np.asarray(drape[key], dtype=float)
        inside, past = distance < 0.0, distance < -thickness_m
        found[key[len("inside/"):]] = {
            "points": int(distance.shape[1]), "frames": int(distance.shape[0]),
            "most points inside on a frame": int(inside.sum(axis=1).max()),
            "frames with a point inside": int(inside.any(axis=1).sum()),
            "deepest mm": round(float(max(0.0, -distance.min())) * 1000.0, 2),
            "frames with a point past the thickness": int(past.any(axis=1).sum())}
    return found


def measures(drape, out):
    """measures.json: penetration, and the drape's seconds a clip frame on this card."""
    clip_frames = max(1, len(drape[next(key for key in drape if key.startswith("inside/"))]) - 1)
    found = {"engine": str(drape["engine"]), "penetration": penetration(drape, THICKNESS_M),
             "sew seconds": round(float(drape["seconds/sew"]), 1),
             "clip seconds a frame": round(float(drape["seconds/clip"]) / clip_frames, 3),
             "substeps a frame": DRAPE["substeps"], "iterations": DRAPE["iterations"]}
    (out / "measures.json").write_text(json.dumps(found, indent=1))
    return found
