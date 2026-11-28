"""A generated person made whole in one run (#223): her head mended, her hair regrown, the head put on her body, the
body rigged and its clothes moved as tethered cloth, then drawn standing and walking from four sides.

    python -m tools.characters.generated.person <name> <sources> <out> [--from <step>] [--only <step>]

<sources> holds the person's inputs by name: head/glb/<name>.glb (the TRELLIS.2 head-and-shoulders model),
head/cutouts/<name>.png (the cut-out photo it was made from), head/closeups/<name>.png (the head's close-up photo),
head/marks/<name>.json (`marks.py`'s landmarks of it), body/glb/<name>.glb (the whole body model) and
body/cutouts/<name>.png. Her height, the head model's height and the swap's cut are in PEOPLE; her hair's style is
data/people/hair/gen_<name>.json.

The steps, each on what the one before made (`--from` starts at one, the ones before read from <out>):
1. head: `head.made` (colour, eyes, lids, skin) into <out>/head.
2. hair: the hair split off <out>/head/head.glb and regrown (`python -m tools.characters.generated`) into <out>/hair.
3. swap: the body toned (`colour.toned`), the mended head alone (no eyeballs: `head_swap.py` takes one mesh) put on
   it (`head_swap.py`) into <out>/swap/<name>.glb and its head-to-body record.
4. rig: still_rig `--person` with an empty palette (her own paint, ungraded) and her body before the swap (its
   hand lumps told from the cloth by her own face, `--own-skin`) into <out>/rig, the Head's share on the
   body's neck under the cut moved down the neck chain (`rig_necked`).
5. pieces: what the cloth and the drawing need to carry the head's own pieces onto the rigged body (`pieces_of`):
   the head-to-rig matrix (the swap's head-to-body matrix after the body-to-rig similarity, found by `framed`), the
   cut's level, the hair step's removed triangles and its points laid onto the scalp, all in the head model's own
   frame, and the rig's faces round the neck by where they came from (`neck_roles`).
6. cloth: `cloth.made` at her height, its film FILM_SECONDS long, into <out>/cloth; the rig's head part round the
   neck that is the body's own (its collar, its neck) read by its paint as every other face (`released`), its old
   hair there painted over as the collar or neck it lies on (`cloth.painted_over`).
7. render: `blender_person.py` (Cycles on the graphics card) into <out>/renders.
8. sheet: the turnaround sheet beside the close-up photo, the walking sheet and the film (ffmpeg) in <out>.
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
from scipy.spatial import cKDTree

from tools.characters.generated import cloth, colour, head, head_swap

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOME = pathlib.Path.home()
BLENDER = pathlib.Path(os.environ.get("SCORE_BLENDER", HOME / ".farm-factory-props/blender-mcp/blender-5.2.2/blender"))
BLENDER_LIBS = BLENDER.parent.parent / "libs"  # the libraries this PC's Blender lacks
LIBRARY = pathlib.Path(os.environ.get("SCORE_LIBRARY", HOME / ".farm-factory-props/cache/library/score_lib"))
DRESSED_LIBRARY = pathlib.Path(os.environ.get("SCORE_DRESSED_LIBRARY",
                                              HOME / ".score-this-pc/cache/library/score_lib"))
CLIPS = pathlib.Path(os.environ.get("SCORE_PEOPLE_CLIPS",
                                    HOME / ".farm-factory-motion/candidates/prop-people/woman_stair/rig.npz"))
# Each person's measures: her height (m), the head model's height as drawn (m), the swap's cut's least depth under the
# crown where the cut `head_swap` reads CUT_UNDER_CHIN under the chin is not low enough (`cut_depth`, body heights: the
# hoodie man's beard hangs under his chin; the body's neck, collar and scarf under the cut stay the body's), where a
# collar rises above that cut the depth under the crown from which down the body keeps it
# (`collar_depth`, `head_swap`'s hood: the stairwell woman's puffer collar reaches 0.13, her chin above it stays the
# head's; `hood_open_front` where it is
# open under the chin, a hoodie's, so the chin and beard stay the head's), the dressed body whose
# skeleton and clips she plays (in DRESSED_LIBRARY, or in LIBRARY when `dressed_in` says "props": the hoodie man's
# dress_person_made_v2 is only there); `tether` a garment's longest tether where her clothes want other than
# cloth_tether.TETHER_M (`cloth.made`'s reach: a long coat's hem).
PEOPLE = {"a_stairwell_woman": {"height_m": 1.68, "head_m": 0.42, "collar_depth": 0.125,
                                "dressed": "character/dress_woman_stair_made/1/body.glb"},
          "c_older_woman": {"height_m": 1.64, "head_m": 0.42,
                            "dressed": "character/dress_woman_stair_made/1/body.glb", "tether": {"jacket": 0.10}},
          "b_hoodie_man": {"height_m": 1.80, "head_m": 0.42, "cut_depth": 0.155, "collar_depth": 0.11,
                           "hood_open_front": True,
                           "dressed": "character/dress_person_made_v2/1/body.glb", "dressed_in": "props"}}
STEPS = ("head", "hair", "swap", "rig", "pieces", "cloth", "render", "sheet")
FILM_SECONDS = 4.0  # the walking film (cloth.SECONDS is the cloth sheet's 3 s)
# still_rig's thinning: the detailed head takes some 60% of the faces; at 100k the clothes kept 35k and folded onto
# themselves as fins and dark flecks (whole person round 5, 2026-11-27: 7.2% of the jacket's edges past 150 degrees)
RIG_FACES = 300000
FRAME_KEPT = 0.8  # the body-to-rig fit's share of closest pairs (the feet are moved onto the dressed body's own)
FRAME_ROUNDS = 30
FRAME_POINTS = 20000
OVER_KNEES = 0.35  # the fit reads the body above this share of its height (the shoes are laid on the dressed feet)
# still_rig closes every open loop with a fan from its middle (`still_rig.closed`); the swap's head and body meet at the
# cut as two open loops, so fans reach across the neck's hollow and out under the hair (whole person round 3,
# 2026-11-27: their wedges stood as dark grey shards between the neck and the jacket collar in both close-ups). A rig
# face within FAN_BAND body heights of the cut with a point more than FAN_OFF_M (the rig's metres) off every point of
# the swapped model is such a fan: the drawing takes it off. The armpits' and boots' fans lie far under the band.
FAN_BAND = 0.04
FAN_OFF_M = 0.012
# And from FAN_BAND under the cut up, a rig face whose middle lies more than FAN_MIDDLE_M off every point of the
# swapped model is a fan too (whole person round 6, 2026-11-27: fans closing the hair's loops out under it stood as
# wedges by the chin; a real face's middle lies at most 5.7 mm off, the jacket's round the neck)
FAN_MIDDLE_M = 0.008
# A fan is whole or not at all: a point shared by FAN_SHARED or more faces found above is a fan's middle (an ordinary
# point of the thinned shell has some 6 faces round it), and every face round it from FAN_BAND under the cut up is
# the fan's (`fans_completed`).
# Whole person round 11 (2026-11-28), ray cast off the close-ups: the stairwell woman's neck was a pleated fan of
# skin-coloured triangles from her chin to her collar, all one fan of 685 faces (the swapped body's open loop round
# the neck, 0.041 under the cut to 0.03 over it), its middle 2 mm off the body's own hood layer kept over the cut, so
# only its faces reaching out over FAN_OFF_M were found (about half) and the rest lay along the neck, folded.
FAN_SHARED = 8
# still_rig's head part is every face within 25 cm of the head's middle over the neck (`still_rig.parts_of`), so on
# the swapped body it took the body's own puffer collar top and its own old hair kept round the neck by the swap's
# hood: the collar's top drawn skinned beside the cloth's collar and torn where the sphere cut it, the old hair as
# dark shards over the collar (whole person round 6, 2026-11-27, ray cast off the front close-up: of 15006 head-kind
# pixels in the collar's zone, some 6400 the body's sage collar, 3885 its old hair, 2693 fans, 19 the swap's head).
# A rig face nearer the swapped body's points than its head's, from RELEASE_BAND body heights under the cut up (the
# cut just under the chin: down past the head part's sphere, some 0.22 under the crown), is
# the body's (`neck_roles`): the cloth reads it by its paint as any other face, and keeps it the head (for the drawing
# to take off) only where its paint is the hair's, read on the swap's head faces lying on the head model's hair
# (within HAIR_ON_M of a hair-step hair face, nearer one than any skin face) up to HAIR_READ_BAND over the cut.
RELEASE_BAND = 0.09
HAIR_ON_M = 0.003
HAIR_READ_BAND = 0.06
# still_rig's weights on the body's neck under the cut are the SOMA mean's matched over the surface, and a neck
# standing forward of the mean's lies on its jaw: whole person round 12 (2026-11-28), the stairwell woman's front neck
# 0.025 to 0.04 under the cut (under the Neck1 joint) hung up to 0.42 from the Head beside points hanging none (the
# Head's share there spread 0.13 to 0.37), so as the head turned and bobbed in the walk those faces folded over and
# were drawn from behind as flat pale shards (skinned through the walk, 11 neck faces over 5 mm turned over at once).
# Under the cut the Head's share is moved down the neck chain (`neck_chained`: NECK_CHAIN by each point's height, each
# joint wholly at its own and shared linearly between two), eased in from none at the cut to all of it NECK_UNDER body
# heights under it (moved right up to the cut, the rig's neck there left the head's skirt, which rides with the
# Head's share it hangs from, and showed through it as a sawtooth band); the collar's and the nape's points, hanging
# from no Head, keep theirs.
NECK_CHAIN = ("Chest", "Neck1", "Neck2")
NECK_UNDER = 0.02
SAMPLES, SIZE, FILM_SAMPLES, FILM_WIDTH = 64, 1200, 64, 720
THREADS = 8
TILE = 400  # the sheets' picture height (px)


def sources_of(folder, name):
    """The person's input files in `folder` by her name."""
    return {"head": folder / "head/glb" / f"{name}.glb", "head_cutout": folder / "head/cutouts" / f"{name}.png",
            "closeup": folder / "head/closeups" / f"{name}.png", "marks": folder / "head/marks" / f"{name}.json",
            "body": folder / "body/glb" / f"{name}.glb", "body_cutout": folder / "body/cutouts" / f"{name}.png",
            "style": REPO / "data/people/hair" / f"gen_{name}.json"}


def run(command, log, env=None, low=True):
    """`command` with its output to `log`, at the lowest priority when `low`; refused on a failed exit."""
    with open(log, "w") as stream:
        done = subprocess.run([*(["nice", "-n", "19"] if low else []), *map(str, command)], stdout=stream,
                              stderr=subprocess.STDOUT,
                              cwd=REPO, env={**os.environ, **(env or {})})
    if done.returncode:
        raise SystemExit(f"{command[0]} failed ({done.returncode}): see {log}")


def blender(script, arguments, log, card=False):
    """A Blender run of `script`: on the processor at the lowest priority, or with `card` seeing the graphics card at
    normal priority (a render on the card fed by a niced process waits on every other job's processor work)."""
    shown = {} if card else {"CUDA_VISIBLE_DEVICES": ""}
    run([BLENDER, "-b", "-t", THREADS, "--python", HERE / script, "--", *arguments], log,
        {"LD_LIBRARY_PATH": str(BLENDER_LIBS), **shown}, low=not card)


def head_step(given, out, person):
    beard = bool(json.loads(pathlib.Path(given["style"]).read_text()).get("beard"))
    stats = head.made(given["head"], given["head_cutout"], given["closeup"], given["marks"], out / "head",
                      person["head_m"], beard=beard)
    (out / "head" / "stats.json").write_text(json.dumps(stats, indent=1))


def hair_step(given, out, person):
    run([sys.executable, "-m", "tools.characters.generated", out / "head/head.glb", given["style"], out / "hair",
         "--height", person["head_m"], "--closeup", given["closeup"]], out / "hair.log")


def head_alone(head_glb, path):
    """head.glb's mended head without its eyeballs and cornea (`head_swap.py` takes one mesh), written to `path`."""
    scene = trimesh.load(str(head_glb), process=False)
    scene.geometry["head"].export(str(path))


def swap_step(given, out, person, name):
    folder = out / "swap"
    folder.mkdir(parents=True, exist_ok=True)
    colour.toned(given["body"], given["body_cutout"], folder / "body_toned.glb", folder / "colour.json")
    head_alone(out / "head/head.glb", folder / "head.glb")
    hood = ([person["collar_depth"]] + (["open"] if person.get("hood_open_front") else [])
            if "collar_depth" in person else [])
    blender("head_swap.py", [folder / "body_toned.glb", folder / "head.glb", person.get("cut_depth", 0.0),
                             folder / f"{name}.glb", folder / f"{name}.json", *hood], out / "swap.log")


def dressed_body(person):
    """The dressed body whose skeleton and clips the person plays: in LIBRARY when her `dressed_in` is "props", else
    in DRESSED_LIBRARY."""
    return (LIBRARY if person.get("dressed_in") == "props" else DRESSED_LIBRARY) / person["dressed"]


def rig_step(out, person, name):
    folder = out / "rig"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "palette.json").write_text(json.dumps({"tokens": {}}))
    run([sys.executable, REPO / "tools/characters/still_rig/still_rig.py", out / "swap" / f"{name}.glb",
         dressed_body(person), CLIPS, folder / "palette.json", folder, "--faces", RIG_FACES,
         "--person", "--own-skin", out / "swap" / "body_toned.glb"], out / "rig.log")
    print(f"rig points under the cut moved off the Head: {rig_necked(out, name)}", flush=True)


def cloth_step(out, person):
    cloth.SECONDS = FILM_SECONDS
    pieces = np.load(out / "pieces.npz")
    record = cloth.made(out / "rig/body.glb", CLIPS, out / "cloth", person["height_m"], person.get("tether"),
                        (pieces["released_centres"], pieces["hair_read_centres"]))
    (out / "cloth" / "cloth.json").write_text(json.dumps(record, indent=1))


def framed(source, target, start, kept=FRAME_KEPT, rounds=FRAME_ROUNDS):
    """The similarity (scale, rotation, translation, rms) taking `source` points onto the `target` points they were
    made into by a turn, a scale and a shift (still_rig's stand, its thinning and its outer cut between), from
    `start`: head_swap's two-way trimmed ICP with a free scale."""
    def nearest(points):
        tree = cKDTree(points)
        return lambda queries: tree.query(queries)[1]
    return head_swap.trimmed_icp(source, target, start, nearest, None, rounds, kept, True)


def body_to_rig(swapped, rigged, seed=0):
    """The swapped body's glTF frame onto the rig's (4x4) and the fit's rms: the points above the knees of both
    (`framed`), started stood as still_rig stands it (prop_rig.stood: the same turn and scale on the whole model) and
    centred on the rig's."""
    sys.path.insert(0, str(REPO / "tools/characters/maker"))
    import prop_rig
    turn, scale, _ = prop_rig.stood(swapped, float(np.ptp(rigged[:, 1])))
    rng = np.random.default_rng(seed)
    source = swapped[swapped[:, 1] > swapped[:, 1].min() + OVER_KNEES * np.ptp(swapped[:, 1])]
    target = rigged[rigged[:, 1] > rigged[:, 1].min() + OVER_KNEES * np.ptp(rigged[:, 1])]
    source = source[rng.choice(len(source), min(FRAME_POINTS, len(source)), replace=False)]
    target = target[rng.choice(len(target), min(FRAME_POINTS, len(target)), replace=False)]
    shift = np.median(target, 0) - scale * np.median(source @ turn.T, 0)
    found_scale, rotation, translation, rms = framed(source, target, (scale, turn, shift))
    matrix = np.eye(4)
    matrix[:3, :3] = found_scale * rotation
    matrix[:3, 3] = translation
    return matrix, rms


def swap_on_rig(out, name):
    """The swap's record, the swapped model's points (its glTF frame), the rig's meshes and the swapped body's frame
    onto the rig's with the fit's rms (`body_to_rig`)."""
    record = json.loads((out / "swap" / f"{name}.json").read_text())
    swapped = np.asarray(trimesh.load(str(out / "swap" / f"{name}.glb"), force="mesh", process=False).vertices, float)
    rigged = trimesh.load(str(out / "rig/body.glb"), process=False).geometry
    shell = np.vstack([np.asarray(item.vertices) for key, item in rigged.items() if not key.startswith("far")])
    to_rig, rms = body_to_rig(swapped, shell)
    return record, swapped, rigged, to_rig, rms


def neck_chained(weights, over, head, chain, chain_over):
    """`weights` (points x joints) with the `head` joint's share under the cut moved down the neck chain: onto the
    `chain` joints (their numbers, from the Chest up) by each point's height `over` the cut (body heights;
    `chain_over` the joints', rising), each joint wholly at its own height and shared linearly between two; wholly
    NECK_UNDER under the cut and lower, less and less up to none at the cut."""
    if np.any(np.diff(chain_over) <= 0.0):
        raise SystemExit(f"the neck chain's joints do not rise: {np.round(chain_over, 3).tolist()}")
    profile = np.zeros_like(weights)
    for number, joint in enumerate(chain):
        profile[:, joint] = np.interp(over, chain_over, np.eye(len(chain))[number])
    moved = weights[:, head] * np.clip(-over / NECK_UNDER, 0.0, 1.0)
    out = weights.copy()
    out[:, head] -= moved
    return out + moved[:, None] * profile


def rig_necked(out, name):
    """<out>/rig/body.glb's Head share under the swap's cut moved down the neck chain (`neck_chained`), written over
    its own JOINTS_0 and WEIGHTS_0 (still_rig's four strongest a point); how many points moved."""
    path = out / "rig/body.glb"
    record, _, _, to_rig, _ = swap_on_rig(out, name)
    back = np.linalg.inv(to_rig)
    level, height = float(record["cut_level_gltf_y"]), float(record["body_height_units"])

    def over_of(points):
        return ((points @ back[:3, :3].T + back[:3, 3])[:, 1] - level) / height

    document, blob, names, bind, _ = cloth.still_rig.skeleton_of(path)
    chain = [names.index(joint) for joint in NECK_CHAIN]
    chain_over = over_of(bind[chain, :3, 3])
    data = bytearray(path.read_bytes())
    chunk = 20 + int.from_bytes(data[12:16], "little") + 8
    node = next(found for found in document["nodes"] if found.get("name") == cloth.still_rig.OUTFIT)
    moved = 0
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        attributes = primitive["attributes"]
        points = cloth.skel_usd.accessor(document, blob, attributes["POSITION"]).astype(float)
        joints = cloth.skel_usd.accessor(document, blob, attributes["JOINTS_0"]).astype(int)
        shares = cloth.skel_usd.accessor(document, blob, attributes["WEIGHTS_0"]).astype(float)
        weights = np.zeros((len(points), len(names)))
        np.add.at(weights, (np.repeat(np.arange(len(points)), 4), joints.ravel()), shares.ravel())
        chained = neck_chained(weights, over_of(points), names.index("Head"), chain, chain_over)
        moved += int((np.abs(chained - weights).max(1) > 1e-6).sum())
        for key, values in zip(("JOINTS_0", "WEIGHTS_0"), cloth.still_rig.strongest(chained)):
            found = document["accessors"][attributes[key]]
            view = document["bufferViews"][found["bufferView"]]
            kind = np.dtype(cloth.skel_usd._COMPONENTS[found["componentType"]])
            if view.get("byteStride", kind.itemsize * 4) != kind.itemsize * 4:
                raise SystemExit(f"{path}: {key} is interleaved; only packed weights are written")
            start = chunk + view.get("byteOffset", 0) + found.get("byteOffset", 0)
            packed = np.ascontiguousarray(values, kind).tobytes()
            data[start:start + len(packed)] = packed
    path.write_bytes(bytes(data))
    return moved


def removed_faces(faces, kept):
    """Which of `faces` the hair step took off: those not among the `kept` faces (kept.glb holds every point and the
    faces left, in their order)."""
    width = int(faces.max()) + 1
    keys = (faces[:, 0].astype(np.int64) * width + faces[:, 1]) * width + faces[:, 2]
    kept_keys = (kept[:, 0].astype(np.int64) * width + kept[:, 1]) * width + kept[:, 2]
    return ~np.isin(keys, kept_keys)


def neck_fans(swapped, to_rig, level, height, faces_points):
    """Which rig faces (`faces_points`, each face's three points in the rig's glTF frame) are still_rig's fans across
    the cut's loops: within FAN_BAND of the swapped body's `level` (its glTF y; `height` its height) with a point
    more than FAN_OFF_M off every point of the swapped model (`swapped`, its glTF frame; `to_rig` onto the rig's), or
    from FAN_BAND under it up with the middle more than FAN_MIDDLE_M off, or from FAN_BAND under it up round the middle
    of a fan so found (`fans_completed`; under the band the hoodie man's hood fans are left as they were)."""
    on_rig = swapped @ to_rig[:3, :3].T + to_rig[:3, 3]
    off = cKDTree(on_rig).query(faces_points.reshape(-1, 3))[0].reshape(-1, 3).max(axis=1)
    back = np.linalg.inv(to_rig)
    heights = (faces_points.mean(axis=1) @ back[:3, :3].T + back[:3, 3])[:, 1]
    middle_off = cKDTree(on_rig).query(faces_points.mean(axis=1))[0]
    over_band = heights > level - FAN_BAND * height
    found = (((np.abs(heights - level) < FAN_BAND * height) & (off > FAN_OFF_M))
             | (over_band & (middle_off > FAN_MIDDLE_M)))
    return found | (fans_completed(faces_points, found) & over_band)


def fans_completed(faces_points, found):
    """`found` (per face of `faces_points`, each face's three points) with every face round a point that FAN_SHARED or
    more found faces share (a fan's middle: its faces lying along the model are its too)."""
    points, which = np.unique(faces_points.reshape(-1, 3), axis=0, return_inverse=True)
    which = which.reshape(-1, 3)
    shared = np.bincount(which[found].ravel(), minlength=len(points))
    return found | (shared[which] >= FAN_SHARED).any(axis=1)


def neck_roles(head_points, body_points, to_rig, level, height, middles, hair, skin):
    """The rig's faces (`middles`, the rig's glTF frame) round the neck by where they came from: (released: nearer
    the swapped body's points than its head's, from RELEASE_BAND under the swapped body's `level` up (`head_points`,
    `body_points` its two primitives' points in its glTF frame, `height` its height, `to_rig` onto the rig's); hair:
    nearer its head's, up to HAIR_READ_BAND over the cut, within HAIR_ON_M of a `hair` point and nearer one than any
    `skin` point (the head model's hair and skin face middles on the rig))."""
    def on_rig(points):
        return np.asarray(points, float) @ to_rig[:3, :3].T + to_rig[:3, 3]

    to_head = cKDTree(on_rig(head_points)).query(middles)[0]
    to_body = cKDTree(on_rig(body_points)).query(middles)[0]
    back = np.linalg.inv(to_rig)
    over = ((middles @ back[:3, :3].T + back[:3, 3])[:, 1] - level) / height
    to_hair = cKDTree(hair).query(middles)[0]
    to_skin = cKDTree(skin).query(middles)[0]
    released = (to_body <= to_head) & (over > -RELEASE_BAND)
    on_hair = (to_head < to_body) & (over >= 0.0) & (over < HAIR_READ_BAND) & (to_hair < HAIR_ON_M) & (to_hair < to_skin)
    return released, on_hair


def swap_parts(path):
    """The swapped model's two primitives' points (its glTF frame): (the head's, the highest; the body's)."""
    parts = [np.asarray(item.vertices, float) for item in trimesh.load(str(path), process=False).geometry.values()]
    parts.sort(key=lambda points: points[:, 1].mean())
    return parts[-1], np.concatenate(parts[:-1])


def pieces_of(out, name):
    """<out>/pieces.npz: head_to_rig (the head model's glTF frame onto the rig's), body_to_rig, the cut's level (the
    swapped body's glTF y), the hair step's face middles and removed faces, its points and how far each was laid
    onto the scalp (`hair_*`, the head model's own units), the hair's scale (its metres over the model's units) and the
    middles of still_rig's fans across the cut's loops (`neck_fans`), of the rig's faces round the neck that are the
    swapped body's own (`released_centres`, fans left out) and of its head's faces on the hair (`hair_read_centres`;
    `neck_roles`), all in the rig's glTF frame."""
    record, swapped, rigged, to_rig, rms = swap_on_rig(out, name)
    triangles = np.vstack([np.asarray(item.vertices)[np.asarray(item.faces)] for key, item in rigged.items()
                           if not key.startswith("far")])
    fans = neck_fans(swapped, to_rig, float(record["cut_level_gltf_y"]),
                     float(record["body_height_units"]), triangles)
    model = trimesh.load(str(out / "head/head.glb"), force="mesh", process=False)
    kept = trimesh.load(str(out / "hair/kept.glb"), force="mesh", process=False)
    points = np.asarray(model.vertices, float)
    hair_scale = float(np.load(out / "hair/groom.npz")["height"]) / float(np.ptp(points[:, 1]))
    if len(kept.vertices) != len(points):
        raise SystemExit(f"kept.glb has {len(kept.vertices)} points, head.glb {len(points)}: not the hair's model")
    faces = np.asarray(model.faces)
    removed = removed_faces(faces, np.asarray(kept.faces))
    head_to_rig = to_rig @ np.asarray(record["head_to_body_gltf"])
    centres = points[faces].mean(1) @ head_to_rig[:3, :3].T + head_to_rig[:3, 3]
    middles = triangles.mean(axis=1)
    released, on_hair = neck_roles(*swap_parts(out / "swap" / f"{name}.glb"), to_rig,
                                   float(record["cut_level_gltf_y"]), float(record["body_height_units"]), middles,
                                   centres[removed], centres[~removed])
    released &= ~fans
    saved = {"head_to_rig": head_to_rig, "body_to_rig": to_rig,
             "level": record["cut_level_gltf_y"], "hair_centres": points[faces].mean(1).astype(np.float32),
             "hair_removed": removed, "hair_points": points.astype(np.float32),
             "hair_laid": (np.asarray(kept.vertices) / hair_scale - points).astype(np.float32),
             "hair_scale": hair_scale, "fan_centres": middles[fans].astype(np.float32),
             "released_centres": middles[released].astype(np.float32),
             "hair_read_centres": middles[on_hair].astype(np.float32)}
    np.savez_compressed(out / "pieces.npz", **saved)
    return {"body_to_rig_rms_m": round(float(rms), 5), "hair_removed": int(saved["hair_removed"].sum()),
            "laid_points": int((np.linalg.norm(saved["hair_laid"], axis=1) > 1e-7).sum()), "neck_fans": int(fans.sum()),
            "released": int(released.sum()), "hair_read": int(on_hair.sum())}


def render_step(given, out):
    width = FILM_WIDTH * 3 // 2  # blender_cloth's film is 2:3 by its height
    blender("blender_person.py", [REPO, out / "rig/body.glb", out / "cloth/cloth.npz", LIBRARY, out / "renders",
                                  SAMPLES, SIZE, FILM_SAMPLES, width, out, given["closeup"]], out / "render.log",
            card=True)


def tile(path, height=TILE):
    """A picture scaled to `height`."""
    picture = Image.open(path).convert("RGB")
    return picture.resize((round(picture.width * height / picture.height), height), Image.LANCZOS)


def sheet(rows, path):
    """Rows of (label, picture path) laid out one under the other, each picture labelled under it."""
    tiles = [[(label, tile(picture)) for label, picture in row] for row in rows]
    width = max(sum(picture.width for _, picture in row) for row in tiles)
    canvas = Image.new("RGB", (width, len(tiles) * (TILE + 24)), "white")
    draw = ImageDraw.Draw(canvas)
    for number, row in enumerate(tiles):
        left = 0
        for label, picture in row:
            canvas.paste(picture, (left, number * (TILE + 24)))
            draw.text((left + 6, number * (TILE + 24) + TILE + 6), label, fill="black")
            left += picture.width
    canvas.save(path, quality=92)


def sheet_step(given, out, name):
    renders = out / "renders"
    sheet([[(f"standing {view}", renders / f"standing_{view}.png") for view in
            ("front", "three_quarter", "side", "back")],
           [("close-up front", renders / "close_front.png"), ("close-up three quarter", renders / "close_three_quarter.png"),
            ("the close-up photo", given["closeup"])]], out / f"{name}_turnaround.jpg")
    sheet([[(f"{view} {point.replace('_', ' ')}", renders / f"walk_{view}_{point}.png")
            for point in ("left_ahead", "passing", "right_ahead")] for view in ("side", "three_quarter")]
          + [[("back passing", renders / "walk_back_passing.png")]], out / f"{name}_walking.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(cloth.FPS), "-i",
                    str(renders / "film/%03d.png"), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "18", str(out / f"{name}_walking.mp4")], check=True)


def made(name, folder, out, first="head", only=None):
    """The whole person `name` from `folder`'s inputs into `out`, from the step `first` on (or `only` that step)."""
    person, given = PEOPLE[name], sources_of(folder, name)
    out.mkdir(parents=True, exist_ok=True)
    steps = {"head": lambda: head_step(given, out, person), "hair": lambda: hair_step(given, out, person),
             "swap": lambda: swap_step(given, out, person, name), "rig": lambda: rig_step(out, person, name),
             "cloth": lambda: cloth_step(out, person), "pieces": lambda: print(pieces_of(out, name), flush=True),
             "render": lambda: render_step(given, out), "sheet": lambda: sheet_step(given, out, name)}
    chosen = [only] if only else STEPS[STEPS.index(first):]
    for step in chosen:
        steps[step]()
        print(f"person step {step} done", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("name", choices=sorted(PEOPLE))
    parser.add_argument("sources", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--from", dest="first", choices=STEPS, default="head")
    parser.add_argument("--only", choices=STEPS)
    options = parser.parse_args()
    made(options.name, options.sources, options.out, options.first, options.only)
    print(f"PERSON DONE {options.out}", flush=True)


if __name__ == "__main__":
    main()
