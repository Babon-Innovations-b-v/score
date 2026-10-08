"""Runs inside Blender on this PC (geometry only, no bake, no render): a room's code models built from its plan and
written each as a .glb, for the model check before anything is paid for (route.py precheck).
    python3 tools/blender/session.py batch <this> -- <worktree> <plan.json> <out folder> [name,name,...]"""
import json
import pathlib
import sys

ROOT, PLAN, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
ONLY = sys.argv[sys.argv.index("--") + 4].split(",") if len(sys.argv) > sys.argv.index("--") + 4 else None
sys.path.insert(0, f"{ROOT}/tools/props/library/inside")
import bpy  # noqa: E402
import bmesh  # noqa: E402
import pieces  # noqa: E402

LIBRARY = json.load(open(f"{ROOT}/data/library/materials.json"))
GLOWING = {name for family in ("screen", "light") for name in LIBRARY["families"][family]["variants"]}

pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
models = json.load(open(PLAN))["models"]
for name, entry in sorted(models.items()):
    if entry["route"] != "code" or (ONLY and name not in ONLY):
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    item = pieces.build(entry["kind"].split("_", 1)[1], entry["size"], entry.get("laid", {}), name)
    # The glowing parts (screens, lenses) are split off into a model of their own by the bake (make_kit.glow_split):
    # left out here, as the model check judges the piece without them.
    glowing = [index for index, slot in enumerate(item.data.materials) if slot.name.split(".")[0] in GLOWING]
    if glowing:
        mesh = bmesh.new()
        mesh.from_mesh(item.data)
        bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.material_index in glowing], context="FACES")
        mesh.to_mesh(item.data)
        mesh.free()
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.export_scene.gltf(filepath=f"{OUT}/{name}.glb", use_selection=True, export_materials="NONE")
    print("BUILT", name, flush=True)
