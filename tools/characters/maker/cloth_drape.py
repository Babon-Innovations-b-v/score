"""Runs inside Blender 4.2 or 5.0 (headless: on the maker's own machine, or through tools/props/cloud/blender_cloud.py):
sew a GarmentCode garment's panels shut round a body and let it hang, then write the cloth as GarmentCode's simulation
wrote it.

    blender -b --python tools/characters/maker/cloth_drape.py -- <job.json>

job.json (written by `drape_garment.py`):
    {"sewing": "<name>_sewing.npz", "coarse": "<name>_coarse_sewing.npz" (optional), "box_mesh": "<name>_boxmesh.obj",
     "body": "ours.obj" (metres, y up), "cloth": {...} the design's cloth.json, "out": "<folder>", "name": "<name>"}

The panels start where GarmentCode laid them round the body, flat and true to the pattern; each seam is a sewing
thread (a loose edge between the two copies of a seam point, `sewing.seams`), which Blender's cloth pulls shut
(sewing springs). Gravity is off while the seams close, as GarmentCode's Warp run held it off for its first steps, then
on while the cloth settles. The body is a collision object; the cloth collides with itself. Everything stays in the
pattern's frame: y up, the body's feet at 0, Blender's gravity along -y.

Sewing round a body is fragile: a pull too hard or too soft drags a torso off the shoulders while its seams close
(2026-10-09). So the garment is sewn coarse first (the "coarse" record, the same pattern at a wider spacing), with each
sewing force of the design tried in turn until no panel sags off the body (`sewn_on_body`), and settled; then the fine
panels are carried onto the sewn coarse cloth (`sewing.carried`) and settle from there, their flat panels as the rest
shape (a rest shape key), so nothing fine is sewn round the body at all. Without a coarse record the fine panels are
sewn and settled the same way directly.

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


def sag(record, points):
    """How far each panel has dropped below where GarmentCode laid it (metres, its points' mean height), by name.

    Sewn with gravity off, a panel that hangs on the body stays about where it was laid; a torso that came off the
    shoulders while its seams closed has dropped down the chest."""
    laid = record["points"] * CENTIMETRES
    return {str(name): float(laid[record["panel"] == number, 1].mean() - points[record["panel"] == number, 1].mean())
            for number, name in enumerate(record["panel_names"])}


def sew(task, record, force, resolution):
    """A scene with the body and the panels (raised, `lifted`), sewn shut with gravity off; the scene, body, cloth,
    the seconds it took and how far each panel sagged."""
    settings, frames = task["cloth"]["blender"], task["cloth"]["frames"]
    scene = empty_scene()
    body = body_object(task["body"], settings)
    cloth = cloth_object(record, lifted(record, settings.get("lift", {})))
    make_cloth(cloth, settings, force, resolution, (frames["sew"], frames["sew"] + frames["gravity_ramp"]))
    seconds = simulate(scene, 1, frames["sew"])
    return scene, body, cloth, seconds, sag(record, cloth_points(cloth))


def attempt(task, record, force, resolution):
    """One try: sewn with gravity off, then, if no panel sagged past the design's limit, settled under gravity and
    checked again (a heavy cloth can slip off a shoulder as it settles); the cloth's points, the body, the try's
    record and whether it held."""
    settings, frames = task["cloth"]["blender"], task["cloth"]["frames"]
    scene, body, cloth, seconds, sagged = sew(task, record, force, resolution)
    worst = max(sagged, key=sagged.get)
    report = {"force": force, "seconds": round(seconds, 1), "worst_panel": worst,
              "sag_cm": round(sagged[worst] / CENTIMETRES, 1)}
    print(f"sewing force {force}: {worst} sagged {sagged[worst] / CENTIMETRES:.1f} cm", flush=True)
    if sagged[worst] > settings["sag_limit"]:
        return cloth_points(cloth), body, report, False
    report["settle_seconds"] = round(simulate(scene, frames["sew"] + 1, frames["sew"] + frames["settle"]), 1)
    points = cloth_points(cloth)
    settled = sag(record, points)
    worst = max(settled, key=settled.get)
    report.update({"settled_worst_panel": worst, "settled_sag_cm": round(settled[worst] / CENTIMETRES, 1)})
    print(f"settled: {worst} sagged {settled[worst] / CENTIMETRES:.1f} cm", flush=True)
    return points, body, report, settled[worst] <= settings["settled_sag_limit"]


def sewn_and_settled(task, record, resolution):
    """The panels sewn on the body and settled, with each sewing force of the design tried in turn until one holds
    (`attempt`); the cloth's points, the body, the record of every try, whether one held, and the force kept. When
    none holds, the try that sagged least is kept."""
    tries, results = [], []
    for force in task["cloth"]["blender"]["sewing_forces"]:
        points, body, report, held = attempt(task, record, force, resolution)
        tries.append(report)
        results.append((points, body))
        if held:
            report["kept"] = True
            return points, body, tries, True, force
    least = min(range(len(tries)), key=lambda index: tries[index].get("settled_sag_cm", tries[index]["sag_cm"]))
    tries[least]["kept"] = True
    print(f"no sewing force kept the garment on the body; force {tries[least]['force']} is kept", flush=True)
    return results[least][0], results[least][1], tries, False, tries[least]["force"]


def settled_from(task, record, start, force):
    """The fine panels started at `start` (carried onto the sewn coarse cloth) and settled under gravity; the cloth's
    points, the body and the seconds it took."""
    settings = task["cloth"]["blender"]
    scene = empty_scene()
    body = body_object(task["body"], settings)
    cloth = cloth_object(record, start)
    make_cloth(cloth, settings, force, task["cloth"]["resolution_scale"], None)
    seconds = simulate(scene, 1, task["cloth"]["frames"]["fine_settle"])
    return cloth_points(cloth), body, seconds


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
    if task.get("coarse"):
        coarse = dict(np.load(task["coarse"]))
        sewn, _, tries, held, force = sewn_and_settled(task, coarse, task["cloth"]["coarse_resolution"])
        start = sewing.carried({**record, "points": record["points"] * CENTIMETRES},
                               {**coarse, "points": coarse["points"] * CENTIMETRES}, sewn)
        points, body, seconds = settled_from(task, record, start, force)
        run = {"tries": tries, "held_on_body": held, "fine_settle_seconds": round(seconds, 1)}
    else:
        points, body, tries, held, _ = sewn_and_settled(task, record, task["cloth"]["resolution_scale"])
        run = {"tries": tries, "held_on_body": held}
    if not held:
        print("WARNING: the garment did not stay on the body while it was sewn; look at it before using it", flush=True)
    write_result(task, points, record, run, inside_body(body, points))


if __name__ == "__main__":
    main()
