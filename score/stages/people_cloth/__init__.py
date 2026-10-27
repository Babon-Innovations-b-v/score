"""The people cloth stage (experimental; owner 2026-10-27, "bring back", PRD #56): row `people-cloth@<place>`, each
character's loose garment parts simulated as cloth on Newton's VBD solver against its sim body (sim-body@<place>),
for a place whose design shows people. The owner retired Newton's drapes on 2026-10-10 (GarmentCode patterns sewn and
settled on a still body, then baked: their silhouette failed against the reference and a coat blew up); this is not
that: the built, dressed garment stays as it is, and only its loose cloth moves, riding a moving body.

    make     for each sim body of sim-body's run whose cast look has a dressed body (people-dress-<look>, its optional
             reads, as the characters layer reads them) and a built one (people-body-<look>: its rig.npz), each
             garment part of the dressed body.glb (material role `garment`, the far body left out) with loose points:
             a point is loose where the shell gate calls it loose cloth (people_bodies/bodies.py: its rig point's
             offset off the fitted SOMA shell over OFFSET_MOST, an edge, hem or cap the shell could not follow);
             every other point of the part rides the skin. The person's skeleton plays the sim body's run: each
             segment turned against its parent as the sim turned it, on the person's own bones (the asset's way of
             playing a clip), and the part is skinned on it (its glTF joints and weights); the body surface under the
             clothes (rig.npz's source surface, the clips rig's weights) is cut into one piece a sim segment, each a
             mesh collider moving with its segment. Its cloth values come from the part's library surface: the
             recipe it is made with (surface-library@people), its row in data/physics/cloth.json, never typed here; a
             part whose recipe has no row is named and left baked. inside/cloth.py runs every part at once in
             Newton's own Python on this machine's card. Written: people_cloth.json (each person and part: its
             points, loose points, material, measures, what was left out and why), layers/people_cloth.usdc (each
             simulated part's baked mesh made invisible and a Mesh in its place, its points every frame:
             /<place>/Characters/<name>/Turned/Cloth/<part>)
    gates    through   no loose point deeper inside the body surface (posed each frame) than the cloth's thickness
                       (bodycloth.MARGIN_MM, the people gates' 3 mm), any frame
             stretch   no edge touching a loose point longer than its built length, or the skin's length for it that
                       frame where the skin draws it longer, by over STRETCH_MOST, past SETTLE
             rests     on a still clip (STILL), the loose points move no faster than the skin would carry them by over
                       REST_MOST on the mean, over the run's last REST_SECONDS

Not here: self contact (a fold may pass through itself), the characters layer's clip cut and start (the layer's
samples are the sim body's own frames from 0), the assembly taking the layer (nothing reads it yet), a crowd (it has
no sim bodies).
"""
import json
import os
import pathlib
import subprocess
import time

import numpy as np

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
INSIDE = "score/stages/people_cloth/inside/cloth.py"
ENV_SCRIPT = "score/stages/physics/inside/newton_env.sh"
ENV = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "envs/newton_env"
SIM_ROW = "sim-body"
CLIPS_ROW = "people-clips-made"
BODY = "people-body"
LINE = "people"
LIBRARY_ROWS = ("surface-library", "finish-route-palette")
LAYER = "layers/people_cloth.usdc"
RECORD = "people_cloth.json"
GARMENT = "garment"
FAR = "far"
SUBSTEPS = 10
ITERATIONS = 10
DEVICE = "cuda:0"
# Gate limits, picked 2026-10-27 before any run, UNMEASURED against footage: woven cloth stretched a tenth past its
# built length reads as rubber; loose cloth on a still body settles to the body's own speed within 1 cm/s.
STRETCH_MOST = 0.10
REST_MOST = 0.01  # m/s
REST_SECONDS = 0.5
SETTLE = 0.5  # seconds let pass before the stretch gate reads: the cloth leaving its built shape for its hang
STILL = ("standing",)
WELD = 1e-6  # metres: glTF points this near are one cloth point (a seam split for its normals)


def files(place):
    """The cloth run's script, the Python it runs in and the cloth materials table."""
    return {"cloth script": "{repo}/" + INSIDE, "sim env": "{repo}/" + ENV_SCRIPT,
            "cloth materials": "{data}/physics/cloth.json"}


def library_place(place):
    """The people line, whose surface library dresses every person (read beside)."""
    return (LINE,)


# --- the body and its parts ----------------------------------------------------------------------------------------

def bodycloth():
    """tools/characters/maker/bodycloth.py, loaded by path (never on the import path: the cast overlay's rule)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bodycloth", REPO / "tools/characters/maker/bodycloth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accessor(document, rest, index):
    """A glTF accessor's values, one row a value (a matrix flattened)."""
    from score.stages.people import dress
    found = document["accessors"][index]
    if found["type"] != "MAT4":
        return dress.accessor(document, rest, index)
    blob = rest[8:8 + int.from_bytes(rest[:4], "little")]
    view = document["bufferViews"][found["bufferView"]]
    start = view.get("byteOffset", 0) + found.get("byteOffset", 0)
    return np.frombuffer(blob, np.float32, found["count"] * 16, start).reshape(-1, 16)


def garment_parts(document, rest):
    """Every garment primitive of the body's mesh nodes but the far body: (node name, primitive number, material
    index, points at the bind, faces, joints, weights)."""
    found = []
    for node in document["nodes"]:
        if "mesh" not in node or node.get("name") == FAR:
            continue
        for number, primitive in enumerate(document["meshes"][node["mesh"]]["primitives"]):
            material = document["materials"][primitive["material"]]
            if material.get("extras", {}).get("role") != GARMENT:
                continue
            attributes = primitive["attributes"]
            found.append({"node": node.get("name", f"mesh{node['mesh']}"), "number": number,
                          "material": primitive["material"], "name": material.get("name", ""),
                          "points": accessor(document, rest, attributes["POSITION"]).astype(float),
                          "faces": accessor(document, rest, primitive["indices"]).reshape(-1, 3).astype(np.int64),
                          "joints": accessor(document, rest, attributes["JOINTS_0"]).astype(np.int64),
                          "weights": accessor(document, rest, attributes["WEIGHTS_0"]).astype(float),
                          "uv": (accessor(document, rest, attributes["TEXCOORD_0"]).astype(float)
                                 if "TEXCOORD_0" in attributes else None)})
    return found


def loose_of(points, rig, limit):
    """Each point loose or not: its nearest rig point's offset off the fitted shell over `limit` (the shell gate's
    loose cloth)."""
    from scipy.spatial import cKDTree
    _, nearest = cKDTree(rig["points"]).query(points)
    return np.asarray(rig["shell_offsets"])[nearest] > limit


def welded(points, faces):
    """The part as one cloth: points within WELD made one (a seam split for normals would tear), faces that lost a
    corner dropped; (points, faces, each glTF point's welded index)."""
    keys = np.round(points / WELD).astype(np.int64)
    _, first, index = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    index = index.ravel()
    joined = index[faces]
    kept = (joined[:, 0] != joined[:, 1]) & (joined[:, 1] != joined[:, 2]) & (joined[:, 0] != joined[:, 2])
    return points[first], joined[kept], index


def person_worlds(rig, kept, poses):
    """The person's joint frames in the world every frame (frames x joints x 4 x 4): the sim body's segment poses
    ((frames x segments x 7), segment k the rig's joint kept[k]) give each segment's turn against its parent, played
    on the person's own bones (its bind's offsets), the top segment where the sim put it; a joint with no segment
    (the root under the body, the end sites) rides its parent at its bind."""
    from scipy.spatial.transform import Rotation
    bind, parents = np.asarray(rig["bind"], dtype=float), np.asarray(rig["parents"])
    poses = np.asarray(poses, dtype=float)
    frames, joints = len(poses), len(parents)
    turns = Rotation.from_quat(poses[:, :, 3:].reshape(-1, 4)).as_matrix().reshape(frames, len(kept), 3, 3)
    segment = {joint: number for number, joint in enumerate(kept)}
    local = [np.linalg.inv(bind[parent]) @ bind[joint] if parent >= 0 else bind[joint]
             for joint, parent in enumerate(parents)]
    worlds = np.zeros((frames, joints, 4, 4))
    top = kept[0]
    worlds[:, top, :3, :3], worlds[:, top, :3, 3], worlds[:, top, 3, 3] = turns[:, 0], poses[:, 0, :3], 1.0
    order = [joint for joint in range(joints) if joint != top]
    for joint in sorted(order, key=lambda joint: (parents[joint] < 0, joint)):
        parent = parents[joint]
        if parent < 0:  # the root under the top segment: where the bind holds it from there
            worlds[:, joint] = worlds[:, top] @ np.linalg.inv(local[top])
        elif joint in segment and parent in segment:
            turn = np.swapaxes(turns[:, segment[parent]], 1, 2) @ turns[:, segment[joint]]
            moved = np.tile(np.eye(4), (frames, 1, 1))
            moved[:, :3, :3], moved[:, :3, 3] = turn, local[joint][:3, 3]
            worlds[:, joint] = worlds[:, parent] @ moved
        else:
            worlds[:, joint] = worlds[:, parent] @ local[joint]
    return worlds


def skinned(points, joints, weights, worlds, bind):
    """The points carried by the skin every frame (frames x points x 3): linear blend of the joints' moves off the
    bind."""
    moves = worlds @ np.linalg.inv(np.asarray(bind, dtype=float))[None]
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    found = np.zeros((len(worlds), len(points), 3))
    for column in range(joints.shape[1]):
        carried = np.einsum("fpij,pj->fpi", moves[:, joints[:, column]], homogeneous)[..., :3]
        found += carried * weights[None, :, column, None]
    return found / np.maximum(weights.sum(axis=1), 1e-9)[None, :, None]


def body_surface(rig, clips_rig):
    """The body under the clothes at the person's bind: rig.npz's source surface (the mean surface moved onto the
    fitted skeleton) with the clips rig's weights over the same points (points, faces, weights)."""
    return (np.asarray(rig["source_points"], dtype=float), np.asarray(rig["source_faces"], dtype=np.int64),
            np.asarray(clips_rig["weights"], dtype=float))


def pieces(points, faces, weights, kept, carriers, bind):
    """The body surface cut into one piece a sim segment: each face goes to the segment carrying its corners'
    strongest joint (most of its corners), its points in that segment's bind frame; [{points, faces}] in kept's
    order. A segment that owns no face gets none."""
    owner = np.asarray(carriers)[weights.argmax(axis=1)]
    face_owner = np.array([np.bincount(row).argmax() for row in owner[faces]])
    found = []
    for joint in kept:
        mine = faces[face_owner == joint]
        used, local_faces = np.unique(mine, return_inverse=True)
        frame = np.linalg.inv(np.asarray(bind[joint], dtype=float))
        local = points[used] @ frame[:3, :3].T + frame[:3, 3]
        found.append({"points": local.tolist(), "faces": local_faces.reshape(-1, 3).tolist()})
    return found


def material_of(row, points, faces, thickness_m):
    """Newton's cloth values from a cloth.json row and the part's mesh: density, mu, lambda, edge stiffness (the
    bending stiffness over the mean edge length) and the particle radius (half the cloth's thickness)."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    mean_edge = float(np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1).mean())
    young, poisson = row["young"], row["poisson"]
    return {"density": row["density"], "mu": row["shear"], "lambda": young * poisson / (1.0 - poisson ** 2),
            "bending": row["bending"] / mean_edge, "radius": thickness_m / 2.0}


# --- the run -------------------------------------------------------------------------------------------------------

def ran(job, out):
    """inside/cloth.py run on `job` in Newton's own Python on this machine (built once by the env script)."""
    subprocess.run(["bash", str(REPO / ENV_SCRIPT), str(ENV)], check=True, stdout=subprocess.DEVNULL)
    started = time.monotonic()
    subprocess.run([str(ENV / "bin/python"), str(REPO / INSIDE), str(job), str(out)], check=True)
    found = dict(np.load(out))
    out.unlink()
    return found, round(time.monotonic() - started, 1)


def recipes_of(inputs):
    """{library surface: its recipe} of the people line's scene library (the dress rows' own read)."""
    from score.stages.people import dress
    return {name: spec.get("recipe") for name, spec in dress.library_surfaces(inputs).items()}


def dress_row(single):
    """The dress row of a cast person, as the characters layer lays it."""
    from score.stages.cast import layer
    return layer.body_row(single.get("look"), single.get("surface"), single.get("variant", 0))


def person_job(name, sim, measures, dressed, rig, clips_rig, recipes, table, thickness_m, motion):
    """One person's share of the job (its segments' pieces and its loose parts, their motion added to `motion`), its
    record, and its parts' layout for the layer."""
    from score.stages import sim_body
    from score.stages.people import dress
    from score.stages.people_bodies import bodies
    document, rest = dress.read_glb(dressed / "body.glb")
    kept, carriers = sim_body.segments_of(clips_rig)
    worlds = person_worlds(rig, kept, [frame["poses"] for frame in measures])
    surface = body_surface(rig, clips_rig)
    record = {"clip": sim["clip"], "parts": {}, "left out": []}
    job = {"name": name, "segments": [dict(piece, name=str(rig["names"][joint])) for piece, joint in
                                      zip(pieces(*surface, kept, carriers, rig["bind"]), kept)], "parts": []}
    motion[f"{name}/segments"] = worlds[:, kept]
    laid = []
    for part in garment_parts(document, rest):
        key = f"{part['node']}/{part['name']}_{part['number']}"
        loose = loose_of(part["points"], rig, bodies.OFFSET_MOST)
        if not loose.any():
            continue
        library = document["materials"][part["material"]].get("extras", {}).get("library")
        recipe = recipes.get(library)
        if recipe not in table:
            record["left out"].append(f"{key}: its surface {library!r} (recipe {recipe!r}) has no cloth row")
            continue
        points, faces, index = welded(part["points"], part["faces"])
        free = np.zeros(len(points), dtype=bool)
        free[index[loose]] = True
        joints, weights = np.zeros((len(points), part["joints"].shape[1]), dtype=np.int64), np.zeros(
            (len(points), part["weights"].shape[1]))
        joints[index], weights[index] = part["joints"], part["weights"]
        carried = skinned(points, joints, weights, worlds, rig["bind"])
        material = material_of(table[recipe], points, faces, thickness_m)
        label = f"{part['name']}_{part['number']}"
        motion[f"{name}/{label}/skinned"] = carried
        job["parts"].append({"name": label, "rest": points.tolist(), "faces": faces.tolist(), "free": free.tolist(),
                             "material": material})
        record["parts"][label] = {"node": part["node"], "points": len(points), "loose": int(free.sum()),
                                  "library": library, "recipe": recipe, "material": material}
        laid.append({"label": label, "node": part["node"], "number": part["number"], "material": part["material"],
                     "material name": part["name"], "index": index, "faces": part["faces"], "uv": part["uv"],
                     "rest": points, "welded faces": faces, "free": free, "carried": carried})
    return job, record, laid, posed_body(surface, worlds, rig["bind"])


def make(inputs, out, seed, params):
    """Every person's loose parts simulated: people_cloth.json, layers/people_cloth.usdc."""
    sim_folder = pathlib.Path(inputs[SIM_ROW])
    sim = json.loads((sim_folder / "sim_bodies.json").read_text())
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    table = json.loads(pathlib.Path(inputs["cloth materials"]).read_text())["recipes"]
    clips_rig = dict(np.load(pathlib.Path(inputs[CLIPS_ROW]) / "rig.npz"))
    recipes = None  # read only once a person has a body to dress: the people line's library is read beside
    thickness_m = bodycloth().MARGIN_MM / 1000.0
    singles = {single["name"]: single for single in cast["characters"]}
    motion, job_people, records, laid, bodies_now, left_out = {}, [], {}, {}, {}, []
    for name, body in sim["bodies"].items():
        row = dress_row(singles.get(name, {}))
        built = f"{BODY}-{(singles.get(name, {}).get('look') or '').replace('/', '-')}"
        if row not in inputs or built not in inputs or "measures" not in body:
            left_out.append(f"{name}: no usable dressed and built body of its look ({row}, {built})")
            continue
        measures = json.loads((sim_folder / "measures" / f"{name}.json").read_text())
        recipes = recipes if recipes is not None else recipes_of(inputs)
        job, record, parts, body_now = person_job(name, body, measures, pathlib.Path(inputs[row]),
                                                  dict(np.load(pathlib.Path(inputs[built]) / "rig.npz")), clips_rig,
                                                  recipes, table, thickness_m, motion)
        records[name] = record
        if job["parts"]:
            job_people.append(job)
            laid[name], bodies_now[name] = parts, body_now
    engine, seconds = None, 0.0
    if job_people:
        engine, seconds = simulated(job_people, motion, sim, out, laid)
    for name, parts in laid.items():
        for part in parts:
            records[name]["parts"][part["label"]]["measures"] = measured(part, bodies_now[name], records[name]["clip"],
                                                                         sim["rate"], thickness_m)
    write_layer(out / LAYER, cast["place"], laid, sim["rate"])
    (out / RECORD).write_text(json.dumps({"place": cast["place"], "engine": engine, "seconds": seconds,
                                          "people": records, "left out": left_out}, indent=1))


def simulated(job_people, motion, sim, out, laid):
    """The job run; each laid part's simulated points (frames x points x 3) set as its `cloth`."""
    np.savez_compressed(out / "motion.npz", **motion)
    job = {"rate": sim["rate"], "gravity": sim["gravity"], "substeps": SUBSTEPS, "iterations": ITERATIONS,
           "device": DEVICE, "motion": str(out / "motion.npz"), "people": job_people}
    (out / "job.json").write_text(json.dumps(job))
    found, seconds = ran(out / "job.json", out / "run.npz")
    for name, parts in laid.items():
        for part in parts:
            part["cloth"] = found[f"{name}/{part['label']}"]
    (out / "job.json").unlink()
    (out / "motion.npz").unlink()
    return str(found["engine"]), seconds


# --- the measures and gates ----------------------------------------------------------------------------------------

def posed_body(surface, worlds, bind):
    """The body surface posed every frame (frames x points x 3) and its faces."""
    points, faces, weights = surface
    every = np.tile(np.arange(weights.shape[1]), (len(points), 1))
    return skinned(points, every, weights, worlds, bind), faces


def depths(cloth, free, body):
    """Each frame's deepest loose point inside the body surface posed there (metres; 0 when none is inside)."""
    import trimesh
    posed, faces = body
    return np.array([max(0.0, float(trimesh.proximity.signed_distance(
        trimesh.Trimesh(posed[frame], faces, process=False), cloth[frame][free]).max()))
        for frame in range(len(cloth))])


def stretches(cloth, rest, carried, faces, free):
    """Each frame's largest stretch of an edge touching a loose point, less 1: its length over the longer of its
    built length and the length the skin gives it that frame. An edge from a riding point is as long as the bake
    makes it (the walking astronaut's skin draws one 99% past its built length), and the bake's own stretch is the
    people gates'; the cloth's is what it adds."""
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    edges = edges[free[edges].any(axis=1)]
    built = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    riding = np.linalg.norm(carried[:, edges[:, 0]] - carried[:, edges[:, 1]], axis=2)
    now = np.linalg.norm(cloth[:, edges[:, 0]] - cloth[:, edges[:, 1]], axis=2)
    return (now / np.maximum(built[None], riding) - 1.0).max(axis=1)


def restlessness(cloth, carried, free, rate):
    """The loose points' mean speed against the skin's (m/s) over the run's last REST_SECONDS: how fast the cloth
    still moves on the body."""
    last = max(2, int(REST_SECONDS * rate) + 1)
    off = cloth[-last:, free] - carried[-last:, free]
    return float(np.linalg.norm(np.diff(off, axis=0), axis=2).mean() * rate)


def measured(part, body, clip, rate, thickness_m):
    """A part's gate numbers: its deepest loose point inside the body (any frame), its largest stretch past SETTLE,
    and on a still clip its restlessness at the end."""
    cloth, free = np.asarray(part["cloth"], dtype=float), part["free"]
    deep = depths(cloth, free, body)
    stretch = stretches(cloth, part["rest"], part["carried"], part["welded faces"], free)[int(SETTLE * rate):]
    found = {"deepest m": round(float(deep.max()), 4), "frames deeper than thickness": int((deep > thickness_m).sum()),
             "largest stretch": round(float(stretch.max()), 4) if len(stretch) else 0.0,
             "largest drift off skin m": round(float(np.linalg.norm(cloth[:, free] - part["carried"][:, free],
                                                                    axis=2).max()), 4)}
    if clip in STILL:
        found["restless m/s"] = round(restlessness(cloth, part["carried"], free, rate), 4)
    return found


def record_of(output):
    return json.loads((pathlib.Path(output) / RECORD).read_text())


def every_part(output):
    """(person, part, its record) for every simulated part."""
    return [(name, label, part) for name, person in record_of(output)["people"].items()
            for label, part in person["parts"].items()]


def verdict(name, faults, passed, measures, findings=()):
    return checks.Verdict(name, checks.FAIL if faults else checks.PASS, "; ".join(faults[:3]) if faults else passed,
                          measures, {}, tuple(faults) or tuple(findings))


def judge_through(output, inputs, evidence):
    """Fail a part with a loose point deeper inside the body than the cloth's thickness in any frame."""
    limit = bodycloth().MARGIN_MM / 1000.0
    parts = every_part(output)
    faults = [f"{name} {label}: a loose point {part['measures']['deepest m']:.4f} m inside the body"
              for name, label, part in parts if part["measures"]["deepest m"] > limit]
    return verdict("through", faults, f"{len(parts)} parts, no loose point deeper than {limit} m in the body",
                   {"parts": len(parts)}, record_of(output)["left out"])


def judge_stretch(output, inputs, evidence):
    """Fail a part with an edge touching a loose point stretched over STRETCH_MOST past SETTLE."""
    parts = every_part(output)
    faults = [f"{name} {label}: stretched {part['measures']['largest stretch']:.3f}" for name, label, part in parts
              if part["measures"]["largest stretch"] > STRETCH_MOST]
    return verdict("stretch", faults, f"{len(parts)} parts, no loose edge stretched over {STRETCH_MOST:.0%}",
                   {"parts": len(parts)})


def judge_rests(output, inputs, evidence):
    """Fail a part on a still clip whose loose points still move on the body faster than REST_MOST at the end."""
    still = [(name, label, part) for name, label, part in every_part(output) if "restless m/s" in part["measures"]]
    faults = [f"{name} {label}: still moving {part['measures']['restless m/s']:.3f} m/s on the body"
              for name, label, part in still if part["measures"]["restless m/s"] > REST_MOST]
    return verdict("rests", faults, f"{len(still)} parts on a still clip, each at rest within {REST_MOST} m/s",
                   {"parts": len(still)})


def output_faults(folder):
    folder = pathlib.Path(folder)
    return [f"no {name}" for name in (RECORD, LAYER) if not (folder / name).exists()]


CONTRACT = contracts.Contract("people-cloth", 1, output_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("through", judge_through), checks.Check("stretch", judge_stretch),
          checks.Check("rests", judge_rests))


# --- the layer -----------------------------------------------------------------------------------------------------

def prim_name(text):
    """A glTF name as skel_usd.py makes it a prim name (loaded by path: the cast overlay's rule)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("skel_usd", REPO / "tools/characters/skel_usd.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prim_name(text)


def write_layer(path, place, laid, rate):
    """layers/people_cloth.usdc: each simulated part's baked mesh (the asset's Turned/Body/<node>/<part>) made
    invisible and a Mesh at Turned/Cloth/<part> in its place, in the skeleton's frame, its points every frame, bound
    to the asset's own material for it."""
    from pxr import Sdf, Usd, UsdGeom, UsdShade, Vt
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    layer.timeCodesPerSecond = layer.framesPerSecond = rate
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for name, parts in laid.items():
        root = f"/{place}/Characters/{name}"
        for prim in (f"/{place}", f"/{place}/Characters", root, f"{root}/Turned"):
            stage.OverridePrim(prim)
        UsdGeom.Scope.Define(stage, f"{root}/Turned/Cloth")
        for part in parts:
            baked = (f"{root}/Turned/Body/{prim_name(part['node'])}/{prim_name(part['material name'])}_"
                     f"{part['number']}")
            UsdGeom.Imageable(stage.OverridePrim(baked)).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
            mesh = UsdGeom.Mesh.Define(stage, f"{root}/Turned/Cloth/{prim_name(part['label'])}")
            mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(part["faces"])))
            mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(np.asarray(part["faces"]).ravel().tolist()))
            mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            points = mesh.CreatePointsAttr()
            for code, frame in enumerate(np.asarray(part["cloth"])[:, part["index"]]):
                points.Set(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(frame, np.float32)), code)
            if part["uv"] is not None:
                primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                                  UsdGeom.Tokens.vertex)
                primvar.Set(Vt.Vec2fArray.FromNumpy(np.ascontiguousarray(part["uv"], np.float32)))
            look = f"{root}/Looks/m{part['material']}_{prim_name(part['material name'])}"
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).GetDirectBindingRel().SetTargets([look])
    layer.Save()
