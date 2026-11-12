"""The motion row's flag cloth (#88's flag, env1's square): every flag the rigid make leaves unmade (its row's move
`cloth`, which no rigid writer makes) waved as cloth in the air by the library's flag cloth
(data/effects/flag_cloth.json: beside data/library, which paid rows read whole, as the exhaust's recipe stands), on
Newton's VBD solver, and written into the place's motion layer. Set on the motion row by the table
(score/stages/__init__.py), as shown_rows.py is: the motion package's own make and gates stay as they are, and a
place with no flag of its own makes the same output as before.

    made(make)     a make (motion's), then each unmade flag's cloth: its mesh's cloth parts (each part whose library surface
                    is made with a recipe the cloth table holds, data/physics/cloth.json, read off the surface bake's
                    specs.json) laid as a grid over the flag's own frame (cloth_rig.py), one Newton run of the
                    library's flag cloth a flag model (inside/flag_cloth.py, in the physics stage's Newton Python) in
                    the wind of the library's recipe and the gravity and air of the body the site stands on, looped
                    over the layer's seconds and written into layers/motion.usda (cloth_layer.py): each flag a SkelRoot
                    playing that one run from its own phase. moves.json loses each waved flag's unmade line and gains
                    `cloth` ({prim: {mesh, run, phase}}) and `cloth runs` ({run: what it was made with and measured});
                    a flag the library cannot wave keeps its unmade line, its reason added
    files           the motion row's files, and for a place whose design shows a flag that waves, the library's flag
                    cloth, the cloth table, the run script and the Python it runs in
    covering(judge) a `covered` judge (motion's, or one built on it), a waved flag counted as moved only where its cloth moves in the layer as
                    UsdSkel skins it (some point at least MOVED_LEAST off where it starts, at a sampled second) and
                    its pole stands (no point riding the pole joint off its rest by over POLE_MOST)
"""
import functools
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

import numpy as np

from score import checks
from score.stages import design_layers, layer_base, people_cloth, row_kinds
from score.stages.motion import cloth_layer, cloth_rig, from_design
import score.stages.motion as motion

REPO = pathlib.Path(__file__).resolve().parents[3]
INSIDE = "score/stages/motion/inside/flag_cloth.py"
FILES = {"flag cloth": "{data}/effects/flag_cloth.json", "cloth materials": "{data}/physics/cloth.json",
         "flag cloth script": "{repo}/" + INSIDE, "sim env": "{repo}/" + people_cloth.ENV_SCRIPT}
MOVE = "cloth"
UNMADE = f": {MOVE}, which no writer makes"
DEVICE = os.environ.get("SCORE_CLOTH_DEVICE", people_cloth.DEVICE)
# Gate limits, picked 2026-11-12 before any run: a waving flag's cloth reaches 5 cm off where it starts at some sampled
# second (a tenth of the square's 42 cm flags), and its pole does not move by a tenth of a millimetre.
MOVED_LEAST = 0.05
POLE_MOST = 1e-4
SAMPLE_STEP = 1.0  # seconds between the times covered reads a flag's skinned points


# --- the files ------------------------------------------------------------------------------------------------------

def waves_in(place):
    """Whether the place's kept design shows a row whose move is cloth (a flag)."""
    path = design_layers.KEPT / f"{place}.json"
    if place is None or not path.is_file():
        return False
    kinds = row_kinds.table()
    return any(from_design.rule_of(row, kinds).get("move") == MOVE
               for row in row_kinds.rows_that(json.loads(path.read_text()), "moves", kinds))


def files(declared):
    """The motion row's file map with the flag cloth's files added for a place that waves a flag."""
    def found(place):
        return {**declared(place), **FILES} if waves_in(place) else declared(place)
    found.__name__, found.__doc__ = declared.__name__, declared.__doc__
    return found


# --- what waves -----------------------------------------------------------------------------------------------------

def unmade_flags(record):
    """The prims of the record's unmade cloth lines, in order."""
    return [line.split(":", 1)[0] for line in record.get("unmade", []) if UNMADE in line]


def cloth_recipes(inputs):
    """{library surface: its recipe} of the place's baked surfaces (the surface bake's specs.json); none without."""
    specs = pathlib.Path(inputs.get("surfaces-bake", "")) / "specs.json"
    if "surfaces-bake" not in inputs or not specs.is_file():
        return {}
    return {name: spec.get("recipe") for name, spec in json.loads(specs.read_text()).items()}


def flag_mesh(stage, path):
    """The flag's one drawn mesh: {"path", "points", "faces" (each face's point indices), "subsets" ({surface name:
    face indices})}; None where it has none or several."""
    from pxr import Usd, UsdGeom
    meshes = [prim for prim in Usd.PrimRange(stage.GetPrimAtPath(path))
              if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputePurpose() == UsdGeom.Tokens.default_]
    if len(meshes) != 1:
        return None
    mesh = UsdGeom.Mesh(meshes[0])
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get())
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
    faces = np.split(indices, np.cumsum(counts)[:-1])
    subsets = {}
    for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):
        surface = subset.GetPrim().GetAttribute("score:surface")
        name = surface.Get() if surface and surface.HasAuthoredValue() else subset.GetPrim().GetName()
        subsets[name] = np.asarray(subset.GetIndicesAttr().Get())
    return {"path": str(meshes[0].GetPath()), "points": np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64),
            "faces": faces, "subsets": subsets}


def cloth_parts(mesh, recipes, table):
    """(the mesh's subsets that are cloth: their library surface's recipe has a cloth table row, the recipe they share
    or None): a baked surface is named `<library surface>__<finish>`."""
    found = {name: recipes.get(name.split("__", 1)[0]) for name in mesh["subsets"]}
    cloth = sorted(name for name, recipe in found.items() if recipe in table)
    kinds = {found[name] for name in cloth}
    return cloth, (kinds.pop() if len(kinds) == 1 else None)


def upright(stage, path):
    """Whether the flag stands with its own up the world's up (it turns about the upright line only)."""
    from pxr import UsdGeom
    placed = np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(0.0))
    up = placed[1, :3] / np.linalg.norm(placed[1, :3])
    return bool(abs(up[1] - 1.0) < 1e-3)


def model_key(mesh, cloth):
    """The flag model's key: its points, faces and cloth parts (the same model is run once)."""
    digest = hashlib.sha256(np.round(mesh["points"], 5).tobytes())
    for face in mesh["faces"]:
        digest.update(np.asarray(face, dtype=np.int64).tobytes())
    for name in cloth:
        digest.update(name.split("__", 1)[0].encode() + np.asarray(mesh["subsets"][name], dtype=np.int64).tobytes())
    return digest.hexdigest()[:12]


def phase_of(path, spread):
    """A flag's own moment into its model's run, seconds: its prim's hash as a share of `spread`."""
    return round(int(hashlib.sha256(path.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF * spread, 4)


def read_flags(stage, paths, recipes, table, body):
    """({run key: {"mesh", "cloth", "recipe"}}, [{"prim", "mesh", "run"}], {prim: why it is not waved})."""
    models, flags, left = {}, [], {}
    for path in paths:
        mesh = flag_mesh(stage, path)
        cloth, recipe = cloth_parts(mesh, recipes, table) if mesh else ([], None)
        why = ("its body's air is not known" if body is None or body.get("air_kpa") is None else
               "it has no one drawn mesh" if mesh is None else
               "no part of it has a library surface whose recipe the cloth table holds" if not cloth else
               "its cloth parts are of more than one recipe" if recipe is None else
               "it has no part that is not cloth to hold it (a pole)" if len(cloth) == len(mesh["subsets"]) else
               "it does not stand upright" if not upright(stage, path) else None)
        if why:
            left[path] = why
            continue
        key = model_key(mesh, cloth)
        models.setdefault(key, {"mesh": mesh, "cloth": cloth, "recipe": recipe})
        flags.append({"prim": path, "mesh": mesh["path"], "run": key})
    return models, flags, left


# --- the run --------------------------------------------------------------------------------------------------------

def kaimal(sigma, scale, mean, frames, rate, draw):
    """A gust series (frames) of standard deviation about `sigma` from the Kaimal spectrum of length scale `scale` at
    mean speed `mean`, summed from cosines at each of the run's own frequencies with random phases."""
    length = frames / rate
    steps = np.arange(1, frames // 2) / length
    spectrum = 4.0 * sigma ** 2 * (scale / mean) / (1.0 + 6.0 * steps * scale / mean) ** (5.0 / 3.0)
    amplitudes = np.sqrt(2.0 * spectrum / length)
    phases = draw.uniform(0.0, 2.0 * np.pi, len(steps))
    times = np.arange(frames) / rate
    return (amplitudes[None, :] * np.cos(2.0 * np.pi * steps[None, :] * times[:, None] + phases[None, :])).sum(axis=1)


def wind_of(recipe, height, frames, rate):
    """The wind at each frame in the flag's own frame ([along, up, normal], m/s): the middle of the recipe's speeds
    along it, and its turbulence's gusts along, across (normal) and up, at `height` metres."""
    mean = float(np.mean(recipe["wind"]["speed"]))
    gusts = recipe["turbulence"]
    first = gusts["intensity"] * (0.75 * mean + gusts["add"])
    scale = gusts["scale_per_height"] * height
    draw = np.random.default_rng(recipe["make"]["seed"])
    along, across, up = (kaimal(first * ratio, size * scale, mean, frames, rate, draw)
                         for ratio, size in zip(gusts["ratios"], gusts["scales"]))
    return np.stack([mean + along, up, across], axis=1)


def material_of(row, grid, thread):
    """Newton's cloth values of a cloth table row over the grid (people_cloth's), its radius half the library
    recipe's thread."""
    return people_cloth.material_of(row, grid["points"], grid["faces"], thread)


def ran(job, folder):
    """inside/flag_cloth.py run on `job` in the physics stage's Newton Python on this machine (built once)."""
    subprocess.run(["bash", str(REPO / people_cloth.ENV_SCRIPT), str(people_cloth.ENV)], check=True,
                   stdout=subprocess.DEVNULL)
    (folder / "job.json").write_text(json.dumps(job))
    subprocess.run([str(people_cloth.ENV / "bin/python"), str(REPO / INSIDE), str(folder / "job.json"),
                    str(folder / "run.npz")], check=True)
    found = np.load(folder / "run.npz")
    return np.asarray(found["points"]), str(found["engine"])


def job_of(grid, material, wind, body, recipe, rate, frames):
    """The run's job (inside/flag_cloth.py's job.json)."""
    make = recipe["make"]
    air = recipe["air"]
    return {"rate": rate, "frames": frames, "substeps": make["substeps"], "iterations": make["iterations"],
            "device": DEVICE, "gravity": [0.0, -float(body["gravity"]), 0.0], "points": grid["points"].tolist(),
            "faces": grid["faces"].tolist(), "pinned": grid["pinned"].tolist(), "material": material,
            "air": {"density": air["density"] * float(body["air_kpa"]) / air["kpa"],
                    "normal_drag": recipe["plate"]["normal_drag"]},
            "wind": wind.tolist()}


def stretch_of(grid, positions):
    """Each grid edge's length over its rest length, at every frame (frames x edges)."""
    faces = grid["faces"]
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    rest = np.linalg.norm(grid["points"][edges[:, 0]] - grid["points"][edges[:, 1]], axis=1)
    return np.linalg.norm(positions[:, edges[:, 0]] - positions[:, edges[:, 1]], axis=2) / rest


def run_model(model, recipe, table, recipes_spec, body, rate, seconds, run=ran):
    """One flag model's run: its grid, its Newton run, looped, and its rig in the model's own space ({"rest",
    "frames", "indices", "shares"}), with what it was made with and measured."""
    mesh, make = model["mesh"], recipe["make"]
    cloth, rigid = cloth_rig.cloth_points(mesh["faces"], mesh["subsets"], model["cloth"], len(mesh["points"]))
    frame = cloth_rig.frame_of(mesh["points"], cloth, rigid)
    local = cloth_rig.local_of(mesh["points"], frame)
    grid = cloth_rig.grid_of(local, cloth_rig.triangles_of(mesh["faces"], mesh["subsets"], model["cloth"]),
                             make["spacing"])
    joints = cloth_rig.joints_of(grid, make["joint_every"])
    settle, seam = int(round(make["settle"] * rate)), int(round(make["seam"] * rate))
    length = int(round(seconds * rate))
    height = float(np.mean(mesh["points"][cloth][:, 1]))
    wind = wind_of(recipe, height, settle + length + seam, rate)
    thread = float(recipes_spec.get("thread", 0.0))
    material = material_of(table[model["recipe"]], grid, thread)
    with tempfile.TemporaryDirectory(prefix="flag-cloth-") as folder:
        positions, engine = run(job_of(grid, material, wind, body, recipe, rate, settle + length + seam),
                                pathlib.Path(folder))
    loop = cloth_rig.looped(positions[settle:], length, seam)
    played = np.concatenate([loop, loop[:int(np.ceil(make["phases"] * rate)) + 1]])
    rest = np.einsum("ab,jbc->jac", frame, cloth_rig.turns_of(grid["points"][None], grid, joints)[0])
    moved = np.einsum("ab,fjbc->fjac", frame, cloth_rig.turns_of(played, grid, joints))
    indices, shares = cloth_rig.weights_of(local, cloth, grid, joints)
    stretched = stretch_of(grid, loop)
    measures = {"grid nodes": len(grid["points"]), "pinned nodes": int(grid["pinned"].sum()), "joints": len(joints),
                "cloth points": len(cloth), "pole points": len(rigid), "height m": round(height, 4),
                "stretch p50": round(float(np.percentile(stretched, 50)), 4),
                "stretch p95": round(float(np.percentile(stretched, 95)), 4),
                "stretch most": round(float(stretched.max()), 4),
                "wind mean m/s": round(float(wind[:, 0].mean()), 3)}
    return {"rest": rest, "frames": list(moved), "indices": indices, "shares": shares}, {
        "recipe": model["recipe"], "parts": model["cloth"], "engine": engine, "seconds": seconds,
        "phases": make["phases"], "air": job_of(grid, material, wind[:1], body, recipe, rate, 1)["air"],
        "gravity": float(body["gravity"]), "material": material, "measures": measures}


def waved(record, inputs, source, layer_path, run=ran):
    """The record with every unmade flag the library waves written into the layer at `layer_path` (cloth_layer), its
    unmade line gone and its cloth and run recorded; one the library cannot wave keeps its line, its reason added."""
    from pxr import Sdf
    paths = unmade_flags(record)
    if not paths:
        return record
    recipe = json.loads(pathlib.Path(inputs["flag cloth"]).read_text())
    table = json.loads(pathlib.Path(inputs["cloth materials"]).read_text())["recipes"]
    specs = json.loads((pathlib.Path(inputs["surfaces-bake"]) / "specs.json").read_text()) \
        if "surfaces-bake" in inputs else {}
    body = motion.body_of(inputs)
    stage = layer_base.opened(source)
    models, flags, left = read_flags(stage, paths, cloth_recipes(inputs), table, body)
    layer = Sdf.Layer.FindOrOpen(str(layer_path))
    rate, seconds = layer.timeCodesPerSecond, float(record["seconds"])
    runs, made = {}, {}
    for key, model in models.items():
        spec = next((specs[name.split("__", 1)[0]] for name in model["cloth"] if name.split("__", 1)[0] in specs), {})
        runs[key], made[key] = run_model(model, recipe, table, spec, body, rate, seconds, run)
    for flag in flags:
        flag["phase"] = phase_of(flag["prim"], recipe["make"]["phases"])
    cloth_layer.write(layer, runs, flags, rate)
    layer.Save()
    waving = {flag["prim"] for flag in flags}
    unmade = [line if line.split(":", 1)[0] not in left else f"{line} ({left[line.split(':', 1)[0]]})"
              for line in record["unmade"] if line.split(":", 1)[0] not in waving]
    return dict(record, unmade=unmade,
                cloth={flag["prim"]: {"mesh": flag["mesh"], "run": flag["run"], "phase": flag["phase"]}
                       for flag in flags},
                **{"cloth runs": made})


def made(make):
    """A make that waves as cloth every flag the motion make left unmade (waved), the record written again."""
    @functools.wraps(make)
    def making(inputs, out, seed, params):
        make(inputs, out, seed, params)
        record = json.loads((pathlib.Path(out) / motion.RECORD).read_text())
        if not unmade_flags(record) or "flag cloth" not in inputs:
            return
        with motion.built(inputs) as source:
            found = waved(record, inputs, source, pathlib.Path(out) / "layers/motion.usda")
        (pathlib.Path(out) / motion.RECORD).write_text(json.dumps(found, indent=1))
    return making


# --- covered --------------------------------------------------------------------------------------------------------

def cloth_faults(stage, record, seconds, rate):
    """({prim: how far its cloth reaches off its start, metres} of the flags that wave, [faults of those that do
    not or whose pole moves]), read off the composed stage as UsdSkel skins it."""
    codes = [step * rate for step in np.arange(0.0, seconds + 1e-9, SAMPLE_STEP)]
    reached, faults = {}, []
    for prim, entry in sorted(record.get("cloth", {}).items()):
        found = cloth_layer.skinned_over(stage, prim, codes)
        if found is None:
            faults.append(f"{prim}: its cloth is not skinned in the layer")
            continue
        off = np.linalg.norm(found - found[:1], axis=2).max(axis=0)
        if off.max() < MOVED_LEAST:
            faults.append(f"{prim}: its cloth reaches only {off.max():.3f} m off its start, under {MOVED_LEAST} m")
            continue
        still = pole_points(stage, entry["mesh"])
        if still is not None and len(still) and off[still].max() > POLE_MOST:
            faults.append(f"{prim}: its pole moves {off[still].max():.4f} m, over {POLE_MOST} m")
            continue
        reached[prim] = round(float(off.max()), 4)
    return reached, faults


def pole_points(stage, mesh):
    """The points of a mesh that ride its pole joint (0) alone, read off its bound skin."""
    prim = stage.GetPrimAtPath(mesh)
    indices, weights = prim.GetAttribute("primvars:skel:jointIndices"), prim.GetAttribute("primvars:skel:jointWeights")
    if not (indices and weights and indices.HasValue() and weights.HasValue()):
        return None
    width = int(indices.GetMetadata("elementSize") or 1)
    joints = np.asarray(indices.Get()).reshape(-1, width)
    shares = np.asarray(weights.Get()).reshape(-1, width)
    return np.flatnonzero((joints[:, 0] == 0) & (shares[:, 0] > 1.0 - 1e-6))


def covering(judge):
    """A `covered` judge (motion's, or one built on it) with each flag the record waves counted as moved where its
    cloth moves in the layer and its pole stands (cloth_faults); a waved flag that does not is named by its cloth's
    fault in place of motion's line."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        verdict = judge(output, inputs, evidence)
        record = json.loads(pathlib.Path(inputs["moves"]).read_text())
        if not record.get("cloth"):
            return verdict
        stage = motion.composed(output, inputs)
        reached, faults = cloth_faults(stage, record, motion.seconds_of(output), stage.GetTimeCodesPerSecond())
        return counted(verdict, set(record["cloth"]), reached, faults)
    return judged


def counted(verdict, waved, reached, faults):
    """`covered`'s verdict with the waved flags' own lines taken out, the waving ones counted as moved and the faults
    of those that do not wave added."""
    kept = tuple(line for line in verdict.findings
                 if not (line.endswith(")") and line.rsplit(" (", 1)[0] in waved)) if verdict.answer == checks.FAIL \
        else ()
    missing = kept + tuple(faults)
    measures = {**verdict.measures, "moved": verdict.measures["moved"] + len(reached), "waving cloth": len(reached)}
    reason = (f"{len(missing)} prims of a moving kind, rows of a moving thing or game motions neither move (by a "
              "writer that makes their move) nor say why" if missing else
              f"all {measures['moving kinds']} prims of a moving kind move ({measures['moved']}, {len(reached)} of "
              "them waving as cloth) or say why not")
    said = verdict.findings if verdict.answer == checks.PASS else ()
    said += tuple(f"{prim}: waves as cloth, reaching {far} m off its start" for prim, far in sorted(reached.items()))
    return checks.Verdict("covered", checks.FAIL if missing else checks.PASS, reason, measures, verdict.better,
                          missing or said)
