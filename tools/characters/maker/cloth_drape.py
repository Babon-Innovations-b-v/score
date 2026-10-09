"""Runs inside Blender 4.2 or 5.0 (headless: on the maker's own machine, or through tools/props/cloud/blender_cloud.py):
sew a GarmentCode garment's panels shut round a body and let it hang, then write the cloth as GarmentCode's simulation
wrote it.

    blender -b --python tools/characters/maker/cloth_drape.py -- <job.json>

job.json (written by `drape_garment.py`):
    {"sewing": "<name>_sewing.npz", "coarse": "<name>_coarse_sewing.npz", "box_mesh": "<name>_boxmesh.obj",
     "body": "ours.obj" (metres, y up), "cloth": {...} the design's cloth.json, "out": "<folder>", "name": "<name>"}

The panels start where GarmentCode laid them round the body, flat and true to the pattern; each seam is a sewing
thread (a loose edge between the two copies of a seam point, `sewing.seams`), which Blender's cloth pulls shut
(sewing springs). Gravity is off while the seams close, as GarmentCode's Warp run held it off for its first steps, then
on while the cloth settles. The body is a collision object; the cloth collides with itself. Everything stays in the
pattern's frame: y up, the body's feet at 0, Blender's gravity along -y.

Sewing round a body is fragile: a pull too hard or too soft drags a torso off the shoulders while its seams close
(2026-10-09). So the garment is sewn coarse first (the "coarse" record, the same pattern at a wider spacing), with each
sewing force of the design tried in turn until no panel sags off the body (`sewn_and_settled`); then the fine panels
are carried onto the sewn coarse cloth (`sewing.carried`) and settle from there, so nothing fine is sewn round the body
at all. Their rest shape is where they start: a rest shape key made Blender start the cloth at the flat panels, and any
shape key on the mesh broke the sewing (2026-10-09). While the fine cloth settles, a design with a `waist_hold` has its
waist pinned and lowered to the body's waist, as GarmentCode's Warp run held it: sewn with its panels lifted, a coverall
otherwise stays up to 10 cm too high.

Writes into <out>: <name>_sim.obj (centimetres, the box mesh's point order: each box point the middle of its copies)
and blender_cloth.json (the settings used and what came out: each sewing try, seconds, how far the threads are still
open, how many cloth points ended inside the body).
"""
import json
import pathlib
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sewing  # noqa: E402

CENTIMETRES = 0.01
# A panel with fewer than this share of the cloth's points is not checked for drifting off the body (`sag`).
SMALL_PANEL = 0.02


def job():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 1:
        raise SystemExit(__doc__)
    return json.loads(pathlib.Path(given[0]).read_text())


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.use_gravity = True
    scene.gravity = (0.0, -9.81, 0.0)
    scene.render.fps = 24
    return scene


def read_obj(path):
    """An OBJ file's points and triangles (the first index of each corner)."""
    points, faces = [], []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("v "):
            points.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            corners = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            faces.extend([corners[0], corners[index], corners[index + 1]] for index in range(1, len(corners) - 1))
    return np.array(points), np.array(faces)


def mesh_object(name, points, faces, edges):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(point) for point in points], [tuple(edge) for edge in edges],
                     [tuple(face) for face in faces])
    mesh.validate()
    holder = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(holder)
    return holder


def body_object(path, settings):
    """The body as a collision object, its normals pointing out."""
    points, faces = read_obj(path)
    body = mesh_object("body", points, faces, [])
    tidy = bmesh.new()
    tidy.from_mesh(body.data)
    bmesh.ops.recalc_face_normals(tidy, faces=tidy.faces)
    tidy.to_mesh(body.data)
    tidy.free()
    body.modifiers.new("Collision", "COLLISION")
    body.collision.thickness_outer = settings["body_distance"]
    body.collision.thickness_inner = settings.get("body_inner", 0.02)
    body.collision.cloth_friction = settings["body_friction"]
    body.collision.damping = settings.get("body_damping", 0.5)
    return body


def lifted(record, lift):
    """The laid panels' points in metres, each panel whose name holds a word of `lift` ({word: metres}) raised by the
    largest of them.

    A torso panel laid where GarmentCode lays it has its shoulder edge level with the shoulder's top, so its seams,
    pulled straight across, meet the body and the torso slides down the chest while they close; raised, they close
    over the shoulders and the cloth settles onto them (the panels it hangs from are raised with it)."""
    points = record["points"] * CENTIMETRES
    for number, name in enumerate(record["panel_names"]):
        rise = max([metres for word, metres in lift.items() if word in str(name)], default=0.0)
        points[record["panel"] == number, 1] += rise
    return points


def cloth_object(record, start):
    """The panels apart, starting at `start` (metres), with a loose edge for every sewing thread."""
    cloth = mesh_object("cloth", start, record["faces"], sewing.seams(record["box_index"]))
    if len(cloth.data.vertices) != len(record["points"]):
        raise RuntimeError(f"Blender merged cloth points: {len(cloth.data.vertices)} of {len(record['points'])}")
    return cloth


def make_cloth(cloth, settings, force, resolution, gravity_frames):
    """Blender's cloth on the panels: the design's stiffness and weight, sewing springs
    pulling with at most `force`, self collision, and gravity off until the first of `gravity_frames` and full from the
    second (None: gravity from the start)."""
    modifier = cloth.modifiers.new("Cloth", "CLOTH")
    physics = modifier.settings
    physics.quality = settings["quality"]
    # The weight is the cloth's per point at the spacing it was tuned at; a finer mesh has more, lighter points.
    physics.mass = settings["mass"] * (resolution / settings["mass_spacing"]) ** 2
    physics.air_damping = settings["air_damping"]
    physics.tension_stiffness = settings["tension"]
    physics.compression_stiffness = settings["compression"]
    physics.shear_stiffness = settings["shear"]
    physics.bending_stiffness = settings["bending"]
    physics.tension_damping = settings.get("tension_damping", 5.0)
    physics.compression_damping = settings.get("compression_damping", 5.0)
    physics.shear_damping = settings.get("shear_damping", 5.0)
    physics.bending_damping = settings.get("bending_damping", 0.5)
    physics.use_sewing_springs = True
    physics.sewing_force_max = force
    physics.use_internal_springs = False
    physics.use_pressure = False
    if gravity_frames:
        physics.effector_weights.gravity = 0.0
        physics.effector_weights.keyframe_insert("gravity", frame=gravity_frames[0])
        physics.effector_weights.gravity = 1.0
        physics.effector_weights.keyframe_insert("gravity", frame=gravity_frames[1])
    collision = modifier.collision_settings
    collision.collision_quality = settings["collision_quality"]
    collision.distance_min = settings["body_distance"]
    collision.use_self_collision = settings["self_collision"]
    collision.self_distance_min = settings["self_distance"]
    collision.self_friction = settings.get("self_friction", 5.0)
    modifier.point_cache.frame_start = 1
    modifier.point_cache.frame_end = 10000
    return modifier


def simulate(scene, first_frame, last_frame):
    """Step the cloth frame by frame from the first to the last frame; the seconds it took."""
    scene.frame_start, scene.frame_end = 1, last_frame
    began = time.time()
    for frame in range(first_frame, last_frame + 1):
        scene.frame_set(frame)
        if frame % 10 == 0:
            print(f"cloth frame {frame} of {last_frame}: {time.time() - began:.0f} s", flush=True)
    return time.time() - began


def cloth_points(cloth):
    """The cloth's points as the simulation left them (metres)."""
    evaluated = cloth.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = np.empty(len(evaluated.data.vertices) * 3)
    evaluated.data.vertices.foreach_get("co", points)
    return points.reshape(-1, 3)


def sag(record, reference, points):
    """How far each panel's middle has moved from where it was (`reference`) across and up or down (metres; its
    points' mean, front to back left out, as the panels close round the body that way), by name.

    A panel that hangs on the body stays about where it was laid; a torso that came off the shoulders while its seams
    closed has dropped down the chest, and a sleeve that came off its arm has bunched up at the shoulder. Small panels
    (cuffs, collars, under SMALL_PANEL of the points) are left out: laid apart from what they are sewn to, they move
    far on every good drape too."""
    return {str(name): float(np.linalg.norm(reference[record["panel"] == number, :2].mean(axis=0)
                                            - points[record["panel"] == number, :2].mean(axis=0)))
            for number, name in enumerate(record["panel_names"])
            if (record["panel"] == number).mean() >= SMALL_PANEL}


def beyond(drifts, limits, allowance=0.0):
    """The panel that drifted furthest past its limit and by how much (metres; at most 0 when every panel is within
    its own). A panel's limit is the strictest of `limits` ({word in its name: metres}, "" for every panel) beyond
    `allowance`: on a good drape the trouser panels close in by about 20 cm and the torso by 5 to 9, while a sleeve
    stays within 2 and one that came off its arm moves 17 to 25 (2026-10-09)."""
    excess = {name: drift - allowance - min(metres for word, metres in limits.items() if word in name)
              for name, drift in drifts.items()}
    worst = max(excess, key=excess.get)
    return worst, excess[worst]


def sew(task, record, force, resolution):
    """A scene with the body and the panels (raised, `lifted`), sewn shut with gravity off; the scene, body, cloth,
    the seconds it took and how far each panel drifted (`sag`)."""
    settings, frames = task["cloth"]["blender"], task["cloth"]["frames"]
    scene = empty_scene()
    body = body_object(task["body"], settings)
    start = lifted(record, settings.get("lift", {}))
    cloth = cloth_object(record, start)
    make_cloth(cloth, settings, force, resolution, (frames["sew"], frames["sew"] + frames["gravity_ramp"]))
    seconds = simulate(scene, 1, frames["sew"])
    return scene, body, cloth, seconds, sag(record, start, cloth_points(cloth))


def attempt(task, record, force, resolution):
    """One try: sewn with gravity off, then, if no panel drifted past its limit (`beyond`), settled under gravity
    and checked again, its seams too (a heavy cloth can slip off a shoulder, a sleeve off its arm, as it settles);
    the cloth's points, the body, the try's record and whether it held."""
    settings, frames = task["cloth"]["blender"], task["cloth"]["frames"]
    scene, body, cloth, seconds, drifted = sew(task, record, force, resolution)
    worst, excess = beyond(drifted, settings["drift_limits"])
    report = {"force": force, "seconds": round(seconds, 1), "worst_panel": worst,
              "past_limit_cm": round(excess / CENTIMETRES, 1)}
    print(f"sewing force {force}: {worst} {excess / CENTIMETRES:+.1f} cm past its limit", flush=True)
    if excess > 0:
        return cloth_points(cloth), body, report, False
    report["settle_seconds"] = round(simulate(scene, frames["sew"] + 1, frames["sew"] + frames["settle"]), 1)
    points = cloth_points(cloth)
    settled = sag(record, record["points"] * CENTIMETRES, points)
    worst, excess = beyond(settled, settings["drift_limits"])
    report.update({"settled_worst_panel": worst, "settled_past_limit_cm": round(excess / CENTIMETRES, 1),
                   "settled_panels_cm": {name: round(value / CENTIMETRES, 1) for name, value in settled.items()}})
    gap = float(sewing.seam_gaps(points, record["box_index"]).max())
    report["settled_open_thread_cm"] = round(gap / CENTIMETRES, 1)
    print(f"settled: {worst} {excess / CENTIMETRES:+.1f} cm past its limit, a seam open {gap / CENTIMETRES:.1f} cm",
          flush=True)
    return points, body, report, excess <= 0 and gap <= settings["open_thread_limit"]


def sewn_and_settled(task, record, resolution):
    """The panels sewn on the body and settled, with each sewing force of the design tried in turn until one holds
    (`attempt`); the cloth's points, the body, the record of every try, whether one held, and the force kept. When
    none holds, the try that drifted least past its limit is kept."""
    tries, results = [], []
    for force in task["cloth"]["blender"]["sewing_forces"]:
        points, body, report, held = attempt(task, record, force, resolution)
        tries.append(report)
        results.append((points, body))
        if held:
            report["kept"] = True
            return points, body, tries, True, force
    least = min(range(len(tries)),
                key=lambda index: tries[index].get("settled_past_limit_cm", tries[index]["past_limit_cm"]))
    tries[least]["kept"] = True
    print(f"no sewing force kept the garment on the body; force {tries[least]['force']} is kept", flush=True)
    return results[least][0], results[least][1], tries, False, tries[least]["force"]


def waist_drop(record, start, below):
    """The waist's points (the copies of the box mesh's waist points) and how far they are lowered (metres) to hold
    them `below` (a share of the body's height) under GarmentCode's waist level."""
    indices = np.where(np.isin(record["box_index"], record["waist_points"]))[0]
    target = (record["waist_level"] - below * record["height"]) * CENTIMETRES
    return indices, float(start[indices, 1].mean() - target) if len(indices) else 0.0


def hold_waist(cloth, indices, drop, frames):
    """The waist's points pinned and lowered by `drop` over `frames` frames, then held there, as GarmentCode's Warp run
    held them at the waist: an empty moved down carries them through a hook placed before the cloth, and the cloth
    pins them to where the hook puts them."""
    group = cloth.vertex_groups.new(name="waist")
    group.add([int(index) for index in indices], 1.0, "REPLACE")
    handle = bpy.data.objects.new("waist_hold", None)
    bpy.context.scene.collection.objects.link(handle)
    hook = cloth.modifiers.new("Waist", "HOOK")
    hook.object = handle
    hook.vertex_group = "waist"
    handle.location = (0.0, 0.0, 0.0)
    handle.keyframe_insert("location", frame=1)
    handle.location = (0.0, -drop, 0.0)
    handle.keyframe_insert("location", frame=frames)


def settled_from(task, record, start, fine):
    """The fine panels started at `start` (carried onto the sewn coarse cloth) and settled under gravity with the
    design's settings changed by `fine` (the fine stage's own stiffness and sewing force), the waist held where the
    design says (`waist_hold`, none if it says nothing); the cloth's points, the body, the seconds it took and how far
    the waist was lowered (metres)."""
    settings = {**task["cloth"]["blender"], **fine}
    scene = empty_scene()
    body = body_object(task["body"], settings)
    start = outside_body(body, start, 2 * settings["body_distance"])
    cloth = cloth_object(record, start)
    held = bool(settings.get("waist_hold")) and len(record.get("waist_points", ())) > 0
    drop = 0.0
    if held:
        indices, drop = waist_drop(record, start, settings["waist_hold"]["below_waist"])
        hold_waist(cloth, indices, drop, settings["waist_hold"]["frames"])
    make_cloth(cloth, settings, fine["sewing_force"], task["cloth"]["resolution_scale"], None)
    if held:
        cloth.modifiers["Cloth"].settings.vertex_group_mass = "waist"
    seconds = simulate(scene, 1, task["cloth"]["frames"]["fine_settle"])
    return cloth_points(cloth), body, seconds, drop


def outside_body(body, points, margin):
    """The points with every one that lies inside the body, or nearer its surface than `margin`, put just outside it.

    Carried from the coarse cloth, a fine point between a coarse triangle's corners can fall inside an arm the corners
    sat outside of; Blender's collision then pushed it out on the far side and a sleeve came off its arm
    (2026-10-09)."""
    tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    moved = points.copy()
    for index, point in enumerate(points):
        nearest, normal, _, _ = tree.find_nearest(point)
        if nearest is None:
            continue
        nearest, normal = np.array(nearest), np.array(normal)
        if (point - nearest) @ normal < margin:
            moved[index] = nearest + normal * margin
    return moved


def fine_settled(task, record, start):
    """The fine panels settled with each of the design's fine settings in turn (`blender.fine`) until no panel
    drifts from where it started past its limit (`beyond`), no seam is open wider than the design allows (one tore
    open at a shoulder, 2026-10-09) and the top has not fallen further than it allows (a pull at the waist dragged
    coveralls off the shoulders), or else the one that went least wrong; a fine setting may hold the waist less low;
    the cloth's points, how many of them lie inside the body, the record of every try, whether one held and how far
    the waist was lowered."""
    tries, results = [], []
    for fine in task["cloth"]["blender"]["fine"]:
        points, body, seconds, drop = settled_from(task, record, start, fine)
        worst, fell = beyond(sag(record, start, points), task["cloth"]["blender"]["drift_limits"])
        gap = float(sewing.seam_gaps(points, record["box_index"]).max())
        # The shoulders: lowering the waist slid a whole coverall off them while every panel's middle moved little.
        slid = float(start[:, 1].max() - points[:, 1].max())
        tries.append({**fine, "seconds": round(seconds, 1), "worst_panel": worst,
                      "past_limit_cm": round(fell / CENTIMETRES, 1), "open_thread_cm": round(gap / CENTIMETRES, 1),
                      "top_fell_cm": round(slid / CENTIMETRES, 1),
                      "waist_lowered_cm": round(drop / CENTIMETRES, 1)})
        # Counted now: the next try's new scene takes this body with it.
        results.append((points, inside_body(body, points), drop))
        print(f"fine cloth {fine}: {worst} {fell / CENTIMETRES:+.1f} cm past its limit, a seam open "
              f"{gap / CENTIMETRES:.1f} cm, the top fell {slid / CENTIMETRES:.1f} cm", flush=True)
        limits = task["cloth"]["blender"]
        if fell <= 0 and gap <= limits["open_thread_limit"] and slid <= limits["top_fall_limit"]:
            tries[-1]["kept"] = True
            return points, results[-1][1], tries, True, drop
    least = min(range(len(tries)), key=lambda index: max(tries[index]["past_limit_cm"], tries[index]["open_thread_cm"],
                                      tries[index]["top_fell_cm"]))
    tries[least]["kept"] = True
    return results[least][0], results[least][1], tries, False, results[least][2]


def inside_body(body, points):
    """How many points lie inside the body: the nearest point of the body's surface faces away from them."""
    tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    count = 0
    for point in points:
        nearest, normal, _, _ = tree.find_nearest(point)
        if nearest is not None and (point - np.array(nearest)) @ np.array(normal) < 0:
            count += 1
    return count


def write_result(task, points, record, run, inside):
    """The sewn cloth in GarmentCode's simulation file, and the record of the run beside it."""
    out = pathlib.Path(task["out"])
    out.mkdir(parents=True, exist_ok=True)
    box_text = pathlib.Path(task["box_mesh"]).read_text()
    gaps = sewing.seam_gaps(points, record["box_index"]) / CENTIMETRES
    positions = sewing.merged(points / CENTIMETRES, record["box_index"], sewing.box_point_count(box_text))
    (out / f"{task['name']}_sim.obj").write_text(sewing.sim_obj(box_text, positions))
    report = {"simulator": f"Blender {bpy.app.version_string} cloth", "cloth": task["cloth"], **run,
              "points": len(points), "threads": len(gaps),
              "open_threads_cm": {"median": round(float(np.median(gaps)), 3),
                                  "p99": round(float(np.percentile(gaps, 99)), 3), "max": round(float(gaps.max()), 3)},
              "points_inside_body": inside}
    (out / "blender_cloth.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


def main():
    task = job()
    record = dict(np.load(task["sewing"]))
    coarse = dict(np.load(task["coarse"]))
    sewn, _, tries, held, _ = sewn_and_settled(task, coarse, task["cloth"]["coarse_resolution"])
    start = sewing.carried({**record, "points": record["points"] * CENTIMETRES},
                           {**coarse, "points": coarse["points"] * CENTIMETRES}, sewn)
    points, inside, fine_tries, fine_held, drop = fine_settled(task, record, start)
    # The fine cloth is checked again from where it starts, so it decides: a coarse seam left a little open closes
    # in the fine stage (2026-10-09).
    if not fine_held:
        print("WARNING: the garment did not stay on the body; look at it before using it", flush=True)
    run = {"tries": tries, "coarse_held": held, "fine_tries": fine_tries, "held_on_body": fine_held,
           "waist_lowered_cm": round(drop / CENTIMETRES, 1)}
    write_result(task, points, record, run, inside)


if __name__ == "__main__":
    main()
