"""Runs inside Blender (on a rented machine, cloud/library_bake.py): build a list of code-built kit pieces and bake
them all into one shared picture set (bake.Atlas), one .gltf each beside the shared pictures.

The job: {"out": folder, "atlas": name, "density": px a metre, "wear", "dirt", "seed",
"specs": {library variant: resolved entry}, "pieces": [{"name", "kind", "size", "laid"}]}. Writes
<out>/<name>.gltf (+ .bin), <out>/textures/<atlas>_*.png and <out>/report.json (the atlas's sides, and per piece its
slots, triangles and bounds in the kit frame).

A piece's parts in a material that gives light (a screen's content, a lamp's lens: recipes `screen` and `glowing`) are
split off into a piece of their own, `<name>_glow`, which the game draws glowing (HubKit); the rest of it never glows
(the owner, round two: "glow from the content only").
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402
import bpy  # noqa: E402
import pieces  # noqa: E402
import scene_setup  # noqa: E402

BAKE_SAMPLES = 16
GLOWING_RECIPES = ("screen", "glowing")


def glow_split(item, specs):
    """The piece's glowing parts separated into `<name>_glow`, or None when it has none."""
    glowing = [index for index, name in enumerate(bake.slot_names(item)) if specs[name]["recipe"] in GLOWING_RECIPES]
    if not glowing or len(glowing) == len(item.data.materials):
        return None
    for polygon in item.data.polygons:
        polygon.select = polygon.material_index in glowing
    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    split = next(iter(set(bpy.data.objects) - before))
    split.name = f"{item.name}_glow"
    split.data.name = split.name
    return split


def bounds(item):
    """The piece's box in the kit frame (Blender x, -z, y back), as its low and high corners."""
    points = [(vertex.co.x, vertex.co.z, -vertex.co.y) for vertex in item.data.vertices]
    return [[round(min(point[axis] for point in points), 5) for axis in range(3)],
            [round(max(point[axis] for point in points), 5) for axis in range(3)]]


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    began = time.time()
    scene_setup.empty_scene(256, BAKE_SAMPLES)
    items = []
    for entry in job["pieces"]:
        item = pieces.build(entry["kind"], entry["size"], entry.get("laid", {}), entry["name"])
        glow = glow_split(item, job["specs"])
        items += [item] + ([glow] if glow else [])
    slots = {item.name: bake.slot_names(item) for item in items}
    atlas = bake.Atlas(job["atlas"], items, job["density"])
    for item in items:
        atlas.bake_self(item, job["specs"], job["wear"], job["dirt"], job["seed"])
        print("BAKED", item.name, flush=True)
    atlas.finish()
    report = {"atlas": {"normal": atlas.side, "colour": atlas.pictures["base_color"].size[0],
                        "seconds": round(time.time() - began, 1)}, "pieces": {}}
    for item in items:
        report["pieces"][item.name] = dict(atlas.export(item, out), slots=slots[item.name], bounds=bounds(item))
    (out / job.get("report", "report.json")).write_text(json.dumps(report, indent=1))


main()
