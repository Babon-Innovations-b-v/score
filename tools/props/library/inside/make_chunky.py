"""Runs inside Blender (on a rented machine, cloud/library_bake.py): re-material generated pieces from the library.

The job: {"out", "density", "wear", "dirt", "seed", "specs", "faces": the cut-down copy's triangles,
"chunky": [{"name", "parts": folder of <library material>.ply (labels.py)}]}. Each piece's parts are joined into the
full-detail model, each part's slot named for its material; a copy is cut down to `faces` triangles and the library
is baked from the full model onto it (bake.baked_from), so wear follows the real edges. Writes <out>/<name>.glb and
<out>/report.json.
"""
import json
import pathlib
import sys

import bmesh
import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402
import scene_setup  # noqa: E402
import shapes  # noqa: E402

BAKE_SAMPLES = 16
# How far the bake looks from the cut-down copy for the full model's surface, as a share of the piece's size.
REACH_SHARE = 0.03


def full_model(parts_folder, name):
    """The full-detail model: every material's part imported and joined, its slot named for the material."""
    found = []
    for path in sorted(pathlib.Path(parts_folder).glob("*.ply")):
        bpy.ops.wm.ply_import(filepath=str(path))
        part = bpy.context.selected_objects[0]
        part.data.materials.clear()
        part.data.materials.append(shapes.slot(path.stem))
        found.append(part)
    # glTF's y-up frame, which labels.py wrote in, onto Blender's z-up one, as the glTF importer would
    for part in found:
        part.rotation_euler = (1.5707963267948966, 0.0, 0.0)
    whole = shapes.joined(found, f"{name}_full")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    # The parts come as loose triangles (labels.py keeps the raw model's own vertices); welded, the cut-down copy
    # unwraps into whole islands instead of one island a triangle (the first cloud run baked dots, 2026-10-06).
    welded = bmesh.new()
    welded.from_mesh(whole.data)
    bmesh.ops.remove_doubles(welded, verts=welded.verts, dist=1e-5)
    # Raw Pixal3D faces are not all wound outward; a face wound inward sends the bake's rays away from the model
    # and its picture stays black (run 4, 2026-10-06).
    bmesh.ops.recalc_face_normals(welded, faces=welded.faces)
    welded.to_mesh(whole.data)
    welded.free()
    return whole


def cut_down(whole, faces, name):
    """A copy of the full model with about `faces` triangles."""
    copy = whole.copy()
    copy.data = whole.data.copy()
    copy.name = name
    bpy.context.scene.collection.objects.link(copy)
    change = copy.modifiers.new("cut", "DECIMATE")
    change.ratio = min(1.0, faces / max(1, len(whole.data.polygons)))
    shapes.apply_modifiers(copy)
    return copy


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for entry in job["chunky"]:
        scene_setup.empty_scene(256, BAKE_SAMPLES)
        whole = full_model(entry["parts"], entry["name"])
        low = cut_down(whole, job["faces"], entry["name"])
        reach = max(whole.dimensions) * REACH_SHARE
        report[entry["name"]] = bake.baked_from(whole, low, job["specs"], job["wear"], job["dirt"], job["seed"],
                                                job["density"], reach, out / f"{entry['name']}.glb")
        print("PIECE", entry["name"], json.dumps(report[entry["name"]]), flush=True)
    (out / "report.json").write_text(json.dumps(report, indent=1))


main()
